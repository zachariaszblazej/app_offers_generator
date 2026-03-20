"""
Application logging module.

Logs are written to .txt files in a 'logs' folder next to the executable
(or next to main.py in development mode).

Rotation rules:
  - Single file max size : 5 MB
  - Max number of files  : 20  (oldest deleted when limit exceeded)
"""

import logging
import logging.handlers
import os
import sys
import glob


# ── Constants ────────────────────────────────────────────────────────────────
_MAX_BYTES = 5 * 1024 * 1024   # 5 MB per file
_BACKUP_COUNT = 19              # 19 backups + 1 active = 20 files max
_LOG_FILENAME = "app.txt"
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _get_logs_dir() -> str:
    """Return the path to the logs directory.

    - PyInstaller frozen  → next to the .exe
    - Development         → project root (where main.py lives)
    """
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        # Go up from src/utils/ to project root
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logs_dir = os.path.join(base, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def _cleanup_old_logs(logs_dir: str) -> None:
    """Delete oldest log files if count exceeds the limit (20 total)."""
    pattern = os.path.join(logs_dir, "app.txt*")
    log_files = sorted(glob.glob(pattern), key=os.path.getmtime)
    max_total = _BACKUP_COUNT + 1  # 20
    while len(log_files) > max_total:
        oldest = log_files.pop(0)
        try:
            os.remove(oldest)
        except OSError:
            pass


def setup_logging() -> logging.Logger:
    """Configure and return the root application logger.

    Call this once at application startup (in main.py).
    Afterwards, any module can simply do:

        import logging
        logger = logging.getLogger(__name__)
        logger.info("message")
    """
    logs_dir = _get_logs_dir()
    log_path = os.path.join(logs_dir, _LOG_FILENAME)

    # Clean up before attaching handler (in case of leftover files)
    _cleanup_old_logs(logs_dir)

    # Rotating file handler  (5 MB × 20 files)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding='utf-8',
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Avoid duplicate handlers on repeated calls
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        root.addHandler(file_handler)

    return root
