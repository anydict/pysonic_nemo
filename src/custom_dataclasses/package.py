from dataclasses import dataclass


@dataclass
class Package(object):
    unicast_host: str
    unicast_port: int
    data: bytes

    def __post_init__(self):
        self.csrc_count = self.data[0] & 0x0F
        self.payload_type = self.data[1] & 0x7F
        self.seq_num = int.from_bytes(self.data[2:4], byteorder='big', signed=False)
        self.ssrc: int = int.from_bytes(self.data[8:12], byteorder='big')
        self.payload: bytes = self.data[12 + (4 * self.csrc_count):]
