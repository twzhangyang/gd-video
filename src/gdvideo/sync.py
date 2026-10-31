"""Find the offset between the iPad recording and the facecam from their audio."""
import sys

import numpy as np

from gdvideo.config import SR


def gcc_phat(a, b):
    """Lag (s) of b inside a, plus a peak z-score."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    r = np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n))
    r /= np.abs(r) + 1e-9
    c = np.abs(np.fft.irfft(r, n))
    c = np.concatenate([c[-len(b):], c[:len(a)]])
    i = int(np.argmax(c))
    return (i - len(b)) / SR, (c[i] - c.mean()) / c.std()


def find_offset(game, voice, window=30):
    """Seconds into face.mov that line up with ipad.mov t=0.

    The facecam mic hears a little game audio from the iPad speaker; match it in
    30 s windows and take the value most windows agree on.
    """
    lags = []
    for start in range(0, int(len(voice) / SR) - window + 1, window):
        seg = voice[start * SR:(start + window) * SR]
        lag, z = gcc_phat(game, seg)
        lags.append(start - lag)
        print(f"  window {start:4d}s: offset {start - lag:+.3f}s (z={z:.1f})", file=sys.stderr)
    lags = np.array(lags)
    best = max(lags, key=lambda x: np.sum(np.abs(lags - x) < 0.1))
    agree = lags[np.abs(lags - best) < 0.1]
    return float(np.median(agree)), len(agree), len(lags)
