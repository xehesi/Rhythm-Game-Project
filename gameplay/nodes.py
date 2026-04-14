from __future__ import annotations

import pygame

from core.conductor import Conductor
from data.chart_parser import NoteTarget, TAP, HOLD_HEAD
from core.game_logger import get_logger

logger = get_logger("Node")


# ======================================================================
# Base Node  – abstract visual for a single note
# ======================================================================
class Node:
    """Lightweight visual representing one note on screen.
    Nodes are created/recycled by the object pool – never directly by
    gameplay code.
    """

    # Pre-scaled surfaces are set once at init time (see init_assets)
    _tap_surface: pygame.Surface | None = None
    _hold_head_surface: pygame.Surface | None = None
    _hold_body_surface: pygame.Surface | None = None
    _hold_tail_surface: pygame.Surface | None = None

    # Lane geometry (set by init_assets)
    _lane_xs: list[int] = []
    _note_w: int = 0
    _note_h: int = 0

    # Colors per lane group (left hand / right hand)
    LANE_COLORS = [
        (230, 80, 80),   # lane 0
        (80, 200, 80),   # lane 1
        (80, 80, 230),   # lane 2
        (230, 200, 50),  # lane 3
        (200, 80, 200),  # lane 4
        (80, 200, 220),  # lane 5
    ]

    @classmethod
    def init_assets(cls, lane_xs: list[int], note_w: int, note_h: int):
        """Pre-scale all note surfaces ONCE (spec §7)."""
        cls._lane_xs = lane_xs
        cls._note_w = note_w
        cls._note_h = note_h

        # Build generic colored surfaces; lane color tinting happens at draw
        cls._tap_surface = pygame.Surface((note_w, note_h), pygame.SRCALPHA)
        cls._tap_surface.fill((255, 255, 255))

        cls._hold_head_surface = pygame.Surface((note_w, note_h), pygame.SRCALPHA)
        cls._hold_head_surface.fill((255, 255, 255))

        cls._hold_body_surface = pygame.Surface((note_w, 1), pygame.SRCALPHA)
        cls._hold_body_surface.fill((180, 180, 180, 160))

        cls._hold_tail_surface = pygame.Surface((note_w, note_h // 2), pygame.SRCALPHA)
        cls._hold_tail_surface.fill((200, 200, 200))

        logger.info("Assets initialised  note_w=%d  note_h=%d", note_w, note_h)

    def __init__(self):
        self.active = False
        self.target: NoteTarget | None = None

    def assign(self, target: NoteTarget):
        self.active = True
        self.target = target

    def release(self):
        self.active = False
        self.target = None

    # ------------------------------------------------------------------
    # Rendering – uses strict interpolation math (spec §2)
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, conductor: Conductor,
             strike_line_y: float, scroll_speed: float):
        if not self.active or self.target is None:
            return

        target_time = conductor.target_hit_time(self.target.row_index)
        y = conductor.note_y(target_time, strike_line_y, scroll_speed)
        x = self._lane_xs[self.target.lane]

        if self.target.note_type == TAP:
            self._draw_tap(surface, x, y)
        elif self.target.note_type == HOLD_HEAD:
            self._draw_hold(surface, conductor, x, y,
                            strike_line_y, scroll_speed)

    def _draw_tap(self, surface: pygame.Surface, x: float, y: float):
        tinted = self._tap_surface.copy()
        color = self.LANE_COLORS[self.target.lane]
        tinted.fill(color, special_flags=pygame.BLEND_MULT)
        surface.blit(tinted, (x, y - self._note_h // 2))

    def _draw_hold(self, surface: pygame.Surface, conductor: Conductor,
                   x: float, head_y: float,
                   strike_line_y: float, scroll_speed: float):
        """Render the hold: body rectangle from head to tail, then caps."""
        tail_time = conductor.target_hit_time(self.target.hold_end_row)
        tail_y = conductor.note_y(tail_time, strike_line_y, scroll_speed)

        # Body: stretch between head and tail
        body_height = max(1, int(head_y - tail_y))
        body = pygame.transform.scale(self._hold_body_surface,
                                      (self._note_w, body_height))
        color = self.LANE_COLORS[self.target.lane]
        body.fill((*color, 120), special_flags=pygame.BLEND_MULT)
        surface.blit(body, (x, tail_y))

        # Head cap
        head = self._hold_head_surface.copy()
        head.fill(color, special_flags=pygame.BLEND_MULT)
        surface.blit(head, (x, head_y - self._note_h // 2))

        # Tail cap
        tail = self._hold_tail_surface.copy()
        tail.fill(color, special_flags=pygame.BLEND_MULT)
        surface.blit(tail, (x, tail_y - self._note_h // 4))


# ======================================================================
# Object Pool  – only instantiate nodes that are mathematically visible
# ======================================================================
class NodePool:
    POOL_SIZE = 128

    def __init__(self):
        self._pool: list[Node] = [Node() for _ in range(self.POOL_SIZE)]
        self._active: list[Node] = []
        logger.info("NodePool created  size=%d", self.POOL_SIZE)

    def acquire(self, target: NoteTarget) -> Node | None:
        for node in self._pool:
            if not node.active:
                node.assign(target)
                self._active.append(node)
                return node
        logger.warning("NodePool exhausted – cannot acquire node")
        return None

    def release(self, node: Node):
        node.release()
        if node in self._active:
            self._active.remove(node)

    def release_all(self):
        for node in self._active:
            node.release()
        self._active.clear()

    @property
    def active_nodes(self) -> list[Node]:
        return self._active
