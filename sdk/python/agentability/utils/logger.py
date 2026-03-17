"""Structured logging utility.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import logging
import sys


class _Colours:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    MAGENTA = "\033[95m"


class _AgentabilityFormatter(logging.Formatter):
    _LEVEL_COLOURS: dict[int, str] = {
        logging.DEBUG: _Colours.GRAY,
        logging.INFO: _Colours.GREEN,
        logging.WARNING: _Colours.YELLOW,
        logging.ERROR: _Colours.RED,
        logging.CRITICAL: _Colours.MAGENTA,
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        colour = self._LEVEL_COLOURS.get(record.levelno, _Colours.RESET)
        msg = (
            f"{colour}[{record.levelname}]{_Colours.RESET} "
            f"{_Colours.CYAN}{record.name}{_Colours.RESET}: "
            f"{record.getMessage()}"
        )
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)
        return msg


_cache: dict[str, logging.Logger] = {}
_default_level: int = logging.INFO


def configure_logging(
    level: int = logging.INFO,
    use_colours: bool = True,
    format_string: str | None = None,
) -> None:
    """Configure the root Agentability logger."""
    global _default_level  # noqa: PLW0603
    _default_level = level

    root = logging.getLogger("agentability")
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if use_colours and format_string is None:
        handler.setFormatter(_AgentabilityFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                format_string or "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a named child logger of ``agentability``."""
    if name not in _cache:
        logger = logging.getLogger(name)
        logger.setLevel(_default_level)
        _cache[name] = logger
    return _cache[name]


configure_logging()
