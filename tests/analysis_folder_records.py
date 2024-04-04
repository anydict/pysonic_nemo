import asyncio
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import soundfile as sf
from loguru import logger

from src.config import Config
from src.custom_dataclasses.template import Template
from src.detector import Detector
from src.fingerprint_mining import get_fingerprint


async def main():
    config = Config()
    config.template_folder_path = 'templates/enable'
    time.sleep(0.1)

    folder_records = 'file_for_analysis'
    os.makedirs(folder_records, exist_ok=True)
    file_list = [file for file in os.listdir(folder_records) if file.endswith('.wav')]

    ppe = ProcessPoolExecutor()

    detector = Detector(config=config,
                        audio_containers=dict(),
                        ppe=ppe)
    await detector.start_detection()
    await asyncio.sleep(2)

    results = {}

    for index, file_name in enumerate(file_list):
        logger.info(f'search in file_name={file_name}')
        file_path = os.path.join(folder_records, file_name)
        data, sample_rate = sf.read(file_path, dtype='int16')

        template = Template(template_id=index + 20000000,
                            template_name=file_name,
                            amplitudes=data.tolist(),
                            sample_rate=sample_rate)

        count_amps = 8000 * 3
        count_parts = len(template.amplitudes) // count_amps + 1

        for part in range(0, count_parts):
            part_amps = template.amplitudes[part * count_amps: (part + 1) * count_amps]
            fingerprint = get_fingerprint(print_name=file_name, amplitudes=part_amps)
            found_template = detector.analise_fingerprint(fingerprint)
            if found_template is not None:
                results[file_name] = found_template
                print(f"in file={file_name} found template={found_template}")

            if index % 10 == 0 and len(results) > 0:
                with open(f"result_{index}", 'w', encoding='utf-8') as jsonf:
                    jsonf.write(json.dumps(results, indent=4))
                    results = {}

    await asyncio.sleep(1)
    config.wait_shutdown = True


if __name__ == '__main__':
    asyncio.run(main())
