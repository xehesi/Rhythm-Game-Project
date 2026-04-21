from __future__ import annotations
from typing import Optional

import pygame

from scenes.scene_manager import Scene
from core.game_logger import get_logger

logger = get_logger("Scenes")

SCREEN_W, SCREEN_H = 800, 600


class MainMenuScene(Scene):
    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font):
        self._font = font
        self._small_font = small_font
        self._selected = 0
        self._easy_mode = False
        self._options = [
            ("Play Demo Chart", "gameplay"),
            ("Import Audio", "import_audio"),
            ("Calibration", "calibration"),
            ("Easy Mode", None),
        ]

    @property
    def easy_mode(self) -> bool:
        return self._easy_mode

    def on_enter(self):
        self._selected = 0
        logger.info("Main Menu entered")

    def handle_events(self, events) -> Optional[str]:
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_UP:
                    self._selected = (self._selected - 1) % len(self._options)
                elif e.key == pygame.K_DOWN:
                    self._selected = (self._selected + 1) % len(self._options)
                elif e.key == pygame.K_RETURN:
                    label, target = self._options[self._selected]
                    if label == "Easy Mode":
                        self._easy_mode = not self._easy_mode
                        logger.info(
                            "Easy Mode toggled %s",
                            "ON" if self._easy_mode else "OFF",
                        )
                    else:
                        return target
        return None

    def update(self) -> Optional[str]:
        return None

    def draw(self, surface: pygame.Surface):
        surface.fill((15, 15, 30))
        title = self._font.render("RHYTHM GAME", True, (255, 255, 255))
        surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 140))

        for i, (label, _) in enumerate(self._options):
            display_label = label
            if label == "Easy Mode":
                display_label = f"Easy Mode: {'On' if self._easy_mode else 'Off'}"
            color = (255, 215, 0) if i == self._selected else (180, 180, 180)
            prefix = "> " if i == self._selected else "  "
            txt = self._small_font.render(prefix + display_label, True, color)
            surface.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, 260 + i * 45))

        hint = self._small_font.render(
            "UP/DOWN to select, ENTER to confirm", True, (100, 100, 120))
        surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 460))
