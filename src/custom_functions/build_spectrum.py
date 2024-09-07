import numpy
from matplotlib import mlab
from numpy import ndarray, zeros

from src.config import DEFAULT_SAMPLE_RATE, DEFAULT_WINDOW_SIZE, DEFAULT_OVERLAP_RATIO


def get_spectrum_with_name(name: str,
                           amplitudes: list[int],
                           fs: int = DEFAULT_SAMPLE_RATE,
                           wsize: int = DEFAULT_WINDOW_SIZE,
                           wratio: float = DEFAULT_OVERLAP_RATIO
                           ) -> tuple[str, ndarray]:
    spectrum, _, _ = mlab.specgram(
        amplitudes,
        NFFT=wsize,
        Fs=fs,
        window=mlab.window_hanning,
        noverlap=int(wsize * wratio)
    )
    if isinstance(spectrum, numpy.ndarray) is False:
        spectrum = zeros((1, 1))

    return name, spectrum
