from __future__ import annotations
from typing import Optional

import pygame

from scenes.scene_manager import Scene
from gameplay.player import Player
from core.game_logger import get_logger

logger = get_logger("Scenes")

SCREEN_W, SCREEN_H = 800, 600


class ResultsScene(Scene):
    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font,
                 get_player_fn):
        self._font = font
        self._small_font = small_font
        self._get_player = get_player_fn
        self._player: Player | None = None

    def on_enter(self):
        self._player = self._get_player()
        if self._player:
            logger.info(
                "Results – score=%d  P=%d G=%d OK=%d M=%d",
                self._player.score, self._player.perfects,
                self._player.goods, self._player.oks, self._player.misses,
            )

    def handle_events(self, events) -> Optional[str]:
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                return "menu"
        return None

    def update(self) -> Optional[str]:
        return None

    def draw(self, surface: pygame.Surface):
        surface.fill((10, 10, 25))
        if not self._player:
            return

        lines = [
            f"FINAL SCORE: {self._player.score}",
            f"Perfect: {self._player.perfects}",
            f"Good:    {self._player.goods}",
            f"OK:      {self._player.oks}",
            f"Miss:    {self._player.misses}",
            "",
            "Press ENTER to return to menu",
        ]
        y = 150
        for i, line in enumerate(lines):
            fnt = self._font if i == 0 else self._small_font
            color = (255, 215, 0) if i == 0 else (200, 200, 200)
            txt = fnt.render(line, True, color)
            surface.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, y))
            y += 50
