from dataclasses import dataclass


@dataclass
class Package(object):
    def __init__(self,
                 unicast_host: str,
                 unicast_port: int,
                 data: bytes,
                 receive_time: str):
        self.unicast_host: str = unicast_host
        self.unicast_port: int = unicast_port
        self.data: bytes = data
        self.receive_time: str = receive_time
        self.ssrc: int = int.from_bytes(data[8:12], byteorder='big')

        self.druid: str = ''
        self.sample_rate: int = 0
        self.sample_width: int = 0
        self.byte_rate: int = 0
        self.channels: int = 0
        self.payload: bytes = b''


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
