import asyncio
import os
from typing import Union

from loguru import logger

from src.config import Config
from src.unicast_server import UnicastServer


class Manager(object):
    """He runs calls and send messages in rooms"""

    def __init__(self, config: Config, app: str):
        self.config: Config = config
        self.queue_packages = []
        self.unicast_server: Union[UnicastServer, None] = None
        self.app = app
        self.log = logger.bind(object_id='manager')

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

        # full stop app
        self.unicast_server.join()
        self.config.alive = False
        # close FastAPI and our app
        parent_pid = os.getppid()
        current_pid = os.getpid()
        os.kill(parent_pid, 9)
        os.kill(current_pid, 9)
