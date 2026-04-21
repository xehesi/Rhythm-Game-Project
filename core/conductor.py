import pygame
from core.game_logger import get_logger

logger = get_logger("Conductor")


class Conductor:
    """Central timing authority. All game timing derives from audio position."""

    def __init__(self, bpm: float, offset: float = 0.0, rows_per_beat: int = 4):
        self.bpm = bpm
        self.ms_per_beat = 60000.0 / bpm
        self.offset = offset
        self.rows_per_beat = rows_per_beat
        self.ms_per_row = self.ms_per_beat / self.rows_per_beat

        self.song_position: float = 0.0
        self.song_started = False
        self.speed_multiplier: float = 1.0
        self._last_update_tick: int = 0
        self._audio_has_finished: bool = False

        # Assist-mode recovery
        self._recovering = False
        self._recovery_rate = 0.005  # multiplier increment per frame toward 1.0

        logger.info(
            "Initialized: BPM=%.1f  ms/beat=%.2f  ms/row=%.2f  offset=%.1f",
            bpm, self.ms_per_beat, self.ms_per_row, offset,
        )

    # ------------------------------------------------------------------
    # Frame update – the ONLY place song_position is written
    # ------------------------------------------------------------------
    def update(self):
        if not self.song_started:
            return
        now_tick = pygame.time.get_ticks()
        if self._last_update_tick == 0:
            self._last_update_tick = now_tick
        delta_ms = max(0, now_tick - self._last_update_tick)
        self._last_update_tick = now_tick

        raw_pos = pygame.mixer.music.get_pos()  # ms since play() was called
        if raw_pos == -1:
            # Keep chart time moving after audio finishes so late-chart notes
            # can still be reached and judged.
            self.song_position += delta_ms
            if not self._audio_has_finished:
                self._audio_has_finished = True
                logger.info("Audio playback ended; continuing chart timing")
        else:
            self.song_position = raw_pos - self.offset
            self._audio_has_finished = False

        # Recovery interpolation toward 1.0x speed
        if self._recovering:
            self.speed_multiplier += self._recovery_rate
            if self.speed_multiplier >= 1.0:
                self.speed_multiplier = 1.0
                self._recovering = False
                logger.info("Speed recovery complete – back to 1.0x")

    # ------------------------------------------------------------------
    # Target-time helpers (strict multiplication – never cumulative)
    # ------------------------------------------------------------------
    def target_hit_time(self, row_index: int) -> float:
        return row_index * self.ms_per_row

    def note_y(self, target_time: float, strike_line_y: float,
               scroll_speed: float) -> float:
        return strike_line_y - (target_time - self.song_position) * scroll_speed

    # ------------------------------------------------------------------
    # Playback control
    # ------------------------------------------------------------------
    def start_song(self, audio_path: str):
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        self.song_started = True
        self.song_position = 0.0
        self._last_update_tick = pygame.time.get_ticks()
        self._audio_has_finished = False
        logger.info("Playback started: %s", audio_path)

    def stop_song(self):
        pygame.mixer.music.stop()
        self.song_started = False
        self._last_update_tick = 0
        self._audio_has_finished = False
        logger.info("Playback stopped")

    # ------------------------------------------------------------------
    # Assist-mode: slow down then recover
    # ------------------------------------------------------------------
    def trigger_slowdown(self):
        self.speed_multiplier = 0.5
        self._recovering = True
        logger.info("Assist slowdown triggered – speed set to 0.5x")

    # ------------------------------------------------------------------
    # Desync reporting (for debug overlay)
    # ------------------------------------------------------------------
    def desync_ms(self) -> float:
        if not self.song_started:
            return 0.0
        raw = pygame.mixer.music.get_pos()
        return abs((raw - self.offset) - self.song_position)
