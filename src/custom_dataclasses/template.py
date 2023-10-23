import math
from typing import Optional


class Template(object):
    def __init__(self,
                 template_id: int,
                 template_name: str,
                 amplitudes: list[int],
                 sample_size: int = 320,
                 limit_samples: Optional[int] = None):
        self.template_id: int = template_id
        self.template_name: str = template_name
        self.sample_size = sample_size

        self.samples: dict[int, list] = dict()

        self.max_amplitude_seq_num: int = 0
        self.max_amplitude_value: int = 0

        self.max_amp_samples: dict[int, int] = dict()
        self.max_amp_samples_list: list[int] = []

        self.abs_sum_amp_samples: dict[int, int] = dict()
        self.trend_samples: dict[int, int] = dict()
        self.trend_samples_str: str = ''

        self.count_samples: int = math.floor(len(amplitudes) / sample_size)
        if limit_samples:
            self.count_samples = min(self.count_samples, limit_samples)

        self.count_amplitudes = self.count_samples * sample_size

        self.amplitudes = amplitudes[0: self.count_amplitudes]

        for seq_num in range(0, self.count_samples):
            self.samples[seq_num] = amplitudes[seq_num * sample_size: (seq_num + 1) * sample_size]
            self.max_amp_samples[seq_num] = max(self.samples[seq_num])
            if self.max_amp_samples[seq_num] > self.max_amplitude_value:
                self.max_amplitude_value = self.max_amp_samples[seq_num]
                self.max_amplitude_seq_num = seq_num

            self.max_amp_samples_list.append(max(self.samples[seq_num]))

            if self.samples.get(seq_num - 1):
                diff = self.max_amp_samples[seq_num] - self.max_amp_samples[seq_num - 1]
                if self.max_amp_samples[seq_num] < 200:
                    self.trend_samples[seq_num] = 0  # zero amplitude
                elif self.max_amp_samples[seq_num] < 800:
                    self.trend_samples[seq_num] = 2  # very small amplitude
                elif diff > 600:
                    self.trend_samples[seq_num] = 4  # x2height
                elif diff > 0:
                    self.trend_samples[seq_num] = 5  # height
                elif diff > -600:
                    self.trend_samples[seq_num] = 8  # decline
                else:
                    self.trend_samples[seq_num] = 9  # x2decline

                self.trend_samples_str += str(self.trend_samples[seq_num])
            else:
                self.trend_samples[seq_num] = 0
                self.trend_samples_str += str(self.trend_samples[seq_num])

        self.avg_amplitude = int(sum(self.max_amp_samples_list) / self.count_samples)

    def save_template2wav(self, path: str = 'test.wav'):
        import wave

        with wave.open(path, 'wb') as f:
            f.setnchannels(1)  # mono
            f.setsampwidth(2)
            f.setframerate(16000)

            dict_bytes = self.convert_samples2dict_bytes()

            for seq_num in range(0, self.count_samples):
                f.writeframes(dict_bytes[seq_num])

    def convert_samples2dict_bytes(self) -> dict:
        from struct import pack

        bytes_samples: dict[int, bytes] = {}
        for seq_num in range(0, self.count_samples):
            b = b''
            for amp in self.samples[seq_num]:
                b += pack('<h', amp)
            bytes_samples[seq_num] = b

        return bytes_samples

        # self.max_rate_amp_samples: dict[int, int] = dict()
        # for seq_num, max_amp_sample in self.max_amp_samples.items():
        #     self.max_rate_amp_samples[seq_num] = round(max_amp_sample / self.max_amplitude * 10 / 5)
