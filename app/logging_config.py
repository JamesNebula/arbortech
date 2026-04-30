import logging
import sys
from typing import Union

def setup_logging(level: Union[str, int] = "INFO") -> None:
    
    log_level = level if isinstance(level, int) else getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        encoding="utf-8",
        force=True
    )

    