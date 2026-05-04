# helpers/env.py

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env for local dev
load_dotenv(BASE_DIR / ".env")

# Logger
logger = logging.getLogger("env")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)

logger.setLevel(logging.INFO)
logger.propagate = False


def get_env(name, default=None, required=False):
    value = os.getenv(name)

    if value is None or value.strip() == "":
        if required:
            logger.warning(f"Missing environment variable: {name}")
        return default

    return value.strip()


def get_bool(name, default=False):
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return value.strip().lower() in {"true", "1", "yes", "on"}


def get_list(name, default=None):
    raw = os.getenv(name, "")
    values = [item.strip() for item in raw.split(",") if item.strip()]

    if values:
        return values

    return default if default is not None else []


def warn_missing(*names):
    for name in names:
        if not os.getenv(name):
            logger.warning(f"Missing environment variable: {name}")