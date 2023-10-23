from dataclasses import dataclass


@dataclass
class ResultDetection(object):
    template_id: int
    template_name: str
    skip_trends: list = None
    first_similar: float = None
    second_similar: float = None
    third_similar: float = None
    fourth_similar: float = None
    final_similar: float = None

    def __post_init__(self):
        self.skip_trends = []

    def add_skip_trend(self, trend: str):
        self.skip_trends.append(trend)

    def set_second_similar(self, similar: float):
        self.second_similar = similar

    def set_third_similar(self, similar: float):
        self.third_similar = similar

    def set_fourth_similar(self, similar: float):
        self.fourth_similar = similar

    def set_final_similar(self, similar: float):
        self.final_similar = similar
