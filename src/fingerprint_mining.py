from operator import itemgetter
from typing import List, Tuple
import numpy as np
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
from scipy.ndimage import maximum_filter
from scipy.ndimage import (binary_erosion,
                           generate_binary_structure,
                           iterate_structure)

from src.custom_dataclasses.fingerprint import FingerPrint

CONNECTIVITY_MASK = 1
DEFAULT_FS = 16000
DEFAULT_WINDOW_SIZE = 1024  # 4096
DEFAULT_OVERLAP_RATIO = 0.6
DEFAULT_FAN_VALUE = 5  # 15 was the original value.
DEFAULT_AMP_MIN = 28
PEAK_NEIGHBORHOOD_SIZE = 5  # 20 was the original value.
MIN_HASH_TIME_DELTA = 0
MAX_HASH_TIME_DELTA = 200
PEAK_SORT = True
FINGERPRINT_REDUCTION = 40
TOPN = 2


def get_fingerprint(print_name: str,
                    amplitudes: list[int],
                    fs: int = DEFAULT_FS,
                    wsize: int = DEFAULT_WINDOW_SIZE,
                    wratio: float = DEFAULT_OVERLAP_RATIO,
                    fan_value: int = DEFAULT_FAN_VALUE,
                    amp_min: int = DEFAULT_AMP_MIN) -> FingerPrint:
    """
    FFT the channel, log transform output, find local maxima, then return locally sensitive hashes.

    :param amplitudes: channel samples to fingerprint.
    :param fs: audio sampling rate.
    :param wsize: FFT windows size.
    :param wratio: ratio by which each sequential window overlaps the last and the next window.
    :param fan_value: degree to which a fingerprint can be paired with its neighbors.
    :param amp_min: minimum amplitude in spectrogram in order to be considered a peak.
    :return: a list of hashes with their corresponding offsets.
    """
    # FFT the signal and extract frequency components
    pxx, freqs, bins = mlab.specgram(
        amplitudes,
        NFFT=wsize,
        Fs=fs,
        window=mlab.window_hanning,
        noverlap=int(wsize * wratio)
    )

    # Apply log transform since specgram function returns linear array. 0s are excluded to avoid np warning.
    arr2d = 10 * np.log10(pxx, out=np.zeros_like(pxx), where=(pxx != 0))

    local_maxima = get_2d_peaks(arr2d, plot=False, amp_min=amp_min)

    skeleton: FingerPrint = FingerPrint(print_name=print_name, arr2d=arr2d)
    fingerprint: FingerPrint = generate_hashes(skeleton, local_maxima, fan_value=fan_value)
    return fingerprint


def get_2d_peaks(arr2d: np.array, plot: bool = False, amp_min: int = DEFAULT_AMP_MIN) -> list[tuple[int, int]]:
    """
    Extract maximum peaks from the spectrogram matrix (arr2d).

    :param arr2d: matrix representing the spectrogram.
    :param plot: for plotting the results.
    :param amp_min: minimum amplitude in spectrogram in order to be considered a peak.
    :return: a list composed by a list of frequencies and times.
    """
    # Original code from the repo is using a morphology mask that does not consider diagonal elements
    # as neighbors (basically a diamond figure) and then applies a dilation over it, so what I'm proposing
    # is to change from the current diamond figure to a just a normal square one:
    #       F   T   F           T   T   T
    #       T   T   T   ==>     T   T   T
    #       F   T   F           T   T   T
    # In my local tests time performance of the square mask was ~3 times faster
    # respect to the diamond one, without hurting accuracy of the predictions.
    # I've made now the mask shape configurable in order to allow both ways of find maximum peaks.
    # That being said, we generate the mask by using the following function
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.generate_binary_structure.html
    struct = generate_binary_structure(2, CONNECTIVITY_MASK)

    #  And then we apply dilation using the following function
    #  http://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.iterate_structure.html
    #  Take into account that if PEAK_NEIGHBORHOOD_SIZE is 2 you can avoid the use of the scipy functions and just
    #  change it by the following code:
    #  neighborhood = np.ones((PEAK_NEIGHBORHOOD_SIZE * 2 + 1, PEAK_NEIGHBORHOOD_SIZE * 2 + 1), dtype=bool)
    neighborhood = iterate_structure(struct, PEAK_NEIGHBORHOOD_SIZE)

    # find local maxima using our filter mask
    local_max = maximum_filter(arr2d, footprint=neighborhood) == arr2d

    # Applying erosion, the dejavu documentation does not talk about this step.
    background = (arr2d == 0)
    eroded_background = binary_erosion(background, structure=neighborhood, border_value=1)

    # Boolean mask of arr2d with True at peaks (applying XOR on both matrices).
    detected_peaks = local_max != eroded_background

    # extract peaks
    amps = arr2d[detected_peaks]
    freqs, times = np.where(detected_peaks)

    # filter peaks
    amps = amps.flatten()

    # get indices for frequency and time
    filter_idxs = np.where(amps > amp_min)

    freqs_filter = freqs[filter_idxs]
    times_filter = times[filter_idxs]

    if plot:
        # scatter of the peaks
        fig, ax = plt.subplots()
        # ax.imshow(arr2d, interpolation='none', extent=[0, 25, 16, 0])
        # ax.imshow(arr2d,
        #           interpolation='none',
        #           extent=[0, lx, ly, 0])
        # ax.scatter(times_filter * DEFAULT_OVERLAP_RATIO / 16 * 100,
        #            freqs_filter * (DEFAULT_WINDOW_SIZE * DEFAULT_OVERLAP_RATIO / DEFAULT_FS * 100))

        ax.imshow(maximum_filter(arr2d, footprint=neighborhood), interpolation='none')
        ax.scatter(times_filter, freqs_filter)
        ax.set_xlabel('Time')
        ax.set_ylabel('Frequency')
        ax.set_title("Spectrogram")
        plt.gca().invert_yaxis()
        plt.show()

    return list(zip(freqs_filter, times_filter))


def generate_hashes(skeleton: FingerPrint,
                    peaks: List[Tuple[int, int]],
                    fan_value: int = DEFAULT_FAN_VALUE) -> FingerPrint:
    """
    :param skeleton: FingerPrint is not complete yet
    :param peaks: list of peak frequencies and times.
    :param fan_value: degree to which a fingerprint can be paired with its neighbors.
    :return: FingerPrint is completely ready
    """
    # frequencies are in the first position of the tuples
    idx_freq = 0
    # times are in the second position of the tuples
    idx_time = 1

    if PEAK_SORT:
        peaks.sort(key=itemgetter(1))

    # hashes = []
    # hash_times = []
    for i in range(len(peaks)):
        for j in range(1, fan_value):
            if (i + j) < len(peaks):

                freq1 = peaks[i][idx_freq]
                freq2 = peaks[i + j][idx_freq]
                t1 = peaks[i][idx_time]
                t2 = peaks[i + j][idx_time]
                t_delta = t2 - t1

                if MIN_HASH_TIME_DELTA <= t_delta <= MAX_HASH_TIME_DELTA:
                    hstr = f"{str(freq1)}|{str(freq2)}|{str(t_delta)}"
                    skeleton.add_hash_offset(hstr, t1)
                    skeleton.add_first_points(hstr, t1, freq1)
                    skeleton.add_second_points(hstr, t2, freq2)

    return skeleton