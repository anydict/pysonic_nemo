import threading
import time
from datetime import datetime

from loguru import logger

from src.config import Config
from src.dataclasses.package import Package


class AudioPackages(threading.Thread):
    def __init__(self,
                 config: Config,
                 unicast_host: str,
                 unicast_port: int,
                 ssrc_host_port: str,
                 unicast_codec: str = '',
                 druid: str = ''):
        threading.Thread.__init__(self)
        self.config: Config = config
        self.app: str = config.app
        self.druid: str = druid
        self.unicast_host: str = unicast_host
        self.unicast_port: int = unicast_port
        self.ssrc_host_port: str = ssrc_host_port
        self.unicast_codec: str = unicast_codec
        self.start_unicast_time: str = ''
        self.start_http_time: str = ''
        self.stop_http_time: str = ''
        self.init_time: str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
        self.packages_for_analyse: list[Package] = []
        self.packages_already_analysed: list[Package] = []

        self.samples_with_int_type: list[int] = []

        self.time_sleep_wait_packages: float = 0.5
        self.minimum_packages_for_analyse: int = 25

        self.first_package_time: str = ''
        self.first_beep_time: str = ''

        self.first_noise_answer_threshold: int = 90 # config.first_noise_answer_threshold
        self.first_noise_after_answer_time: str = ''

        self.first_voice_time: str = ''
        self.first_voice_threshold: int = 260

        self.seconds_for_absolute_silence: int = 30
        self.flag_absolute_silence: int = 0

        self.log = logger.bind(object_id=ssrc_host_port)

        self.start()

    def append_package_for_analyse(self, package: Package):
        self.packages_for_analyse.append(package)

    def add_http_chan_info(self, druid: str, unicast_codec: str):
        self.druid = druid
        self.unicast_codec = unicast_codec

    def run(self):
        while self.config.alive:
            if self.stop_http_time != '':
                break
            time.sleep(self.time_sleep_wait_packages)

            if self.first_package_time == '':
                self.first_package_time = self.get_first_package_time(self.packages_for_analyse[0])

            if len(self.packages_for_analyse) < self.minimum_packages_for_analyse:
                time.sleep(self.time_sleep_wait_packages)
                if len(self.packages_for_analyse) < self.minimum_packages_for_analyse:
                    self.log.info('No found new package go end')
                    break

            self.parse_packages()

            if self.first_beep_time == '':
                self.first_beep_time = self.find_first_beep_time()

            if self.first_noise_after_answer_time == '':
                self.first_noise_after_answer_time = self.find_first_noise_after_answer_time()

            if self.first_voice_time == '':
                self.first_voice_time = self.find_first_voice_time()

            if self.flag_absolute_silence == 0 and self.first_noise_after_answer_time == '':
                self.flag_absolute_silence = self.find_absolute_silence()


    def parse_packages(self):
        timestamp_int = 0
        while len(self.packages_for_analyse) > 0:
            package = self.packages_for_analyse.pop(0)
            csrc_count = package.data[0] & 0x0F
            payload = package.data[12 + (4 * csrc_count):]

            timestamp_bytes = package.data[4:8]
            timestamp_int = int.from_bytes(timestamp_bytes, byteorder='big')


            for i in range(0, len(payload), 2):
                self.samples_with_int_type.append(int.from_bytes(payload[i:i + 2], byteorder='big', signed=True))
            # sample = int.from_bytes(package[i:16], byteorder='little', signed=True)
        self.log.info(len(self.samples_with_int_type))
        self.log.info(timestamp_int)


    def get_first_package_time(self, package: Package):
        timestamp_bytes = package.data[4:8]
        timestamp_int = int.from_bytes(timestamp_bytes, byteorder='big')
        timestamp_datetime = datetime.fromtimestamp(timestamp_int)
        self.log.info(timestamp_datetime)
        self.log.info(timestamp_int)
        return timestamp_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')


    def find_first_beep_time(self):
        pass
        return ''

    def find_first_noise_after_answer_time(self):
        pass
        return ''

    def find_first_voice_time(self):
        pass
        return ''

    def find_absolute_silence(self):
        pass
        return 0
