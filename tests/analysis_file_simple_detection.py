import os
import random
import time

import soundfile as sf

from src.audio_container import AudioContainer
from src.config import Config
from src.custom_dataclasses.template import Template
from src.simple_detection import SimpleDetection

join_config = {"app": "pysonic", "first_noise_answer_threshold": 250}
config = Config(join_config=join_config)

audio_containers: dict[str, AudioContainer] = {}
sample_size = 320
sample_width = 2
folder_records = 'file_for_analysis'
os.makedirs(folder_records, exist_ok=True)
file_list = [file for file in os.listdir(folder_records) if file.endswith('.wav')]

for index, file_name in enumerate(file_list):
    file_path = os.path.join(folder_records, file_name)
    data, sample_rate = sf.read(file_path, dtype='int16')

    template = Template(template_id=index + 20000000,
                        template_name=file_name,
                        amplitudes=data.tolist(),
                        sample_size=sample_size)

    audio_container = AudioContainer(config=config,
                                     em_host=file_name,
                                     em_port=index,
                                     em_ssrc=index,
                                     first_seq_num=0,
                                     length_payload=sample_size * sample_width)

    audio_containers[file_name] = audio_container

    audio_container.call_id = random.randrange(1, 100000)
    audio_container.trend_samples = template.trend_samples
    audio_container.max_amplitude_samples = template.max_amp_samples
    audio_container.analyzed_samples = template.samples
    audio_container.bytes_samples = template.convert_samples2dict_bytes()

simple = SimpleDetection(config=config, audio_containers=audio_containers)
simple.start()

time.sleep(60)
config.shutdown = True
print(time.time())

# for key in audio_containers:
#     print(audio_containers[key].result_detections)
