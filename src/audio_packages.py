import threading
import time
import wave
from datetime import datetime
from typing import Optional

from loguru import logger

from src.config import Config
from src.dataclasses.package import Package
from struct import unpack, pack
import src.models.http_models as http_models

CODE_ERROR = -9
CODE_AWAIT_ANALISE = -1
CODE_NOT_FOUND = 0

MAX_RTP_SEQ_NUMBER = 65535
AMPLITUDE_THRESHOLD_BEEP = 9999
AMPLITUDE_THRESHOLD_VOICE = 260
AMPLITUDE_THRESHOLD_NOISE = 20

SECONDS_SLEEP_WAIT_PACKAGES = 0.5
SECONDS_FOR_ABSOLUTE_SILENCE = 30
DEFAULT_SAMPLE_WIDTH = 2  # for 16 bit this equal 2


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
        self.druid: str = ''

        self.event_create: Optional[http_models.EventCreate] = None
        self.event_progress: Optional[http_models.EventProgress] = None
        self.event_answer: Optional[http_models.EventAnswer] = None
        self.events_detect: list[http_models.EventDetect] = []
        self.event_destroy: Optional[http_models.EventDestroy] = None

        self.packages_for_analyse: list[Package] = []
        self.analyzed_samples: dict[int, list] = {}
        self.max_amplitude_analyzed_samples: dict[int, int] = {}

        self.break_while_time: str = ''
        self.time_add_first_package: datetime = datetime.now()
        self.time_add_last_package: datetime = datetime.now()

        self.wrap_around_coefficient: int = 1
        self.length_payload = length_payload
        self.seq_num_first_package: int = first_seq_num
        self.seq_num_last_package: int = first_seq_num

        self.seq_num_answer_package: int = CODE_AWAIT_ANALISE
        self.seq_num_first_beep: int = CODE_AWAIT_ANALISE
        self.seq_num_first_noise_after_answer: int = CODE_AWAIT_ANALISE
        self.seq_num_first_voice: int = CODE_AWAIT_ANALISE
        self.flag_absolute_silence: int = 0

        self.log = logger.bind(object_id=f'{em_ssrc}@{em_host}:{em_port}')
        self.log.debug('init AudioPackages')

    def get_sample_width(self) -> int:
        if self.event_create:
            if self.event_create.info.em_sample_width != DEFAULT_SAMPLE_WIDTH:
                self.log.warning('Correct operation with another number is not guaranteed')
            return self.event_create.info.em_sample_width
        else:
            return DEFAULT_SAMPLE_WIDTH

    def append_package_for_analyse(self, package: Package):
        self.time_add_last_package: datetime = datetime.now()

        self.packages_for_analyse.append(package)

    def add_event_create(self, event: http_models.EventCreate):
        self.event_create = event
        self.druid = event.druid

    def add_event_progress(self, event: http_models.EventProgress):
        self.event_progress = event

    def add_event_answer(self, event: http_models.EventAnswer):
        self.event_answer = event
        if self.event_create is not None:
            create_datetime = datetime.fromisoformat(self.event_create.event_time)
            answer_datetime = datetime.fromisoformat(event.event_time)
            duration_before_answer = (answer_datetime - create_datetime).total_seconds()
            duration_one_sample = self.length_payload / self.get_sample_width() / self.event_create.info.em_sample_rate
            number_samples_before_answer = duration_before_answer / duration_one_sample
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
        # This class use threading
        super().start()
        # function self.run in new Thread

    def run(self):
        try:
            while self.break_while_time == '':
                if self.config.alive is False:
                    return

                if self.check_end():
                    self.start_parse()
                    self.break_while_time = datetime.now().isoformat()

                if self.event_create is None:
                    time.sleep(0.3)
                    continue

                self.start_parse()

                if self.seq_num_first_beep < 0:
                    self.seq_num_first_beep = self.find_seq_num_first_beep()

                if self.event_answer is not None:
                    self.seq_num_first_noise_after_answer = self.find_seq_num_first_noise_after_answer()
                    self.seq_num_first_voice = self.find_seq_num_first_voice()
                    self.flag_absolute_silence = self.find_absolute_silence()

                time.sleep(SECONDS_SLEEP_WAIT_PACKAGES)
        except Exception as e:
            self.log.error(e)
            self.log.exception(e)
            return

        self.start_save()

    def check_end(self):
        if self.event_destroy is not None:
            time.sleep(1)
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

        while len(self.packages_for_analyse) > 0:
            package = self.packages_for_analyse.pop(0)
            if package.seq_num < 20 and package.seq_num < self.seq_num_first_package:
                self.wrap_around_coefficient = 1 + round(self.seq_num_last_package / MAX_RTP_SEQ_NUMBER)
                self.log.error(f'FIND wrap_around={self.wrap_around_coefficient}')

            fix_seq_num = self.wrap_around_coefficient * package.seq_num
            self.analyzed_samples[fix_seq_num] = list(unpack(">" + "h" * number_samples, package.payload))
            self.max_amplitude_analyzed_samples[fix_seq_num] = max(self.analyzed_samples[fix_seq_num])

            if self.seq_num_last_package < fix_seq_num:
                self.seq_num_last_package = fix_seq_num

        if len(self.analyzed_samples) == self.seq_num_last_package - self.seq_num_first_package + 1:
            return

        for seq_num in range(self.seq_num_first_package, self.seq_num_last_package):
            if seq_num not in self.analyzed_samples:
                self.log.error(f'Find loss package! {seq_num}')
                self.analyzed_samples[seq_num] = [0] * number_samples
                self.max_amplitude_analyzed_samples[seq_num] = 0

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
        if self.seq_num_first_beep > 0:
            return 0
        elif self.seq_num_first_noise_after_answer > 0:
            return 0
        elif self.seq_num_first_voice > 0:
            return 0
        elif self.flag_absolute_silence > 0:
            return self.flag_absolute_silence

        # TODO find silence seconds

        return 0

    def start_save(self):
        try:
            self.log.info('start_save')

            self.log.info(f' self.seq_num_first_package={self.seq_num_first_package}')
            self.log.info(f'self.seq_num_first_beep={self.seq_num_first_beep}')
            self.log.info(f' self.seq_num_first_noise_after_answer={self.seq_num_first_noise_after_answer}')
            self.log.info(f' self.seq_num_answer_package={self.seq_num_answer_package}')
            self.log.info(f' self.seq_num_first_voice={self.seq_num_first_voice}')
            self.log.info(f' self.seq_num_last_package={self.seq_num_last_package}')
            self.log.info(f' self.flag_absolute_silence={self.flag_absolute_silence}')

            self.log.info(f' len packs={len(self.max_amplitude_analyzed_samples)}')
            self.log.info(f' len raw packs={len(self.packages_for_analyse)}')
            time.sleep(1)

            if len(self.packages_for_analyse) > 0:
                self.log.error(f'len={len(self.packages_for_analyse)}')

            if self.seq_num_last_package - self.seq_num_first_package + 1 != len(self.max_amplitude_analyzed_samples):
                self.log.error('found loss packs')

            if self.event_create is None or self.event_create.info.save_record == 1:
                with wave.open(f'audio{self.em_ssrc}.wav', 'wb') as f:
                    f.setnchannels(1)  # mono
                    f.setsampwidth(2)  # 16-bit
                    f.setframerate(16000)  # 16 kHz

                    for seq_num in self.analyzed_samples:
                        for amp in self.analyzed_samples[seq_num]:
                            data = pack('<h', amp)
                            f.writeframes(data)
        except Exception as exc:
            self.log.error(exc)
            self.log.exception(exc)
