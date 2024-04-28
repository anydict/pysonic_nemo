import asyncio
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor

import soundfile as sf
from loguru import logger

from src.audio_container import AudioContainer
from src.config import Config
from src.custom_dataclasses.template import Template
from src.detector import Detector


async def main():
    config = Config()
    config.template_folder_path = 'templates/enable'

    audio_containers: dict[str, AudioContainer] = {}
    folder_records = 'file_for_analysis'
    os.makedirs(folder_records, exist_ok=True)

    index = 0
    file_name = '123_audio_two1601800793.wav'
    file_path = os.path.join(folder_records, file_name)
    data, sample_rate = sf.read(file_path, dtype='int16')
    sample_size = int(sample_rate * 0.02)

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
    ppe = ProcessPoolExecutor()
    audio_container = AudioContainer(config=config,
                                     em_host=file_name,
                                     em_port=index,
                                     call_id='X123',
                                     chan_id='X123',
                                     event_create=None,  # noqa
                                     call_service_client=None,  # noqa
                                     )

    logger.info(len(template.amplitudes))
    logger.info(template.count_samples)
    logger.info(template.template_name)

    audio_containers[file_name] = audio_container
    audio_container.call_id = random.randrange(1, 100000)
    audio_container.max_amplitude_samples[0] = template.max_amp_samples[0]
    audio_container.analyzed_samples[0] = template.samples[0]
    audio_container.bytes_samples = template.convert_samples2dict_bytes(samples=template.samples)

    detector = Detector(config=config,
                        audio_containers=audio_containers,
                        ppe=ppe)
    await detector.start_detection()

    await asyncio.sleep(3)

    start_time = time.time()

    for seq_num in range(1, max(template.samples)):
        if seq_num in template.samples:
            audio_container.max_amplitude_samples[seq_num] = template.max_amp_samples[seq_num]
            audio_container.analyzed_samples[seq_num] = template.samples[seq_num]
            await asyncio.sleep(0.02)
            if seq_num % 50 == 0:
                logger.info(f'add new second, left {round(seq_num * 0.02, 2)} seconds')
        else:
            logger.info('end stream')
            break

    await asyncio.sleep(0.2)
    config.wait_shutdown = True
    logger.info(time.time() - start_time)
    await asyncio.sleep(1)

    # for key in audio_containers:
    #     print(audio_containers[key].result_detections)


if __name__ == '__main__':
    asyncio.run(main())
