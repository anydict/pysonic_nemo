import threading
import time
import wave
from datetime import datetime
from typing import Optional

from loguru import logger

from src.client.callpy_client import CallPyClient
from src.config import Config
from src.dataclasses.package import Package
from struct import unpack, pack
import src.models.http_models as http_models

CODE_ERROR = -9
CODE_AWAIT_ANALISE = -1
CODE_NOT_FOUND = 0

SEQ_NUMBER_AFTER_FIRST_RESET = 65535
AMPLITUDE_THRESHOLD_BEEP = 9999
AMPLITUDE_THRESHOLD_VOICE = 270
AMPLITUDE_THRESHOLD_NOISE = 20

SECONDS_SLEEP_WAIT_PACKAGES = 0.5
SECONDS_FOR_ABSOLUTE_SILENCE = 30
DEFAULT_SAMPLE_WIDTH = 2  # for 16 bit this equal 2
DEFAULT_SAMPLE_RATE = 16000  # 16k kHz


class AudioPackages(threading.Thread):
    def __init__(self,
                 config: Config,
                 em_host: str,
                 em_port: int,
                 em_ssrc: int,
                 first_seq_num: int,
                 length_payload: int
                 ):
        threading.Thread.__init__(self)
        self.config: Config = config
        self.app: str = config.app
        self.em_host: str = em_host
        self.em_port: int = em_port
        self.em_ssrc: int = em_ssrc
        self.call_id: str = ''

        self.event_create: Optional[http_models.EventCreate] = None
        self.event_progress: Optional[http_models.EventProgress] = None
        self.event_answer: Optional[http_models.EventAnswer] = None
        self.events_detect: list[http_models.EventDetect] = []
        self.event_destroy: Optional[http_models.EventDestroy] = None

        self.callpy_client: Optional[CallPyClient] = None

        self.packages_for_analyse: list[Package] = []
        self.bytes_samples: dict[int, bytes] = {}
        self.analyzed_samples: dict[int, list] = {}
        self.max_amplitude_analyzed_samples: dict[int, int] = {}
        self.min_amplitude_analyzed_samples: dict[int, int] = {}

        self.break_while_time: str = ''
        self.time_add_first_package: datetime = datetime.now()
        self.time_add_last_package: datetime = datetime.now()

        self.number_resets_sequence: int = 0
        self.length_payload = length_payload
        self.seq_num_first_package: int = first_seq_num
        self.seq_num_last_package: int = first_seq_num

        self.seq_num_answer_package: int = CODE_AWAIT_ANALISE
        self.seq_num_first_beep: int = CODE_AWAIT_ANALISE
        self.seq_num_first_noise_after_answer: int = CODE_AWAIT_ANALISE
        self.seq_num_first_voice: int = CODE_AWAIT_ANALISE
        self.amp_adc_noise: int = CODE_AWAIT_ANALISE
        self.flag_absolute_silence: int = 0

        self.log = logger.bind(object_id=f'{em_ssrc}@{em_host}:{em_port}')
        self.log.info(f'init AudioPackages length_payload={length_payload} first_seq_num={first_seq_num}')

    def get_sample_width(self) -> int:
        if self.event_create:
            if self.event_create.info.em_sample_width != DEFAULT_SAMPLE_WIDTH:
                self.log.warning('Correct work with another sample_width is not guaranteed')
            return self.event_create.info.em_sample_width
        else:
            return DEFAULT_SAMPLE_WIDTH

    def get_sample_rate(self) -> int:
        if self.event_create:
            if self.event_create.info.em_sample_rate != DEFAULT_SAMPLE_RATE:
                self.log.warning('Correct work with another sample_rate is not guaranteed')
            return self.event_create.info.em_sample_rate
        else:
            return DEFAULT_SAMPLE_RATE

    def get_duration_one_sample(self):
        return self.length_payload / self.get_sample_width() / self.get_sample_rate()

    def append_package_for_analyse(self, package: Package):
        self.time_add_last_package: datetime = datetime.now()

        self.packages_for_analyse.append(package)

    def add_event_create(self, event: http_models.EventCreate, callpy_client: CallPyClient):
        self.event_create = event
        self.callpy_client = callpy_client
        self.call_id = event.call_id
        self.log.info(f'sample_rate={event.info.em_sample_rate} and sample_width={event.info.em_sample_width}')

    def add_event_progress(self, event: http_models.EventProgress):
        self.event_progress = event

    def add_event_answer(self, event: http_models.EventAnswer):
        self.event_answer = event
        if self.event_create is not None:
            create_datetime = datetime.fromisoformat(self.event_create.event_time)
            answer_datetime = datetime.fromisoformat(event.event_time)
            duration_before_answer = (answer_datetime - create_datetime).total_seconds()
            number_samples_before_answer = duration_before_answer / self.get_duration_one_sample()
            self.seq_num_answer_package: int = int(self.seq_num_first_package + number_samples_before_answer)
        else:
            self.log.error('event_create not found!')

    def add_event_detect(self, event: http_models.EventDetect):
        self.events_detect.append(event)

    def add_event_destroy(self, event: http_models.EventDestroy):
        self.event_destroy = event

    def stop(self):
        self.log.debug('go stop')
        self.config.alive = False

    def start(self) -> None:
        # This class use threading (see function self.run)
        super().start()

    def run(self):
        try:
            while True:
                if self.config.alive is False:
                    return

                if self.check_end() and len(self.packages_for_analyse) == 0:
                    self.start_parse()
                    self.break_while_time = datetime.now().isoformat()
                    break

                if self.event_create is None:
                    time.sleep(0.3)
                    continue

                self.start_parse()

                if self.seq_num_first_beep == CODE_AWAIT_ANALISE:
                    self.seq_num_first_beep = self.find_seq_num_first_beep()
                    self.amp_adc_noise = self.find_amp_adc_noise()

                if self.event_answer is not None:
                    self.seq_num_first_noise_after_answer = self.find_seq_num_first_noise_after_answer()
                    self.seq_num_first_voice = self.find_seq_num_first_voice()
                    self.flag_absolute_silence = self.find_absolute_silence()

                if len(self.packages_for_analyse) == 0:
                    time.sleep(SECONDS_SLEEP_WAIT_PACKAGES)
        except Exception as e:
            self.log.error(e)
            self.log.exception(e)
            return

        self.start_save()

    def check_end(self):
        if self.event_destroy is not None:
            time.sleep(2)
            return True

        elif (datetime.now() - self.time_add_last_package).total_seconds() > 10:
            self.log.error('new packages are not received and event_destroy not found')
            return True

        elif (datetime.now() - self.time_add_first_package).total_seconds() > 2 * 60 * 60:
            self.log.error('the call is too long')
            return True

        else:
            return False

    def start_parse(self):

        number_samples = int(self.length_payload / self.get_sample_width())
        parse_packages = []
        for _ in range(min(len(self.packages_for_analyse), 50)):
            parse_packages.append(self.packages_for_analyse.pop(0))

        for package in parse_packages:
            fix_seq_num = package.seq_num

            # find reset sequence package number
            if package.seq_num < self.seq_num_first_package and package.seq_num <= 50:
                self.number_resets_sequence = round(self.seq_num_last_package / SEQ_NUMBER_AFTER_FIRST_RESET)
                fix_seq_num = package.seq_num + self.number_resets_sequence * SEQ_NUMBER_AFTER_FIRST_RESET
            elif package.seq_num > 50:
                fix_seq_num = package.seq_num + self.number_resets_sequence * SEQ_NUMBER_AFTER_FIRST_RESET

            self.analyzed_samples[fix_seq_num] = list(unpack(">" + "h" * number_samples, package.payload))

            self.bytes_samples[fix_seq_num] = b''
            for amp in self.analyzed_samples[fix_seq_num]:
                self.bytes_samples[fix_seq_num] += pack('<h', amp)

            self.max_amplitude_analyzed_samples[fix_seq_num] = max(self.analyzed_samples[fix_seq_num])
            self.min_amplitude_analyzed_samples[fix_seq_num] = min(self.analyzed_samples[fix_seq_num])

            if self.seq_num_last_package < fix_seq_num:
                self.seq_num_last_package = fix_seq_num

        if len(self.packages_for_analyse) > 100:
            self.log.warning(f'find delay!!! packages_for_analyse={len(self.packages_for_analyse)}')

        if len(self.analyzed_samples) == self.seq_num_last_package - self.seq_num_first_package + 1:
            return

        for seq_num in range(self.seq_num_first_package, self.seq_num_last_package):
            lost_sequences = []
            if seq_num not in self.analyzed_samples:
                lost_sequences.append(seq_num)
                self.analyzed_samples[seq_num] = [0] * number_samples
                self.max_amplitude_analyzed_samples[seq_num] = 0
            if len(lost_sequences) > 0:
                self.log.error(f'lost_sequences={lost_sequences} last={self.seq_num_last_package}')

    def find_seq_num_first_beep(self):
        if self.seq_num_first_beep != CODE_AWAIT_ANALISE:
            return self.seq_num_first_beep

        sorted_seq_num = sorted(self.max_amplitude_analyzed_samples)
        for seq_num in sorted_seq_num:
            if self.event_answer and seq_num >= self.seq_num_answer_package:
                self.log.warning(f'find answer, but not found beep!')
                return CODE_NOT_FOUND
            if self.max_amplitude_analyzed_samples[seq_num] > AMPLITUDE_THRESHOLD_BEEP:
                self.log.debug(f'find_first_beep_time seq_num={seq_num}')
                return seq_num

        return self.seq_num_first_beep

    def find_amp_adc_noise(self):
        if self.amp_adc_noise > 0:
            return self.amp_adc_noise
        elif self.seq_num_first_beep > 0:
            return CODE_NOT_FOUND
        elif self.event_answer is not None:
            return CODE_NOT_FOUND

        for seq_num in self.analyzed_samples:
            max_amp = self.max_amplitude_analyzed_samples[seq_num]
            min_amp = self.min_amplitude_analyzed_samples[seq_num]

            if abs(max_amp) < AMPLITUDE_THRESHOLD_NOISE or abs(min_amp) < AMPLITUDE_THRESHOLD_NOISE:
                continue
            elif max_amp - min_amp > AMPLITUDE_THRESHOLD_BEEP:
                return CODE_NOT_FOUND
            elif 0.8 < min_amp / max_amp < 1.25:
                avg = sum(self.analyzed_samples) / len(self.analyzed_samples)
                self.log.debug(f'found ADC noise min_amp={min_amp} and max_amp={max_amp} avg={avg}')
                return avg

        return self.amp_adc_noise

    def find_seq_num_first_noise_after_answer(self):
        if self.seq_num_first_noise_after_answer != CODE_AWAIT_ANALISE:
            return self.seq_num_first_noise_after_answer

        if self.event_answer is None:
            return self.seq_num_first_noise_after_answer

        sorted_seq_num = sorted(self.max_amplitude_analyzed_samples)
        for seq_num in sorted_seq_num:
            if seq_num < self.seq_num_answer_package:
                continue

            if self.max_amplitude_analyzed_samples[seq_num] > AMPLITUDE_THRESHOLD_NOISE:
                return seq_num
        return self.seq_num_first_noise_after_answer

    def find_seq_num_first_voice(self):
        if self.seq_num_first_voice != CODE_AWAIT_ANALISE:
            return self.seq_num_first_voice

        sorted_seq_num = sorted(self.max_amplitude_analyzed_samples)
        for seq_num in sorted_seq_num:
            if seq_num < self.seq_num_answer_package:
                continue

            if self.max_amplitude_analyzed_samples[seq_num] > AMPLITUDE_THRESHOLD_VOICE:
                return seq_num

        return self.seq_num_first_voice

    def find_absolute_silence(self):
        if self.flag_absolute_silence > 0:
            return self.flag_absolute_silence
        elif self.seq_num_first_beep > 0:
            return 0
        elif self.seq_num_first_noise_after_answer > 0:
            return 0
        elif self.seq_num_first_voice > 0:
            return 0

        current_duration = len(self.analyzed_samples) * self.get_duration_one_sample()
        if current_duration < 30:
            return 0

        if max(self.max_amplitude_analyzed_samples) < AMPLITUDE_THRESHOLD_NOISE:
            self.log.error('FOUND SILENCE')
            return 1

        return 0

    def start_save(self):
        try:
            self.log.info('start_save')

            self.log.info(f' self.seq_num_first_package={self.seq_num_first_package}')
            self.log.info(f' self.seq_num_first_beep={self.seq_num_first_beep}')
            self.log.info(f' self.seq_num_first_noise_after_answer={self.seq_num_first_noise_after_answer}')
            self.log.info(f' self.seq_num_answer_package={self.seq_num_answer_package}')
            self.log.info(f' self.seq_num_first_voice={self.seq_num_first_voice}')
            self.log.info(f' self.seq_num_last_package={self.seq_num_last_package}')
            self.log.info(f' self.flag_absolute_silence={self.flag_absolute_silence}')
            self.log.info(f' self.get_sample_rate={self.get_sample_rate()}')
            self.log.info(f' self.get_sample_width={self.get_sample_width()}')
            self.log.info(f' self.get_duration_one_sample={self.get_duration_one_sample()}')
            self.log.info(f' self.amp_adc_noise={self.amp_adc_noise}')

            self.log.info(f' len packs={len(self.max_amplitude_analyzed_samples)}')
            self.log.info(f' len raw packs={len(self.packages_for_analyse)}')
            time.sleep(1)

            if len(self.packages_for_analyse) > 0:
                self.log.error(f'len={len(self.packages_for_analyse)}')

            if self.seq_num_last_package - self.seq_num_first_package + 1 != len(self.max_amplitude_analyzed_samples):
                self.log.error('found loss packs')

            if self.event_create is None or self.event_create.info.save_record == 1:
                with wave.open(f'audio_two{self.em_ssrc}.wav', 'wb') as f:
                    f.setnchannels(1)  # mono
                    f.setsampwidth(self.get_sample_width())
                    f.setframerate(self.get_sample_rate())

                    df = datetime.now()
                    for data in self.bytes_samples.values():
                        f.writeframes(data)

                    self.log.info('f2')
                    self.log.info(datetime.now() - df)

        except Exception as exc:
            self.log.error(exc)
            self.log.exception(exc)
