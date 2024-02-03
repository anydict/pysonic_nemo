from dataclasses import dataclass, field
from datetime import datetime, timedelta
from struct import unpack, pack

from src.config import DEFAULT_SAMPLE_WIDTH


@dataclass
class Package(object):
    em_host: str
    em_port: int
    data: bytes
    csrc_count: int = None
    payload_type: int = None
    seq_num: int = None
    payload: bytes = None
    timestamp: int = None
    ssrc: int = None
    em_address: str = ''
    em_address_ssrc: str = ''
    amplitudes: list = None
    max_amplitude: int = 0
    min_amplitude: int = 0
    wav_bytes: bytes = b''
    lose_time: datetime = field(default_factory=lambda: datetime.now() + timedelta(seconds=5))

    def __post_init__(self):
        self.csrc_count = self.data[0] & 0x0F
        self.payload_type = self.data[1] & 0x7F
        self.seq_num = int.from_bytes(self.data[2:4], byteorder='big', signed=False)
        self.payload: bytes = self.data[12 + (4 * self.csrc_count):]
        self.timestamp: int = int.from_bytes(self.data[4:8], byteorder='big')
        self.ssrc: int = int.from_bytes(self.data[8:12], byteorder='big')
        self.em_address = f"{self.em_host}:{self.em_port}"
        self.em_address_ssrc = f"{self.ssrc}@{self.em_host}:{self.em_port}"

        self.amplitudes = list(unpack(">" + "h" * (len(self.payload) // DEFAULT_SAMPLE_WIDTH), self.payload))

        self.max_amplitude = max(self.amplitudes)
        self.min_amplitude = min(self.amplitudes)

        # big-endian to little-endian for next save wav file
        for amp in self.amplitudes:
            self.wav_bytes += pack('<h', amp)
