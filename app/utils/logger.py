
# app/utils/logger.py

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = BASE_DIR / "logs"

os.makedirs(LOG_DIR, exist_ok=True)

# Create main logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

if root_logger.hasHandlers():
    root_logger.handlers.clear()

# Console Handler (clean logs)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # only important logs

console_formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
console_handler.setFormatter(console_formatter)

# File Handler (full logs)
file_handler = RotatingFileHandler(
    LOG_DIR / "app.log",
    maxBytes=5_000_000,
    backupCount=3
)
file_handler.setLevel(logging.DEBUG)  # everything

file_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
file_handler.setFormatter(file_formatter)

# Error File Handler (only errors)
error_handler = RotatingFileHandler(
    LOG_DIR / "error.log",
    maxBytes=2_000_000,
    backupCount=2
)
error_handler.setLevel(logging.ERROR)

error_handler.setFormatter(file_formatter)

# Add all handlers
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)
root_logger.addHandler(error_handler)

# noise control 
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)