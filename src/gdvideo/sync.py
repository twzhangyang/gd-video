"""Find the offset between the horizontal and the vertical recording from their audio."""
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


def find_offset(ref, other, window=30):
    """Seconds into `other` that line up with `ref` t=0.

    Match `other` in windows of `window` seconds against `ref` and take the value most windows agree on.
    Returns (offset, windows that agree, windows).
    """
    lags = []
    for start in range(0, int(len(other) / SR) - window + 1, window):
        seg = other[start * SR:(start + window) * SR]
        lag, z = gcc_phat(ref, seg)
        lags.append(start - lag)
        print(f"  window {start:4d}s: offset {start - lag:+.3f}s (z={z:.1f})", file=sys.stderr)
    lags = np.array(lags)
    best = max(lags, key=lambda x: np.sum(np.abs(lags - x) < 0.1))
    agree = lags[np.abs(lags - best) < 0.1]
    return float(np.median(agree)), len(agree), len(lags)


def sync_window(duration, longest=30):
    """Window length for find_offset: `longest`, or shorter so a short recording still has 3 windows."""
    return max(3, min(longest, int(duration / 3)))
