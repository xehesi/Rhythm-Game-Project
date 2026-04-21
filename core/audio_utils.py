from __future__ import annotations

import os
import wave

from core.game_logger import get_logger

logger = get_logger("Audio")


def get_slowed_wav_path(source_path: str, speed: float) -> str:
    """Return a cached slowed WAV path for the requested speed.

    The slowed file keeps the same sample rate and duplicates source frames
    according to the playback factor. This lowers pitch, but preserves sync
    with chart timing without requiring an external DSP dependency.
    """
    if speed <= 0:
        raise ValueError("Playback speed must be positive")
    if abs(speed - 1.0) < 1e-6:
        return source_path
    if not source_path.lower().endswith(".wav"):
        raise ValueError("Easy Mode slowdown currently supports WAV files only")

    base, ext = os.path.splitext(source_path)
    slowed_path = f"{base}__easy_{int(round(speed * 100)):02d}{ext}"

    if os.path.exists(slowed_path):
        source_mtime = os.path.getmtime(source_path)
        slowed_mtime = os.path.getmtime(slowed_path)
        if slowed_mtime >= source_mtime:
            return slowed_path

    _write_slowed_wav(source_path, slowed_path, speed)
    return slowed_path


def _write_slowed_wav(source_path: str, output_path: str, speed: float):
    with wave.open(source_path, "rb") as src:
        params = src.getparams()
        frame_count = src.getnframes()
        raw_frames = src.readframes(frame_count)

    frame_size = params.sampwidth * params.nchannels
    if params.sampwidth not in (1, 2):
        raise ValueError(
            f"Unsupported WAV sample width: {params.sampwidth} bytes"
        )
    if frame_size <= 0:
        raise ValueError("Invalid WAV frame size")
    if frame_count <= 0:
        raise ValueError("Cannot slow an empty WAV file")

    output_frame_count = max(1, int(frame_count / speed))
    slowed_frames = bytearray(output_frame_count * frame_size)

    for out_idx in range(output_frame_count):
        src_idx = min(frame_count - 1, int(out_idx * speed))
        src_start = src_idx * frame_size
        out_start = out_idx * frame_size
        slowed_frames[out_start:out_start + frame_size] = (
            raw_frames[src_start:src_start + frame_size]
        )

    with wave.open(output_path, "wb") as dst:
        dst.setnchannels(params.nchannels)
        dst.setsampwidth(params.sampwidth)
        dst.setframerate(params.framerate)
        dst.writeframes(slowed_frames)

    logger.info(
        "Generated slowed audio '%s' from '%s' at %.2fx",
        output_path,
        source_path,
        speed,
    )