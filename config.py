# ─────────────────────────────────────────────
#  Emergency Exit Guidance System — Config v2
#
#  3-floor, 9-node layout.
#  Real sensors: exit_A (GPIO4/CH0), exit_B (GPIO5/CH1), mid_F2 (GPIO6/CH2)
#  Real webcam:  exit_A only
#  GPIO LEDs:    exit_A, exit_B, mid_F2 (Floor 2 only)
# ─────────────────────────────────────────────

# ── System Settings ───────────────────────────
REFRESH_INTERVAL        = 2      # seconds between sensor reads
WEBCAM_INDEX            = 0      # cv2.VideoCapture index for exit_A
CAMERA_REFRESH_INTERVAL = 0.75
CAMERA_FRAME_WIDTH      = 640
CAMERA_FRAME_HEIGHT     = 480
CAMERA_ANALYSIS_WIDTH   = 320
CAMERA_ANALYSIS_HEIGHT  = 240
CAMERA_MOG2_HISTORY     = 500
CAMERA_MOG2_VAR_THRESH  = 50
CAMERA_HYBRID_EDGE_WEIGHT    = 0.3
CAMERA_HYBRID_SCORE_DIVISOR  = 100.0

# ── Node lists ────────────────────────────────
ALL_NODES = [
    "exit_A", "mid_F2", "exit_B",    # Floor 2
    "exit_C", "mid_F1", "exit_D",    # Floor 1
    "exit_E", "main_exit", "exit_F", # Ground
]

NODE_FLOOR = {
    "exit_A": 2, "mid_F2": 2, "exit_B": 2,
    "exit_C": 1, "mid_F1": 1, "exit_D": 1,
    "exit_E": 0, "main_exit": 0, "exit_F": 0,
}

NODE_LABEL = {
    "exit_A":    "Exit A",
    "mid_F2":    "Corridor F2",
    "exit_B":    "Exit B",
    "exit_C":    "Exit C",
    "mid_F1":    "Corridor F1",
    "exit_D":    "Exit D",
    "exit_E":    "Exit E",
    "main_exit": "Main Exit",
    "exit_F":    "Exit F",
}

# Nodes with physical DHT22 + MQ2 sensors
REAL_SENSOR_NODES = {"exit_A", "exit_B", "mid_F2"}

# Only exit_A has a real USB webcam
REAL_CAM_NODE = "exit_A"

# Floor 2 nodes with physical GPIO LEDs
GPIO_LED_NODES = {"exit_A", "exit_B", "mid_F2"}

# DHT22 GPIO pin per real-sensor node
DHT22_PIN_MAP = {
    "exit_A": 4,
    "exit_B": 5,
    "mid_F2": 6,
}

# MQ2 SPI channel per real-sensor node
MQ2_CHANNEL_MAP = {
    "exit_A": 0,
    "exit_B": 1,
    "mid_F2": 2,
}

# Used by init_sensors — ordered list matches DHT22 sensor indices
DHT22_PINS = [4, 5, 6]   # exit_A, exit_B, mid_F2
MQ2_CHANNELS = [0, 1, 2]

# ── GPIO Pins (Floor 2 only) ──────────────────
# Keyed by node_id
GPIO_PINS = {
    "exit_A": {"green": 17, "red": 27},
    "exit_B": {"green": 22, "red": 23},
    "mid_F2": {"green": 24, "red": 25},
}

# ── Scoring weights by node type ──────────────
WEIGHTS = {
    "real_webcam": {"temp": 0.25, "smoke": 0.35, "crowd": 0.10, "camera": 0.30},
    "sim_webcam":  {"temp": 0.28, "smoke": 0.38, "crowd": 0.20, "camera": 0.14},
    "no_webcam":   {"temp": 0.30, "smoke": 0.40, "crowd": 0.30, "camera": 0.00},
    "corridor":    {"temp": 0.35, "smoke": 0.45, "crowd": 0.20, "camera": 0.00},
}

NODE_TYPE = {
    "exit_A":    "real_webcam",
    "exit_B":    "sim_webcam",
    "exit_C":    "sim_webcam",
    "exit_D":    "sim_webcam",
    "exit_E":    "sim_webcam",
    "exit_F":    "sim_webcam",
    "main_exit": "no_webcam",
    "mid_F2":    "corridor",
    "mid_F1":    "corridor",
}

# ── Risk thresholds ───────────────────────────
# risk_score 0–100, higher = more dangerous
RISK_THRESHOLDS = [
    (85, "CRITICAL"),
    (65, "DANGER"),
    (40, "CAUTION"),
    (0,  "SAFE"),
]
