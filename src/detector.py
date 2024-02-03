import asyncio
import functools
import os
import time
from asyncio import AbstractEventLoop
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime

import soundfile
from loguru import logger

from src.audio_container import AudioContainer
from src.config import Config, MIN_AMPLITUDE_FOR_DETECTION
from src.custom_dataclasses.fingerprint import FingerPrint
from src.custom_dataclasses.template import Template
from src.fingerprint_mining import get_fingerprint


class Detector(object):
    def __init__(self,
                 config: Config,
                 audio_containers: dict[str, AudioContainer],
                 ppe: ProcessPoolExecutor,
                 tpe: ThreadPoolExecutor
                 ):
        self.config = config
        self.audio_containers: dict[str, AudioContainer] = audio_containers
        self.ppe: ProcessPoolExecutor = ppe
        self.tpe: ThreadPoolExecutor = tpe

        self.templates: dict[str, Template] = {}
        self.all_templates_hash: dict[str, list[str]] = {}
        self.chan_id_with_amps: dict[str, list[int]] = {}
        self.result = {}
        self.times: list[float] = []
        self.event_loop: AbstractEventLoop = asyncio.get_running_loop()
        self.log = logger.bind(object_id=self.__class__.__name__)
        self.log.info(f'init Detection')

    async def start_detection(self):
        self.log.info("start_detection")
        self.load_samples()
        asyncio.create_task(self.start_loop())

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
                                                     amplitudes=list(audio_data))
            for tmp_hash in self.templates[template_name].fingerprint.hashes_offsets.keys():
                if self.all_templates_hash.get(tmp_hash) is None:
                    self.all_templates_hash[tmp_hash] = [template_name]
                else:
                    self.all_templates_hash[tmp_hash].append(template_name)

        for template_name in self.templates.keys():
            found_template = self.analise_fingerprint(ac_print=self.templates[template_name].fingerprint,
                                                      skip_template_name=self.templates[template_name].template_name,
                                                      real_search=False)
            if found_template:
                self.log.warning(f"Found cross template: {template_name} and {found_template}")

                # a_file_path = os.path.join(folder, f'{template_name}.wav')
                # b_file_path = os.path.join(folder, f'{found_template}.wav')
                # if self.templates[found_template].count_samples > self.templates[template_name].count_samples:
                #     if os.path.isfile(a_file_path):
                #         os.remove(a_file_path)
                # else:
                #     if os.path.isfile(b_file_path):
                #         os.remove(a_file_path)
        self.log.info('end load_samples')
        self.log.info(f"count hashes: {len(self.all_templates_hash)}, count templates: {len(self.templates)}")

    async def start_loop(self):
        self.log.info("start loop for prepare amplitudes and detection")
        while self.config.wait_shutdown is False:
            await asyncio.sleep(0.1)
            await self.run_prepare_amplitude()
            await asyncio.sleep(0.1)
            await self.run_detection()
        self.log.info("end start_loop")

    async def run_prepare_amplitude(self):
        if len(self.audio_containers) == 0:
            await asyncio.sleep(0.2)
            return

        for chan_id in self.audio_containers.keys():
            audio_container = self.audio_containers[chan_id]
            if audio_container is None:
                continue
            elif audio_container.event_destroy:
                continue
            elif audio_container.found_templates:
                continue
            elif audio_container.found_first_noise == 0:
                continue
            elif audio_container.duration_stream < 2:
                continue
            elif datetime.now() > audio_container.detect_until_time:
                continue
            elif audio_container.seq_num_last_package == audio_container.last_detect_seq_num:
                continue

            ac_amps = []
            last_seq_numbers = sorted(list(audio_container.analyzed_samples.keys()))[-150:]  # last three seconds
            for seq_num in last_seq_numbers:
                ac_amps.extend(audio_container.analyzed_samples[seq_num])

            if len(ac_amps) < 1024:
                # very few amplitudes
                continue
            elif max(ac_amps) < MIN_AMPLITUDE_FOR_DETECTION:
                # skip silence
                continue
            else:
                audio_container.last_detect_seq_num = audio_container.seq_num_last_package
                self.chan_id_with_amps[chan_id] = ac_amps

        # self.log.info(f"len self.chan_id_with_amps={self.chan_id_with_amps}")

    async def run_detection(self):
        if len(self.audio_containers) == 0:
            return
        elif len(self.chan_id_with_amps) == 0:
            return

        t1 = time.monotonic()

        self.log.info("BEFORE run_in_executor")
        tasks = []
        for chan_id, ac_amps in self.chan_id_with_amps.items():
            if time.monotonic() - t1 > 0.5:
                await asyncio.sleep(0.1)
            task = self.event_loop.run_in_executor(self.ppe, get_fingerprint, chan_id, ac_amps)
            tasks.append(task)

        self.chan_id_with_amps.clear()

        for task in asyncio.as_completed(tasks):
            fingerprint: FingerPrint = await task

            found_template = self.analise_fingerprint(fingerprint)
            chan_id = fingerprint.print_name
            audio_container = self.audio_containers.get(chan_id)
            if audio_container is None:
                continue
            audio_container.duration_check_detect += time.monotonic() - t1

            if found_template is not None:
                self.log.success(f"{fingerprint.print_name}, {found_template}")
                self.audio_containers[fingerprint.print_name].add_found_template(found_template)

        t2 = time.monotonic()
        self.times.append(t2 - t1)
        if t2 - t1 > 1:
            self.log.warning(f"Huge time detection! {t2 - t1}")
        elif len(self.times) > 200:
            self.log.info(f"detection max_time={max(self.times)} avg_time={sum(self.times) / len(self.times)}")
            self.times.clear()

    def analise_fingerprint(self,
                            ac_print: FingerPrint,
                            skip_template_name: str = '',
                            real_search: bool = True) -> str | None:

        ac_tmp_hash_similar: dict[str, list[str]] = {}
        for ac_hash in ac_print.hashes_offsets.keys():
            if ac_hash in self.all_templates_hash.keys():
                for tmp_name in self.all_templates_hash[ac_hash]:
                    if isinstance(ac_tmp_hash_similar.get(tmp_name), list):
                        ac_tmp_hash_similar[tmp_name].append(ac_hash)
                    else:
                        ac_tmp_hash_similar[tmp_name] = [ac_hash]

        for template_name in ac_tmp_hash_similar.keys():
            count_start_points = len(ac_tmp_hash_similar[template_name])
            if count_start_points < 11:
                continue
            elif template_name == skip_template_name:
                continue

            template_hashes_offsets = self.templates[template_name].fingerprint.hashes_offsets
            timely_hashes, shift = ac_print.get_timely_hashes(source_hashes_offsets=ac_print.hashes_offsets,
                                                              correct_hashes_offsets=template_hashes_offsets)
            if len(timely_hashes) < 10:
                continue

            offset_times = sorted(set(timely_hashes.values()))

            if len(timely_hashes) > 22 and len(offset_times) > 1:
                if real_search:
                    self.log.warning(f'found many points: {len(timely_hashes)}, offset_times: {offset_times}')
            elif len(offset_times) < 4:
                if real_search:
                    self.log.warning(f"the offset is too small: {offset_times}, count points: {len(timely_hashes)} "
                                     f"template_name:{template_name}")
                continue

            self.log.success(f'len points:{len(timely_hashes)} template:{template_name} chan_id:{ac_print.print_name} '
                             f'len offset_times: {len(offset_times)}, count_start_points: {count_start_points}')

            if real_search:
                args = functools.partial(ac_print.save_matching_print2png,
                                         first_points=ac_print.first_points,
                                         second_points=ac_print.second_points,
                                         arr2d=ac_print.arr2d,
                                         hashes=ac_tmp_hash_similar[template_name],
                                         save_folder='fingerprint_record',
                                         print_name=f"{ac_print.print_name}_{template_name}",
                                         shift_line=shift)
                self.event_loop.run_in_executor(self.tpe, args)

            return template_name

        return None


if __name__ == "__main__":
    cfg = Config()
    detector = Detector(audio_containers=dict(), config=cfg, ppe=ProcessPoolExecutor(), tpe=ThreadPoolExecutor())
    asyncio.create_task(detector.start_detection())
