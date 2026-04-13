# ─────────────────────────────────────────────
#  Emergency Exit Guidance System — Sensors v2
#
#  Real hardware nodes: exit_A, exit_B, mid_F2 (Floor 2)
#    exit_A — DHT22 GPIO4 + MQ2 CH0 + real USB webcam CV
#    exit_B — DHT22 GPIO5 + MQ2 CH1 + crowd slider
#    mid_F2 — DHT22 GPIO6 + MQ2 CH2 + no camera
#
#  Slider-controlled nodes (all others):
#    Values come from slider_store (operator sets via UI).
#    No hardware read attempted for these nodes.
#
#  Sensor errors on real nodes → None values → SENSOR_ERROR
# ─────────────────────────────────────────────

import html
import threading
import time

import pigpio
import DHT22
import spidev

from config import (
    ALL_NODES,
    CAMERA_ANALYSIS_HEIGHT,
    CAMERA_ANALYSIS_WIDTH,
    CAMERA_FRAME_HEIGHT,
    CAMERA_FRAME_WIDTH,
    CAMERA_HYBRID_EDGE_WEIGHT,
    CAMERA_HYBRID_SCORE_DIVISOR,
    CAMERA_MOG2_HISTORY,
    CAMERA_MOG2_VAR_THRESH,
    CAMERA_REFRESH_INTERVAL,
    DHT22_PIN_MAP,
    MQ2_CHANNEL_MAP,
    REAL_CAM_NODE,
    REAL_SENSOR_NODES,
    GPIO_LED_NODES,
    REFRESH_INTERVAL,
    WEBCAM_INDEX,
    DHT22_PINS,
)
import slider_store
from logger import log_sensor

try:
    import numpy as np
except Exception as ex:
    np = None
    log_sensor("WARN", f"NumPy unavailable — webcam disabled: {ex}")

try:
    import cv2
    _CV2_OK = np is not None
except Exception as ex:
    cv2 = None
    _CV2_OK = False
    log_sensor("WARN", f"OpenCV unavailable — webcam disabled: {ex}")

_bg_subtractor = (
    cv2.createBackgroundSubtractorMOG2(
        history=CAMERA_MOG2_HISTORY,
        varThreshold=CAMERA_MOG2_VAR_THRESH,
        detectShadows=False,
    )
    if _CV2_OK else None
)

# ── Shared state ──────────────────────────────────────────
_threads_started = False
_data_lock       = threading.Lock()
# Dict: node_id -> latest reading dict
_sensor_data: dict[str, dict | None] = {nid: None for nid in ALL_NODES}

_camera_lock  = threading.Lock()
_camera_state = {
    "crowd":          0,
    "density_pct":    0.0,
    "motion_pixels":  0,
    "edge_pixels":    0,
    "crowd_score":    0.0,
    "display_score":  0,
    "status":         "booting",
    "available":      False,
    "frame_bytes":    b"",
    "frame_mimetype": "image/svg+xml",
    "updated_at":     0.0,
}

_pi        = None
_dht_ready = False
_spi       = None
_spi_ready = False

# DHT sensor objects indexed by position in DHT22_PINS list
_dht_sensors: list = []

# Map: node_id -> index in _dht_sensors
_REAL_NODE_IDX = {"exit_A": 0, "exit_B": 1, "mid_F2": 2}


# ── Hardware init ─────────────────────────────────────────
def _init_pigpio():
    global _pi, _dht_ready
    _pi = pigpio.pi()
    if not getattr(_pi, "connected", False):
        raise RuntimeError(
            "pigpio daemon is not running — start it with: sudo pigpiod"
        )
    _dht_ready = True
    log_sensor("INFO", "pigpio connected OK")


def _init_spi():
    global _spi, _spi_ready
    _spi = spidev.SpiDev()
    _spi.open(0, 0)
    _spi.max_speed_hz = 1_350_000
    _spi_ready = True
    log_sensor("INFO", "SPI / MCP3008 ready")


def _read_mcp3008(channel: int) -> int:
    adc = _spi.xfer2([1, (8 + channel) << 4, 0])
    return ((adc[1] & 3) << 8) + adc[2]


# ── Camera helpers ─────────────────────────────────────────
def _build_placeholder_frame(message: str) -> tuple[bytes, str]:
    safe_msg = html.escape(message or "Webcam starting")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480">
  <rect width="640" height="480" fill="#081019"/>
  <rect x="20" y="20" width="600" height="440" rx="18" fill="#101826" stroke="#22344b" stroke-width="2"/>
  <text x="320" y="180" fill="#e4eefc" font-family="Arial,sans-serif" font-size="26" text-anchor="middle">USB Webcam Preview</text>
  <text x="320" y="240" fill="#8db4ff" font-family="Courier New,monospace" font-size="20" text-anchor="middle">{safe_msg}</text>
  <text x="320" y="290" fill="#6a7f9f" font-family="Arial,sans-serif" font-size="16" text-anchor="middle">Waiting for /dev/video0</text>
