import os
import random
import time

from loguru import logger
import soundfile as sf

from src.audio_container import AudioContainer
from src.config import Config
from src.custom_dataclasses.template import Template
from src.detection import Detection

config = Config()
logger.bind(object_id='main')

audio_containers: dict[str, AudioContainer] = {}
sample_size = 320
sample_width = 2
folder_records = 'file_for_analysis'
os.makedirs(folder_records, exist_ok=True)

index = 0
file_name = '123_audio_two1601800793.wav'
file_path = os.path.join(folder_records, file_name)
data, sample_rate = sf.read(file_path, dtype='int16')

template = Template(template_id=index + 20000000,
                    template_name=file_name,
                    amplitudes=data.tolist(),
                    trim_first_low_amplitudes=False,
                    sample_size=sample_size,
                    sample_rate=sample_rate)

# tmp: [int, list] = {}
# for seq_num in template.samples:
#     if 206 <= seq_num <= 217:
#         tmp[seq_num] = template.samples[seq_num]
#
# template.save_samples2wav(samples=tmp, path='test.wav')

audio_container = AudioContainer(config=config,
                                 em_host=file_name,
                                 em_port=index,
                                 em_ssrc=index,
                                 first_seq_num=0,
                                 length_payload=sample_size * sample_width)

logger.info(len(template.amplitudes))
logger.info(template.count_samples)
logger.info(template.template_name)

audio_containers[file_name] = audio_container
audio_container.call_id = random.randrange(1, 100000)
audio_container.max_amplitude_samples[0] = template.max_amp_samples[0]
audio_container.analyzed_samples[0] = template.samples[0]
audio_container.bytes_samples = template.convert_samples2dict_bytes(samples=template.samples)

simple = Detection(config=config, audio_containers=audio_containers)
simple.start()

time.sleep(1)

start_time = time.time()

for seq_num in range(1, max(template.samples)):
    if seq_num in template.samples:
        audio_container.max_amplitude_samples[seq_num] = template.max_amp_samples[seq_num]
        audio_container.analyzed_samples[seq_num] = template.samples[seq_num]
        time.sleep(0.02)
        if seq_num % 50 == 0:
            logger.info(f'add new second, left {round(seq_num * 0.02, 2)} seconds')
    else:
        logger.info('end stream')
        break

time.sleep(0.02)
config.shutdown = True
logger.info(time.time() - start_time)
time.sleep(1)

# for key in audio_containers:
#     print(audio_containers[key].result_detections)
