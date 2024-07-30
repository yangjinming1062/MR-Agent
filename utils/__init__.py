import os
import sys

from loguru import logger

from .functions import call_with_retry
from .functions import clip_tokens
from .functions import convert_to_markdown
from .functions import is_valid_file
from .functions import load_yaml
from config import CONFIG

if log_dir := CONFIG.log.dir:
    # 日志记录
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    _c = {
        "handlers": [
            {
                "sink": os.path.join(log_dir, CONFIG.log.info_name),
                "format": CONFIG.log.format,
                "filter": lambda _x: _x["level"].name in ["DEBUG", "INFO"],
                "level": CONFIG.log.level,
            },
            {
                "sink": os.path.join(log_dir, CONFIG.log.error_name),
                "format": CONFIG.log.format,
                "filter": lambda _x: _x["level"].name in ["WARNING", "ERROR", "CRITICAL"],
                "level": "WARNING",
            },
            {
                "sink": sys.stdout,
                "colorize": True,
                "format": CONFIG.log.format,
                "level": CONFIG.log.level,
            },
        ],
    }
    logger.configure(**_c)

__all__ = [
    "logger",
    "call_with_retry",
    "clip_tokens",
    "convert_to_markdown",
    "is_valid_file",
    "load_yaml",
]
