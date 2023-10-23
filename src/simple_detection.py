import os
import random
import re
import time
import wave
from difflib import SequenceMatcher
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
        self.templates: dict[str, Template] = {}
        self.template_trends: dict[str, list] = {}
        self.first_times: list[float] = [0.0000000001]
        self.second_times: list[float] = [0.0000000001]
        self.three_times: list[float] = [0.0000000001]
        self.final_times: list[float] = [0.0000000001]
        self.matcher_times: list[float] = [0.0000000001]
        self.result = {}
        self.first_value = []
        self.second_value = []
        self.third_value = []
        self.fourth_value = []
        self.final_value = []

    def start(self) -> None:
        # This class use threading (see function self.run)
        super().start()

    def run(self):
        self.load_samples()
        self.run_simple_detection()

    def load_samples(self):
        self.log.info('start load_samples')
        folder = '/home/anydict/PycharmProjects/pysonic_nemo/tests/templates'
        file_list = [file for file in os.listdir(folder) if file.endswith('.wav')]

        for template_id, file_name in enumerate(file_list):
            file_path = os.path.join(folder, file_name)
            template_name = file_name.replace('.wav', '')

            audio_data, samplerate = soundfile.read(file_path, dtype='int16')
            self.templates[template_name] = Template(template_id=template_id,
                                                     template_name=template_name,
                                                     amplitudes=list(audio_data),
                                                     limit_samples=40)
            template_trend = [a for a in self.templates[template_name].trend_samples.values()]
            self.template_trends[template_name] = template_trend
            # self.log.info(f' template_name={file_name} trend: {self.templates[template_id].trend_samples_str}')

        self.log.info('end load_samples')

    def run_simple_detection(self):
        self.log.info(f'start simple_detection count templates={len(self.templates)}')
        start_time = time.time()
        while self.config.shutdown is False:
            time.sleep(0.001)
            last_second_ac_trends: dict[str, list] = {}
            for key in self.audio_containers.keys():
                audio_container = self.audio_containers[key]
                if audio_container.event_destroy:
                    continue
                if len(audio_container.found_templates) > 0:
                    continue
                trend_sample = []

                for seq_num in sorted(list(audio_container.trend_samples.keys())):
                    trend_sample.append(audio_container.trend_samples[seq_num])

                # a lot of silence
                if sum(trend_sample[-50:]) < 15:
                    continue
                last_second_ac_trends[key] = trend_sample[-50:]

            for key in last_second_ac_trends:
                # seq_nums = []
                # for seq_num in self.audio_containers[key].analyzed_samples.keys():
                #     seq_nums.append(seq_num)
                #
                # with wave.open(f"found/last_{key}.wav", "wb") as f:
                #     f.setnchannels(1)  # mono
                #     f.setsampwidth(2)
                #     f.setframerate(16000)
                #
                #     b = b''
                #     for seq_num in seq_nums[-50:]:
                #         for amp in self.audio_containers[key].analyzed_samples[seq_num]:
                #             b += pack('<h', amp)
                #     f.writeframes(b)

                for template_name in self.template_trends:
                    t1 = time.time()
                    # if len(self.audio_containers[key].found_templates) > 0:
                    #     continue  # TODO uncomment PROD
                    # sum_template_trend = sum(self.template_trends[template_name])
                    # sum_container_trend = sum(last_second_ac_trends[key])
                    # if sum_template_trend == 0:
                    #     self.log.warning(f"template_name={template_name} zero trend!!")
                    #     self.matcher_times.append(time.time() - t1)
                    #     continue
                    #
                    # if sum_container_trend / sum_template_trend < 0.5:
                    #     self.matcher_times.append(time.time() - t1)
                    #     continue
                    # elif sum_container_trend / sum_template_trend > 3:
                    #     self.matcher_times.append(time.time() - t1)
                    #     continue

                    matcher = SequenceMatcher(None, last_second_ac_trends[key], self.template_trends[template_name])
                    similarity = matcher.ratio()
                    self.matcher_times.append(time.time() - t1)
                    if similarity > 0.5:
                        self.check_audio_container(self.audio_containers[key], self.templates[template_name])
                    else:
                        self.check_audio_container(self.audio_containers[key], self.templates[template_name])

            break
        end_time = time.time()
        self.log.info(f'end simple_detection')
        self.log.info(f'avg_first_time={sum(self.first_times) / len(self.first_times)} sum={sum(self.first_times)}')
        self.log.info(f'....')
        self.log.info(f'avg_second_time={sum(self.second_times) / len(self.second_times)} sum={sum(self.second_times)}')
        self.log.info(f'....')
        self.log.info(f'avg_three_time={sum(self.three_times) / len(self.three_times)} sum={sum(self.three_times)}')
        self.log.info(f'....')
        self.log.info(f'avg_final_time={sum(self.final_times) / len(self.final_times)} sum={sum(self.final_times)}')
        self.log.info(f'....')
        self.log.info(f'sum_matcher_times={sum(self.matcher_times)}')
        self.log.info(f'....')
        self.log.info(f'all_time={end_time - start_time}')

        self.log.info(f'f1={sum(self.first_value) / len(self.first_value)}')
        self.log.info(f'f2={sum(self.second_value) / len(self.second_value)}')
        self.log.info(f'f3={sum(self.third_value) / len(self.third_value)}')
        self.log.info(f'f4={sum(self.fourth_value) / len(self.fourth_value)}')
        self.log.info(f'f5={sum(self.final_value) / len(self.final_value)}')

        self.log.info(f'f1={min(self.first_value)}')
        self.log.info(f'f2={min(self.second_value)}')
        self.log.info(f'f3={min(self.third_value)}')
        self.log.info(f'f4={min(self.fourth_value)}')
        self.log.info(f'f5={min(self.final_value)}')

    def get_similar_amplitude_sections(self, source_trend: str, template_trend: str) -> dict:
        start_time = time.time()
        mask_pattern = template_trend
        sections: dict[str, float] = {}
        position = 0
        while True:
            source_trend_cut = source_trend[position:len(mask_pattern) + position]
            position += 3

            if len(source_trend_cut) < len(mask_pattern):
                break
            if len(source_trend_cut.strip('0')) < len(mask_pattern) / 2:
                continue

            a = [*(source_trend_cut)]
            b = [*(mask_pattern)]

            a.extend(sorted(a))
            b.extend(sorted(b))

            c = [1 if i == j else 0 for i, j in zip(a, b)]
            match_percent = sum(c) / len(a)

            if match_percent > 0.8:
                position -= 2
                sections[source_trend_cut] = round(match_percent, 3)

        self.first_times.append(time.time() - start_time)
        sections = {k: v for k, v in sorted(sections.items(), key=lambda item: -item[1])}
        return sections

    def get_similarity_second(self, first_amps: list, second_amps: list) -> float:
        start_time = time.time()
        if len(first_amps) != len(second_amps):
            self.log.warning(f' diff len first={len(first_amps)} and len second_amps={len(second_amps)}')
        max_first_amp = max(first_amps)
        first_rate = []
        for amp in first_amps:
            first_rate.append(round(amp / max_first_amp * 2))

        max_second_amp = max(second_amps)
        second_rate = []
        for amp in second_amps:
            second_rate.append(round(amp / max_second_amp * 2))

        # matcher = SequenceMatcher(None, first_rate, second_rate)
        # return round(matcher.ratio(), 3)  # similarity
        c = [1 if i == j else 0 for i, j in zip(first_rate, second_rate)]
        match_percent = sum(c) / len(first_rate)
        self.second_times.append(time.time() - start_time)

        return round(match_percent, 3)

    #
    # def get_similarity_average(self, first_amps: list, second_amps: list) -> float:
    #     start_time = time.time()
    #     if len(first_amps) != len(second_amps):
    #         self.log.warning(f' diff len first={len(first_amps)} and len second_amps={len(second_amps)}')
    #     avg_first = sum(first_amps) / len(first_amps)
    #     first_patter = []
    #     for amp in first_amps:
    #         first_patter.append(round(amp / avg_first * 10))
    #
    #     avg_second = sum(second_amps) / len(second_amps)
    #     second_patter = []
    #     for amp in second_amps:
    #         second_patter.append(round(amp / avg_second * 10))
    #     self.log.info(first_patter)
    #     self.log.info(second_patter)
    #
    #     # matcher = SequenceMatcher(None, first_patter, second_patter)
    #     # return round(matcher.ratio(), 3)  # similarity
    #     c = [1 if i == j else 0 for i, j in zip(first_patter, second_patter)]
    #     match_percent = sum(c) / len(first_patter)
    #
    #     self.three_times.append(time.time() - start_time)
    #
    #     return round(match_percent, 3)

    def get_similarity_third(self, first_amps: list, second_amps: list) -> float:
        start_time = time.time()
        if len(first_amps) != len(second_amps):
            self.log.warning(f' diff len first={len(first_amps)} and len second_amps={len(second_amps)}')
        # avg_amp = sum(first_amps) / len(first_amps)
        max_amp = max(first_amps)

        b = second_amps.copy()
        c = []
        for a_val in first_amps:
            b_val = b.pop(0)
            c.append(abs(a_val - b_val) / max_amp)

        match_percent = 1 - sum(c) / len(c)

        self.three_times.append(time.time() - start_time)
        return round(match_percent, 3)

    @staticmethod
    def get_similarity_fourth(container_trend_str: str, template_trend_str: str) -> float:
        a = sorted(container_trend_str)
        b = sorted(template_trend_str)

        c = [1 if i == j else 0 for i, j in zip(a, b)]
        match_percent = sum(c) / len(a)

        return round(match_percent, 3)

    def final_check(self,
                    container_amps: list[int],
                    container_avg_amp: int,
                    template_amps: list[int],
                    template_avg_amp: int,
                    template_name: str,
                    unique: int) -> float:
        start_time = time.time()

        shift_avg = abs(container_avg_amp - template_avg_amp) / max(template_avg_amp, container_avg_amp)

        container_amps_up = [a for a in container_amps if a > 1000]
        template_amps_up = [a for a in template_amps if a > 1000]

        min_len = min(len(container_amps_up), len(template_amps_up))
        max_len = max(len(container_amps_up), len(template_amps_up))

        shift_rate = min_len / max_len

        self.log.info(f"template_name={template_name} unique={unique} d1={shift_avg} shift_rate={shift_rate}")
        self.log.info(f"template_name={template_name} unique={unique} a1={container_avg_amp} a2={template_avg_amp}")
        self.final_times.append(time.time() - start_time)
        avg_similar = 1 - shift_avg

        return round(avg_similar * shift_rate, 2)
        # abs_container_amps = list(map(abs, container_amps))
        # abs_template_amps = list(map(abs, template_amps))
        #
        # sum_abs_container_amp = sum(map(abs, abs_container_amps))
        #
        # min_between = np.array([abs_container_amps, abs_template_amps]).min(axis=0, initial=None).tolist()
        # max_between = np.array([abs_container_amps, abs_template_amps]).max(axis=0, initial=None).tolist()
        # sum_min_between = sum(map(abs, min_between))
        # sum_max_between = sum(map(abs, max_between))
        #
        # min_shift_rate = round(sum_min_between / sum_abs_container_amp, 3)
        # max_shift_rate = round(sum_abs_container_amp / sum_max_between, 3)
        #
        # # if min_shift_rate > 1:
        # #     min_shift_rate = 0.8
        # # elif min_shift_rate < 0.7:
        # #     min_shift_rate = 0.7
        # shift_rate = min(min_shift_rate, max_shift_rate)
        # avg_rate = (min_shift_rate + max_shift_rate) / 2
        # # max_other_rate = max(first_similar, second_similar, third_similar, fourth_similar) * 4
        # # min_other_rate = min(first_similar, second_similar, third_similar, fourth_similar) * 4
        #
        # # final_similar = max_other_rate * min_other_rate * shift_rate * avg_rate
        # similar = first_similar * second_similar * third_similar * fourth_similar * shift_rate * avg_rate * 6
        #
        # self.log.info(f'u={unique} min={min_shift_rate} max={max_shift_rate} t={template_name} f={similar}')

        # self.final_times.append(time.time() - start_time)

        # if similar < 1111:
        #     return round(similar, 3)
        # else:
        #     with wave.open(f"found/max_{unique}_{template_name}.wav", 'wb') as f:
        #         f.setnchannels(1)  # mono
        #         f.setsampwidth(2)
        #         f.setframerate(16000)
        #
        #         b = b''
        #         for amp in min_between:
        #             b += pack('<h', amp)
        #         f.writeframes(b)
        #     return round(similar, 3)

    def check_audio_container(self,
                              audio_container: AudioContainer,
                              template: Template):
        audio_container_trend = audio_container.trend_samples.copy()
        audio_container_trend_str = ''

        for seq_num in sorted(list(audio_container_trend.keys())):
            audio_container_trend_str += str(audio_container_trend[seq_num])

        found_patterns = self.get_similar_amplitude_sections(source_trend=audio_container_trend_str.strip('0'),
                                                             template_trend=template.trend_samples_str)

        for pattern, first_similar in found_patterns.items():

            search = re.search(pattern, audio_container_trend_str)

            seq_num_start = min(audio_container_trend.keys()) + search.start(0)  # this number first sample
            seq_num_last = min(audio_container_trend.keys()) + search.end(0) - 1  # this number last sample

            max_amps_found_pattern = []
            for seq_num in sorted(list(audio_container_trend.keys())):
                if seq_num_start <= seq_num <= seq_num_last:
                    max_amps_found_pattern.append(audio_container.max_amplitude_samples[seq_num])

            if template.template_id in audio_container.result_detections:
                result = audio_container.result_detections[template.template_id]
                if pattern in result.skip_trends:
                    continue
                result.add_skip_trend(pattern)
            else:
                result = ResultDetection(template_id=template.template_id,
                                         template_name=template.template_name,
                                         first_similar=first_similar)
                result.add_skip_trend(pattern)
                audio_container.add_result_detections(template_id=template.template_id,
                                                      result=result)

            second_similar = self.get_similarity_second(first_amps=max_amps_found_pattern,
                                                        second_amps=template.max_amp_samples_list)

            result.set_second_similar(similar=second_similar)
            # self.log.error(result)
            if second_similar < 0.4:
                # self.log.warning(f' skip on second={result}')
                continue

            third_similar = self.get_similarity_third(first_amps=max_amps_found_pattern,
                                                      second_amps=template.max_amp_samples_list)

            result.set_third_similar(similar=third_similar)
            # self.log.error(result)
            if third_similar < 0.4:
                # self.log.warning(f' skip on three={result}')
                continue

            fourth_similar = self.get_similarity_fourth(container_trend_str=pattern,
                                                        template_trend_str=template.trend_samples_str)
            #
            # all_similar = first_similar * second_similar * third_similar * fourth_similar * 4

            result.set_fourth_similar(fourth_similar)
            if fourth_similar < 0.7:
                self.log.warning(f'skip fourth_similar={fourth_similar} result={result}')
                continue

            unique = random.randrange(0, 1000000)
            container_amps = []

            self.log.success(f'fourth_similar={fourth_similar} unique={unique} name={template.template_name}')

            for seq_num in sorted(list(audio_container_trend.keys())):
                if seq_num_start <= seq_num <= seq_num_last:
                    container_amps.extend(audio_container.analyzed_samples[seq_num])

            container_avg_amp = int(sum(max_amps_found_pattern) / len(max_amps_found_pattern))
            final_similar = self.final_check(container_amps=container_amps,
                                             container_avg_amp=container_avg_amp,
                                             template_amps=template.amplitudes,
                                             template_avg_amp=template.avg_amplitude,
                                             template_name=template.template_name,
                                             unique=unique)

            other_similar = first_similar * second_similar * third_similar * fourth_similar * 4
            final_similar = round(final_similar * other_similar, 3)

            result.set_final_similar(final_similar)
            if final_similar < 0.7:
                self.log.warning(f'skip final_similar={final_similar} template_name={template.template_name}')
                continue

            self.first_value.append(first_similar)
            self.second_value.append(first_similar)
            self.third_value.append(third_similar)
            self.fourth_value.append(fourth_similar)
            self.final_value.append(final_similar)

            audio_container.add_found_template(template.template_name)

            self.log.success(result)
            self.log.success(pattern)
            self.log.success(audio_container_trend_str)
            self.log.success(template.trend_samples_str)

            self.log.success(f'call_id: {audio_container.call_id} ssrc={audio_container.em_host} unique={unique}')
            self.log.info(f'first_similar={first_similar}')
            self.log.info(f'second_similar={second_similar}')
            self.log.info(f'third_similar={third_similar}')
            self.log.info(f'final_similar={final_similar}')
            self.log.info(f'template_name={template.template_name}')

            similar_str = f'{first_similar}_{second_similar}_{third_similar}_{fourth_similar}_{final_similar}'

            found_name = f'{similar_str}_{audio_container.em_host}_{unique}_{template.template_name}.wav'

            with wave.open(os.path.join('found', found_name), 'wb') as f:
                f.setnchannels(1)  # mono
                f.setsampwidth(2)
                f.setframerate(16000)

                for seq_num in sorted(list(audio_container_trend.keys())):
                    if seq_num_start <= seq_num <= seq_num_last:
                        f.writeframes(audio_container.bytes_samples[seq_num])

            return


if __name__ == "__main__":
    cfg = Config(join_config=dict())
    sd = SimpleDetection(audio_containers=dict(), config=cfg)
    sd.start()
