# ─────────────────────────────────────────────
#  Emergency Exit Guidance System — Logger
#
#  Thread-safe circular log buffers.
#  The entire codebase uses these instead of print().
#  Logs are exposed via /api/logs/sensors and /api/logs/api
# ─────────────────────────────────────────────

import threading
import time
from collections import deque

_lock       = threading.Lock()
_sensor_log = deque(maxlen=500)
_api_log    = deque(maxlen=500)


def _entry(level: str, msg: str) -> dict:
    return {
        "ts":    time.strftime("%Y-%m-%dT%H:%M:%S"),
        "level": level,
        "msg":   msg,
    }


def log_sensor(level: str, msg: str) -> None:
    """Append a sensor-related log entry (DHT22, MQ2, webcam, GPIO)."""
    with _lock:
        _sensor_log.append(_entry(level, msg))


def log_api(level: str, msg: str) -> None:
    """Append an API / main-loop log entry."""
    with _lock:
        _api_log.append(_entry(level, msg))


def get_sensor_logs() -> list:
    """Return sensor log entries as a list (oldest first)."""
    with _lock:
        return list(_sensor_log)


def get_api_logs() -> list:
    """Return API log entries as a list (oldest first)."""
    with _lock:
        return list(_api_log)
