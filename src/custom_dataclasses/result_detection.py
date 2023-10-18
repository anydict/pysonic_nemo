from dataclasses import dataclass


@dataclass
class ResultDetection(object):
    template_id: int
    skip_trends: list
    first_similar: float = 0
    second_similar: float = 0
    third_similar: float = 0
    amplitude_similar: float = 0

    def add_skip_trend(self, trend: str):
        self.skip_trends.append(trend)

    def set_second_similar(self, similar: float):
        self.second_similar = similar

    def set_third_similar(self, similar: float):
        self.third_similar = similar

    def set_amplitude_similar(self, similar: float):
        self.amplitude_similar = similar
