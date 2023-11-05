import numpy as np
from typing import Optional

from src.fingerprint_mining import get_fingerprint


class Template(object):
    def __init__(self,
                 template_id: int,
                 template_name: str,
                 amplitudes: list[int],
                 trim_first_low_amplitudes: bool = True,
                 add_first_silence_sample: bool = False,
                 limit_samples: Optional[int] = None,
                 sample_size: int = 320,
                 sample_rate: int = 16000):
        self.template_id: int = template_id
        self.template_name: str = template_name
        self.sample_size = sample_size
        self.sample_rate = sample_rate

        while True:
            amp = amplitudes.pop(0)
            if amp > 0 or len(amplitudes) == 0:
                amplitudes.insert(0, amp)
                break

        while trim_first_low_amplitudes:
            amp = amplitudes.pop(0)
            if amp > 350 or len(amplitudes) == 0:
                amplitudes.insert(0, amp)
                break

        if add_first_silence_sample:
            for _ in range(0, 320):
                amplitudes.insert(0, 0)

        self.count_samples: int = len(amplitudes) // sample_size
        if limit_samples:
            self.count_samples = min(self.count_samples, limit_samples)

        self.fingerprint = get_fingerprint(print_name=template_name, amplitudes=amplitudes)

        self.count_amplitudes = self.count_samples * sample_size
        self.amplitudes = amplitudes[0: self.count_amplitudes]
        self.samples: dict[int, list] = self.convert_amplitudes2samples(amplitudes=self.amplitudes,
                                                                        samples_size=self.sample_size)
        self.max_amp_samples: dict[int, int] = {k: max(v) for k, v in self.samples.items()}
        # self.trend_samples: dict[int, int] = self.convert_samples2trend(samples=self.samples)
        # self.trend_str: str = self.trend_dict2trend_string(trend_samples=self.trend_samples)
        #
        # self.zcross: dict[int, int] = self.ger_zero_crossing(samples=self.samples)
        # self.zcross_str: str = self.zcross2zcross_string(zcross=self.zcross)

        # self.fingerprint.save_print2png(print_name=self.template_name)

    @staticmethod
    def trend_dict2trend_string(trend_samples: dict[int, int]) -> str:
        return ''.join([str(a) for a in trend_samples.values()])

    @staticmethod
    def zcross2zcross_string(zcross: dict[int, int]) -> str:
        return ''.join([str(a // 10) for a in zcross.values()])

    @staticmethod
    def ger_zero_crossing(samples: dict[int, list]) -> dict[int, int]:
        zero_crossings = {}
        for seq_num in samples:
            zero_crossing = np.where(np.diff(np.sign(samples[seq_num])))[0]
            zero_crossings[seq_num] = len(zero_crossing)
        return zero_crossings

    @staticmethod
    def convert_amplitudes2samples(amplitudes: list[int],
                                   samples_size: int) -> dict[int, list]:
        samples: dict[int, list] = {}
        for seq_num in range(0, (len(amplitudes) // samples_size)):
            samples[seq_num] = list(amplitudes[seq_num * samples_size: (seq_num + 1) * samples_size])

        return samples

    @staticmethod
    def convert_samples2trend(samples: dict[int, list]) -> dict[int, int]:
        trend_samples: dict[int, int] = {}
        for seq_num in range(min(samples), max(samples) + 1):

            if seq_num > min(samples):
                curr = int(max(samples[seq_num]))
                last1 = int(max(samples[seq_num - 1]))

                if abs(curr) < 400:
                    trend_samples[seq_num] = 0
                elif curr >= last1 * 1.5:
                    trend_samples[seq_num] = min(trend_samples[seq_num - 1] + 3, 9)
                else:
                    trend_samples[seq_num] = max(trend_samples[seq_num - 1] - 3, 1)

            else:
                if int(max(samples[seq_num])) < 400:
                    trend_samples[seq_num] = 0
                else:
                    trend_samples[seq_num] = 5

        return trend_samples

    @staticmethod
    def convert16khz_to_8khz(amplitudes: list[int]) -> list[int]:
        """
        :param amplitudes: amplitudes from PCM-wav 16kHz
        :return: amplitudes for PCM-wav 8kHz
        """
        from scipy import signal
        resampled_audio = signal.resample_poly(amplitudes, 1, 2)

        return list(resampled_audio)

    def save_samples2wav(self,
                         samples: dict[int, list],
                         path: str = 'test.wav'):
        """
        Save samples to wav file

        Example use:
        template.save_template2wav(samples=template.samples, path='raw.wav')

        :param samples: amplitudes arranged by samples
        :param path: where to save the wav file
        :return:
        """
        import wave

        with wave.open(path, 'wb') as f:
            f.setnchannels(1)  # mono
            f.setsampwidth(2)
            f.setframerate(16000)

            dict_bytes = self.convert_samples2dict_bytes(samples=samples)

            for seq_num in range(min(samples), max(samples) + 1):
                f.writeframes(dict_bytes[seq_num])

    @staticmethod
    def convert_samples2dict_bytes(samples: dict[int, list]) -> dict:
        """
        Convert samples to bytes

        :param samples:  amplitudes arranged by samples
        :return:
        """

        from struct import pack

        bytes_samples: dict[int, bytes] = {}
        for seq_num in range(min(samples), max(samples) + 1):
            b = b''
            for amp in samples[seq_num]:
                b += pack('<h', amp)
            bytes_samples[seq_num] = b

        return bytes_samples
