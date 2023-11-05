import os
import time
from threading import Thread
import requests
import soundfile
from loguru import logger
from src.audio_container import AudioContainer
from src.config import Config
from src.custom_dataclasses.fingerprint import FingerPrint
from src.custom_dataclasses.template import Template
from src.fingerprint_mining import get_fingerprint
import concurrent.futures


class Detection(Thread):
    def __init__(self, config: Config, audio_containers: dict[str, AudioContainer]):
        Thread.__init__(self)
        self.config = config
        self.audio_containers: dict[str, AudioContainer] = audio_containers
        self.log = logger.bind(object_id=f'Detection')
        self.templates: dict[str, Template] = {}
        self.all_templates_hash: dict[str, str] = {}
        self.result = {}
        self.times: list = [0.001]
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=8)
        self.log.info(f'init Detection')

    def start(self) -> None:
        # This class use threading (see function self.run)
        super().start()

    def run(self):
        self.load_samples()
        self.run_detection()

    def load_samples(self):
        self.log.info('start load_samples')
        folder = '/home/anydict/PycharmProjects/pysonic_nemo/tests/templates/enable'
        file_list = [file for file in os.listdir(folder) if file.endswith('.wav')]

        for template_id, file_name in enumerate(file_list):
            file_path = os.path.join(folder, file_name)
            template_name = file_name.replace('.wav', '')

            audio_data, samplerate = soundfile.read(file_path, dtype='int16')
            self.templates[template_name] = Template(template_id=template_id,
                                                     template_name=template_name,
                                                     amplitudes=list(audio_data),
                                                     limit_samples=60)
            for tmp_hash in self.templates[template_name].fingerprint.hashes_offsets.keys():
                self.all_templates_hash[tmp_hash] = template_name

        # self.log.success(self.all_templates_hash)
        self.log.info('end load_samples')
        self.log.info(f"count template hashes: {len(self.all_templates_hash)}")

    def run_detection(self):
        self.log.info(f'start detection count templates={len(self.templates)}')
        result = set()
        while self.config.shutdown is False:
            time.sleep(0.02)
            if len(self.audio_containers) == 0:
                time.sleep(0.1)
            ac_amplitudes: list[list[int]] = []
            ac_keys: list[str] = []
            for ac_key in self.audio_containers.keys():
                audio_container = self.audio_containers[ac_key]
                if audio_container.event_destroy:
                    continue
                if len(audio_container.found_templates) > 0:
                    continue

                ac_samples = audio_container.analyzed_samples
                ac_amps = []
                for seq_num in sorted(list(ac_samples.keys())):
                    ac_amps.extend(ac_samples[seq_num])

                # skip silence
                if len(ac_amps[-8000:]) < 1024 or max(ac_amps[-8000:]) < 5000:
                    continue
                else:
                    ac_amplitudes.append(ac_amps[-8000:])
                    ac_keys.append(ac_key)

            t1 = time.time()

            # # use only one thread
            # for fingerprint in map(get_fingerprint, ac_keys, ac_amplitudes):
            #     found_template = self.analise_amplitude_use_fingerprint(fingerprint)
            #     if found_template is not None:
            #         self.log.success(f"{fingerprint.print_name}, {found_template}")

            # use multiprocessing
            for fingerprint in self.executor.map(get_fingerprint, ac_keys, ac_amplitudes):
                found_template = self.analise_amplitude_use_fingerprint(fingerprint)
                if found_template is not None:
                    self.log.success(f"{fingerprint.print_name}, {found_template}")

                    if '123' == '321':
                        url = 'http://127.0.0.1:8005/extapi?token=612tkABC&cmd=hangup&call_id=X123'
                        response = requests.get(url)
                        self.log.success(response)

            t2 = time.time()
            self.times.append(t2 - t1)

        self.executor.shutdown()
        self.log.info(f'end simple_detection avg_time={sum(self.times) / len(self.times)}')
        self.log.info(f'result={result}')

    def analise_amplitude_use_fingerprint(self, ac_print: FingerPrint) -> str | None:
        # ac_print = get_fingerprint(amplitudes=amplitudes)
        found_template = None

        ac_tmp_hash_similar: dict[str, list[str]] = {}
        for ac_hash in ac_print.hashes_offsets.keys():
            if ac_hash in self.all_templates_hash.keys():
                tmp_name: str = self.all_templates_hash[ac_hash]
                if isinstance(ac_tmp_hash_similar.get(tmp_name), list):
                    ac_tmp_hash_similar[tmp_name].append(ac_hash)
                else:
                    ac_tmp_hash_similar[tmp_name] = [ac_hash]

        for template_name in ac_tmp_hash_similar.keys():
            if len(ac_tmp_hash_similar[template_name]) < 12:
                continue

            template_hashes_offsets = self.templates[template_name].fingerprint.hashes_offsets
            timely_hashes, shift = ac_print.get_timely_hashes(source_hashes_offsets=ac_print.hashes_offsets,
                                                              correct_hashes_offsets=template_hashes_offsets)
            if len(timely_hashes) < 12:
                continue

            offset_set = set(timely_hashes.values())

            if len(offset_set) < 3:
                self.log.warning(f'the offset is too small: {offset_set}')
                continue

            # self.log.success(f'n={template_name} {shift}')
            # self.log.info([ac_tmp_hash_similar[template_name]])
            ac_print.save_matching_print2png(hashes=ac_tmp_hash_similar[template_name],
                                             print_folder='fingerprint_record',
                                             print_name=f"{ac_print.print_name}_{template_name}",
                                             shift_line=shift)

            return template_name

        return found_template


if __name__ == "__main__":
    cfg = Config()
    sd = Detection(audio_containers=dict(), config=cfg)
    sd.start()
