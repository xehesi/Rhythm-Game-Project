"""
Import Audio Scene – lets the user pick a WAV file, auto-detects beats,
optionally lets them calibrate, then generates & saves a chart JSON
that can be played immediately.

Flow:
  1. User types a file path (or drops a file) and presses ENTER.
  2. Beat detection runs; a chart is generated and saved to charts/.
  3. User can press P to play the new chart, C to calibrate first,
     or ESC to go back.
"""

from __future__ import annotations

import os
import shutil
from typing import Optional

import pygame

from scenes.scene_manager import Scene
from data.beat_detector import detect_beats, estimate_bpm, generate_chart_json, save_chart
from core.game_logger import get_logger

logger = get_logger("Import")

SCREEN_W, SCREEN_H = 800, 600
CHARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "charts")


class ImportAudioScene(Scene):
    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font,
                 on_play_chart: callable, on_calibrate: callable):
        self._font = font
        self._small_font = small_font
        self._on_play_chart = on_play_chart  # callback(chart_json_path)
        self._on_calibrate = on_calibrate    # callback(audio_path)

        self._input_text: str = ""
        self._phase: str = "input"  # "input" | "processing" | "done" | "error"
        self._status_lines: list[str] = []
        self._generated_chart_path: str = ""
        self._generated_audio_path: str = ""

    def on_enter(self):
        self._input_text = ""
        self._phase = "input"
        self._status_lines = []
        self._generated_chart_path = ""
        self._generated_audio_path = ""
        logger.info("Import Audio scene entered")

    def handle_events(self, events) -> Optional[str]:
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return "menu"

                if self._phase == "input":
                    if e.key == pygame.K_RETURN:
                        self._process_import()
                    elif e.key == pygame.K_BACKSPACE:
                        self._input_text = self._input_text[:-1]
                    else:
                        ch = e.unicode
                        if ch and ch.isprintable():
                            self._input_text += ch

                elif self._phase == "done":
                    if e.key == pygame.K_p:
                        self._on_play_chart(self._generated_chart_path)
                        return "gameplay"
                    elif e.key == pygame.K_c:
                        self._on_calibrate(self._generated_audio_path)
                        return "calibration"
                    elif e.key == pygame.K_RETURN:
                        return "menu"

                elif self._phase == "error":
                    if e.key == pygame.K_RETURN:
                        self._phase = "input"

        return None

    def update(self) -> Optional[str]:
        return None

    def draw(self, surface: pygame.Surface):
        surface.fill((10, 15, 30))
        title = self._font.render("IMPORT AUDIO", True, (255, 255, 255))
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 40))

        if self._phase == "input":
            self._draw_input(surface)
        elif self._phase == "processing":
            self._draw_processing(surface)
        elif self._phase == "done":
            self._draw_done(surface)
        elif self._phase == "error":
            self._draw_error(surface)

    # ------------------------------------------------------------------
    def _draw_input(self, surface: pygame.Surface):
        prompt = self._small_font.render(
            "Enter the full path to a WAV file:", True, (180, 180, 180))
        surface.blit(prompt, (60, 130))

        # Text box
        box_rect = pygame.Rect(60, 170, SCREEN_W - 120, 36)
        pygame.draw.rect(surface, (30, 30, 50), box_rect)
        pygame.draw.rect(surface, (100, 100, 140), box_rect, 2)
        txt = self._small_font.render(self._input_text, True, (255, 255, 255))
        surface.blit(txt, (box_rect.x + 8, box_rect.y + 8))

        hint = self._small_font.render(
            "Press ENTER to import  |  ESC to cancel", True, (100, 100, 120))
        surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 240))

    def _draw_processing(self, surface: pygame.Surface):
        txt = self._font.render("Processing...", True, (255, 215, 0))
        surface.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, 250))

    def _draw_done(self, surface: pygame.Surface):
        y = 130
        for line in self._status_lines:
            txt = self._small_font.render(line, True, (180, 255, 180))
            surface.blit(txt, (60, y))
            y += 30

        options = [
            "[P] Play the generated chart",
            "[C] Calibrate (tap along to fine-tune BPM/offset)",
            "[ENTER] Return to menu",
            "[ESC] Return to menu",
        ]
        y += 20
        for line in options:
            txt = self._small_font.render(line, True, (200, 200, 200))
            surface.blit(txt, (60, y))
            y += 30

    def _draw_error(self, surface: pygame.Surface):
        y = 150
        for line in self._status_lines:
            color = (255, 100, 100) if "Error" in line else (200, 200, 200)
            txt = self._small_font.render(line, True, color)
            surface.blit(txt, (60, y))
            y += 30
        hint = self._small_font.render(
            "Press ENTER to try again", True, (150, 150, 150))
        surface.blit(hint, (60, y + 20))

    # ------------------------------------------------------------------
    def _process_import(self):
        path = self._input_text.strip().strip('"').strip("'")
        self._phase = "processing"

        if not os.path.isfile(path):
            self._status_lines = [f"Error: file not found – {path}"]
            self._phase = "error"
            logger.error("Import failed – file not found: %s", path)
            return

        if not path.lower().endswith(".wav"):
            self._status_lines = [
                "Error: only WAV files are supported.",
                f"Got: {path}",
            ]
            self._phase = "error"
            logger.error("Import failed – not a WAV: %s", path)
            return

        try:
            # 1. Copy audio into charts/
            os.makedirs(CHARTS_DIR, exist_ok=True)
            dest_audio = os.path.join(CHARTS_DIR, os.path.basename(path))
            if os.path.abspath(path) != os.path.abspath(dest_audio):
                shutil.copy2(path, dest_audio)

            # 2. Detect beats
            onsets = detect_beats(dest_audio)
            bpm = estimate_bpm(onsets)

            # 3. Generate chart
            chart = generate_chart_json(dest_audio, bpm, onsets)
            base = os.path.splitext(os.path.basename(path))[0]
            chart_path = os.path.join(CHARTS_DIR, f"{base}_chart.json")
            save_chart(chart, chart_path)

            self._generated_chart_path = chart_path
            self._generated_audio_path = dest_audio
            self._status_lines = [
                f"Audio copied to: {dest_audio}",
                f"Detected BPM: {bpm:.1f}",
                f"Onsets found: {len(onsets)}",
                f"Chart saved: {chart_path}",
            ]
            self._phase = "done"
            logger.info("Import complete – chart at %s", chart_path)

        except Exception as exc:
            self._status_lines = [f"Error: {exc}"]
            self._phase = "error"
            logger.exception("Import failed")
