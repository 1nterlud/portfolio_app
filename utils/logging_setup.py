"""
Lightweight logging setup. Each module gets a logger via get_logger(__name__).
Log level defaults to INFO; can be overridden via STREAMLIT_LOG_LEVEL env var.
"""
import logging
import os
import sys

_INITIALIZED = False


def _setup() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    level = os.environ.get("STREAMLIT_LOG_LEVEL", "INFO").upper()
    fmt   = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))

    root = logging.getLogger("portfolio_app")
    root.setLevel(level)
    root.handlers = [handler]
    root.propagate = False
    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    _setup()
    return logging.getLogger(f"portfolio_app.{name}")
