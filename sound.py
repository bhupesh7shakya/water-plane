#!/usr/bin/python3
"""
Sound module for the Water Plane notification system.
Synthesizes a pleasant, gentle water droplet sound in pure Python,
and plays it asynchronously using standard Linux audio utilities.
"""

import math
import os
import shutil
import struct
import subprocess
import wave

SOUND_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets")
CHIME_FILE = os.path.join(SOUND_DIR, "water_chime.wav")


def ensure_sound_file():
    """Generates the soft double water droplet audio file if missing."""
    if os.path.isfile(CHIME_FILE):
        return CHIME_FILE

    os.makedirs(SOUND_DIR, exist_ok=True)
    sample_rate = 44100
    samples = []

    def make_drop(start_freq, end_freq, duration, peak_vol=0.55):
        n_samples = int(sample_rate * duration)
        phase = 0.0
        drop_samples = []
        for i in range(n_samples):
            t = i / sample_rate
            # Upward chirp characteristic of a water drop bubble
            f = start_freq + (end_freq - start_freq) * (t / duration) ** 2.2
            phase += 2.0 * math.pi * f / sample_rate

            # Smooth attack and exponential decay
            if t < 0.008:
                env = t / 0.008
            else:
                env = math.exp(-(t - 0.008) * 18.0)

            # Pure sine tone with soft second harmonic for glassy resonance
            val = (
                env * (math.sin(phase) * 0.75 + math.sin(phase * 2.0) * 0.25) * peak_vol
            )
            drop_samples.append(int(max(-1.0, min(1.0, val)) * 32767))
        return drop_samples

    # Droplet 1 (bloop)
    samples.extend(make_drop(480, 1350, 0.18, 0.55))
    # Brief pause
    samples.extend([0] * int(sample_rate * 0.08))
    # Droplet 2 (higher bloop)
    samples.extend(make_drop(620, 1680, 0.18, 0.65))
    # Tail decay
    samples.extend([0] * int(sample_rate * 0.05))

    with wave.open(CHIME_FILE, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    return CHIME_FILE


def play_chime(enabled=True):
    """Plays the water chime asynchronously in the background."""
    if not enabled:
        return

    try:
        chime_path = ensure_sound_file()
        for player in ["paplay", "pw-play", "aplay"]:
            if shutil.which(player):
                subprocess.Popen(
                    [player, chime_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
    except Exception:
        # Silently ignore audio playback errors
        pass


if __name__ == "__main__":
    ensure_sound_file()
    print("Playing chime test...")
    play_chime(True)
