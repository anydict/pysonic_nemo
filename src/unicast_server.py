import socket
import threading
from datetime import datetime

from loguru import logger
from src.config import Config
from src.dataclasses.package import Package


class UnicastServer(threading.Thread):
    def __init__(self, config: Config, queue_packages: list[Package]):
        threading.Thread.__init__(self)
        self.app: str = config.app
        self.unicast_host: str = config.app_unicast_host
        self.unicast_port: int = config.app_unicast_port
        self.unicast_protocol: str = config.app_unicast_protocol
        self.app_unicast_buffer_size: int = config.app_unicast_buffer_size
        self.queue_packages: list[Package] = queue_packages
        self.config: Config = config
        self.log = logger.bind(object_id='unicast_server')
        self._stop_event = threading.Event()
        self.server_socket = None
        self.peak_packages: int = 0

    def start(self) -> None:
        # This class use threading
        super().start()
        # function self.run in new Thread

    def stop(self):
        self.log.debug('go stop')
        self._stop_event.set()

    def run(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.unicast_host, self.unicast_port))
        self.server_socket.settimeout(1)
        self.log.debug(f'socket for receive Unicast packages started')

        while not self._stop_event.is_set():
            try:
                data, addr = self.server_socket.recvfrom(self.app_unicast_buffer_size)
                package = Package(addr[0], addr[1], data, datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f'))
                self.queue_packages.append(package)
                if len(self.queue_packages) > self.peak_packages + 10:
                    self.peak_packages = len(self.queue_packages)
                    self.log.debug(f'new value for the peak_packages={self.peak_packages}')

            except socket.timeout:
                pass
            except socket.error as e:
                self.log.error(e)
