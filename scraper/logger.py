import sys
from pathlib import Path
from loguru import logger


def setup_logger(verbose: bool = False):
    logger.remove()
    
    log_level = "DEBUG" if verbose else "INFO"
    
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    logger.add(
        logs_dir / "scraper_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    return logger
