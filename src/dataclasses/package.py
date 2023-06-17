from dataclasses import dataclass

@dataclass
class Package(object):
    def __init__(self,
                 unicast_host: str,
                 unicast_port: int,
                 data: bytes):
        self.unicast_host: str = unicast_host
        self.unicast_port: int = unicast_port

        self.csrc_count = data[0] & 0x0F
        self.payload_type = data[1] & 0x7F
        self.seq_num = int.from_bytes(data[2:4], byteorder='big', signed=False)
        self.ssrc: int = int.from_bytes(data[8:12], byteorder='big')
        self.payload: bytes = data[12 + (4 * self.csrc_count):]