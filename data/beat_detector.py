"""
Beat detection via energy-based onset detection.

Reads a WAV file, computes short-term energy in windows, finds onset peaks,
and quantizes them onto a 6-lane grid at the given BPM.
"""

from __future__ import annotations

import json
import math
import os
import struct
import wave

from data.chart_parser import NUM_LANES, TAP, EMPTY
from core.game_logger import get_logger

logger = get_logger("BeatDetect")

# ── helpers ──────────────────────────────────────────────────────────

def _read_wav_mono(path: str) -> tuple[list[float], int]:
    """Return (samples_normalised_float, sample_rate)."""
    with wave.open(path, "rb") as wf:
        n_channels = wf.getnchannels()
        samp_width = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if samp_width == 2:
        fmt = f"<{n_frames * n_channels}h"
        samples = struct.unpack(fmt, raw)
        scale = 32768.0
    elif samp_width == 1:
        samples = [b - 128 for b in raw]
        scale = 128.0
    else:
        raise ValueError(f"Unsupported sample width: {samp_width}")

    # Mix to mono
    if n_channels == 2:
        mono = [(samples[i] + samples[i + 1]) / 2.0 for i in range(0, len(samples), 2)]
    else:
        mono = list(samples)

    normalised = [s / scale for s in mono]
    return normalised, framerate


def _compute_energy(samples: list[float], framerate: int,
                    window_ms: float = 20.0) -> list[float]:
    """RMS energy per window."""
    window_size = max(1, int(framerate * window_ms / 1000.0))
    energies = []
    for start in range(0, len(samples), window_size):
        chunk = samples[start:start + window_size]
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))
        energies.append(rms)
    return energies


def _detect_onsets(energies: list[float], threshold_factor: float = 1.5,
                   local_window: int = 7) -> list[int]:
    """Return indices (into energies list) where an onset occurs."""
    onsets: list[int] = []
    half = local_window // 2
    for i in range(half, len(energies) - half):
        local_mean = sum(energies[i - half:i + half + 1]) / local_window
        if energies[i] > local_mean * threshold_factor and energies[i] > 0.02:
            # Suppress duplicates within the local window
            if not onsets or i - onsets[-1] > half:
                onsets.append(i)
    return onsets


# ── public API ───────────────────────────────────────────────────────

def detect_beats(wav_path: str, window_ms: float = 20.0,
                 threshold: float = 1.5) -> list[float]:
    """Return a list of onset times in milliseconds detected in a WAV file."""
    samples, sr = _read_wav_mono(wav_path)
    energies = _compute_energy(samples, sr, window_ms)
    onset_indices = _detect_onsets(energies, threshold)
    onset_times = [i * window_ms for i in onset_indices]
    logger.info("Detected %d onsets in '%s'", len(onset_times), wav_path)
    return onset_times


def estimate_bpm(onset_times: list[float],
                 min_bpm: float = 60, max_bpm: float = 200) -> float:
    """Estimate BPM from inter-onset intervals."""
    if len(onset_times) < 2:
        return 120.0  # fallback

    intervals = [onset_times[i + 1] - onset_times[i]
                 for i in range(len(onset_times) - 1)]
    # Filter to plausible beat-level intervals
    min_ms = 60000.0 / max_bpm
    max_ms = 60000.0 / min_bpm
    beat_intervals = [iv for iv in intervals if min_ms <= iv <= max_ms]
    if not beat_intervals:
        return 120.0

    avg_ms = sum(beat_intervals) / len(beat_intervals)
    bpm = 60000.0 / avg_ms
    logger.info("Estimated BPM: %.1f  (from %d intervals)", bpm, len(beat_intervals))
    return round(bpm, 1)


def generate_chart_json(wav_path: str, bpm: float, onset_times: list[float],
                        rows_per_beat: int = 4,
                        song_name: str | None = None) -> dict:
    """Build a chart dict from detected onsets, quantized to the grid."""
    ms_per_row = 60000.0 / bpm / rows_per_beat

    if not onset_times:
        return _empty_chart(wav_path, bpm, rows_per_beat, song_name)

    max_row = int(onset_times[-1] / ms_per_row) + rows_per_beat * 4  # pad end
    grid: list[list[int]] = [[EMPTY] * NUM_LANES for _ in range(max_row + 1)]

    lane_cursor = 0  # simple round-robin across lanes
    for t in onset_times:
        row = round(t / ms_per_row)
        if 0 <= row <= max_row:
            grid[row][lane_cursor % NUM_LANES] = TAP
            lane_cursor += 1

    name = song_name or os.path.splitext(os.path.basename(wav_path))[0]
    chart = {
        "song_name": name,
        "bpm": bpm,
        "audio_file": os.path.basename(wav_path),
        "rows_per_beat": rows_per_beat,
        "chart": grid,
    }
    logger.info("Generated chart: %d rows, %d notes, BPM=%.1f",
                len(grid), len(onset_times), bpm)
    return chart


def save_chart(chart: dict, output_path: str):
    """Write chart dict to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chart, f, indent=2)
    logger.info("Chart saved to '%s'", output_path)


def _empty_chart(wav_path, bpm, rows_per_beat, song_name):
    name = song_name or os.path.splitext(os.path.basename(wav_path))[0]
    return {
        "song_name": name,
        "bpm": bpm,
        "audio_file": os.path.basename(wav_path),
        "rows_per_beat": rows_per_beat,
        "chart": [[EMPTY] * NUM_LANES for _ in range(rows_per_beat * 4)],
    }
