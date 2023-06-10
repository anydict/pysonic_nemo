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

        # run new call until receive "restart" request (see api/routes.py)
        while self.config.shutdown is False:
            if len(self.queue_packages) == 0:
                await asyncio.sleep(0.1)
                continue

            package = self.queue_packages.pop(0)
            # self.log.info(package)

            # lead = self.queue_lead.pop(0)  # get and remove first lead from queue
            # raw_dialplan = self.get_raw_dialplan(lead.dialplan_name)
            # room_config = Config(self.config.join_config)  # Each room has its own Config
            #
            # if self.rooms.get(lead.druid) is not None:
            #     self.log.error(f'Room with druid={lead.druid} already exists')
            # else:
            #     room = Room(ari=self.ari, config=room_config, lead=lead, raw_dialplan=raw_dialplan, app=self.app)
            #     asyncio.create_task(room.start_room())
            #     self.rooms[lead.druid] = room

        # while len(list(self.rooms)) > 0:
        #     await asyncio.sleep(1)

        # full stop app
        self.config.alive = False
        # close FastAPI and our app
        parent_pid = os.getppid()
        current_pid = os.getpid()
        os.kill(parent_pid, 9)
        os.kill(current_pid, 9)
