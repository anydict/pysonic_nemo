import socket
import time
from multiprocessing import Queue, Event, Process

from loguru import logger

from src.config import Config
from src.custom_dataclasses.package import Package


class UnicastServer(Process):
    def __init__(self,
                 config: Config,
                 mp_queue: Queue,
                 finish_event: Event):
        Process.__init__(self)
        self.app_name: str = config.app_name
        self.em_host: str = config.app_unicast_host
        self.em_port: int = config.app_unicast_port
        self.unicast_protocol: str = config.app_unicast_protocol
        self.app_unicast_buffer_size: int = config.app_unicast_buffer_size
        self.mp_queue: Queue = mp_queue
        self.finish_event: Event = finish_event
        self.buffer_queue: list[Package] = []
        self.alive_time: time = time.monotonic()
        self.buffer_send_time: time = time.monotonic()
        self.config: Config = config
        self.count_received: int = 0
        self.server_socket = None
        self.log = None

    def start(self) -> None:
        # This class use multiprocessing.Process
        self.log = logger.bind(object_id=self.__class__.__name__)
        super().start()
        # function self.run in new Process

    def send_buffer(self):
        if len(self.buffer_queue) > 0:
            self.mp_queue.put_nowait(self.buffer_queue)
            self.buffer_send_time = time.monotonic()
            self.buffer_queue = []
        if time.monotonic() - self.alive_time > 30:
            self.log.info(f"alive, count_received={self.count_received}")
            self.alive_time = time.monotonic()

    def run(self):
        if self.unicast_protocol.lower() != 'udp':
            self.log.error('only UDP protocol is supported')

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.em_host, self.em_port))
        self.server_socket.settimeout(1)
        self.log.debug(f'socket {self.em_host}:{self.em_port} for receive Unicast packages started')

        while self.finish_event.is_set() is False:
            try:
                try:
                    data, addr = self.server_socket.recvfrom(self.app_unicast_buffer_size)
                    package = Package(addr[0], addr[1], data)
                    self.buffer_queue.append(package)
                    self.count_received += 1

                    if len(self.buffer_queue) > 300 or (time.monotonic() - self.buffer_send_time) > 0.3:
                        self.mp_queue.put_nowait(self.buffer_queue)
                        self.buffer_send_time = time.monotonic()
                        self.buffer_queue = []

                except socket.timeout:
                    self.send_buffer()
                except socket.error as e:
                    self.send_buffer()
                    self.log.error(e)
            except KeyboardInterrupt:
                self.log.info('KeyboardInterrupt')
                break
        self.server_socket.close()
        self.log.info('END WHILE UNICAST')
