import soundfile


def convert_samples2dict_bytes(samples: dict[int, list]) -> dict:
    """
    Convert samples to bytes

    :param samples:  amplitudes arranged by samples
    :return:
    """

    from struct import pack

    bytes_samples: dict[int, bytes] = {}
    for seq_num in sorted(samples.keys()):
        b = b''
        for amp in samples[seq_num]:
            b += pack('<h', amp)
        bytes_samples[seq_num] = b

    return bytes_samples


def save_samples2wav(samples: dict[int, list],
                     path: str = 'test_i_2.wav'):
    """
    Save samples to wav file

    Example use:
    template.save_template2wav(samples=template.samples, path='raw.wav')

    :param samples: amplitudes arranged by samples
    :param path: where to save the wav file
    :return:
    """
    import wave

    with wave.open(path, 'wb') as f:
        f.setnchannels(1)  # mono
        f.setsampwidth(2)
        f.setframerate(16000)

        dict_bytes = convert_samples2dict_bytes(samples=samples)

        for seq_num in sorted(samples.keys()):
            f.writeframes(dict_bytes[seq_num])


def convert_amplitudes2samples(amplitudes: list[int],
                               samples_size: int) -> dict[int, list]:
    samples: dict[int, list] = {}
    for seq_num in range(0, (len(amplitudes) // samples_size)):
        samples[seq_num] = list(amplitudes[seq_num * samples_size: (seq_num + 1) * samples_size])

    return samples


audio_data, samplerate = soundfile.read('i_8000.wav', dtype='int16')

print(samplerate)
print(audio_data)

count_samples: int = len(audio_data) // 160
print(count_samples)

old_samples: dict[int, list] = convert_amplitudes2samples(amplitudes=audio_data,
                                                          samples_size=160)
new_samples: dict[int, list] = {}
last_value = 0
for s, amps in old_samples.items():
    new_amps = []
    for a in amps:
        new_amp = (last_value + round(a)) // 2
        new_amps.append(new_amp)
        new_amps.append(a)
        last_value = a

    new_samples[s] = new_amps

save_samples2wav(new_samples)