</svg>""".strip()
    return svg.encode("utf-8"), "image/svg+xml"


def _set_camera_state(*, crowd, density_pct, motion_pixels, edge_pixels,
                       crowd_score, display_score, status, available,
                       frame_bytes, frame_mimetype):
    with _camera_lock:
        _camera_state["crowd"]          = crowd
        _camera_state["density_pct"]    = round(density_pct, 1)
        _camera_state["motion_pixels"]  = motion_pixels
        _camera_state["edge_pixels"]    = edge_pixels
        _camera_state["crowd_score"]    = round(crowd_score, 1)
        _camera_state["display_score"]  = display_score
        _camera_state["status"]         = status
        _camera_state["available"]      = available
        _camera_state["frame_bytes"]    = frame_bytes
        _camera_state["frame_mimetype"] = frame_mimetype
        _camera_state["updated_at"]     = time.time()


def _set_camera_placeholder(message: str):
    fb, fm = _build_placeholder_frame(message)
    _set_camera_state(
        crowd=0, density_pct=0.0, motion_pixels=0, edge_pixels=0,
        crowd_score=0.0, display_score=0, status=message,
        available=False, frame_bytes=fb, frame_mimetype=fm,
    )


def _camera_snapshot() -> dict:
    with _camera_lock:
        return dict(_camera_state)


# ── Webcam thread (exit_A only) ────────────────────────────
def _open_camera():
    if not _CV2_OK:
        return None
    backend = getattr(cv2, "CAP_V4L2", 0)
    try:
        cap = cv2.VideoCapture(WEBCAM_INDEX, backend) if backend else cv2.VideoCapture(WEBCAM_INDEX)
    except TypeError:
        cap = cv2.VideoCapture(WEBCAM_INDEX)
    if cap is None or not cap.isOpened():
        if cap is not None:
            cap.release()
        return None
    if hasattr(cv2, "CAP_PROP_FOURCC") and hasattr(cv2, "VideoWriter_fourcc"):
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_FRAME_HEIGHT)
    if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def _analyse_frame(frame):
    small = cv2.resize(frame, (CAMERA_ANALYSIS_WIDTH, CAMERA_ANALYSIS_HEIGHT))
    gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

    motion_mask   = _bg_subtractor.apply(small)
    motion_mask   = cv2.medianBlur(motion_mask, 5)
    motion_pixels = int(np.sum(motion_mask > 0))

    edges         = cv2.Canny(gray, 50, 150)
    edge_pixels   = int(np.sum(edges > 0))

    crowd_score   = motion_pixels + (CAMERA_HYBRID_EDGE_WEIGHT * edge_pixels)
    display_score = int(crowd_score / CAMERA_HYBRID_SCORE_DIVISOR)
    crowd         = max(0, min(10, display_score))
    density_pct   = round(max(0.0, min(100.0, display_score * 10.0)), 1)

    cv2.putText(small, f"Crowd: {display_score}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.putText(small, f"Motion: {motion_pixels}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.putText(small, f"Edges: {edge_pixels}", (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

    motion_display = cv2.cvtColor(motion_mask, cv2.COLOR_GRAY2BGR)
    edge_display   = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    top            = np.hstack((small, motion_display))
    bottom         = np.hstack((edge_display, np.zeros_like(edge_display)))
    preview        = np.vstack((top, bottom))

    ok, encoded = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    if not ok:
        raise RuntimeError("JPEG encode failed")

    return density_pct, crowd, encoded.tobytes(), motion_pixels, edge_pixels, crowd_score, display_score


def _webcam_thread():
    if not _CV2_OK:
        _set_camera_placeholder("OpenCV not installed")
        return
    cap = None
    while True:
        try:
            if cap is None:
                cap = _open_camera()
                if cap is None:
                    _set_camera_placeholder("USB webcam not found on /dev/video0")
                    time.sleep(1.5)
                    continue
            ok, frame = cap.read()
            if not ok or frame is None:
                _set_camera_placeholder("USB webcam read failed — retrying")
                cap.release()
                cap = None
                time.sleep(1.0)
                continue
            (density_pct, crowd, frame_bytes,
             motion_pixels, edge_pixels,
             crowd_score, display_score) = _analyse_frame(frame)
            _set_camera_state(
                crowd=crowd, density_pct=density_pct,
                motion_pixels=motion_pixels, edge_pixels=edge_pixels,
                crowd_score=crowd_score, display_score=display_score,
                status="USB webcam live (hybrid)",
                available=True, frame_bytes=frame_bytes,
                frame_mimetype="image/jpeg",
            )
        except Exception as ex:
            log_sensor("ERROR", f"Webcam: {ex}")
            _set_camera_placeholder(f"Webcam error: {ex}")
            if cap is not None:
                cap.release()
                cap = None
        time.sleep(CAMERA_REFRESH_INTERVAL)


# ── Per-node read helpers ─────────────────────────────────
def _read_dht(node_id: str) -> tuple:
    """Return (temp_C, humidity_pct) — floats or None on error."""
    idx = _REAL_NODE_IDX.get(node_id)
    if idx is None or not _dht_ready or idx >= len(_dht_sensors):
        return None, None
    try:
        sensor = _dht_sensors[idx]
        sensor.trigger()
        time.sleep(0.2)
        raw_temp = sensor.temperature()
        raw_hum  = sensor.humidity()
        temp = round(raw_temp, 1) if raw_temp != -999 else None
        hum  = round(raw_hum,  1) if raw_hum  != -999 else None
        return temp, hum
    except Exception as ex:
        log_sensor("WARN", f"DHT22[{node_id}] read error: {ex}")
        return None, None


def _read_smoke(node_id: str):
    """Return smoke level 0–5, or None on SPI error."""
    if not _spi_ready:
        return None
    channel = MQ2_CHANNEL_MAP.get(node_id)
    if channel is None:
        return None
    try:
        raw = _read_mcp3008(channel)
        return round((raw / 1023.0) * 5.0, 2)
    except Exception as ex:
        log_sensor("WARN", f"MQ2[{node_id}] CH{channel} read error: {ex}")
        return None


# ── Unified node reader ───────────────────────────────────
def _read_node(node_id: str) -> dict:
    if node_id in REAL_SENSOR_NODES:
        temp, humidity = _read_dht(node_id)
        smoke          = _read_smoke(node_id)
        crowd          = int(slider_store.get_values(node_id).get("crowd", 0))
        source_base    = "dht22+mq2"
    else:
        vals     = slider_store.get_values(node_id)
        temp     = vals.get("temp", 25.0)
        humidity = None
        smoke    = vals.get("smoke", 0.1)
        crowd    = int(vals.get("crowd", 0))
        source_base = "slider"

    is_real_cam = (node_id == REAL_CAM_NODE)

    if is_real_cam:
        camera    = _camera_snapshot()
        cam_crowd = camera["crowd"]
        camera_density = round(cam_crowd / 10.0, 2)
        source_cam     = "+real_cam" if camera["available"] else "+cam_fallback"
        extra = {
            "density_pct":          camera["density_pct"],
            "motion_pixels":        camera["motion_pixels"],
            "edge_pixels":          camera["edge_pixels"],
            "camera_crowd_score":   camera["crowd_score"],
            "camera_display_score": camera["display_score"],
            "camera_status":        camera["status"],
            "camera_ready":         camera["available"],
            "camera_updated_at":    camera["updated_at"],
        }
    else:
        camera_density = round(crowd / 10.0, 2)
        source_cam     = ""
        extra = {
            "density_pct":          None,
            "motion_pixels":        None,
            "edge_pixels":          None,
            "camera_crowd_score":   None,
            "camera_display_score": None,
            "camera_status":        None,
            "camera_ready":         False,
            "camera_updated_at":    None,
        }

    return {
        "node_id":      node_id,
        "temp":         temp,
        "humidity":     humidity,
        "smoke":        smoke,
        "crowd":        crowd,
        "camera":       camera_density,
        "has_gpio_led": node_id in GPIO_LED_NODES,
        "source":       source_base + source_cam,
        **extra,
    }


# ── Sensor polling thread ─────────────────────────────────
def _sensor_thread():
    while True:
        try:
            new_data = {}
            for nid in ALL_NODES:
                new_data[nid] = _read_node(nid)
            with _data_lock:
                _sensor_data.update(new_data)
            # Log summary for real nodes only
            for nid in REAL_SENSOR_NODES:
                d = new_data[nid]
                log_sensor(
                    "INFO",
                    f"{nid} T={d['temp']}°C H={d['humidity']}% "
                    f"S={d['smoke']}/5 C={d['crowd']}/10 [{d['source']}]"
                )
        except Exception as ex:
            log_sensor("ERROR", f"Sensor thread: {ex}")
        time.sleep(REFRESH_INTERVAL)


# ── Public API ────────────────────────────────────────────
def init_sensors():
    global _threads_started, _dht_sensors
    if _threads_started:
        return
    _init_pigpio()
    _init_spi()
    _dht_sensors = [DHT22.sensor(_pi, pin) for pin in DHT22_PINS]
    log_sensor("INFO", f"DHT22 sensors on pins {DHT22_PINS}")
    _set_camera_placeholder("USB webcam starting")
    threading.Thread(target=_webcam_thread, daemon=True).start()
    threading.Thread(target=_sensor_thread, daemon=True).start()
    _threads_started = True


def get_all_data() -> dict[str, dict | None]:
    with _data_lock:
        return dict(_sensor_data)


def get_latest_camera_frame() -> tuple[bytes, str]:
    camera = _camera_snapshot()
    if camera["frame_bytes"]:
        return camera["frame_bytes"], camera["frame_mimetype"]
    return _build_placeholder_frame(camera["status"])
