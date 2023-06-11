import asyncio
import os
from datetime import datetime
from typing import Union

from loguru import logger

from src.audio_packages import AudioPackages
from src.config import Config
from src.dataclasses.package import Package
from src.unicast_server import UnicastServer


class Manager(object):
    """He runs calls and send messages in rooms"""

    def __init__(self, config: Config):
        self.config: Config = config
        self.queue_packages: list[Package] = []
        self.unicast_server: Union[UnicastServer, None] = None
        self.chans: list[AudioPackages] = []
        self.app = config.app
        self.log = logger.bind(object_id='manager')
        self.audio_packages: dict[str, AudioPackages] = {}

    def __del__(self):
        self.log.debug('object has died')

    async def alive(self):
        while self.config.alive:
            self.log.info(f"alive")
            await asyncio.sleep(60)

    async def start_manager(self):
        self.log.info('start_manager')

        self.unicast_server = UnicastServer(self.config, self.queue_packages)
        self.unicast_server.start()

        while self.config.shutdown is False:

            if len(self.queue_packages) == 0:
                await asyncio.sleep(0.1)
                continue

            package = self.queue_packages.pop(0)

            key_for_dict = f'{package.ssrc}@{package.unicast_host}{package.unicast_port}'
            if key_for_dict not in self.audio_packages:
                audiopackage = AudioPackages(config=self.config,
                                             unicast_host=package.unicast_host,
                                             unicast_port=package.unicast_port)

                self.audio_packages[key_for_dict] = audiopackage

            if key_for_dict in self.audio_packages:
                self.log.info('HEHE HAHA')
                self.log.info(key_for_dict)
                self.audio_packages[key_for_dict].packages.append(package)
                self.log.info(len(self.audio_packages[key_for_dict].packages))

        # full stop app
        self.unicast_server.join()
        self.config.alive = False
        # close FastAPI and our app
        parent_pid = os.getppid()
        current_pid = os.getpid()
        os.kill(parent_pid, 9)
        os.kill(current_pid, 9)
