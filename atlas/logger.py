from __future__ import annotations

import logging
from typing import Optional


def configure_logging(level: int = logging.INFO) -> None:
    if logging.getLogger().handlers:
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name)
