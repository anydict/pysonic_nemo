from dataclasses import dataclass


@dataclass
class ResultDetection(object):
    template_id: int
    skip_trends: list = None
    first_similar: float = None
    second_similar: float = None
    third_similar: float = None
    amplitude_similar: float = None

    def __post_init__(self):
        self.skip_trends = []

    def add_skip_trend(self, trend: str):
        self.skip_trends.append(trend)

    def set_second_similar(self, similar: float):
        self.second_similar = similar

    def set_third_similar(self, similar: float):
        self.third_similar = similar

    def set_amplitude_similar(self, similar: float):
        self.amplitude_similar = similar
