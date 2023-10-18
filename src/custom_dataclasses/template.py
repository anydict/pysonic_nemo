import math


class Template(object):
    def __init__(self,
                 template_id: int,
                 template_name: str,
                 amplitudes: list[int],
                 sample_size: int = 320):
        self.template_id: int = template_id
        self.template_name: str = template_name
        self.sample_size = sample_size

        self.samples: dict[int, list] = dict()

        self.max_amplitude_seq_num: int = 0
        self.max_amplitude_value: int = 0

        self.max_amp_samples: dict[int, int] = dict()
        self.max_amp_samples_list: list[int] = []

        self.avg_amp_samples: dict[int, int] = dict()
        self.trend_samples: dict[int, int] = dict()
        self.trend_samples_str: str = ''

        self.count_samples: int = math.floor(len(amplitudes) / sample_size)
        self.count_amplitudes = self.count_samples * sample_size

        self.amplitudes = amplitudes[0: self.count_amplitudes]

        for seq_num in range(0, self.count_samples):
            self.samples[seq_num] = amplitudes[seq_num * sample_size: (seq_num + 1) * sample_size]
            self.max_amp_samples[seq_num] = max(self.samples[seq_num])
            if self.max_amp_samples[seq_num] > self.max_amplitude_value:
                self.max_amplitude_value = self.max_amp_samples[seq_num]
                self.max_amplitude_seq_num = seq_num

            self.avg_amp_samples[seq_num] = round(sum(self.samples[seq_num]) / len(self.samples[seq_num]))
            self.max_amp_samples_list.append(max(self.samples[seq_num]))

            if self.samples.get(seq_num - 1):
                diff = self.max_amp_samples[seq_num] - self.max_amp_samples[seq_num - 1]
                if self.max_amp_samples[seq_num] < 200:
                    self.trend_samples[seq_num] = 0  # very small amplitude
                elif diff > 200:
                    self.trend_samples[seq_num] = 1  # height
                else:
                    self.trend_samples[seq_num] = 2  # decline

                self.trend_samples_str += str(self.trend_samples[seq_num])

        # self.max_rate_amp_samples: dict[int, int] = dict()
        # for seq_num, max_amp_sample in self.max_amp_samples.items():
        #     self.max_rate_amp_samples[seq_num] = round(max_amp_sample / self.max_amplitude * 10 / 5)

        # import wave
        # from struct import pack
        # with wave.open(f'321.wav', 'wb') as f:
        #     f.setnchannels(1)  # mono
        #     f.setsampwidth(2)
        #     f.setframerate(16000)
        #
        #     for seq_num in range(0, self.count_samples):
        #         b = b''
        #         for amp in self.samples[seq_num]:
        #             b += pack('<h', amp)
        #         f.writeframes(b)
