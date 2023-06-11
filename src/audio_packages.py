import threading
from datetime import datetime

from loguru import logger

from src.config import Config
from src.dataclasses.package import Package


class AudioPackages(threading.Thread):
    def __init__(self,
                 config: Config,
                 unicast_host: str,
                 unicast_port: int,
                 druid: str = ''):
        threading.Thread.__init__(self)
        self.config: Config = config
        self.app: str = config.app
        self.druid: str = druid
        self.unicast_host: str = unicast_host
        self.unicast_port: int = unicast_port
        self.start_unicast_time: str = ''
        self.start_http_time: str = ''
        self.init_time: str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
        self.packages: list[Package] = []
        self.log = logger.bind(object_id='audio_packages')
        self.start()

    def run(self):
        print("Hello from thread", self.init_time)