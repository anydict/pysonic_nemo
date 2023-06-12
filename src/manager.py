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

            ssrc_host_port = f'{package.ssrc}@{package.unicast_host}:{package.unicast_port}'
            if ssrc_host_port not in self.audio_packages:
                audio_packages = AudioPackages(config=self.config,
                                               unicast_host=package.unicast_host,
                                               unicast_port=package.unicast_port,
                                               ssrc_host_port=ssrc_host_port)

                self.audio_packages[ssrc_host_port] = audio_packages

            if ssrc_host_port in self.audio_packages:
                audio_packages = self.audio_packages[ssrc_host_port]
                audio_packages.append_package_for_analyse(package)
