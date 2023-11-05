import os.path
import pathlib
import statistics
from dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import use


@dataclass
class FingerPrint(object):
    print_name: str
    arr2d: np.array
    hashes_offsets: dict[str, int] = None
    first_points: dict[str, tuple[int, int]] = None
    second_points: dict[str, tuple[int, int]] = None

    def __post_init__(self):
        self.hashes_offsets: dict[str, int] = {}
        self.first_points: dict[str, tuple[int, int]] = dict()
        self.second_points: dict[str, tuple[int, int]] = dict()

    def add_hash_offset(self, _hash: str, offset: int):
        self.hashes_offsets[_hash] = offset

    def add_first_points(self, _hash, x, y):
        self.first_points[_hash] = (x, y)

    def add_second_points(self, _hash, x, y):
        self.second_points[_hash] = (x, y)

    def save_print2png(self, print_name: str, print_folder: str = 'fingerprint_template'):
        if len(self.first_points) == 0:
            return

        pathlib.Path(print_folder).mkdir(parents=True, exist_ok=True)
        full_path = os.path.join(print_folder, f"{print_name}.png")

        use('agg')
        fig, ax = plt.subplots()
        ax.set_title('specgram')
        ax.set_aspect(0.1)
        ax.pcolor(self.arr2d)

        a_points = set(self.first_points.values())
        b_points = set(self.second_points.values())
        x, y = zip(*a_points.union(b_points))
        ax.scatter(x, y)

        fig.savefig(full_path)
        plt.close(fig)

    @staticmethod
    def get_timely_hashes(source_hashes_offsets: dict[str, int],
                          correct_hashes_offsets: dict[str, int]) -> tuple[dict[str, int], int]:
        hashes_diff_offset: dict[str, int] = {}
        for s_hash, s_offset in source_hashes_offsets.items():
            if s_hash in correct_hashes_offsets:
                hashes_diff_offset[s_hash] = s_offset - correct_hashes_offsets[s_hash]

        if len(hashes_diff_offset) == 0:
            return dict(), 0  # not found matches

        median = statistics.median(hashes_diff_offset.values())
        for h in list(hashes_diff_offset.keys()):
            if hashes_diff_offset[h] - median in range(-3, 3):
                continue
            # print(f"delete shift: {h} || {hashes_diff_offset}")
            hashes_diff_offset.pop(h)
        correct_hashes_offsets = {h: o for h, o in source_hashes_offsets.items() if h in hashes_diff_offset}

        return correct_hashes_offsets, median

    def save_matching_print2png(self,
                                hashes: list[str],
                                print_name: str,
                                print_folder: str = 'fingerprint_template',
                                shift_line: int | None = None):
        matching_points: set[tuple[int, int]] = set()
        for h in hashes:
            if h in self.first_points.keys():
                matching_points.add(self.first_points[h])
                matching_points.add(self.second_points[h])

        if len(matching_points) == 0:
            return

        pathlib.Path(print_folder).mkdir(parents=True, exist_ok=True)
        full_path = os.path.join(print_folder, f"{print_name}.png")

        use('agg')
        fig, ax = plt.subplots()
        plt.axvline(x=shift_line, color='r', label='start_found')

        ax.set_title(print_name)
        ax.set_aspect(0.1)
        ax.pcolor(self.arr2d)

        x, y = zip(*matching_points)
        ax.scatter(x, y, c="g")

        fig.savefig(full_path)
        plt.close(fig)
