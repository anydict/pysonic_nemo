import asyncio
import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from multiprocessing import Queue, Event
from queue import Empty

from loguru import logger

import src.custom_models.http_models as http_models
from src.audio_container import AudioContainer
from src.config import Config
from src.custom_dataclasses.package import Package
from src.detector import Detector
from src.http_clients.callpy_client import CallPyClient


class Manager(object):
    """He runs calls and send messages in rooms"""

    def __init__(self,
                 config: Config,
                 mp_queue: Queue,
                 ppe: ProcessPoolExecutor,
                 tpe: ThreadPoolExecutor,
                 finish_event: Event):
        self.config: Config = config
        self.mp_queue = mp_queue
        self.ppe: ProcessPoolExecutor = ppe
        self.tpe: ThreadPoolExecutor = tpe
        self.finish_event: Event = finish_event

        self.callpy_clients: dict[str, CallPyClient] = {}
        self.packages_queue: list[Package] = []
        self.log = logger.bind(object_id=self.__class__.__name__)

        self.em_address_ssrc_with_chan_id: dict[str, str] = {}  # {em_address_ssrc: chan_id}
        self.em_address_wait_ssrc: dict[str, str] = {}  # {em_address: chan_id}
        self.audio_containers: dict[str, AudioContainer] = {}
        self.stress_peak: int = 0
        self.alloc_times: list[float] = []

    def __del__(self):
        # DO NOT USE loguru here: https://github.com/Delgan/loguru/issues/712
        if self.config.console_log:
            print('Manager object has died')

    async def close_session(self):
        self.log.info('start close_session')
        self.config.alive = False
        self.config.wait_shutdown = True
        self.finish_event.set()
        self.ppe.shutdown()

        for callpy_client in self.callpy_clients.values():
            await callpy_client.close_session()

        for key in list(self.audio_containers.keys()):
            self.log.info(f'unbind {key}')
            self.audio_containers.pop(key)
        self.log.info('end close_session')
        await asyncio.sleep(4)

    async def smart_sleep(self, delay: int):
        for sec in range(0, delay):
            if self.config.alive:
                await asyncio.sleep(1)

    async def alive(self):
        while self.config.alive:
            self.log.info(f"alive")
            await self.smart_sleep(60)

    async def save_result_into_db(self):
        while self.config.alive:
            self.log.info(f"save_result_into_db")
            await self.smart_sleep(60)

    async def start_manager(self):
        self.log.info('start_manager')

        detector = Detector(config=self.config,
                            audio_containers=self.audio_containers,
                            ppe=self.ppe,
                            tpe=self.tpe)
        await detector.start_detection()

        asyncio.create_task(self.alive())
        asyncio.create_task(self.start_allocate())
        asyncio.create_task(self.save_result_into_db())

        try:
            while self.config.wait_shutdown is False:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.log.warning('asyncio.CancelledError')

        await asyncio.sleep(1.1)

        self.log.info('start_dialer is end, go kill application')

        # close FastAPI and our application
        self.config.alive = False
        current_pid = os.getpid()
        os.kill(current_pid, 9)

    async def start_allocate(self):
        self.log.info('start_allocate')

        package_wait_chan_id = []
        while self.config.wait_shutdown is False:
            await asyncio.sleep(0)
            try:
                self.packages_queue: list[Package] = self.mp_queue.get_nowait()
            except Empty:
                self.packages_queue: list[Package] = []
                await asyncio.sleep(0.2)

            t1 = time.monotonic()

            if package_wait_chan_id:
                self.packages_queue.extend(package_wait_chan_id)
                package_wait_chan_id.clear()

            len_queue = len(self.packages_queue)
            if len_queue > self.stress_peak + 99:
                self.stress_peak = len_queue
                self.log.debug(f'update stress peak={self.stress_peak}')
            elif len_queue > 0:
                self.stress_peak = max(0, self.stress_peak - 1)
            else:
                await asyncio.sleep(0.1)
                continue

            self.packages_queue.sort(key=lambda p: p.seq_num, reverse=False)

            lose_packages = 0
            for package in self.packages_queue:
                if package.em_address_ssrc in self.em_address_ssrc_with_chan_id:
                    chan_id = self.em_address_ssrc_with_chan_id[package.em_address_ssrc]
                    if chan_id in self.audio_containers:
                        audio_container = self.audio_containers[chan_id]
                        audio_container.append_package_for_analyse(package)
                elif package.em_address in self.em_address_wait_ssrc:
                    chan_id = self.em_address_wait_ssrc.pop(package.em_address)
                    self.em_address_ssrc_with_chan_id[package.em_address_ssrc] = chan_id
                    if chan_id in self.audio_containers:
                        audio_container = self.audio_containers[chan_id]
                        audio_container.append_package_for_analyse(package)
                elif datetime.now() < package.lose_time:
                    package_wait_chan_id.append(package)
                else:
                    lose_packages += 1

            if lose_packages > 0:
                self.log.warning(f"lose_packages: {lose_packages}")

            self.alloc_times.append(time.monotonic() - t1)
            if self.alloc_times[-1] > 1:
                self.log.warning(f"Huge alloc_time: {self.alloc_times[-1]}")
            elif len(self.alloc_times) > 400:
                self.log.info(f"avg_alloc_time={self.alloc_times}/{len(self.alloc_times)} "
                              f"max_alloc_time={max(self.alloc_times)}")
                self.alloc_times.clear()

        self.log.info('END WHILE MANAGER')

    async def start_event_create(self, event: http_models.EventCreate) -> bool:
        em_address = f'{event.info.em_host}:{event.info.em_port}'
        self.log.info(f'event_name={event.event_name} and call_id={event.call_id} em_address={em_address}')

        callback_address = f'{event.info.callback_host}:{event.info.callback_port}'

        if callback_address not in self.callpy_clients:
            self.log.debug('start create callpy_client')
            callpy_client = CallPyClient(event.info.callback_host, event.info.callback_port)
            self.callpy_clients[callback_address] = callpy_client
        else:
            self.log.debug(f'callpy_client {callback_address} already exists')

        callpy_client = self.callpy_clients[callback_address]
        self.em_address_wait_ssrc[em_address] = event.chan_id
        self.audio_containers[event.chan_id] = AudioContainer(config=self.config,
                                                              em_host=event.info.em_host,
                                                              em_port=event.info.em_port,
                                                              call_id=event.call_id,
                                                              chan_id=event.chan_id,
                                                              event_create=event,
                                                              callpy_client=callpy_client,
                                                              tpe=self.tpe)

        return True

    async def start_event_progress(self, event: http_models.EventProgress) -> bool:
        self.log.info(f'event_name={event.event_name} and call_id={event.call_id}')

        for _ in range(0, 5):
            if event.chan_id in self.audio_containers:
                self.audio_containers[event.chan_id].add_event_progress(event)
                return True
            else:
                await asyncio.sleep(0.2)

        self.log.error(f'chan_id={event.chan_id} not found')
        return False

    async def start_event_answer(self, event: http_models.EventAnswer) -> bool:
        self.log.info(f'event_name={event.event_name} and call_id={event.call_id}')

        for _ in range(0, 5):
            if event.chan_id in self.audio_containers:
                self.audio_containers[event.chan_id].add_event_answer(event)
                return True
            else:
                await asyncio.sleep(0.2)

        self.log.error(f'chan_id={event.chan_id} not found')
        return False

    async def start_event_detect(self, event: http_models.EventDetect) -> bool:
        self.log.info(f'event_name={event.event_name} and call_id={event.call_id}')

        for _ in range(0, 5):
            if event.chan_id in self.audio_containers:
                self.audio_containers[event.chan_id].add_event_detect(event)
                return True
            else:
                await asyncio.sleep(0.2)

        self.log.error(f'chan_id={event.chan_id} not found')
        return False

    async def start_event_destroy(self, event: http_models.EventDestroy) -> bool:
        self.log.info(f'event_name={event.event_name} and call_id={event.call_id}')

        for _ in range(0, 5):
            if event.chan_id in self.audio_containers:
                self.audio_containers[event.chan_id].add_event_destroy(event)
                return True
            else:
                await asyncio.sleep(0.2)

        self.log.error(f'chan_id={event.chan_id} not found')
        return False
