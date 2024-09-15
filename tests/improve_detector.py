import asyncio
import os

import soundfile as sf
from loguru import logger

from src.config import Config
from src.custom_dataclasses.template import Template
from src.fingerprint_mining import get_fingerprint


async def main():
    config = Config()
    config.template_folder_path = 'templates/enable'
    folder_records = 'file_for_analysis'
    os.makedirs(folder_records, exist_ok=True)
    file_list = [file for file in os.listdir(folder_records) if file.endswith('.wav')]

    for index, file_name in enumerate(file_list):
        logger.info(f'search in file_name={file_name}')
        file_path = os.path.join(folder_records, file_name)
        data, sample_rate = sf.read(file_path, dtype='int16')

        template = Template(template_id=index + 20000000,
                            template_name=file_name,
                            amplitudes=data.tolist(),
                            sample_rate=sample_rate)

        fingerprint = get_fingerprint(print_name=file_name,
                                      amplitudes=template.amplitudes)

        logger.info(f'print_name={fingerprint.print_name}')


if __name__ == '__main__':
    asyncio.run(main())
