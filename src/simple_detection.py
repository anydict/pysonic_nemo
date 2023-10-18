import re
import time
import wave
from struct import pack
import numpy as np
from difflib import SequenceMatcher
from random import randrange
from threading import Thread
from loguru import logger
import soundfile

from src.audio_container import AudioContainer
from src.config import Config
from src.custom_dataclasses.result_detection import ResultDetection
from src.custom_dataclasses.template import Template


class SimpleDetection(Thread):
    def __init__(self, config: Config, audio_containers: dict[str, AudioContainer]):
        Thread.__init__(self)
        self.config = config
        self.audio_containers: dict[str, AudioContainer] = audio_containers
        self.log = logger.bind(object_id=f'SimpleDetection')
        self.log.info(f'init SimpleDetection')
        self.templates: dict[int, Template] = {}
        self.skip_amps: list[list] = []
        self.time_list: list[float] = []

    def start(self) -> None:
        # This class use threading (see function self.run)
        super().start()

    def run(self):
        self.load_samples()
        self.start_simple_detection()

    def load_samples(self):
        audio_data, samplerate = soundfile.read(
            '/home/anydict/PycharmProjects/pysonic_nemo/src/custom_templates/hello.wav',
            dtype='int16')

        for num in range(1, 3):
            self.templates[num] = Template(template_id=num,
                                           template_name=f'hell{num}',
                                           amplitudes=list(audio_data))

        template = Template(template_id=0,
                            template_name=f'hell{0}',
                            amplitudes=list(audio_data))
        self.log.info('load_samples')
        self.log.info(f'count samples: {template.count_samples}')
        self.log.info(f'sample size: {template.sample_size}')
        self.log.info(f'count amplitudes: {template.count_amplitudes}')
        self.log.info(f'max amplitudes in sample: {template.max_amp_samples}')
        self.log.info(f'avg amplitudes in sample: {template.avg_amp_samples}')
        self.log.info(f'max amplitude value: {template.max_amplitude_value}')
        self.log.info(f'max amplitude seq_num: {template.max_amplitude_seq_num}')

        self.log.info(f'upper_trend_amp: {template.trend_samples}')
        self.log.info(f'upper_trend_amp_str: {template.trend_samples_str}')
        # self.log.info(f' max_rate_amp_samples: {template.max_rate_amp_samples}')
        # self.log.info(f' qwe: {"".join([str(t) for t in template.max_rate_amp_samples.values()])}')
        self.templates[template.template_id] = template

    def start_simple_detection(self):
        while self.config.shutdown is False:
            time.sleep(0.02)
            for key in list(self.audio_containers.keys()):
                audio_container = self.audio_containers[key]
                if audio_container.event_destroy:
                    continue
                self.check_audio_container(audio_container)

    def get_similarity_amplitudes(self, first_amps: list, second_amps: list) -> float:
        if len(first_amps) != len(second_amps):
            self.log.warning(f' diff len first={len(first_amps)} and len second_amps={len(second_amps)}')
        max_first_amp = max(first_amps)
        first_rate = []
        for amp in first_amps:
            first_rate.append(round(amp / max_first_amp * 10 / 5))

        max_second_amp = max(second_amps)
        second_rate = []
        for amp in second_amps:
            second_rate.append(round(amp / max_second_amp * 10 / 5))

        matcher = SequenceMatcher(None, first_rate, second_rate)
        return round(matcher.ratio(), 3)  # similarity

    def get_similarity_average(self, first_amps: list, second_amps: list) -> float:
        if len(first_amps) != len(second_amps):
            self.log.warning(f' diff len first={len(first_amps)} and len second_amps={len(second_amps)}')
        avg_first = sum(first_amps) / len(first_amps)
        first_patter = []
        for amp in first_amps:
            first_patter.append(1 if amp > avg_first else 0)
        self.log.info(first_patter)

        avg_second = sum(second_amps) / len(second_amps)
        second_patter = []
        for amp in second_amps:
            second_patter.append(1 if amp > avg_second else 0)
        self.log.info(second_patter)

        matcher = SequenceMatcher(None, first_patter, second_patter)
        return round(matcher.ratio(), 3)  # similarity

    @staticmethod
    def get_similar_amplitude_sections(source_trend: str, template_trend: str) -> dict:
        mask_pattern = template_trend
        sections: dict[str, float] = {}

        # exit if mask at half is empty (lots of dots)
        while mask_pattern.count('.') / len(mask_pattern) < 0.5:
            place = randrange(0, len(mask_pattern) - 1)
            if mask_pattern[place] == '.':
                # when replacing dot with itself
                continue
            mask_pattern = mask_pattern[:place] + '.' + mask_pattern[place + 1:]
            results = re.findall(mask_pattern, source_trend)

            for result in results:
                matcher = SequenceMatcher(None, template_trend, result)
                first_similarity = matcher.ratio()
                if first_similarity > 0.7:
                    sections[result] = first_similarity
                else:
                    continue

        return sections

    def check_audio_container(self, audio_container: AudioContainer):
        for template in self.templates.values():
            if len(audio_container.samples_trend) < template.count_samples:
                # the number of samples is not enough to check
                continue
            if template.template_name in audio_container.found_templates:
                # this template already found in audio_container
                continue

            audio_container_trend = audio_container.samples_trend.copy()
            audio_container_trend_str = ''
            first_seq_num = min(audio_container_trend.keys())
            last_seq_num = max(audio_container_trend.keys())

            for seq_num in range(first_seq_num, last_seq_num + 1):
                audio_container_trend_str += str(audio_container_trend[seq_num])
            if audio_container_trend_str.strip('0') == '':
                # empty trend
                break

            similar_patterns = self.get_similar_amplitude_sections(source_trend=audio_container_trend_str,
                                                                   template_trend=template.trend_samples_str)

            for pattern, first_similar in similar_patterns.items():
                search = re.search(pattern, audio_container_trend_str)
                # this sequence number samples (NOT TREND)
                seq_num_start = first_seq_num + search.start(0) - 1  # this number first sample
                seq_num_last = first_seq_num + search.end(0) - 1  # this number last sample

                max_amps_found_section = []
                for seq_num in range(seq_num_start, seq_num_last + 1):
                    max_amps_found_section.append(audio_container.max_amplitude_analyzed_samples[seq_num])

                result = ResultDetection(template_id=template.template_id,
                                         skip_trends=max_amps_found_section,
                                         first_similar=first_similar)
                audio_container.add_result_detections(template_id=template.template_id,
                                                      result=result)
                if pattern in audio_container.result_detections[template.template_id].skip_trends:
                    continue

                second_similarity = self.get_similarity_amplitudes(first_amps=max_amps_found_section,
                                                                   second_amps=template.max_amp_samples_list)

                result.set_second_similar(similar=second_similarity)
                if second_similarity < 0.8:
                    self.log.warning(result)
                    continue

                self.log.info(f'second_similarity={second_similarity}')

                three_similarity = self.get_similarity_average(first_amps=max_amps_found_section,
                                                               second_amps=template.max_amp_samples_list)

                result.set_third_similar(similar=three_similarity)
                if three_similarity < 0.9:
                    self.log.warning(result)
                    self.log.info(f'skip three_similarity={three_similarity}')
                    continue

                audio_container.add_found_template(template.template_name)

                self.log.info(f'three_similarity={three_similarity}')

                start_time = time.time()
                container_amps = []

                for seq_num in range(seq_num_start, seq_num_last + 1):
                    try:
                        container_amps.extend(audio_container.analyzed_samples[seq_num])
                    except:
                        self.log.warning(f'seq_num={seq_num} max={audio_container.analyzed_samples}')

                half = int(len(container_amps) / 2)

                sum_container_amp = sum(map(abs, container_amps[:half]))
                # min_amp_between = [min(i) for i in zip_longest(container_amps[:half], template.amplitudes[:half])]
                min_amp_between = np.array([container_amps[:half],
                                            template.amplitudes[:half]]).min(axis=0, initial=None).tolist()

                # max_amp_between = np.array([container_amps[:half],
                #                             template.amplitudes[:half]]).max(axis=0, initial=None).tolist()
                # max_amp_between = [max(i) for i in zip_longest(container_amps, template.amplitudes)]

                sum_between_min = sum(map(abs, min_amp_between))
                # sum_between_max = sum(map(abs, max_amp_between))

                with wave.open(f'between_{audio_container.em_ssrc}_{template.template_id}.wav', 'wb') as f:
                    f.setnchannels(1)  # mono
                    f.setsampwidth(2)
                    f.setframerate(16000)

                    b = b''
                    for amp in min_amp_between:
                        b += pack('<h', amp)
                    f.writeframes(b)

                # with wave.open(f'4444_{random.randrange(1, 1000)}.wav', 'wb') as f:
                #     f.setnchannels(1)  # mono
                #     f.setsampwidth(2)
                #     f.setframerate(16000)
                #
                #     b = b''
                #     for amp in max_amp_between:
                #         b += pack('<h', amp)
                #     f.writeframes(b)

                amplitude_similar = sum_container_amp / sum_between_min
                result.set_amplitude_similar(similar=amplitude_similar)
                # resonance_max = sum_container_amp / sum_between_max

                self.log.success(result)
                self.log.info(f' amplitude_similar={amplitude_similar}')
                self.log.info(f' sum_container_amp={sum_container_amp} half={half}')
                self.log.info(f' sum_between_min={sum_between_min}')

                if round(amplitude_similar, 1) not in (0.9, 1.0, 1.1, 1.2):
                    self.log.info(f'skip amplitude_similar={amplitude_similar}')
                    self.skip_amps.append(max_amps_found_section)
                    continue

                self.log.info(f'start={search.start(0)} end={search.end(0)}')
                self.log.success(f'call_id: {audio_container.call_id} ssrc={audio_container.em_ssrc}')

                end_time = time.time()
                self.time_list.append(end_time - start_time)

                self.log.info(f' cnt time_list={len(self.time_list)} ')
                self.log.info(f' avg_time={sum(self.time_list) / len(self.time_list)} ')
                self.log.info(f' max_time={max(self.time_list)} sum={sum(self.time_list)}')
                self.log.info(f' seq_num_first_package={audio_container.seq_num_first_package}')
                self.log.info(f' seq_num_last_package={audio_container.seq_num_last_package}')
                self.log.info(f' cnt_samples={len(audio_container.max_amplitude_analyzed_samples)}')
                self.log.info(f' len_trend={len(audio_container_trend_str)}')
                self.log.info(audio_container.max_amplitude_analyzed_samples)
                self.log.info(audio_container.samples_trend)
                self.log.info(f' audio_container_trend_str={audio_container_trend_str}')

                self.log.info(f' EM: start_amp={audio_container.max_amplitude_analyzed_samples[seq_num_start]}')
                self.log.info(f' EM: end_amp={audio_container.max_amplitude_analyzed_samples[seq_num_last]}')

                self.log.info(f'TEMPLATE {template.template_name}')
                self.log.info(f' template start_amp={template.max_amp_samples[0]}')
                self.log.info(f' template end_amp={template.max_amp_samples[template.count_samples - 1]}')

                with wave.open(f'found_section_{audio_container.em_ssrc}_{template.template_id}.wav', 'wb') as f:
                    f.setnchannels(1)  # mono
                    f.setsampwidth(2)
                    f.setframerate(16000)

                    for seq_num in range(seq_num_start, seq_num_last + 1):
                        f.writeframes(audio_container.bytes_samples[seq_num])

                # self.log.info(max_amp_samples[min(simple_dff_samples)])
                # self.log.info(max_amp_samples[max(simple_dff_samples)])
                break


if __name__ == "__main__":
    cfg = Config(join_config=dict())
    sd = SimpleDetection(audio_containers=dict(), config=cfg)
    sd.start()
