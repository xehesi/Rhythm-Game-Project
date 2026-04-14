import pygame
from core.game_logger import get_logger

logger = get_logger("Input")

# Default key bindings: 6 lanes mapped to keyboard
#   Left hand:  S  D  F
#   Right hand:  J  K  L
DEFAULT_BINDINGS = {
    pygame.K_s: 0,
    pygame.K_d: 1,
    pygame.K_f: 2,
    pygame.K_j: 3,
    pygame.K_k: 4,
    pygame.K_l: 5,
}


class InputHandler:
    """Captures KEYDOWN/KEYUP events and translates to lane actions."""

    def __init__(self, bindings: dict[int, int] | None = None):
        self.bindings = bindings or DEFAULT_BINDINGS
        # Per-frame results populated by process()
        self.lane_presses: list[int] = []
        self.lane_releases: list[int] = []

    def process(self, events: list[pygame.event.Event], song_position: float):
        """Process pygame events for the current frame.
        Only uses KEYDOWN/KEYUP (spec §5 – no get_pressed).
        """
        self.lane_presses.clear()
        self.lane_releases.clear()
        for event in events:
            if event.type == pygame.KEYDOWN and event.key in self.bindings:
                lane = self.bindings[event.key]
                self.lane_presses.append(lane)
                logger.debug("PRESS  lane=%d  song_pos=%.1f ms", lane, song_position)
            elif event.type == pygame.KEYUP and event.key in self.bindings:
                lane = self.bindings[event.key]
                self.lane_releases.append(lane)
                logger.debug("RELEASE  lane=%d  song_pos=%.1f ms", lane, song_position)
