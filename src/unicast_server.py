import socket
import multiprocessing
import time

from loguru import logger
from src.config import Config
from src.dataclasses.package import Package


class UnicastServer(multiprocessing.Process):
    def __init__(self, config: Config, mp_queue: multiprocessing.Queue):
        multiprocessing.Process.__init__(self)
        self.app: str = config.app
        self.unicast_host: str = config.app_unicast_host
        self.unicast_port: int = config.app_unicast_port
        self.unicast_protocol: str = config.app_unicast_protocol
        self.app_unicast_buffer_size: int = config.app_unicast_buffer_size
        self.mp_queue: multiprocessing.Queue = mp_queue
        self.buffer_queue: list[Package] = []
        self.buffer_clear_time = time.time()
        self.config: Config = config
        self.log = logger.bind(object_id='unicast_server')
        self.server_socket = None
        self.exit = multiprocessing.Event()
        self.start()

    def start(self) -> None:
        # This class use threading
        super().start()
        # function self.run in new Thread

    def kill(self):
        self.log.debug('kill multiprocessing.Process')
        self.exit.set()

    def run(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.unicast_host, self.unicast_port))
        self.server_socket.settimeout(1)
        self.log.debug(f'socket for receive Unicast packages started')

        while self.exit.is_set() is False:
            try:
                data, addr = self.server_socket.recvfrom(self.app_unicast_buffer_size)
                package = Package(addr[0], addr[1], data)
                self.buffer_queue.append(package)

                if (time.time() - self.buffer_clear_time) > 0.2 and len(self.buffer_queue) > 0:
                    self.mp_queue.put_nowait(self.buffer_queue)
                    self.buffer_clear_time = time.time()
                    self.buffer_queue = []

            except socket.timeout:
                if len(self.buffer_queue) > 0:
                    self.mp_queue.put_nowait(self.buffer_queue)
                    self.buffer_clear_time = time.time()
                    self.buffer_queue = []
            except socket.error as e:
                if len(self.buffer_queue) > 0:
                    self.mp_queue.put_nowait(self.buffer_queue)
                    self.buffer_clear_time = time.time()
                    self.buffer_queue = []
                self.log.error(e)
