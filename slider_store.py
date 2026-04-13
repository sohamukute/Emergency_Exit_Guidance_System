# ─────────────────────────────────────────────
#  Emergency Exit Guidance System — Slider Store
#
#  Holds manually-controlled sensor values for all non-real-sensor nodes.
#  The React dashboard POSTs slider changes to /api/override;
#  sensors.py reads from here instead of real hardware for those nodes.
# ─────────────────────────────────────────────

import threading

_lock = threading.Lock()

# Nodes whose values are set by the UI operator
_DEFAULTS: dict[str, dict] = {
    "exit_C":    {"temp": 25.0, "smoke": 0.1, "crowd": 0},
    "exit_D":    {"temp": 25.0, "smoke": 0.1, "crowd": 0},
    "exit_E":    {"temp": 25.0, "smoke": 0.1, "crowd": 0},
    "exit_F":    {"temp": 25.0, "smoke": 0.1, "crowd": 0},
    "main_exit": {"temp": 25.0, "smoke": 0.1, "crowd": 0},
    "mid_F1":    {"temp": 25.0, "smoke": 0.1, "crowd": 0},
    # Real-sensor nodes still allow a crowd override from the slider
    "exit_A":    {"crowd": 0},
    "exit_B":    {"crowd": 0},
    "mid_F2":    {"crowd": 0},
}

_store: dict[str, dict] = {k: dict(v) for k, v in _DEFAULTS.items()}

# Slider ranges (enforced on write)
_RANGES: dict[str, tuple] = {
    "temp":  (0.0, 100.0),
    "smoke": (0.0, 5.0),
    "crowd": (0,   10),
}


def set_value(node_id: str, field: str, value: float) -> bool:
    """
    Set a slider value for a node.
    Returns True on success, False if node_id / field unknown.
    """
    with _lock:
        if node_id not in _store:
            return False
        if field not in _store[node_id]:
            return False
        lo, hi = _RANGES.get(field, (None, None))
        if lo is not None:
            value = max(lo, min(hi, value))
        _store[node_id][field] = value
        return True


def get_values(node_id: str) -> dict:
    """Return current slider values for a node (copy)."""
    with _lock:
        return dict(_store.get(node_id, {}))


def get_all() -> dict:
    """Return all slider state (copy)."""
    with _lock:
        return {k: dict(v) for k, v in _store.items()}
