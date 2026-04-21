"""
Rhythm Game – main entry point
6-lane vertical-scrolling rhythm game built with Pygame.
"""

import os
import sys

import pygame

from scenes.scene_manager import SceneManager
from scenes.main_menu import MainMenuScene
from scenes.gameplay import GameplayScene
from scenes.results import ResultsScene
from scenes.calibration import CalibrationScene
from scenes.import_audio import ImportAudioScene
from core.game_logger import get_logger

logger = get_logger("Main")

# ======================================================================
# Configuration
# ======================================================================
SCREEN_W, SCREEN_H = 800, 600
FPS = 60
CHART_PATH = os.path.join(os.path.dirname(__file__), "charts", "demo_chart.json")
AUDIO_PATH = os.path.join(os.path.dirname(__file__), "charts", "demo.wav")
ASSIST_MODE = False  # flip to True to enable forgiving mechanic


def main():
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Rhythm Game")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("Consolas", 28)
    small_font = pygame.font.SysFont("Consolas", 18)

    # --- Build scenes ---
    menu = MainMenuScene(font, small_font)

    gameplay = GameplayScene(
        chart_path=CHART_PATH,
        font=font,
        small_font=small_font,
        assist_mode=ASSIST_MODE,
        get_easy_mode_fn=lambda: menu.easy_mode,
    )

    results = ResultsScene(
        font=font,
        small_font=small_font,
        get_player_fn=lambda: gameplay._player,
    )

    calibration = CalibrationScene(
        font=font,
        small_font=small_font,
        audio_path=AUDIO_PATH,
    )

    import_audio = ImportAudioScene(
        font=font,
        small_font=small_font,
        on_play_chart=lambda path: gameplay.set_chart_path(path),
        on_calibrate=lambda path: calibration.set_audio(path),
    )

    # --- Register with scene manager ---
    sm = SceneManager()
    sm.register("menu", menu)
    sm.register("gameplay", gameplay)
    sm.register("results", results)
    sm.register("calibration", calibration)
    sm.register("import_audio", import_audio)
    sm.switch_to("menu")

    logger.info("Game initialised – starting main loop")

    # ==================================================================
    # Main loop
    # ==================================================================
    running = True
    while running:
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT:
                running = False

        sm.handle_events(events)
        sm.update()
        sm.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    logger.info("Game shut down cleanly")
    sys.exit()


if __name__ == "__main__":
    main()
