from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import pygame

from core.game_logger import get_logger

if TYPE_CHECKING:
    from typing import Optional

logger = get_logger("Scene")


# ======================================================================
# Base Scene
# ======================================================================
class Scene(ABC):
    """All scenes inherit from this base."""

    @abstractmethod
    def handle_events(self, events: list[pygame.event.Event]) -> Optional[str]:
        """Process input. Return a scene name string to transition, or None."""

    @abstractmethod
    def update(self) -> Optional[str]:
        """Per-frame logic. Return a scene name string to transition, or None."""

    @abstractmethod
    def draw(self, surface: pygame.Surface):
        """Render the scene."""

    def on_enter(self):
        """Called once when the scene becomes active."""

    def on_exit(self):
        """Called once when leaving this scene."""


# ======================================================================
# Scene Manager (state machine)
# ======================================================================
class SceneManager:
    def __init__(self):
        self._scenes: dict[str, Scene] = {}
        self._current_name: Optional[str] = None
        self._current: Optional[Scene] = None

    def register(self, name: str, scene: Scene):
        self._scenes[name] = scene

    def switch_to(self, name: str):
        if name not in self._scenes:
            logger.error("Unknown scene '%s' – no transition", name)
            return
        if self._current:
            self._current.on_exit()
            logger.info("Exited scene '%s'", self._current_name)
        self._current_name = name
        self._current = self._scenes[name]
        self._current.on_enter()
        logger.info("Entered scene '%s'", name)

    def handle_events(self, events: list[pygame.event.Event]):
        if self._current:
            result = self._current.handle_events(events)
            if result:
                self.switch_to(result)

    def update(self):
        if self._current:
            result = self._current.update()
            if result:
                self.switch_to(result)

    def draw(self, surface: pygame.Surface):
        if self._current:
            self._current.draw(surface)
