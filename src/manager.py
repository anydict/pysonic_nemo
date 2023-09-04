import asyncio
from datetime import datetime, timedelta
from queue import Empty

from loguru import logger

from src.audio_packages import AudioPackages
from src.client.callpy_client import CallPyClient
from src.config import Config
from src.dataclasses.package import Package
import src.models.http_models as http_models


class Manager(object):
    """He runs calls and send messages in rooms"""

    def __init__(self, config: Config, mp_queue):
        self.config: Config = config
        self.callpy_clients: dict[str, CallPyClient] = {}
        self.queue_packages: list[Package] = []
        self.mp_queue = mp_queue
        self.chans: list[AudioPackages] = []
        self.app = config.app
        self.log = logger.bind(object_id='manager')
        self.audio_packages: dict[str, AudioPackages] = {}
        self.stress_peak: int = 0

    def __del__(self):
        self.log.debug('object has died')

    def close_session(self):
        self.log.info('start close_session')
        self.config.alive = False
        self.config.shutdown = True

        for callpy_client in self.callpy_clients.values():
            asyncio.create_task(callpy_client.close_session())
        self.log.info('end close_session')

    async def alive(self):
        while self.config.alive:
            self.log.info(f"alive")
            await asyncio.sleep(60)

    async def start_manager(self):
        self.log.info('start_manager')
        while self.config.shutdown is False:
            self.queue_packages: list[Package] = []
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
                    self.log.info(f'New AudioPackages {ssrc_host_port} payload_type={package.payload_type}')
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

        self.log.info('END WHILE MANAGER')

    async def start_event_create(self, event: http_models.EventCreate) -> str:
        self.log.info(f'event_name={event.event_name} and call_id={event.call_id}')
        host_port = f'{event.info.em_host}:{event.info.em_port}'
        em_ssrc = ''
        stop_time = datetime.now() + timedelta(seconds=event.info.em_wait_seconds)

        address = f'{event.info.callback_host}:{event.info.callback_port}'
        if address not in self.callpy_clients:
            self.log.debug('start create callpy_client')
            callpy_client = CallPyClient(event.info.callback_host, event.info.callback_port)
            self.callpy_clients[address] = callpy_client
        else:
            self.log.debug('callpy_client already exists')

        while em_ssrc == '' and stop_time > datetime.now():
            for ssrc_host_port in self.audio_packages:
                if host_port in ssrc_host_port and self.audio_packages[ssrc_host_port].call_id == '':
                    audio_packages = self.audio_packages[ssrc_host_port]
                    audio_packages.add_event_create(event, self.callpy_clients[address])
                    em_ssrc = audio_packages.em_ssrc
            await asyncio.sleep(0.5)

        if em_ssrc == '':
            self.log.error(f'for call_id={event.call_id} not found audio_packages')
            self.log.error(f'{event.call_id} >> {event.info.em_host}:{event.info.em_port}')

        return em_ssrc

    async def start_event_progress(self, event: http_models.EventProgress) -> bool:
        ssrc_host_port = f'{event.info.em_ssrc}@{event.info.em_host}:{event.info.em_port}'
        self.log.info(f'event_name={event.event_name} and call_id={event.call_id} ssrc_host_port={ssrc_host_port}')

        if ssrc_host_port in self.audio_packages:
            audio_packages = self.audio_packages[ssrc_host_port]
            audio_packages.add_event_progress(event)
            return True
        else:
            return False

    async def start_event_answer(self, event: http_models.EventAnswer) -> bool:
        ssrc_host_port = f'{event.info.em_ssrc}@{event.info.em_host}:{event.info.em_port}'
        self.log.info(f'event_name={event.event_name} and call_id={event.call_id} ssrc_host_port={ssrc_host_port}')

        if ssrc_host_port in self.audio_packages:
            audio_packages = self.audio_packages[ssrc_host_port]
            audio_packages.add_event_answer(event)
            return True
        else:
            self.log.error(f'ssrc_host_port={ssrc_host_port} not found')
            return False

    async def start_event_detect(self, event: http_models.EventDetect) -> bool:
        ssrc_host_port = f'{event.info.em_ssrc}@{event.info.em_host}:{event.info.em_port}'
        self.log.info(f'event_name={event.event_name} and call_id={event.call_id} ssrc_host_port={ssrc_host_port}')

        if ssrc_host_port in self.audio_packages:
            audio_packages = self.audio_packages[ssrc_host_port]
            audio_packages.add_event_detect(event)
            return True
        else:
            return False

    async def start_event_destroy(self, event: http_models.EventDestroy) -> bool:
        ssrc_host_port = f'{event.info.em_ssrc}@{event.info.em_host}:{event.info.em_port}'
        self.log.info(f'event_name={event.event_name} and call_id={event.call_id} ssrc_host_port={ssrc_host_port}')

        if ssrc_host_port in self.audio_packages:
            audio_packages = self.audio_packages[ssrc_host_port]
            audio_packages.add_event_destroy(event)
            return True
        else:
            return False
