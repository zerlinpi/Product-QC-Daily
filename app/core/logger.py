import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logging(directory: Path) -> None:
    logger = logging.getLogger("qc")
    logger.setLevel(logging.INFO)
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    handler = TimedRotatingFileHandler(
        directory / "app.log", when="midnight", backupCount=30, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
