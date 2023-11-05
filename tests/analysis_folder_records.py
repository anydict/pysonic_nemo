import json
import os
import time
import soundfile as sf

from src.config import Config
from src.custom_dataclasses.template import Template
from src.detection import Detection
from src.fingerprint_mining import get_fingerprint

config = Config()

sample_size = 320
sample_width = 2
folder_records = 'file_for_analysis'
os.makedirs(folder_records, exist_ok=True)
file_list = [file for file in os.listdir(folder_records) if file.endswith('.wav')]

detection = Detection(config=config,
                      audio_containers=dict())
detection.start()
time.sleep(3)

results = {}

for index, file_name in enumerate(file_list):
    file_path = os.path.join(folder_records, file_name)
    data, sample_rate = sf.read(file_path, dtype='int16')

    template = Template(template_id=index + 20000000,
                        template_name=file_name,
                        amplitudes=data.tolist(),
                        sample_size=sample_size)

    # resampled_audio = template.convert16khz_to_8khz(template.amplitudes)

    for part in range(0, len(template.amplitudes) // 8000):
        part_amps = template.amplitudes[part * 8000: (part + 1) * 8000]
        fingerprint = get_fingerprint(print_name=file_name, amplitudes=part_amps)
        found_template = detection.analise_amplitude_use_fingerprint(fingerprint)
        if found_template is not None:
            results[file_name] = found_template
            print(f"in file={file_name} found template={found_template}")

        if index % 10 == 0 and len(results) > 0:
            with open(f"result_{index}", 'w', encoding='utf-8') as jsonf:
                jsonf.write(json.dumps(results, indent=4))
                results = {}

time.sleep(1)
config.shutdown = True

# for key in audio_containers:
#     print(audio_containers[key].result_detections)
