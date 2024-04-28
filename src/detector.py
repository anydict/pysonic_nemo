import asyncio
import os
import time
from asyncio import AbstractEventLoop
from concurrent.futures import ProcessPoolExecutor, Future
from datetime import datetime

import soundfile
from loguru import logger

from src.audio_container import AudioContainer
from src.config import Config, DEFAULT_SAMPLE_RATE
from src.custom_dataclasses.fingerprint import FingerPrint
from src.custom_dataclasses.template import Template
from src.fingerprint_mining import get_fingerprint


class Detector(object):
    def __init__(self,
                 config: Config,
                 audio_containers: dict[str, AudioContainer],
                 ppe: ProcessPoolExecutor):
        self.config = config
        self.audio_containers: dict[str, AudioContainer] = audio_containers
        self.ppe: ProcessPoolExecutor = ppe

        self.executor_tasks: list[Future] = []
        self.executor_times: list[float] = []
        self.detection_times: list[float] = []
        self.templates: dict[str, Template] = {}
        self.all_templates_hash: dict[str, list[str]] = {}
        self.chan_id_with_amps: dict[str, list[int]] = {}
        self.event_loop: AbstractEventLoop = asyncio.get_running_loop()
        self.log = logger.bind(object_id=self.__class__.__name__)
        self.log.info(f'init Detection')

    async def start_detection(self):
        self.log.info("start_detection")
        self.load_templates()
        asyncio.create_task(self.start_loop())
        asyncio.create_task(self.run_detection())

    def load_templates(self):
        self.log.info('start load_templates')
        folder = self.config.template_folder_path
        file_list = [file for file in os.listdir(folder) if file.endswith('.wav')]

        for template_id, file_name in enumerate(file_list):
            file_path = os.path.join(folder, file_name)
            template_name = file_name.replace('.wav', '')

            audio_data, samplerate = soundfile.read(file_path, dtype='int16')

            if samplerate != DEFAULT_SAMPLE_RATE:
                self.log.warning(f'incorrect sample_rate in file_name={file_name} / {samplerate}, SKIP!')
                continue
            elif hasattr(audio_data[0], "size") is False:
                self.log.warning(f'invalid audio_data in file_name={file_name}, SKIP!')
                continue
            elif hasattr(audio_data[0], "size") and audio_data[0].size == 2:
                self.log.warning(f'found stereo in file_name={file_name}, SKIP!')
                continue

            self.templates[template_name] = Template(template_id=template_id,
                                                     template_name=template_name,
                                                     limit_samples=0,
                                                     amplitudes=list(audio_data))
            for tmp_hash in self.templates[template_name].fingerprint.hashes_offsets.keys():
                if self.all_templates_hash.get(tmp_hash) is None:
                    self.all_templates_hash[tmp_hash] = [template_name]
                elif template_name in self.all_templates_hash[tmp_hash]:
                    continue
                else:
                    self.all_templates_hash[tmp_hash].append(template_name)

        for template_name in self.templates.keys():
            detect_result = self.analise_fingerprint(ac_print=self.templates[template_name].fingerprint,
                                                     skip_template_name=self.templates[template_name].template_name,
                                                     real_search=False)
            if detect_result:
                found_template, match_count = detect_result
                self.log.warning(f"Found cross template: {template_name} >> {detect_result} "
                                 f"hash_count_1={len(self.templates[template_name].fingerprint.hashes_offsets)} "
                                 f"hash_count_2={len(self.templates[found_template].fingerprint.hashes_offsets)} ")

                # a_file_path = os.path.join(folder, f'{template_name}.wav')
                # b_file_path = os.path.join(folder, f'{found_template}.wav')
                # if self.templates[found_template].count_samples > self.templates[template_name].count_samples:
                #     if os.path.isfile(a_file_path):
                #         os.remove(a_file_path)
                # else:
                #     if os.path.isfile(b_file_path):
                #         os.remove(a_file_path)
        self.log.info(f"end load_templates, hashes: {len(self.all_templates_hash)}, templates: {len(self.templates)}")

    async def start_loop(self):
        self.log.info("start loop for prepare amplitudes and detection")
        while self.config.wait_shutdown is False:
            await asyncio.sleep(0.1)
            await self.run_prepare_amplitude()
            await self.add_amps_in_executor()
        self.log.info("end start_loop")

    async def run_prepare_amplitude(self):
        if len(self.audio_containers) == 0:
            await asyncio.sleep(0.5)
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

            audio_container.last_detect_seq_num = audio_container.seq_num_last_package
            self.chan_id_with_amps[chan_id] = ac_amps

        # self.log.info(f"len self.chan_id_with_amps={self.chan_id_with_amps}")

    async def add_amps_in_executor(self):
        if len(self.chan_id_with_amps) == 0:
            return

        self.log.info("BEFORE run_in_executor")
        for chan_id in list(self.chan_id_with_amps):
            ac_amps = self.chan_id_with_amps.pop(chan_id)
            task = self.event_loop.run_in_executor(self.ppe, get_fingerprint, chan_id, ac_amps)
            self.executor_tasks.append(task)

    async def run_detection(self):
        self.log.info('start run_detection')
        while self.config.wait_shutdown is False:
            if len(self.executor_tasks) == 0:
                await asyncio.sleep(0.1)
                continue

            t1 = time.monotonic()
            for task in asyncio.as_completed(self.executor_tasks):
                fingerprint: FingerPrint = await task
                detect_result = self.analise_fingerprint(fingerprint)
                audio_container = self.audio_containers.get(fingerprint.print_name)
                if audio_container is None:
                    continue

                audio_container.duration_check_detect += time.monotonic() - t1

                if detect_result is not None:
                    found_template, match_count = detect_result
                    self.audio_containers[fingerprint.print_name].add_found_template(found_template)

            t2 = time.monotonic()
            self.detection_times.append(t2 - t1)

            if len(self.detection_times) > 10:
                self.log.info(f"detection_times={max(self.detection_times)} "
                              f"avg_time={sum(self.detection_times) / len(self.detection_times)} "
                              f"max_time={max(self.detection_times)}")
                self.detection_times.clear()

            for task in self.executor_tasks.copy():
                if task.done():
                    self.executor_tasks.remove(task)
        self.log.info('end run_detection')

    def analise_fingerprint(self,
                            ac_print: FingerPrint,
                            skip_template_name: str = '',
                            real_search: bool = True) -> tuple[str, int] | None:
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

            offset_times = sorted(set(timely_hashes.values()))

            len_timely_hashes, len_offset_times = len(timely_hashes), len(offset_times)

            if len_timely_hashes < 5 or len_offset_times < 2:
                continue

            match_count = len_timely_hashes + len_offset_times * 15

            if match_count < 80:
                if match_count > 60:
                    self.log.info(f'match_count={match_count} {ac_print.print_name} > {template_name}')
                continue

            if real_search:
                self.log.success(f'len points:{len(timely_hashes)} template:{template_name} '
                                 f'chan_id:{ac_print.print_name} len offset_times: {len(offset_times)}, '
                                 f'count_start_points: {count_start_points}')
                if self.config.save_png_match_detection:
                    ac_print.save_matching_print2png(first_points=ac_print.first_points,
                                                     second_points=ac_print.second_points,
                                                     arr2d=ac_print.arr2d,
                                                     hashes=ac_tmp_hash_similar[template_name],
                                                     save_folder='fingerprint_record',
                                                     print_name=f"{ac_print.print_name}_{template_name}",
                                                     shift_line=shift)

            return template_name, match_count

        return None


if __name__ == "__main__":
    cfg = Config()
    detector = Detector(audio_containers=dict(), config=cfg, ppe=ProcessPoolExecutor())
    asyncio.create_task(detector.start_detection())
