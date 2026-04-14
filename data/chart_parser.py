from __future__ import annotations

import json
from dataclasses import dataclass, field

from core.game_logger import get_logger

logger = get_logger("Chart")

# State integers used in the 2D chart grid
EMPTY = 0
TAP = 1
HOLD_HEAD = 2
HOLD_BODY = 3
HOLD_TAIL = 4

NUM_LANES = 6


# ======================================================================
# NoteTarget  – a single actionable event parsed from the grid
# ======================================================================
@dataclass
class NoteTarget:
    lane: int
    row_index: int
    note_type: int            # TAP | HOLD_HEAD | HOLD_TAIL
    hold_end_row: int = -1    # only meaningful for HOLD_HEAD
    hit: bool = False
    missed: bool = False


# ======================================================================
# Song  – flat data container produced by the parser
# ======================================================================
@dataclass
class Song:
    name: str
    bpm: float
    audio_path: str
    rows_per_beat: int
    notes: list[NoteTarget] = field(default_factory=list)


# ======================================================================
# ChartParser  – reads a JSON chart file and builds a Song
# ======================================================================
class ChartParser:
    @staticmethod
    def load(path: str) -> Song:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        name: str = data["song_name"]
        bpm: float = float(data["bpm"])
        audio_path: str = data["audio_file"]
        grid: list[list[int]] = data["chart"]
        rows_per_beat: int = int(data.get("rows_per_beat", 4))

        song = Song(name=name, bpm=bpm, audio_path=audio_path,
                    rows_per_beat=rows_per_beat)

        for row_idx, row in enumerate(grid):
            if len(row) != NUM_LANES:
                logger.warning(
                    "Row %d has %d columns (expected %d) – skipping",
                    row_idx, len(row), NUM_LANES,
                )
                continue
            for lane, cell in enumerate(row):
                if cell == TAP:
                    song.notes.append(
                        NoteTarget(lane=lane, row_index=row_idx, note_type=TAP)
                    )
                elif cell == HOLD_HEAD:
                    # Scan forward for the HOLD_TAIL in this lane
                    tail_row = ChartParser._find_hold_tail(grid, row_idx, lane)
                    song.notes.append(
                        NoteTarget(lane=lane, row_index=row_idx,
                                   note_type=HOLD_HEAD, hold_end_row=tail_row)
                    )

        # Sort by row_index so the gameplay loop can process them in order
        song.notes.sort(key=lambda n: (n.row_index, n.lane))

        logger.info(
            "Loaded chart '%s' – BPM=%.1f  rows=%d  active notes=%d",
            name, bpm, len(grid), len(song.notes),
        )
        return song

    @staticmethod
    def _find_hold_tail(grid: list[list[int]], head_row: int, lane: int) -> int:
        for r in range(head_row + 1, len(grid)):
            if grid[r][lane] == HOLD_TAIL:
                return r
        logger.warning("No HOLD_TAIL found for head at row %d lane %d", head_row, lane)
        return head_row  # degenerate: treat as zero-length hold
