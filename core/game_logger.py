import logging
import sys

_LOG_FORMAT = "%(asctime)s [%(name)-14s] %(levelname)-7s %(message)s"
_DATE_FORMAT = "%H:%M:%S"

_formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

# Console handler
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_formatter)

# File handler
_file_handler = logging.FileHandler("rhythm_game.log", mode="w", encoding="utf-8")
_file_handler.setFormatter(_formatter)

_root = logging.getLogger("RhythmGame")
_root.setLevel(logging.DEBUG)
_root.addHandler(_console_handler)
_root.addHandler(_file_handler)


def get_logger(name: str) -> logging.Logger:
    return _root.getChild(name)
