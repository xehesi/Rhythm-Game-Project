"""
Calibration Scene – user taps along to audio to determine BPM and offset.

Flow:
  1. Audio plays.
  2. User taps SPACE on every beat they hear.
  3. After enough taps (or ENTER pressed), BPM and offset are computed.
  4. Results shown; ENTER returns to menu.
"""

from __future__ import annotations
from typing import Optional

import pygame

from scenes.scene_manager import Scene
from core.game_logger import get_logger

logger = get_logger("Calibrate")

SCREEN_W, SCREEN_H = 800, 600
MIN_TAPS = 8  # need at least this many to calculate


class CalibrationScene(Scene):
    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font,
                 audio_path: str):
        self._font = font
        self._small_font = small_font
        self._audio_path = audio_path

        self._tap_times: list[float] = []
        self._phase: str = "tapping"  # "tapping" | "results"
        self._result_bpm: float = 0.0
        self._result_offset: float = 0.0
        self._flash_timer: float = 0.0

    @property
    def result_bpm(self) -> float:
        return self._result_bpm

    @property
    def result_offset(self) -> float:
        return self._result_offset

    def set_audio(self, path: str):
        self._audio_path = path

    def on_enter(self):
        self._tap_times.clear()
        self._phase = "tapping"
        self._result_bpm = 0.0
        self._result_offset = 0.0
        self._flash_timer = 0.0
        pygame.mixer.music.load(self._audio_path)
        pygame.mixer.music.play()
        logger.info("Calibration started – audio: %s", self._audio_path)

    def on_exit(self):
        pygame.mixer.music.stop()

    def handle_events(self, events) -> Optional[str]:
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return "menu"

                if self._phase == "tapping":
                    if e.key == pygame.K_SPACE:
                        pos = pygame.mixer.music.get_pos()
                        if pos >= 0:
                            self._tap_times.append(float(pos))
                            self._flash_timer = pos + 150
                            logger.debug("Tap at %.1f ms  (total %d)",
                                         pos, len(self._tap_times))
                    elif e.key == pygame.K_RETURN:
                        self._finalise()

                elif self._phase == "results":
                    if e.key == pygame.K_RETURN:
                        return "menu"
        return None

    def update(self) -> Optional[str]:
        # Auto-finalise when music ends
        if self._phase == "tapping" and not pygame.mixer.music.get_busy():
            self._finalise()
        return None

    def draw(self, surface: pygame.Surface):
        surface.fill((10, 15, 30))

        if self._phase == "tapping":
            self._draw_tapping(surface)
        else:
            self._draw_results(surface)

    # ------------------------------------------------------------------
    def _draw_tapping(self, surface: pygame.Surface):
        title = self._font.render("CALIBRATION", True, (255, 255, 255))
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 80))

        instructions = [
            "Listen to the audio and tap SPACE on every beat.",
            f"Taps recorded: {len(self._tap_times)}  (need at least {MIN_TAPS})",
            "",
            "Press ENTER when done, or wait for the song to end.",
            "Press ESC to cancel.",
        ]
        y = 200
        for line in instructions:
            txt = self._small_font.render(line, True, (180, 180, 180))
            surface.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, y))
            y += 35

        # Flash circle on tap
        now = pygame.mixer.music.get_pos()
        if now >= 0 and now < self._flash_timer:
            pygame.draw.circle(surface, (255, 215, 0),
                               (SCREEN_W // 2, 460), 30)
        else:
            pygame.draw.circle(surface, (60, 60, 80),
                               (SCREEN_W // 2, 460), 30, 2)

    def _draw_results(self, surface: pygame.Surface):
        title = self._font.render("CALIBRATION RESULTS", True, (255, 215, 0))
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 100))

        lines = [
            f"Detected BPM:  {self._result_bpm:.1f}",
            f"First-beat offset:  {self._result_offset:.1f} ms",
            f"Taps used:  {len(self._tap_times)}",
            "",
            "Press ENTER to return to menu.",
        ]
        y = 220
        for line in lines:
            txt = self._small_font.render(line, True, (200, 200, 200))
            surface.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, y))
            y += 40

    # ------------------------------------------------------------------
    def _finalise(self):
        if len(self._tap_times) < MIN_TAPS:
            logger.warning("Only %d taps – not enough to calibrate", len(self._tap_times))
            self._result_bpm = 0.0
            self._result_offset = 0.0
        else:
            intervals = [self._tap_times[i + 1] - self._tap_times[i]
                         for i in range(len(self._tap_times) - 1)]
            # Drop outliers (> 2x or < 0.5x the median)
            intervals.sort()
            median = intervals[len(intervals) // 2]
            filtered = [iv for iv in intervals
                        if 0.5 * median <= iv <= 2.0 * median]
            if not filtered:
                filtered = intervals

            avg_ms = sum(filtered) / len(filtered)
            self._result_bpm = round(60000.0 / avg_ms, 1) if avg_ms > 0 else 0.0
            self._result_offset = round(self._tap_times[0], 1)

            logger.info(
                "Calibration done – BPM=%.1f  offset=%.1f ms  (%d intervals, %d after filter)",
                self._result_bpm, self._result_offset,
                len(intervals), len(filtered),
            )

        self._phase = "results"
        pygame.mixer.music.stop()
