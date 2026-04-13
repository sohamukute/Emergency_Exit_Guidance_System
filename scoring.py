# ─────────────────────────────────────────────
#  Emergency Exit Guidance System — Risk Scoring & GPIO
#
#  Risk score: 0–100 (higher = more dangerous)
#  Status: SAFE (<40) | CAUTION (40-65) | DANGER (65-85) | CRITICAL (≥85)
#  None temp or smoke → SENSOR_ERROR (both LEDs off)
#
#  GPIO LEDs only on: exit_A, exit_B, mid_F2 (Floor 2)
# ─────────────────────────────────────────────

import threading
import time

import RPi.GPIO as GPIO

from config import GPIO_PINS, GPIO_LED_NODES, WEIGHTS, NODE_TYPE, RISK_THRESHOLDS
from logger import log_sensor


# ── GPIO setup (Floor 2 nodes only) ──────────────────────
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for _node_id, _pins in GPIO_PINS.items():
    GPIO.setup(_pins["green"], GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(_pins["red"],   GPIO.OUT, initial=GPIO.LOW)

_last_led_state: dict = {}

# ── Blink state ───────────────────────────────────────────
_blink_lock   = threading.Lock()
_blink_states: dict[str, dict] = {}   # node_id -> {green, red, hz}
_blink_thread_started = False


def _blink_worker():
    """Background thread: toggles LEDs that need blinking."""
    while True:
        with _blink_lock:
            items = list(_blink_states.items())
        for node_id, cfg in items:
            if node_id not in GPIO_PINS:
                continue
            pins = GPIO_PINS[node_id]
            hz   = cfg.get("hz", 0)
            if hz <= 0:
                continue
            # Toggle green
            if cfg.get("green"):
                cur = GPIO.input(pins["green"])
                GPIO.output(pins["green"], GPIO.LOW if cur else GPIO.HIGH)
            # Toggle red
            if cfg.get("red"):
                cur = GPIO.input(pins["red"])
                GPIO.output(pins["red"], GPIO.LOW if cur else GPIO.HIGH)
        time.sleep(0.25)   # 4 checks/s — fine for 1 Hz and 2 Hz blink


def _start_blink_thread():
    global _blink_thread_started
    if not _blink_thread_started:
        threading.Thread(target=_blink_worker, daemon=True).start()
        _blink_thread_started = True


# ── Normalisation helpers ─────────────────────────────────
def _norm_temp(t: float) -> float:
    if t <= 30:
        return 0.0
    if t <= 50:
        return (t - 30) / 40.0          # 0 → 0.5
    if t <= 80:
        return 0.5 + (t - 50) / 60.0   # 0.5 → 1.0
    return 1.0


def _norm_smoke(s: float) -> float:
    if s <= 0.5:
        return 0.0
    if s <= 2.0:
        return (s - 0.5) / 3.0          # 0 → 0.5
    if s <= 4.0:
        return 0.5 + (s - 2.0) / 4.0   # 0.5 → 1.0
    return 1.0


def _norm_crowd(c: int) -> float:
    if c <= 3:
        return 0.0
    if c <= 7:
        return (c - 3) / (4 / 0.6)     # 0 → 0.6
    return 0.6 + (c - 7) / (3 / 0.4)  # 0.6 → 1.0


def _risk_to_status(risk: float) -> str:
    for threshold, status in RISK_THRESHOLDS:
        if risk >= threshold:
            return status
    return "SAFE"


# ── Core risk computation ─────────────────────────────────
def compute_risk(reading: dict) -> dict:
    """
    Parameters
    ----------
    reading : dict from sensors._read_node() — must contain
              node_id, temp, smoke, crowd, camera

    Returns
    -------
    {"risk": float | None, "status": str}
    """
    if reading.get("temp") is None or reading.get("smoke") is None:
        return {"risk": None, "status": "SENSOR_ERROR"}

    node_type = NODE_TYPE.get(reading["node_id"], "no_webcam")
    w = WEIGHTS[node_type]

    temp_n  = _norm_temp(reading["temp"])
    smoke_n = _norm_smoke(reading["smoke"])
    crowd_n = _norm_crowd(reading["crowd"])
    cam_n   = reading.get("camera")
    if cam_n is None:
        cam_n = crowd_n   # fallback: use crowd slider when no webcam

    risk = (
        w["temp"]   * temp_n  +
        w["smoke"]  * smoke_n +
        w["crowd"]  * crowd_n +
        w["camera"] * cam_n
    ) * 100.0

    risk = round(max(0.0, min(100.0, risk)), 1)
    return {"risk": risk, "status": _risk_to_status(risk)}


# ── LED control ───────────────────────────────────────────
def _resolve_led_config(status: str) -> dict:
    """
    Return blink config dict:
      {"green": bool, "red": bool, "hz": float,
       "green_static": int, "red_static": int}
    """
    if status == "SAFE":
        return {"green": False, "red": False, "hz": 0,
                "green_static": GPIO.HIGH, "red_static": GPIO.LOW}
    if status == "CAUTION":
        return {"green": True,  "red": False, "hz": 1,
                "green_static": GPIO.HIGH, "red_static": GPIO.LOW}
    if status == "DANGER":
        return {"green": False, "red": False, "hz": 0,
                "green_static": GPIO.LOW, "red_static": GPIO.HIGH}
    if status == "CRITICAL":
        return {"green": False, "red": True,  "hz": 2,
                "green_static": GPIO.LOW, "red_static": GPIO.HIGH}
    # SENSOR_ERROR — both off
    return {"green": False, "red": False, "hz": 0,
            "green_static": GPIO.LOW, "red_static": GPIO.LOW}


def update_led(node_id: str, status: str) -> dict:
    """Drive GPIO LED for a single node. No-op for non-GPIO nodes."""
    if node_id not in GPIO_LED_NODES:
        return {"node_id": node_id, "status": status, "has_gpio": False}

    pins = GPIO_PINS[node_id]
    cfg  = _resolve_led_config(status)

    GPIO.setup(pins["green"], GPIO.OUT)
    GPIO.setup(pins["red"],   GPIO.OUT)

    # Set static levels first
    GPIO.output(pins["green"], cfg["green_static"])
    GPIO.output(pins["red"],   cfg["red_static"])

    # Register blink config
    blink_entry = {"green": cfg["green"], "red": cfg["red"], "hz": cfg["hz"]}
    with _blink_lock:
        _blink_states[node_id] = blink_entry

    state = {
        "node_id":    node_id,
        "status":     status,
        "has_gpio":   True,
        "green_pin":  pins["green"],
        "red_pin":    pins["red"],
        "green_on":   cfg["green_static"] == GPIO.HIGH,
        "red_on":     cfg["red_static"]   == GPIO.HIGH,
        "blink_hz":   cfg["hz"],
    }

    if _last_led_state.get(node_id) != status:
        log_sensor(
            "INFO",
            f"LED {node_id} {status} → "
            f"G(GPIO{pins['green']})={'BLINK' if cfg['green'] else ('ON' if state['green_on'] else 'OFF')} "
            f"R(GPIO{pins['red']})={'BLINK' if cfg['red'] else ('ON' if state['red_on'] else 'OFF')}"
        )
        _last_led_state[node_id] = status

    return state


def update_all_leds(nodes: list) -> dict:
    """Drive LEDs for all nodes. nodes: list of dicts with 'node_id' and 'status'."""
    _start_blink_thread()
    states = {}
    for n in nodes:
        states[n["node_id"]] = update_led(n["node_id"], n["status"])
    return states


# ── Cleanup ───────────────────────────────────────────────
def cleanup_gpio():
    try:
        GPIO.cleanup()
    except Exception:
        pass
