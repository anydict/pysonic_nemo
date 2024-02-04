import asyncio
import functools
import json
import os
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from os import makedirs
from pathlib import Path
from typing import Optional

from loguru import logger

import src.custom_models.http_models as http_models
from src.config import (Config,
                        DEFAULT_SAMPLE_WIDTH,
                        DEFAULT_SAMPLE_RATE,
                        SEQ_NUMBER_AFTER_FIRST_RESET,
                        AMPLITUDE_THRESHOLD_BEEP,
                        AMPLITUDE_THRESHOLD_NOISE,
                        AMPLITUDE_THRESHOLD_VOICE)
from src.custom_dataclasses.package import Package
from src.http_clients.callpy_client import CallPyClient

CODE_ERROR = -9
CODE_AWAIT = -1
CODE_NOT_FOUND = 0


class AudioContainer(object):
    def __init__(self,
                 config: Config,
                 em_host: str,
                 em_port: int,
                 chan_id: str,
                 call_id: str,
                 event_create,
                 callpy_client: CallPyClient,
                 tpe: ThreadPoolExecutor
                 ):
        self.config: Config = config
        self.em_host: str = em_host
        self.em_port: int = em_port
        self.call_id: str = call_id
        self.chan_id: str = chan_id
        self.callpy_client: CallPyClient = callpy_client
        self.tpe: ThreadPoolExecutor = tpe

        self.em_ssrc: int = CODE_AWAIT

        self.event_create: http_models.EventCreate = event_create
        self.event_progress: Optional[http_models.EventProgress] = None
        self.event_answer: Optional[http_models.EventAnswer] = None
        self.events_detect: list[http_models.EventDetect] = []
        self.event_destroy: Optional[http_models.EventDestroy] = None

        self.packages_for_analyse: list[Package] = []
        self.bytes_samples: dict[int, bytes] = {}
        self.analyzed_samples: dict[int, list[int]] = {}
        self.max_amplitude_samples: dict[int, int] = {}
        self.min_amplitude_samples: dict[int, int] = {}

        self.trend_samples: dict[int, int] = {}

        self.detect_until_time: datetime = datetime.now() + timedelta(minutes=2)
        self.break_while_time: datetime = datetime.now() + timedelta(minutes=90)
        self.time_add_first_package: Optional[datetime] = None
        self.time_add_last_package: Optional[datetime] = None

        self.duration_stream: float = 0
        self.duration_check_detect: float = 0
        self.number_resets_sequence: int = 0
        self.length_payload = CODE_AWAIT
        self.seq_num_first_package: int = CODE_AWAIT
        self.seq_num_last_package: int = CODE_AWAIT

        self.seq_num_answer_package: int = CODE_AWAIT
        self.seq_num_first_beep: int = CODE_AWAIT
        self.seq_num_noise_after_answer: int = CODE_AWAIT
        self.seq_num_voice_before_answer: int = CODE_AWAIT
        self.amp_adc_noise: int = CODE_AWAIT
        self.found_first_noise: int = 0

        self.last_detect_seq_num: int = 0
        self.found_templates: str = ''

        self.log = logger.bind(object_id=f'{chan_id}@{em_host}:{em_port}')
        self.log.info(f'init AudioPackages call_id: {call_id} chan_id:{chan_id}')

    def add_found_template(self, name: str):
        self.log.info(f'found template with name={name}')
        self.detect_until_time = datetime.now()
        self.found_templates = name

    def get_sample_width(self) -> int:
        if self.event_create:
            if self.event_create.info.em_sample_width != DEFAULT_SAMPLE_WIDTH:
                self.log.warning('Correct work with another sample_width is not guaranteed')
            return self.event_create.info.em_sample_width
        else:
            return DEFAULT_SAMPLE_WIDTH

    def get_sample_rate(self) -> int:
        if self.event_create:
            if self.event_create.info.em_sample_rate != DEFAULT_SAMPLE_RATE:
                self.log.warning('Correct work with another sample_rate is not guaranteed')
            return self.event_create.info.em_sample_rate
        else:
            return DEFAULT_SAMPLE_RATE

    def get_duration_one_sample(self):
        return self.length_payload / self.get_sample_width() / self.get_sample_rate()

    def append_package_for_analyse(self, package: Package):
        self.time_add_last_package: datetime = datetime.now()
        self.packages_for_analyse.append(package)

        if self.seq_num_first_package == CODE_AWAIT:
            self.log.info(f"add first package: {package.seq_num}")
            self.seq_num_first_package = package.seq_num
            self.seq_num_last_package = package.seq_num
            self.time_add_first_package = datetime.now()
            self.length_payload = len(package.payload)
            asyncio.create_task(self.start_parse())

    def add_event_progress(self, event: http_models.EventProgress):
        self.event_progress = event

    def add_event_answer(self, event: http_models.EventAnswer):
        self.event_answer = event
        if datetime.now() < self.detect_until_time:
            self.detect_until_time = datetime.now() + timedelta(seconds=15)

        create_datetime = datetime.fromisoformat(self.event_create.event_time)
        answer_datetime = datetime.fromisoformat(event.event_time)
        duration_before_answer = (answer_datetime - create_datetime).total_seconds()
        number_samples_before_answer = duration_before_answer / self.get_duration_one_sample()
        self.seq_num_answer_package: int = int(self.seq_num_first_package + number_samples_before_answer)

    def add_event_detect(self, event: http_models.EventDetect):
        if datetime.now() < self.detect_until_time:
            self.detect_until_time = datetime.now()

        self.events_detect.append(event)

    def add_event_destroy(self, event: http_models.EventDestroy):
        self.event_destroy = event
        self.break_while_time = datetime.now() + timedelta(seconds=5)

    async def start_parse(self):
        self.log.info("begin start_parse")
        try:
            while self.config.alive and datetime.now() < self.break_while_time:
                if self.event_answer:
                    await asyncio.sleep(0.2)
                else:
                    await asyncio.sleep(0.5)

                self.check_end()
                self.fast_build()
                self.find_first_noise()

                if self.seq_num_first_beep == CODE_AWAIT:
                    self.find_seq_num_first_beep()
                    self.find_amp_adc_noise()

                if self.event_answer:
                    self.find_seq_num_noise_after_answer()
                else:
                    self.find_seq_num_voice_before_answer()

        except Exception as e:
            self.log.error(e)
            self.log.exception(e)
            return

        self.log.info("end start_parse")
        self.start_save()

    def check_end(self):
        if datetime.now() > self.break_while_time:
            return

        elif (datetime.now() - self.time_add_last_package).total_seconds() > 30:
            self.break_while_time = self.time_add_last_package + timedelta(seconds=30)
            self.log.error('new packages are not received and event_destroy not found')
            return

    def fast_build(self) -> None:

        parse_packages = self.packages_for_analyse[0: 400]
        self.packages_for_analyse = self.packages_for_analyse[len(parse_packages):]

        for package in parse_packages:
            fix_seq_num = package.seq_num

            # find reset sequence package number
            if self.seq_num_last_package - fix_seq_num > SEQ_NUMBER_AFTER_FIRST_RESET - 1000:
                if fix_seq_num < 1000:
                    self.number_resets_sequence = round(self.seq_num_last_package / SEQ_NUMBER_AFTER_FIRST_RESET)
                fix_seq_num = package.seq_num + (self.number_resets_sequence * SEQ_NUMBER_AFTER_FIRST_RESET)

            if self.seq_num_last_package < fix_seq_num:
                self.seq_num_last_package = fix_seq_num

            self.analyzed_samples[fix_seq_num] = package.amplitudes

            self.bytes_samples[fix_seq_num] = package.wav_bytes
            self.max_amplitude_samples[fix_seq_num] = package.max_amplitude
            self.min_amplitude_samples[fix_seq_num] = package.min_amplitude

        self.duration_stream = len(self.analyzed_samples) * self.get_duration_one_sample()

        if datetime.now() < self.detect_until_time and len(parse_packages) > 50:
            self.log.warning(f'find delay!!! count parse_packages={len(parse_packages)}')

        if len(self.analyzed_samples) == self.seq_num_last_package - self.seq_num_first_package + 1:
            return

        lost_sequences = []
        for seq_num in range(self.seq_num_first_package, self.seq_num_last_package):
            if seq_num not in self.analyzed_samples:
                lost_sequences.append(seq_num)
                self.analyzed_samples[seq_num] = self.analyzed_samples[self.seq_num_first_package]
                self.max_amplitude_samples[seq_num] = 0
                self.min_amplitude_samples[seq_num] = 0

        if len(lost_sequences) > 0:
            self.log.error(f'lost from {lost_sequences[0]} to {lost_sequences[-1]}, count={len(lost_sequences)}')

    def find_seq_num_first_beep(self) -> None:
        if self.seq_num_first_beep != CODE_AWAIT:
            return

        for seq_num in sorted(self.max_amplitude_samples.keys()):
            if self.seq_num_answer_package != CODE_AWAIT:
                self.log.warning(f'find answer, but not found beep!')
                self.seq_num_first_beep = CODE_NOT_FOUND
                return
            elif self.max_amplitude_samples[seq_num] > AMPLITUDE_THRESHOLD_BEEP:
                self.seq_num_first_beep = seq_num
                self.log.debug(f'find_first_beep_time seq_num={seq_num}')
                return

    def find_amp_adc_noise(self) -> None:
        if self.amp_adc_noise != CODE_AWAIT:
            return
        elif self.seq_num_first_beep > 0:
            self.amp_adc_noise = CODE_NOT_FOUND
            return
        elif self.event_answer is not None:
            self.amp_adc_noise = CODE_NOT_FOUND
            return

        for seq_num in self.analyzed_samples:
            max_amp = self.max_amplitude_samples[seq_num]
            min_amp = self.min_amplitude_samples[seq_num]

            if min(abs(min_amp), abs(max_amp)) < AMPLITUDE_THRESHOLD_NOISE:
                continue
            elif max_amp - min_amp > AMPLITUDE_THRESHOLD_BEEP:
                self.amp_adc_noise = CODE_NOT_FOUND
                return
            elif 0.8 < min_amp / max_amp < 1.25:
                avg = (max_amp + min_amp) // 2
                self.log.debug(f'found ADC noise min_amp={min_amp} and max_amp={max_amp} avg={avg}')
                self.amp_adc_noise = avg
                return

    def find_seq_num_noise_after_answer(self) -> None:
        if self.seq_num_noise_after_answer != CODE_AWAIT:
            return

        if self.event_answer is None:
            return

        counter = 0
        for seq_num, max_amp in self.max_amplitude_samples.items():
            if seq_num < self.seq_num_answer_package:
                continue

            if self.amp_adc_noise > 0:
                max_amp = max_amp - self.amp_adc_noise

            if max_amp > AMPLITUDE_THRESHOLD_NOISE:
                counter += 1
            else:
                counter = max(counter - 0.3, 0)

            if counter > 2:
                self.log.info(f"found noise after answer seq_num={seq_num}")
                self.seq_num_noise_after_answer = seq_num
                return

    def find_seq_num_voice_before_answer(self) -> None:
        if self.seq_num_voice_before_answer != CODE_AWAIT:
            return

        seq_num_last_beep = 0
        counter = 0
        for seq_num, max_amp in self.max_amplitude_samples.items():
            if seq_num < seq_num_last_beep:
                continue
            elif max_amp > AMPLITUDE_THRESHOLD_BEEP:
                counter += 1
            else:
                counter = 0

            if counter > 10:
                seq_num_last_beep = seq_num + 50

        if counter > 1:
            seq_num_last_beep = self.seq_num_last_package

        for seq_num in sorted(self.max_amplitude_samples.keys()):
            if seq_num < seq_num_last_beep:
                continue

            if self.max_amplitude_samples[seq_num] > AMPLITUDE_THRESHOLD_VOICE:
                self.log.info(f"found voice before answer seq_num={seq_num}")
                self.seq_num_voice_before_answer = seq_num
                return

    def find_first_noise(self) -> None:
        if self.found_first_noise == 1:
            return
        elif max(self.seq_num_first_beep, self.seq_num_noise_after_answer, self.seq_num_voice_before_answer) > 0:
            self.found_first_noise = 1
            return

        if max(self.max_amplitude_samples) > AMPLITUDE_THRESHOLD_NOISE:
            counter = 0
            for seq_num, max_amp in self.max_amplitude_samples.items():
                min_amp = self.min_amplitude_samples.get(seq_num, 0)
                if max_amp - min_amp > AMPLITUDE_THRESHOLD_NOISE:
                    counter += 1

            if counter > 1:
                self.log.success('FOUND FIRST NOISE')
                self.found_first_noise = 1
                return

    def start_save(self) -> None:
        try:
            self.log.info('start_save')
            info = {
                "seq_num_first_package": self.seq_num_first_package,
                "seq_num_first_beep": self.seq_num_first_beep,
                "seq_num_noise_after_answer": self.seq_num_noise_after_answer,
                "seq_num_answer_package": self.seq_num_answer_package,
                "seq_num_voice_before_answer": self.seq_num_voice_before_answer,
                "seq_num_last_package": self.seq_num_last_package,
                "found_first_noise": self.found_first_noise,
                "get_sample_rate": self.get_sample_rate(),
                "get_sample_width": self.get_sample_width(),
                "get_duration_one_sample": self.get_duration_one_sample(),
                "amp_adc_noise": self.amp_adc_noise,
                "len_parse_packs": len(self.max_amplitude_samples),
                "len_raw_packs": len(self.packages_for_analyse),
                "duration_check_detect": self.duration_check_detect
            }
            self.log.success(f'info: {json.dumps(info)}')

            if len(self.packages_for_analyse) > 0:
                self.log.error(f'found raw packs, count: {len(self.packages_for_analyse)}')

            if self.seq_num_last_package == CODE_AWAIT:
                self.log.warning('not found packs')

            if self.event_create.info.save_record == 1:
                file_path = self.get_path_for_save_file(self.chan_id, self.event_create.info.save_format)
                args = functools.partial(self.save_wav_file,
                                         file_path=file_path,
                                         bytes_samples=self.bytes_samples,
                                         sample_width=self.get_sample_width(),
                                         sample_rate=self.get_sample_rate())
                asyncio.get_event_loop().run_in_executor(self.tpe, args)
                self.log.info(f"running save file: {file_path}")

        except Exception as exc:
            self.log.error(exc)
            self.log.exception(exc)

    @staticmethod
    def get_path_for_save_file(file_name: str, save_format: str = 'wav', folder: str = 'records'):
        sysdate = datetime.now()
        path = os.path.join(folder, str(sysdate.year), str(sysdate.month), str(sysdate.day), str(sysdate.hour))
        if Path(path).is_dir() is False:
            makedirs(path, exist_ok=True)

        return f'{path}/{file_name.replace(".wav", "")}.{save_format}'

    @staticmethod
    def save_wav_file(file_path: str, bytes_samples: dict[int, bytes], sample_width: int, sample_rate: int):
        try:
            with wave.open(file_path, 'wb') as f:
                f.setnchannels(1)  # mono
                f.setsampwidth(sample_width)
                f.setframerate(sample_rate)

                for data in bytes_samples.values():
                    f.writeframes(data)
        except Exception as e:
            print(f'ERROR save_wav_file, e={e}')
