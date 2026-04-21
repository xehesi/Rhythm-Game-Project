from __future__ import annotations

import os
from typing import Optional

import pygame

from scenes.scene_manager import Scene
from core.conductor import Conductor
from data.chart_parser import ChartParser, Song, NoteTarget, TAP, HOLD_HEAD
from gameplay.nodes import Node, NodePool
from gameplay.player import Player
from gameplay.input_handler import InputHandler
from core.game_logger import get_logger

logger = get_logger("Scenes")

# ======================================================================
# Layout constants
# ======================================================================
SCREEN_W, SCREEN_H = 800, 600
LANE_COUNT = 6
LANE_WIDTH = 80
PLAYFIELD_W = LANE_COUNT * LANE_WIDTH
PLAYFIELD_X = (SCREEN_W - PLAYFIELD_W) // 2
STRIKE_LINE_Y = SCREEN_H - 100
SCROLL_SPEED = 0.45  # pixels per millisecond
VISIBLE_MS = SCREEN_H / SCROLL_SPEED  # how far ahead (in ms) we show notes
MISS_WINDOW_MS = 150  # notes past this offset below strike line are missed


class GameplayScene(Scene):
    def __init__(self, chart_path: str, font: pygame.font.Font,
                 small_font: pygame.font.Font, assist_mode: bool = False):
        self._chart_path = chart_path
        self._font = font
        self._small_font = small_font
        self._assist_mode = assist_mode

        # Initialised in on_enter so we get a fresh state each play
        self._conductor: Conductor | None = None
        self._song: Song | None = None
        self._pool: NodePool | None = None
        self._player: Player | None = None
        self._input: InputHandler | None = None

        self._note_cursor: int = 0
        self._chart_end_time: float = 0.0
        self._active_holds: dict[int, NoteTarget] = {}
        self._last_grade: str = ""
        self._grade_timer: float = 0

        self._lane_xs = [PLAYFIELD_X + i * LANE_WIDTH for i in range(LANE_COUNT)]

    # Allow the chart path to be changed before entering the scene
    def set_chart_path(self, path: str):
        self._chart_path = path

    def on_enter(self):
        song = ChartParser.load(self._chart_path)
        self._song = song
        self._conductor = Conductor(bpm=song.bpm,
                                    rows_per_beat=song.rows_per_beat)
        self._pool = NodePool()
        self._player = Player(assist_mode=self._assist_mode)
        self._input = InputHandler()
        self._note_cursor = 0
        self._chart_end_time = 0.0
        self._active_holds.clear()
        self._last_grade = ""
        self._grade_timer = 0

        if song.notes:
            last_row = max(
                n.hold_end_row if n.note_type == HOLD_HEAD else n.row_index
                for n in song.notes
            )
            self._chart_end_time = self._conductor.target_hit_time(last_row)

        Node.init_assets(self._lane_xs, LANE_WIDTH - 4, 20)

        audio = song.audio_path
        if not os.path.isabs(audio):
            audio = os.path.join(os.path.dirname(self._chart_path), audio)
        self._conductor.start_song(audio)
        logger.info("Gameplay started – chart '%s'", song.name)

    def on_exit(self):
        if self._conductor:
            self._conductor.stop_song()
        if self._pool:
            self._pool.release_all()

    def handle_events(self, events) -> Optional[str]:
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return "menu"

        self._input.process(events, self._conductor.song_position)
        return None

    def update(self) -> Optional[str]:
        cond = self._conductor
        cond.update()

        # --- Activate nodes entering the visible window ---
        notes = self._song.notes
        while self._note_cursor < len(notes):
            nt = notes[self._note_cursor]
            target_t = cond.target_hit_time(nt.row_index)
            if target_t - cond.song_position > VISIBLE_MS:
                break
            if not nt.hit and not nt.missed:
                self._pool.acquire(nt)
            self._note_cursor += 1

        # --- Judge lane presses ---
        for lane in self._input.lane_presses:
            closest = self._find_closest_note(lane, cond.song_position)
            if closest:
                error = cond.song_position - cond.target_hit_time(closest.row_index)
                grade = self._player.judge(error)
                closest.hit = True
                self._last_grade = grade.upper()
                self._grade_timer = cond.song_position + 400

                if closest.note_type == HOLD_HEAD:
                    # Keep the node alive so body + tail keep rendering
                    self._active_holds[lane] = closest
                else:
                    # Tap notes are released immediately
                    self._release_node_for(closest)

                logger.debug(
                    "Input  lane=%d  err=%.1fms  grade=%s  target_row=%d",
                    lane, error, grade, closest.row_index,
                )

        # --- Release held notes on key-up ---
        for lane in self._input.lane_releases:
            if lane in self._active_holds:
                hold = self._active_holds.pop(lane)
                self._release_node_for(hold)

        # --- Auto-release holds whose tail time has passed ---
        for lane in list(self._active_holds):
            hold = self._active_holds[lane]
            tail_t = cond.target_hit_time(hold.hold_end_row)
            if cond.song_position > tail_t + MISS_WINDOW_MS:
                self._release_node_for(self._active_holds.pop(lane))

        # --- Auto-miss notes that have fallen past the window ---
        for node in list(self._pool.active_nodes):
            if node.target is None:
                continue
            # Skip hold nodes that are actively being held
            if node.target.hit and node.target.note_type == HOLD_HEAD:
                continue
            target_t = cond.target_hit_time(node.target.row_index)
            if cond.song_position - target_t > MISS_WINDOW_MS:
                if not node.target.hit:
                    node.target.missed = True
                    self._player.register_miss()
                    self._last_grade = "MISS"
                    self._grade_timer = cond.song_position + 400
                    if self._assist_mode:
                        cond.trigger_slowdown()
                self._pool.release(node)

        # --- Fail state ---
        if self._player.is_dead:
            logger.info("Player failed – health depleted")
            return "results"

        # --- Chart finished ---
        if (
            self._note_cursor >= len(notes)
            and not self._pool.active_nodes
            and not self._active_holds
            and cond.song_position >= self._chart_end_time + MISS_WINDOW_MS
        ):
            logger.info("Chart finished")
            return "results"

        return None

    def draw(self, surface: pygame.Surface):
        surface.fill((10, 10, 25))
        cond = self._conductor

        # Playfield background
        pf_rect = pygame.Rect(PLAYFIELD_X, 0, PLAYFIELD_W, SCREEN_H)
        pygame.draw.rect(surface, (20, 20, 40), pf_rect)

        # Lane dividers
        for i in range(LANE_COUNT + 1):
            x = PLAYFIELD_X + i * LANE_WIDTH
            pygame.draw.line(surface, (50, 50, 70), (x, 0), (x, SCREEN_H))

        # Strike line
        pygame.draw.line(surface, (255, 200, 50),
                         (PLAYFIELD_X, STRIKE_LINE_Y),
                         (PLAYFIELD_X + PLAYFIELD_W, STRIKE_LINE_Y), 3)

        # Active notes
        for node in self._pool.active_nodes:
            node.draw(surface, cond, STRIKE_LINE_Y, SCROLL_SPEED)

        # HUD
        score_txt = self._font.render(f"Score: {self._player.score}", True, (255, 255, 255))
        streak_txt = self._small_font.render(
            f"Streak: {self._player.streak}  x{self._player.multiplier}", True, (200, 200, 200))
        health_txt = self._small_font.render(
            f"Health: {self._player.health:.0f}", True, (200, 100, 100))
        surface.blit(score_txt, (10, 10))
        surface.blit(streak_txt, (10, 50))
        surface.blit(health_txt, (10, 75))

        # Grade flash
        if cond.song_position < self._grade_timer:
            grade_color = {
                "PERFECT": (255, 215, 0),
                "GOOD": (100, 255, 100),
                "OK": (100, 180, 255),
                "MISS": (255, 60, 60),
            }.get(self._last_grade, (255, 255, 255))
            g_surf = self._font.render(self._last_grade, True, grade_color)
            surface.blit(g_surf, (SCREEN_W // 2 - g_surf.get_width() // 2,
                                  STRIKE_LINE_Y + 30))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _find_closest_note(self, lane: int, now: float) -> NoteTarget | None:
        best = None
        best_err = float("inf")
        for node in self._pool.active_nodes:
            t = node.target
            if t is None or t.lane != lane or t.hit or t.missed:
                continue
            err = abs(now - self._conductor.target_hit_time(t.row_index))
            if err < best_err and err <= Player.OK_WINDOW:
                best_err = err
                best = t
        return best

    def _release_node_for(self, target: NoteTarget):
        for node in self._pool.active_nodes:
            if node.target is target:
                self._pool.release(node)
                return
