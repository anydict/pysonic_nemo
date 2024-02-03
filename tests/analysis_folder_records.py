import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import soundfile as sf

from src.config import Config
from src.custom_dataclasses.template import Template
from src.detector import Detector
from src.fingerprint_mining import get_fingerprint


async def main():
    config = Config()

    sample_size = 160
    folder_records = 'file_for_analysis'
    os.makedirs(folder_records, exist_ok=True)
    file_list = [file for file in os.listdir(folder_records) if file.endswith('.wav')]

    tpe = ThreadPoolExecutor()
    ppe = ProcessPoolExecutor()

    detector = Detector(config=config,
                        audio_containers=dict(),
                        ppe=ppe,
                        tpe=tpe)
    await detector.start_detection()
    await asyncio.sleep(3)

    results = {}

    for index, file_name in enumerate(file_list):
        file_path = os.path.join(folder_records, file_name)
        data, sample_rate = sf.read(file_path, dtype='int16')

        template = Template(template_id=index + 20000000,
                            template_name=file_name,
                            amplitudes=data.tolist(),
                            sample_size=sample_size)

        count_amps = 8000 * 2
        count_parts = len(template.amplitudes) // count_amps

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

    # for key in audio_containers:
    #     print(audio_containers[key].result_detections)


if __name__ == '__main__':
    asyncio.run(main())
