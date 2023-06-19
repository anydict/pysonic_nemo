import asyncio
import multiprocessing
from datetime import datetime, timedelta
from queue import Empty
from typing import Union

from loguru import logger

from src.audio_packages import AudioPackages
from src.config import Config
from src.dataclasses.package import Package
import src.models.http_models as http_models
from src.unicast_server import UnicastServer


class Manager(object):
    """He runs calls and send messages in rooms"""

    def __init__(self, config: Config):
        self.config: Config = config
        self.queue_packages: list[Package] = []
        self.mp_queue = multiprocessing.Queue()
        self.unicast_server: Union[UnicastServer, None] = None
        self.chans: list[AudioPackages] = []
        self.app = config.app
        self.log = logger.bind(object_id='manager')
        self.audio_packages: dict[str, AudioPackages] = {}
        self.stress_peak: int = 0

    def __del__(self):
        self.log.debug('object has died')

    async def alive(self):
        while self.config.alive:
            self.log.info(f"alive")
            await asyncio.sleep(60)

    async def start_manager(self):
        self.log.info('start_manager')

        self.unicast_server = UnicastServer(self.config, self.mp_queue)

        while self.config.shutdown is False:
            self.queue_packages = []
            try:
                item = self.mp_queue.get_nowait()
                self.queue_packages.extend(item)
            except Empty:
                pass

            len_queue = len(self.queue_packages)

            if len_queue == 0:
                await asyncio.sleep(0.2)
                continue

            if len_queue > self.stress_peak + 5:
                self.stress_peak = len_queue
                self.log.debug(f'update stress peak={self.stress_peak}')

            for package in self.queue_packages:
                ssrc_host_port = f'{package.ssrc}@{package.unicast_host}:{package.unicast_port}'
                if ssrc_host_port not in self.audio_packages:
                    self.log.info(f'New AudioPackages {ssrc_host_port}')
                    audio_packages = AudioPackages(config=self.config,
                                                   em_host=package.unicast_host,
                                                   em_port=package.unicast_port,
                                                   em_ssrc=package.ssrc,
                                                   first_seq_num=package.seq_num,
                                                   length_payload=len(package.payload))
                    audio_packages.start()
                    audio_packages.append_package_for_analyse(package)
                    self.audio_packages[ssrc_host_port] = audio_packages

                elif ssrc_host_port in self.audio_packages:
                    audio_packages = self.audio_packages[ssrc_host_port]
                    audio_packages.append_package_for_analyse(package)
            await asyncio.sleep(0)

    async def start_event_create(self, event: http_models.EventCreate) -> str:
        self.log.info(f'event_name={event.event_name} and druid={event.druid}')
        host_port = f'{event.info.em_host}:{event.info.em_port}'
        em_ssrc = ''
        stop_time = datetime.now() + timedelta(seconds=event.info.em_wait_seconds)

        while em_ssrc == '' and stop_time > datetime.now():
            for ssrc_host_port in self.audio_packages:
                if host_port in ssrc_host_port and self.audio_packages[ssrc_host_port].druid == '':
                    audio_packages = self.audio_packages[ssrc_host_port]
                    audio_packages.add_event_create(event)
                    em_ssrc = audio_packages.em_ssrc
            await asyncio.sleep(0.5)

        if em_ssrc == '':
            self.log.error(f'for druid={event.druid} not found audio_packages')
            self.log.error(f'{event.druid} >> {event.info.em_host}:{event.info.em_port}')

        return em_ssrc

    async def start_event_progress(self, event: http_models.EventProgress) -> bool:
        ssrc_host_port = f'{event.info.em_ssrc}@{event.info.em_host}:{event.info.em_port}'
        self.log.info(f'event_name={event.event_name} and druid={event.druid} ssrc_host_port={ssrc_host_port}')

        if ssrc_host_port in self.audio_packages:
            audio_packages = self.audio_packages[ssrc_host_port]
            audio_packages.add_event_progress(event)
            return True
        else:
            return False

    async def start_event_answer(self, event: http_models.EventAnswer) -> bool:
        ssrc_host_port = f'{event.info.em_ssrc}@{event.info.em_host}:{event.info.em_port}'
        self.log.info(f'event_name={event.event_name} and druid={event.druid} ssrc_host_port={ssrc_host_port}')

        if ssrc_host_port in self.audio_packages:
            audio_packages = self.audio_packages[ssrc_host_port]
            audio_packages.add_event_answer(event)
            return True
        else:
            self.log.error(f'ssrc_host_port={ssrc_host_port} not found')
            return False

    async def start_event_detect(self, event: http_models.EventDetect) -> bool:
        ssrc_host_port = f'{event.info.em_ssrc}@{event.info.em_host}:{event.info.em_port}'
        self.log.info(f'event_name={event.event_name} and druid={event.druid} ssrc_host_port={ssrc_host_port}')

        if ssrc_host_port in self.audio_packages:
            audio_packages = self.audio_packages[ssrc_host_port]
            audio_packages.add_event_detect(event)
            return True
        else:
            return False

    async def start_event_destroy(self, event: http_models.EventDestroy) -> bool:
        ssrc_host_port = f'{event.info.em_ssrc}@{event.info.em_host}:{event.info.em_port}'
        self.log.info(f'event_name={event.event_name} and druid={event.druid} ssrc_host_port={ssrc_host_port}')

        if ssrc_host_port in self.audio_packages:
            audio_packages = self.audio_packages[ssrc_host_port]
            audio_packages.add_event_destroy(event)
            return True
        else:
            return False
