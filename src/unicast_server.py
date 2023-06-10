import socket
import threading

from loguru import logger

from src.config import Config


class UnicastServer(threading.Thread):
    def __init__(self, config: Config, queue_packages: list):
        threading.Thread.__init__(self)
        self.app: str = config.app
        self.unicast_host: str = config.app_unicast_host
        self.unicast_port: int = config.app_unicast_port
        self.unicast_protocol: str = config.app_unicast_protocol
        self.app_unicast_buffer_size: int = config.app_unicast_buffer_size
        self.queue_packages: list = queue_packages
        self.config: Config = config
        self.log = logger.bind(object_id='unicast_server')
        self._stop_event = threading.Event()
        self.server_socket = None

    def start(self) -> None:
        # This class use threading
        super().start()
        # function self.run in new Thread

    def stop(self):
        self.log.debug('go stop')
        self._stop_event.set()

    def run(self):
        self.log.debug(f'run UnicastServer on address={self.unicast_host}:{self.unicast_port}')

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.unicast_host, self.unicast_port))
        self.server_socket.settimeout(1)

        while not self._stop_event.is_set():
            try:
                data, addr = self.server_socket.recvfrom(self.app_unicast_buffer_size)
                self.queue_packages.append(data)
                self.log.debug(addr)
                self.log.debug(len(self.queue_packages))
            except socket.timeout:
                pass
            except socket.error as e:
                self.log.error(e)

    # # Configure the UDP socket
    # UDP_IP_ADDRESS = "0.0.0.0"
    # UDP_PORT_NO = 1234
    # server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # server_socket.bind((UDP_IP_ADDRESS, UDP_PORT_NO))
    #
    # # Configure the RTP packet parameters
    # SAMPLE_RATE = 8000
    # SAMPLE_WIDTH = 2
    # CHANNELS = 1
    #
    # # Initialize a list to store RTP packets
    # rtp_packets = []
    #
    # # Receive RTP packets and add them to the list
    # while True:
    #     data, addr = server_socket.recvfrom(1024)
    #     rtp_packets.append(data)
    #
    #     # If enough RTP packets have been received to create a WAV file
    #     if len(rtp_packets) >= 100:
    #
    #         # Concatenate the RTP packets into a byte string
    #         payload = b''.join(rtp_packets)
    #
    #         # Convert the byte string to an AudioSegment object
    #         audio_segment = AudioSegment(
    #             payload,
    #             sample_width=SAMPLE_WIDTH,
    #             frame_rate=SAMPLE_RATE,
    #             channels=CHANNELS
    #         )
    #
    #         # Save the audio to a WAV file
    #         output_file = "output.wav"
    #         audio_segment.export(output_file, format="wav")
    #
    #         # Clear the RTP packet list to receive the next part of the audio
    #         rtp_packets = []
