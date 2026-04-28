import logging
import sys

def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        stream=sys.stdout
    )

    