import os.path
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
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

        Path(print_folder).mkdir(parents=True, exist_ok=True)
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
            if hashes_diff_offset[h] - median == 0:
                continue
            hashes_diff_offset.pop(h)
        correct_hashes_offsets = {h: o for h, o in source_hashes_offsets.items() if h in hashes_diff_offset}

        return correct_hashes_offsets, median

    @staticmethod
    def save_matching_print2png(first_points: dict[str, tuple[int, int]],
                                second_points: dict[str, tuple[int, int]],
                                arr2d: np.array,
                                hashes: list[str],
                                print_name: str,
                                save_folder: str = 'fingerprint_template',
                                shift_line: int | None = None):
        try:
            matching_points: set[tuple[int, int]] = set()
            for h in hashes:
                if h in first_points.keys():
                    matching_points.add(first_points[h])
                    matching_points.add(second_points[h])

            if len(matching_points) == 0:
                return

            sysdate = datetime.now()
            path = os.path.join(save_folder, str(sysdate.year), str(sysdate.month), str(sysdate.day), str(sysdate.hour))

            if Path(path).is_dir() is False:
                Path(path).mkdir(parents=True, exist_ok=True)
            path_with_name = os.path.join(path, f"{print_name}.png")

            use('agg')
            fig, ax = plt.subplots()
            plt.axvline(x=shift_line, color='r', label='start_found')

            ax.set_title(print_name)
            ax.pcolor(arr2d)

            x, y = zip(*matching_points)
            ax.scatter(x, y, c="g")

            fig.savefig(path_with_name)
            plt.close(fig)
        except Exception as e:
            print(f'ERROR! [save_matching_print2png] Exception detail: {e}')
