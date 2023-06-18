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

        self.seconds_sleep_wait_packages: float = 0.5
        self.minimum_packages_for_analyse: int = 25

        self.time_add_first_package: datetime = datetime.now()
        self.time_add_last_package: datetime = datetime.now()

        self.seq_num_first_package: int = first_seq_num
        self.seq_num_last_package: int = first_seq_num
        self.length_payload = length_payload

        self.wrap_around_coefficient: int = 1

        self.first_beep_threshold: int = 9999
        self.first_beep_seq_num: int = -1

        self.first_noise_answer_threshold: int = 90  # config.first_noise_answer_threshold
        self.first_noise_after_answer_time: str = ''

        self.first_voice_threshold: int = 260
        self.first_voice_time: str = ''

        self.seconds_for_absolute_silence: int = 30
        self.flag_absolute_silence: int = 0

        self.log = logger.bind(object_id=f'{em_ssrc}@{em_host}:{em_port}')
        self.log.debug('init AudioPackages')

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

    def add_event_detect(self, event: http_models.EventDetect):
        self.events_detect.append(event)

    def add_event_destroy(self, event: http_models.EventDestroy):
        self.event_destroy = event

    def stop(self):
        self.log.debug('go stop')
        self.config.alive = False

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

                if self.first_beep_seq_num < 0:
                    self.first_beep_seq_num = self.find_first_beep_time()

                if self.event_answer is not None:
                    self.first_noise_after_answer_time = self.find_first_noise_after_answer_time()
                    self.first_voice_time = self.find_first_voice_time()
                    self.flag_absolute_silence = self.find_absolute_silence()

                time.sleep(self.seconds_sleep_wait_packages)
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
        if self.event_create is None:
            self.log.error('event_create not found')
            number_samples = int(self.length_payload / 2)
        else:
            number_samples = int(self.length_payload / self.event_create.info.em_sample_width)

        while len(self.packages_for_analyse) > 0:
            package = self.packages_for_analyse.pop(0)
            if package.seq_num < 20 and package.seq_num < self.seq_num_first_package:
                self.wrap_around_coefficient = 1 + round(self.seq_num_last_package / 65535)
                self.log.error(f'FIND wrap_around={self.wrap_around_coefficient}')

            fix_seq_num = self.wrap_around_coefficient * package.seq_num
            self.analyzed_samples[fix_seq_num] = list(unpack(">" + "h" * number_samples, package.payload))
            self.max_amplitude_analyzed_samples[fix_seq_num] = max(self.analyzed_samples[fix_seq_num])

            if self.seq_num_last_package < fix_seq_num:
                self.seq_num_last_package = fix_seq_num

        # if len(self.analyzed_samples) == self.seq_num_last_package - self.seq_num_first_package + 1:
        #     return

        # for seq_num in range(self.seq_num_first_package, self.seq_num_last_package):
        #     if seq_num not in self.analyzed_samples:
        #         self.log.error(f'Find loss package! {seq_num}')
        #         self.analyzed_samples[seq_num] = [0] * number_samples
        #         self.max_amplitude_analyzed_samples[seq_num] = 0

    def find_first_beep_time(self):
        if self.first_beep_seq_num > 0:
            return self.first_beep_seq_num

        sorted_seq_num = sorted(self.max_amplitude_analyzed_samples)
        for seq_num in sorted_seq_num:
            if self.max_amplitude_analyzed_samples[seq_num] > self.first_beep_threshold:
                self.log.debug(f'find_first_beep_time seq_num={seq_num}')
                return seq_num

        return self.first_beep_seq_num

    def find_first_noise_after_answer_time(self):
        if self.first_noise_after_answer_time != '':
            return self.first_noise_after_answer_time

        if self.event_answer is None:
            return ''

        for seq_num in self.analyzed_samples:
            if self.analyzed_samples[seq_num][0] > 0:
                return datetime.now().isoformat()
        return ''

    def find_first_voice_time(self):
        if self.first_voice_time != '':
            return self.first_voice_time

        for seq_num in self.analyzed_samples:
            if self.analyzed_samples[seq_num][0] > 150:
                return datetime.now().isoformat()
        return ''

    def find_absolute_silence(self):
        if self.first_beep_seq_num > 0:
            return 0
        elif self.first_noise_after_answer_time != '':
            return 0
        elif self.first_voice_time != '':
            return
        elif self.flag_absolute_silence > 0:
            return self.flag_absolute_silence

        return 0

    def start_save(self):
        try:
            self.log.info('start_save')
            self.log.info(f'self.first_beep_seq_num={self.first_beep_seq_num}')
            self.log.info(f' self.seq_num_first_package={self.seq_num_first_package}')
            self.log.info(f' self.seq_num_last_package={self.seq_num_last_package}')
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
