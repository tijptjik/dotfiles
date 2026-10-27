#!/usr/bin/env python3
"""Render a quiet, ethereal replacement for Codex and Herdr notifications."""

import array
import math
from pathlib import Path
import sys
import wave


def render(destination):
    rate = 48000
    duration = 0.8
    samples = []
    for index in range(round(rate * duration)):
        time = index / rate
        channels = []
        for side in (-1, 1):
            value = 0.0
            for frequency, weight, delay in (
                (523.25, 1.0, 0.0),
                (784.88, 0.32, 0.045),
                (1046.5, 0.12, 0.09),
            ):
                age = time - delay
                if age < 0:
                    continue
                # Rounded onset, slow release, and slight stereo detuning.
                envelope = (1 - math.exp(-age / 0.065)) ** 2
                envelope *= math.exp(-age / 0.18)
                envelope *= min(1.0, (duration - time) / 0.2) ** 2
                value += weight * envelope * math.sin(
                    2 * math.pi * (frequency + side * 0.35) * age
                )
            channels.append(value)
        samples.extend(channels)
    # -30 dBFS peak: 6 dB below the first preview, without a hard strike.
    gain = 10 ** (-30 / 20) / max(map(abs, samples))
    pcm = array.array('h', (round(value * gain * 32767) for value in samples))
    if sys.byteorder != 'little':
        pcm.byteswap()
    with wave.open(str(destination), 'wb') as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm.tobytes())


if __name__ == '__main__':
    render(Path(sys.argv[1]))
