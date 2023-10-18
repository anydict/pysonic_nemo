import math
import os
import random
from struct import pack

import soundfile as sf

from src.audio_container import AudioContainer
from src.config import Config
from src.simple_detection import SimpleDetection

folder = 'file_for_analysis'
os.makedirs(folder, exist_ok=True)

join_config = {"app": "pysonic", "first_noise_answer_threshold": 250}
config = Config(join_config=join_config)

file_list = [file for file in os.listdir(folder) if file.endswith('.wav')]
audio_containers: dict[str, AudioContainer] = {}

for file_name in file_list:
    file_path = os.path.join(folder, file_name)
    data, sample_rate = sf.read(file_path, dtype='int16')

    amplitudes = data.tolist()

    bytes_samples: dict[int, bytes] = {}
    samples: dict[int, list] = dict()
    max_amp_samples: dict[int, int] = dict()
    trend_samples: dict[int, int] = dict()
    trend_samples_str: str = ''
    first_seq_num = 0
    last_seq_num = math.ceil(len(data) / 320)
    for seq_num in range(first_seq_num, last_seq_num):
        samples[seq_num] = amplitudes[seq_num * 320: (seq_num + 1) * 320]
        max_amp_samples[seq_num] = max(samples[seq_num])

        b = b''
        for amp in samples[seq_num]:
            b += pack('<h', amp)
        bytes_samples[seq_num] = b

        if samples.get(seq_num - 1):
            diff = max_amp_samples[seq_num] - max_amp_samples[seq_num - 1]
            if max_amp_samples[seq_num] < 200:
                trend_samples[seq_num] = 0  # very small amplitude
            elif diff > 200:
                trend_samples[seq_num] = 1  # height
            else:
                trend_samples[seq_num] = 2  # decline

            trend_samples_str += str(trend_samples[seq_num])

    em_host = str(random.randrange(1, 10000))
    em_port = random.randrange(1, 10000)
    ssrc = random.randrange(1, 10000)

    ac_id = f'{ssrc}@{em_host}:{em_port}'

    audio_container = AudioContainer(config=config,
                                     em_host=em_host,
                                     em_port=em_port,
                                     em_ssrc=ssrc,
                                     first_seq_num=first_seq_num,
                                     length_payload=640)

    audio_containers[ac_id] = audio_container

    audio_container.call_id = random.randrange(1, 100000)
    audio_container.samples_trend = trend_samples
    audio_container.max_amplitude_analyzed_samples = max_amp_samples
    audio_container.analyzed_samples = samples
    audio_container.bytes_samples = bytes_samples

simple = SimpleDetection(config=config, audio_containers=audio_containers)
simple.start()
