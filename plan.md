# Implementation Plan — AEGIS v2 (3-Floor, Multi-Exit, React+Tailwind UI)

## Overview

Major overhaul: 3-floor building with distinct hardware configurations per floor. **GPIO LEDs are physical hardware on Floor 2 only** (exit_A, mid_F2, exit_B). **Exit A, B, and mid_F2 use real DHT22 + MQ2 sensors**; all other nodes are **manually controlled via UI sliders** (temp, smoke, crowd). Webcam on exit_A is real USB; all other webcam nodes show a static SVG crowd indicator. Cross-floor stair connections, 8-scenario decision logic, risk scoring (replacing safety score), and a React + Tailwind CSS dashboard.

> [!NOTE]
> **"Simulated" throughout this document means: values are set by a human operator using sliders in the React dashboard, which POST to the backend.** There is no auto-generated or time-varying data — the last slider value is what the scoring engine uses.

---

## Physical Layout

### Floor 2 (Top Floor)

```
[Exit A] ─── [1L][1R] ─── [No-Exit Sensor] ─── [2L][2R] ─── [Exit B]
  real webcam                  gpio led (indicator)             sim webcam
  REAL sensor                  gpio led (indicator)             REAL sensor
  gpio led                                                       gpio led
```

> [!IMPORTANT]
> GPIO LEDs are **only on Floor 2** (exit_A, mid_F2, exit_B). Floor 1 and Ground Floor nodes have no physical LED indicators.

| Node | Type | Hardware |
|------|------|----------|
| Exit A | Real exit | **Real DHT22 + MQ2 sensor**, **real USB webcam**, GPIO LED |
| 1L, 1R | Signage | Software state only (shown in UI) |
| mid_F2 | No-exit sensor point | **Real DHT22 + MQ2 sensor**, **GPIO LED** (status indicator only) |
| 2L, 2R | Signage | Software state only (shown in UI) |
| Exit B | Real exit | **Real DHT22 + MQ2 sensor**, simulated webcam (OpenCV), GPIO LED |

### Floor 1 (Middle Floor)

All inputs simulated. **No GPIO LEDs on this floor** — status is UI-only.

```
[Exit C] ─── [3L][3R] ─── [No-Exit Sensor] ─── [4L][4R] ─── [Exit D]
  sim webcam                  (no gpio)                        sim webcam
  sim sensor                  sim sensor                       sim sensor
  (no gpio)                                                    (no gpio)
```

| Node | Type | Hardware |
|------|------|----------|
| Exit C | Real exit | Simulated sensor + webcam, **no GPIO LED** |
| mid_F1 | No-exit sensor point | Simulated sensor, **no GPIO LED** |
| Exit D | Real exit | Simulated sensor + webcam, **no GPIO LED** |

### Ground Floor

All inputs simulated. **No GPIO LEDs on this floor** — status is UI-only.

```
[Exit E] ─── [5L][5R] ─── [Main Exit] ─── [6L][6R] ─── [Exit F]
 sim sensor                sim sensor                    sim sensor
 sim webcam                no webcam                     sim webcam
 (no gpio)                 (no gpio)                     (no gpio)
```

| Node | Type | Hardware |
|------|------|----------|
| Exit E | Real exit | Simulated sensor + webcam, **no GPIO LED** |
| Main Exit | Primary evacuation exit | Simulated sensor only (no webcam), **no GPIO LED** |
| Exit F | Real exit | Simulated sensor + webcam, **no GPIO LED** |

### Inter-Floor Connections (Stairs)

Each outdoor exit (A, B, C, D, E, F) has a staircase connecting it to exits on adjacent floors:

```
Exit A (F2) ←stairs→ Exit C (F1) ←stairs→ Exit E (GF)
Exit B (F2) ←stairs→ Exit D (F1) ←stairs→ Exit F (GF)
```

The stairwell carries evacuation flow — if an upper-floor exit is blocked, occupants can descend stairs to the floor below and use that floor's exit.

---

## Exit & Sensor ID Reference

| ID | Location | Floor | Has Webcam | Sensor Type | GPIO LED |
|----|----------|-------|------------|-------------|----------|
| `exit_A` | Left end | 2 | ✅ Real USB webcam | ✅ **Real DHT22 + MQ2** | ✅ Yes |
| `exit_B` | Right end | 2 | Simulated (OpenCV) | ✅ **Real DHT22 + MQ2** | ✅ Yes |
| `exit_C` | Left end | 1 | Simulated (OpenCV) | Simulated | ❌ No |
| `exit_D` | Right end | 1 | Simulated (OpenCV) | Simulated | ❌ No |
| `exit_E` | Left end | Ground | Simulated (OpenCV) | Simulated | ❌ No |
| `exit_F` | Right end | Ground | Simulated (OpenCV) | Simulated | ❌ No |
| `main_exit` | Centre | Ground | None | Simulated | ❌ No |
| `mid_F2` | Centre | 2 | None | ✅ **Real DHT22 + MQ2** | ✅ Yes (indicator) |
| `mid_F1` | Centre | 1 | None | Simulated | ❌ No |

### Sign IDs

| Sign | Location | Points To |
|------|----------|-----------|
| 1L | Between Exit A & mid_F2 (Floor 2) | Exit A (←) |
| 1R | Between Exit A & mid_F2 (Floor 2) | mid_F2 then Exit B (→) |
| 2L | Between mid_F2 & Exit B (Floor 2) | Exit A then mid_F2 (←) |
| 2R | Between mid_F2 & Exit B (Floor 2) | Exit B (→) |
| 3L | Between Exit C & mid_F1 (Floor 1) | Exit C (←) |
| 3R | Between Exit C & mid_F1 (Floor 1) | mid_F1 then Exit D (→) |
| 4L | Between mid_F1 & Exit D (Floor 1) | Exit C then mid_F1 (←) |
| 4R | Between mid_F1 & Exit D (Floor 1) | Exit D (→) |
| 5L | Between Exit E & Main Exit (GF) | Exit E (←) |
| 5R | Between Exit E & Main Exit (GF) | Main Exit (→) |
| 6L | Between Main Exit & Exit F (GF) | Main Exit (←) |
| 6R | Between Main Exit & Exit F (GF) | Exit F (→) |

---

## Scoring: Risk Score (replaces Safety Score)

**Risk Score** is now the primary metric. Higher = more dangerous.

### Risk Formula

```
risk_score = (
    w_temp   * temp_norm   +
    w_smoke  * smoke_norm  +
    w_crowd  * crowd_norm  +
    w_camera * camera_norm
) * 100
```

Where each `_norm` is `[0.0, 1.0]` (0 = safe, 1 = max danger).

### Thresholds & Weights

#### Temperature Normalisation

| Range | norm |
|-------|------|
| ≤ 30°C | 0.0 |
| 30–50°C | linear 0→0.5 |
| 50–80°C | linear 0.5→1.0 |
| > 80°C | 1.0 |

#### Smoke Normalisation (0–5V ADC equivalent)

| Range | norm |
|-------|------|
| 0.0–0.5 | 0.0 |
| 0.5–2.0 | linear 0→0.5 |
| 2.0–4.0 | linear 0.5→1.0 |
| > 4.0 | 1.0 |

#### Crowd Normalisation (0–10 scale)

| Range | norm |
|-------|------|
| 0–3 | 0.0 |
| 3–7 | linear 0→0.6 |
| 7–10 | linear 0.6→1.0 |

#### Camera (Computer Vision crowd density, 0–1 float)

Pass-through: `camera_norm = cv_density_float`

> If no webcam, `camera_norm = crowd_norm` (manual override propagates).

### Default Weights

| Node type | w_temp | w_smoke | w_crowd | w_camera |
|-----------|--------|---------|---------|----------|
| Exit with real webcam | 0.25 | 0.35 | 0.10 | 0.30 |
| Exit with sim webcam | 0.28 | 0.38 | 0.20 | 0.14 |
| No-webcam exit (Main Exit) | 0.30 | 0.40 | 0.30 | 0.00 |
| Mid-corridor sensor (no exit) | 0.35 | 0.45 | 0.20 | 0.00 |

### Status Thresholds

| risk_score | Status |
|------------|--------|
| 0–39 | `SAFE` |
| 40–64 | `CAUTION` |
| 65–84 | `DANGER` |
| ≥ 85 | `CRITICAL` |
| `None` | `SENSOR_ERROR` |

---

## Decision Logic (Sign Routing)

### Base Rule (per sign)

Each sign displays the **risk level of the exit it points to**. If blocked/critical, it flip to `BLOCKED`.

```
sign_state = "blocked" if target_exit.status in ("DANGER", "CRITICAL", "SENSOR_ERROR") else "safe"
```

### Multi-Sensor Critical Scenarios

These handle cascading failures and cross-floor routing recommendations.

#### Scenario 1 — Same-Floor Both Exits CRITICAL (e.g. Exit A + Exit B = CRITICAL)

> All signs on Floor 2 point DOWN (stairwell).  
> Signs 1L, 1R, 2L, 2R → state = `"stairs"`  
> Mid corridor sensor LED → blink amber  
> UI shows floor-level alert banner: "Both exits critical — Use stairs to Floor 1"

Logic:
```python
if exit_A.status in ("CRITICAL","DANGER") and exit_B.status in ("CRITICAL","DANGER"):
    floor2_override = "stairs"
```

#### Scenario 2 — Mid-corridor sensor CRITICAL (e.g. mid_F2 CRITICAL)

> The corridor centre is too dangerous to traverse.  
> 1R and 2L flip to `"blocked"` (don't walk toward centre).  
> 1L → still shows Exit A status.  
> 2R → still shows Exit B status.  
> Users near Exit A side are routed to Exit A; users near Exit B side routed to Exit B directly.

Logic:
```python
if mid_F2.status in ("CRITICAL", "DANGER"):
    sign_1R = "blocked"
    sign_2L = "blocked"
```

#### Scenario 3 — One exit CRITICAL + mid-corridor CAUTION/DANGER

> The safe side is preferred but congestion at centre is noted.  
> Signs on the CRITICAL exit side get `"blocked"`.  
> Signs pointing toward centre blink amber (`"caution"` state).  
> Signs pointing to safe exit get `"safe"`.

Logic:
```python
if exit_A.status == "CRITICAL" and mid_F2.status in ("CAUTION","DANGER"):
    sign_1L = "blocked"
    sign_1R = "caution"   # centre congested
    sign_2L = "caution"
    sign_2R = "safe" if exit_B.status not in ("CRITICAL","DANGER") else "blocked"
```

#### Scenario 4 — Sensors 4 and 5 both CRITICAL (cross-floor cascade)

> `exit_D` (Floor 1 right) and `exit_E` (Ground floor left) are both CRITICAL.  
> The entire right-side stair column (B→D→F) and left-side ground (E) are compromised.

Decision tree:
```
if exit_D.CRITICAL and exit_E.CRITICAL:
    ├── sign_4R = "blocked"          # don't use Exit D
    ├── sign_5L = "blocked"          # don't use Exit E
    ├── sign_5R = "safe"             # redirect toward Main Exit
    ├── sign_6L = "safe"             # Main Exit reachable from right side
    ├── sign_6R = eval(exit_F)       # if Exit F clear → "safe", else "blocked"
    ├── Floor 1 banner: "Exit D blocked — descend left stair to Ground Floor"
    └── Ground banner: "Exit E blocked — use Main Exit or Exit F"
```

#### Scenario 5 — All same-side exits across floors CRITICAL (full column failure)

> E.g. Exit A (F2), Exit C (F1), Exit E (GF) all CRITICAL — entire left column gone.  
> All left-pointing signs → `"blocked"`.  
> All right-pointing signs → `"safe"` or current status.  
> Global alert: "Left evacuation column compromised — use RIGHT side exits only."

#### Scenario 6 — Main Exit CRITICAL (Ground Floor)

> Main Exit is primary — its failure has highest impact.  
> Signs 5R and 6L flip to `"blocked"`.  
> 5L → redirects to Exit E if clear.  
> 6R → redirects to Exit F if clear.  
> If Exit E AND Exit F are also CRITICAL/DANGER → trigger full EVACUATE TO UPPER FLOOR alarm (reverse stair flow).

Logic:
```python
if main_exit.status in ("CRITICAL", "DANGER"):
    sign_5R = "blocked"
    sign_6L = "blocked"
    if exit_E safe:
        sign_5L = "safe"
    if exit_F safe:
        sign_6R = "safe"
    if exit_E.CRITICAL and exit_F.CRITICAL:
        global_alert = "ALL GROUND EXITS COMPROMISED — shelter in place or ascend stairs"
```

#### Scenario 7 — SENSOR_ERROR on any node

> Treat as worst-case (`DANGER`) for sign routing.  
> LEDs on that node: both off (neutral).  
> Signs pointing to that node: `"blocked"`.  
> UI amber chip visible.

#### Scenario 8 — Stairwell Routing Priority

Signs showing `"stairs"` override all other states.  
`"stairs"` state: blue background, ↓ arrow, text "USE STAIRS".  
This is only set by cross-floor cascade logic, not by individual sensor readings.

### Sign State Summary

| State | LED Colour | Arrow | Background | Text |
|-------|-----------|-------|------------|------|
| `safe` | Green | ← or → | `#00c853` | SAFE |
| `caution` | Amber blink | ← or → | `#ff8f00` | CAUTION |
| `blocked` | Red | ✕ | `#cc0000` | BLOCKED |
| `stairs` | Blue | ↓ | `#1565c0` | USE STAIRS |

---

## Change 1 — Slider Override Store (`slider_store.py`)

> **No `simulation.py`. No `sim_webcam.py`.** Simulated nodes have their sensor values set by UI sliders. The backend stores the latest slider-posted values and serves them as sensor readings.

### New File: `slider_store.py`

Thread-safe in-memory store for all manually controlled sensor values.

```python
# slider_store.py
# Holds slider-controlled sensor values for all non-real-sensor nodes.
# UI posts to /api/override; backend reads from here.

import threading

_lock = threading.Lock()

# Default starting values for each simulated node
_DEFAULTS = {
    "exit_C":    {"temp": 25.0, "smoke": 0.1, "crowd": 0},
    "exit_D":    {"temp": 25.0, "smoke": 0.1, "crowd": 0},
    "exit_E":    {"temp": 25.0, "smoke": 0.1, "crowd": 0},
    "exit_F":    {"temp": 25.0, "smoke": 0.1, "crowd": 0},
    "main_exit": {"temp": 25.0, "smoke": 0.1, "crowd": 0},
    "mid_F1":    {"temp": 25.0, "smoke": 0.1, "crowd": 0},
}

_store = {k: dict(v) for k, v in _DEFAULTS.items()}

def set_value(node_id: str, field: str, value: float) -> None:
    """Called when a UI slider is moved. field is 'temp', 'smoke', or 'crowd'."""
    with _lock:
        if node_id in _store and field in _store[node_id]:
            _store[node_id][field] = value

def get_values(node_id: str) -> dict:
    """Returns current slider values for a node."""
    with _lock:
        return dict(_store.get(node_id, {}))

def get_all() -> dict:
    with _lock:
        return {k: dict(v) for k, v in _store.items()}
```

### Slider Ranges

| Field | Min | Max | Step | Unit |
|-------|-----|-----|------|------|
| `temp` | 0 | 100 | 0.5 | °C |
| `smoke` | 0.0 | 5.0 | 0.05 | V (ADC equiv.) |
| `crowd` | 0 | 10 | 1 | people scale |

### Files Affected

- **[NEW]** `slider_store.py` — thread-safe slider value store
- **[MODIFY]** `sensors.py` — simulated nodes read from `slider_store` instead of sensors
- **[MODIFY]** `app.py` — add `POST /api/override` endpoint
- **~~[REMOVED]~~** `simulation.py` — not needed
- **~~[REMOVED]~~** `sim_webcam.py` — not needed

---

## Change 2 — Multi-Floor Sensor Layer (`sensors.py`)

### Node List

```python
ALL_NODES = [
    "exit_A", "exit_B",            # Floor 2
    "mid_F2",                       # Floor 2 corridor
    "exit_C", "exit_D",            # Floor 1
    "mid_F1",                       # Floor 1 corridor
    "exit_E", "main_exit", "exit_F" # Ground Floor
]
```

### Per-Node Reader Pattern

```python
# Nodes that use real physical DHT22 + MQ2 sensors
REAL_SENSOR_NODES = {"exit_A", "exit_B", "mid_F2"}

# Only exit_A has a real USB webcam; all other webcam nodes show SVG placeholder
REAL_CAM_NODE = "exit_A"

# Nodes whose webcam panel shows a static SVG crowd indicator (no video stream)
SVG_PLACEHOLDER_NODES = {"exit_B", "exit_C", "exit_D", "exit_E", "exit_F"}

# Floor 2 nodes with physical GPIO LEDs
GPIO_LED_NODES = {"exit_A", "mid_F2", "exit_B"}

def _read_node(node_id: str) -> dict:
    """Returns unified sensor dict for any node."""
    if node_id in REAL_SENSOR_NODES:
        # Read physical DHT22 for temp/humidity, MQ2 via SPI for smoke
        temp, humidity = _read_dht22(node_id)
        smoke          = _read_mq2(node_id)
        # Crowd for real-sensor nodes is still set by the UI crowd slider
        crowd          = slider_store.get_values(node_id).get("crowd", 0)
        source_base    = "dht22+mq2"
    else:
        # All values come from the slider store (set by operator via UI)
        vals     = slider_store.get_values(node_id)
        temp     = vals["temp"]
        humidity = None
        smoke    = vals["smoke"]
        crowd    = vals["crowd"]
        source_base = "slider"

    has_real_cam = (node_id == REAL_CAM_NODE)

    if has_real_cam:
        camera_density = _read_real_webcam()
        source_cam     = "+real_cam"
    else:
        # No synthetic video — crowd slider value is used directly as camera density
        camera_density = round(crowd / 10.0, 2)  # normalise 0-10 → 0.0-1.0
        source_cam     = ""

    return {
        "node_id":      node_id,
        "temp":         temp,
        "humidity":     humidity,
        "smoke":        smoke,
        "crowd":        crowd,
        "camera":       camera_density,
        "has_gpio_led": node_id in GPIO_LED_NODES,
        "source":       source_base + source_cam,
    }
```

### Files Affected

#### [MODIFY] `sensors.py`
- Remove all per-exit functions (`_read_exit1`, `_read_exit2`, `_read_exit3`)
- Add `ALL_NODES` list and unified `_read_node(node_id)` function
- Define `REAL_SENSOR_NODES = {"exit_A", "exit_B", "mid_F2"}` — only these read physical hardware
- Define `GPIO_LED_NODES = {"exit_A", "mid_F2", "exit_B"}` — only these drive GPIO pins
- DHT22 index map: `exit_A → GPIO4`, `exit_B → GPIO5`, `mid_F2 → GPIO6`
- MQ2 SPI channel map: `exit_A → CH0`, `exit_B → CH1`, `mid_F2 → CH2`
- Import `slider_store` (replaces `simulation` and `sim_webcam`)
- `_sensor_thread()` iterates `ALL_NODES` every 2s
- Expose `get_all_readings() -> dict[str, dict]`

---

## Change 3 — Risk Scoring (`scoring.py`)

### Changes

- **Remove** `compute_safety_score()` / any reference to "safety score"
- **Rename** all occurrences → `compute_risk_score()`
- Risk score field in API response: `"risk"` (not `"score"`)
- `status` derived from `risk` as per threshold table above
- Weights table in `config.py` keyed by node type

#### [MODIFY] `config.py`

```python
WEIGHTS = {
    "real_webcam":  {"temp": 0.25, "smoke": 0.35, "crowd": 0.10, "camera": 0.30},
    "sim_webcam":   {"temp": 0.28, "smoke": 0.38, "crowd": 0.20, "camera": 0.14},
    "no_webcam":    {"temp": 0.30, "smoke": 0.40, "crowd": 0.30, "camera": 0.00},
    "corridor":     {"temp": 0.35, "smoke": 0.45, "crowd": 0.20, "camera": 0.00},
}

# Which nodes use real physical sensors (DHT22 + MQ2)
REAL_SENSOR_NODES = {"exit_A", "exit_B", "mid_F2"}

# Which nodes have physical GPIO LEDs
GPIO_LED_NODES = {"exit_A", "mid_F2", "exit_B"}

NODE_TYPE = {
    "exit_A":    "real_webcam",   # real DHT22+MQ2, real USB cam
    "exit_B":    "sim_webcam",    # real DHT22+MQ2, sim cam
    "exit_C":    "sim_webcam",    # fully simulated
    "exit_D":    "sim_webcam",    # fully simulated
    "exit_E":    "sim_webcam",    # fully simulated
    "exit_F":    "sim_webcam",    # fully simulated
    "main_exit": "no_webcam",     # fully simulated
    "mid_F2":    "corridor",      # real DHT22+MQ2, LED indicator
    "mid_F1":    "corridor",      # simulated, no LED
}

RISK_THRESHOLDS = {
    "SAFE":     (0,  40),
    "CAUTION":  (40, 65),
    "DANGER":   (65, 85),
    "CRITICAL": (85, 101),
}
```

#### [MODIFY] `scoring.py`

```python
def compute_risk(reading: dict) -> dict:
    if reading["temp"] is None or reading["smoke"] is None:
        return {"risk": None, "status": "SENSOR_ERROR"}

    node_type = config.NODE_TYPE[reading["node_id"]]
    w = config.WEIGHTS[node_type]

    temp_n  = _norm_temp(reading["temp"])
    smoke_n = _norm_smoke(reading["smoke"])
    crowd_n = _norm_crowd(reading["crowd"])
    cam_n   = reading["camera"] if reading["camera"] is not None else crowd_n

    risk = (w["temp"]*temp_n + w["smoke"]*smoke_n +
            w["crowd"]*crowd_n + w["camera"]*cam_n) * 100

    status = _risk_to_status(risk)
    return {"risk": round(risk, 1), "status": status}
```

---

## Change 4 — Decision Logic (`decision.py`)

### New File: `decision.py`

Centralises all cross-node, cross-floor routing decisions.

```python
# decision.py
# Inputs:  dict of {node_id: {"risk": float, "status": str}}
# Outputs: dict of {sign_id: sign_state, "alerts": [str], "floor_overrides": {}}

SIGN_TARGETS = {
    # Floor 2
    "1L": "exit_A",  "1R": "mid_F2",
    "2L": "mid_F2",  "2R": "exit_B",
    # Floor 1
    "3L": "exit_C",  "3R": "mid_F1",
    "4L": "mid_F1",  "4R": "exit_D",
    # Ground
    "5L": "exit_E",  "5R": "main_exit",
    "6L": "main_exit","6R": "exit_F",
}

def compute_signs(node_states: dict) -> dict:
    signs = {}
    alerts = []

    def st(nid): return node_states.get(nid, {}).get("status", "SENSOR_ERROR")
    def bad(nid): return st(nid) in ("DANGER", "CRITICAL", "SENSOR_ERROR")
    def crit(nid): return st(nid) in ("CRITICAL",)

    # --- Base rule ---
    for sign, target in SIGN_TARGETS.items():
        signs[sign] = "blocked" if bad(target) else "safe"

    # --- Scenario 2: mid-corridor CRITICAL/DANGER ---
    if bad("mid_F2"):
        signs["1R"] = "blocked"
        signs["2L"] = "blocked"
    if bad("mid_F1"):
        signs["3R"] = "blocked"
        signs["4L"] = "blocked"

    # --- Scenario 1: both floor exits bad → stairs ---
    if bad("exit_A") and bad("exit_B"):
        signs.update({"1L":"stairs","1R":"stairs","2L":"stairs","2R":"stairs"})
        alerts.append("Floor 2: Both exits critical — USE STAIRS to Floor 1")
    if bad("exit_C") and bad("exit_D"):
        signs.update({"3L":"stairs","3R":"stairs","4L":"stairs","4R":"stairs"})
        alerts.append("Floor 1: Both exits critical — USE STAIRS to Ground Floor")

    # --- Scenario 4: exit_D + exit_E both CRITICAL ---
    if bad("exit_D") and bad("exit_E"):
        signs["4R"] = "blocked"
        signs["5L"] = "blocked"
        signs["5R"] = "safe" if not bad("main_exit") else "blocked"
        signs["6L"] = "safe" if not bad("main_exit") else "blocked"
        signs["6R"] = "safe" if not bad("exit_F") else "blocked"
        alerts.append("Exit D (F1 right) + Exit E (GF left) blocked — use Main Exit or Exit F")

    # --- Scenario 6: Main Exit critical ---
    if bad("main_exit"):
        signs["5R"] = "blocked"
        signs["6L"] = "blocked"
        signs["5L"] = "safe" if not bad("exit_E") else "blocked"
        signs["6R"] = "safe" if not bad("exit_F") else "blocked"
        if bad("exit_E") and bad("exit_F"):
            alerts.append("CRITICAL: ALL GROUND EXITS COMPROMISED — shelter in place or ascend stairs")

    # --- Scenario 5: full column failure ---
    left_col = [bad("exit_A"), bad("exit_C"), bad("exit_E")]
    if all(left_col):
        for s in ["1L","2L","3L","4L","5L"]:
            signs[s] = "blocked"
        alerts.append("Left evacuation column compromised — use RIGHT-side exits only")

    right_col = [bad("exit_B"), bad("exit_D"), bad("exit_F")]
    if all(right_col):
        for s in ["1R","2R","3R","4R","6R"]:
            signs[s] = "blocked"
        alerts.append("Right evacuation column compromised — use LEFT-side exits only")

    # --- Scenario 3: mixed critical + corridor caution ---
    if bad("exit_A") and st("mid_F2") in ("CAUTION", "DANGER") and not bad("exit_B"):
        signs["1L"] = "blocked"
        signs["1R"] = "caution"
        signs["2L"] = "caution"
        signs["2R"] = "safe"
    if bad("exit_B") and st("mid_F2") in ("CAUTION", "DANGER") and not bad("exit_A"):
        signs["2R"] = "blocked"
        signs["2L"] = "caution"
        signs["1R"] = "caution"
        signs["1L"] = "safe"

    return {"signs": signs, "alerts": alerts}
```

### Files Affected

- **[NEW]** `decision.py`
- **[MODIFY]** `signs.py` → delegates entirely to `decision.compute_signs()`
- **[MODIFY]** `app.py` → call `decision.compute_signs()` and include `alerts` in API response

---

## Change 5 — API Layer (`app.py`)

### New / Modified Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/data` | All node readings + signs + alerts |
| `POST` | `/api/crowd` | Manual crowd override for any node (legacy — replaced by `/api/override`) |
| `POST` | `/api/override` | Set any slider field (temp/smoke/crowd) for a simulated node |
| `GET` | `/api/logs/sensors` | Sensor log circular buffer |
| `GET` | `/api/logs/api` | API log circular buffer |
| `GET` | `/api/video/exit_A` | MJPEG stream (real webcam only) |

### `/api/data` Response Schema

```json
{
  "ts": "2026-04-13T14:30:00",
  "nodes": {
    "exit_A": {
      "node_id": "exit_A", "floor": 2,
      "temp": 31.2, "smoke": 0.45, "crowd": 3, "camera": 0.28,
      "risk": 34.1, "status": "SAFE", "source": "sim+real_cam",
      "has_webcam": true
    },
    "mid_F2": {
      "node_id": "mid_F2", "floor": 2,
      "temp": 29.1, "smoke": 0.12, "crowd": 1, "camera": null,
      "risk": 14.5, "status": "SAFE", "source": "dht22+mq2",
      "has_webcam": false
    }
  },
  "signs": {
    "1L": "safe", "1R": "safe", "2L": "safe", "2R": "safe",
    "3L": "safe", "3R": "safe", "4L": "safe", "4R": "safe",
    "5L": "safe", "5R": "safe", "6L": "safe", "6R": "safe"
  },
  "alerts": [],
  "gpio_leds": {
    "exit_A": "green",
    "exit_B": "green",
    "mid_F2": "off"
  }
}
```

### `/api/override` Body

Sent by the UI whenever a slider changes. `field` is `"temp"`, `"smoke"`, or `"crowd"`.

```json
{ "node_id": "exit_D", "field": "temp",  "value": 72.0 }
{ "node_id": "exit_E", "field": "smoke", "value": 3.5  }
{ "node_id": "mid_F1", "field": "crowd", "value": 8   }
```

---

## Change 6 — GPIO LED Mapping

> [!IMPORTANT]
> **Physical GPIO LEDs exist only on Floor 2**: `exit_A`, `mid_F2`, and `exit_B`.  
> Floor 1 and Ground Floor nodes have **no GPIO wiring** — their status is reflected in the UI only.

| Node | Green GPIO | Red GPIO | Floor | Notes |
|------|-----------|---------|-------|-------|
| exit_A | 17 | 27 | 2 | Left exit — real sensor + real cam |
| exit_B | 22 | 23 | 2 | Right exit — real sensor + sim cam |
| mid_F2 | 24 | 25 | 2 | Centre corridor indicator only |

All other nodes (`exit_C`, `exit_D`, `exit_E`, `exit_F`, `main_exit`, `mid_F1`) → **no GPIO LED**, UI status only.

### LED States by Status

| Status | Green | Red |
|--------|-------|-----|
| SAFE | HIGH | LOW |
| CAUTION | HIGH (blink 1 Hz) | LOW |
| DANGER | LOW | HIGH |
| CRITICAL | LOW | HIGH (blink 2 Hz) |
| SENSOR_ERROR | LOW | LOW |

### Files Affected

#### [MODIFY] `scoring.py`
- `_resolve_led_levels(status)` → returns `(green_level, red_level, blink_hz)`
- Only call `GPIO.output()` for nodes in `GPIO_LED_NODES`; skip silently for others
- Blink handled by background thread with `time.sleep`

---

## Change 7 — React + Tailwind Dashboard (New Frontend)

### Technology Stack

| Item | Choice | Reason |
|------|--------|--------|
| Framework | **React 18** (Vite) | Component model needed for 3-floor complexity |
| Styling | **Tailwind CSS v3** | Utility-first, fast prototyping, Raspi-friendly |
| Charts | **Recharts** | Lightweight, pure JS, no CDN required offline |
| Icons | **Lucide React** | Replaces inline SVG symbols |
| State | React `useState` + `useEffect` poll | Simple polling at 2s |
| Video | `<img>` MJPEG stream | Works on Raspi Chromium |

### Setup

```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install tailwindcss @tailwindcss/vite lucide-react recharts
```

### File Structure

```
frontend/
├── src/
│   ├── App.jsx              # Root, data fetcher, alert banner
│   ├── components/
│   │   ├── FloorMap.jsx     # SVG floor plan per floor (interactive)
│   │   ├── NodeCard.jsx     # Per-node sensor card
│   │   ├── SignBadge.jsx    # Sign state pill (safe/caution/blocked/stairs)
│   │   ├── RiskGauge.jsx    # Recharts radial gauge for risk score
│   │   ├── AlertBanner.jsx  # Top alert ribbon for cross-floor events
│   │   ├── VideoPanel.jsx   # MJPEG <img> with fallback SVG
│   │   ├── LogViewer.jsx    # Sensor + API logs, auto-refresh 5s
│   │   └── IncidentControls.jsx  # Inject/clear incident buttons (dev panel)
│   ├── hooks/
│   │   └── useApiData.js    # Polling hook, returns {nodes, signs, alerts}
│   └── main.jsx
├── tailwind.config.js
├── vite.config.js           # Proxy /api → Flask :5000
└── package.json
```

### Key Component Details

#### `App.jsx`
- Polls `/api/data` every 2s via `useApiData` hook
- Top-level layout: `<AlertBanner>` → 3× `<FloorSection>` stacked vertically
- Each `<FloorSection>` contains `<FloorMap>` + row of `<NodeCard>` components
- Dark background `bg-gray-950`, accent colours from Tailwind `emerald/amber/red/blue`

#### `FloorMap.jsx`
- Inline SVG corridor diagram per floor (top-down view)
- Exit nodes coloured by status: green/amber/red/gray/blue
- Sign badges rendered as SVG `<foreignObject>` or positioned absolutely
- Stair icons at each end of the corridor linking to adjacent floors
- Corridor nodes (mid_F2, mid_F1) shown as smaller diamonds
- Click on a node → opens `NodeCard` detail modal

#### `NodeCard.jsx`
- Shows: node ID, floor, status chip, risk gauge, temp, smoke, crowd, source tag
- Status chip colours: `bg-emerald-500` SAFE, `bg-amber-500` CAUTION, `bg-red-600` DANGER, `bg-red-800` CRITICAL, `bg-orange-500` SENSOR_ERROR
- Risk gauge: `<RiskGauge value={risk} />` — semi-circle radial, green→amber→red gradient
- Crowd override slider for any node (posts to `/api/crowd`)
- Incident inject buttons: 🔥 Fire, 👥 Crowd Surge, ✅ Clear (dev mode toggle)

#### `SignBadge.jsx`
- Renders sign state as coloured pill
- `safe` → green pill, arrow icon
- `caution` → amber pulsing pill
- `blocked` → red pill, X icon
- `stairs` → blue pill, ↓ arrow

#### `AlertBanner.jsx`
- Red ribbon at top when alerts array non-empty
- Each alert as a dismissable chip
- Auto-scrolls if multiple alerts

#### `VideoPanel.jsx`
- `<img src="/api/video/{node_id}" />` for MJPEG stream
- If no webcam → shows SVG silhouette placeholder with crowd level number
- Error fallback → grey box with camera-off icon

#### `RiskGauge.jsx`
- Semi-circular gauge using Recharts `RadialBarChart`
- 0–100 range, colour zones: 0–40 emerald, 40–65 amber, 65–85 red, 85–100 deep red
- Score displayed in centre with status label below

#### `LogViewer.jsx`
- Collapsible panel at bottom of page
- Two tabs: "Sensor Logs" / "API Logs"
- Auto-refresh every 5s from `/api/logs/sensors` and `/api/logs/api`
- Entries newest-first, level-coloured rows: red=ERROR, amber=WARN, grey=INFO

#### `IncidentControls.jsx`
- Dev-mode toggle (hidden by default, activated by pressing `Ctrl+Shift+D`)
- Grid of all nodes with "🔥 Fire" / "👥 Surge" / "✅ Clear" buttons
- Instantly posts to `/api/incident`
- Useful for demos and testing scenario logic

### Tailwind Theme (`tailwind.config.js`)

```js
theme: {
  extend: {
    colors: {
      safe:    '#00c853',
      caution: '#ff8f00',
      danger:  '#cc0000',
      critical:'#7b0000',
      neutral: '#1e293b',
    },
    animation: {
      'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      'blink':      'blink 0.5s step-end infinite',
    },
  }
}
```

### Vite Proxy (dev mode)

```js
// vite.config.js
server: {
  proxy: {
    '/api': 'http://localhost:5000'
  }
}
```

In production on the Raspi, run `npm run build` and serve the `dist/` folder from Flask's `static_folder`.

### Flask Integration

```python
# app.py additions
from flask import send_from_directory

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path and os.path.exists(os.path.join("frontend/dist", path)):
        return send_from_directory("frontend/dist", path)
    return send_from_directory("frontend/dist", "index.html")
```

---

## Change 8 — Silent Terminal + Logging (unchanged from v1)

All `print()` → `log_sensor()` / `log_api()` via `logger.py`.  
`logger.py` already in codebase — extend to handle new node IDs.

---

## Execution Order

| Step | Change | Files | Risk |
|------|--------|-------|------|
| 1 | `slider_store.py` — new file | `slider_store.py` | None |
| 2 | `config.py` — weights, thresholds, node types | `config.py` | Low |
| 3 | `sensors.py` — unified node reader + slider integration | `sensors.py` | Medium |
| 4 | `scoring.py` — risk score, remove safety score | `scoring.py` | Medium |
| 5 | `decision.py` — sign+alert logic | New file | Medium |
| 6 | `signs.py` — delegate to decision.py | `signs.py` | Low |
| 7 | `app.py` — new routes + `/api/override`, React serving | `app.py` | Medium |
| 8 | React frontend scaffold + components | `frontend/` | High |
| 9 | GPIO LED blink thread | `scoring.py` | Low |
| 10 | Log viewer + SimControls sliders in UI | `frontend/src/components/` | Low |
| 11 | End-to-end hardware test | — | — |

---

## Verification Plan

```bash
# 1. Check all nodes in data response
curl http://localhost:5000/api/data | python3 -m json.tool | grep node_id

# 2. Risk scores present, no "score" key
curl http://localhost:5000/api/data | python3 -m json.tool | grep risk

# 3. Push temp slider on exit_B to 75°C, check sign 2R flips to blocked
curl -X POST http://localhost:5000/api/override \
     -H "Content-Type: application/json" \
     -d '{"node_id":"exit_B","field":"temp","value":75}'
curl http://localhost:5000/api/data | python3 -m json.tool | grep -A2 '"2R"'

# 4. Push temp+smoke on exit_D and exit_E to trigger Scenario 4
curl -X POST http://localhost:5000/api/override -H "Content-Type: application/json" \
     -d '{"node_id":"exit_D","field":"smoke","value":4.5}'
curl -X POST http://localhost:5000/api/override -H "Content-Type: application/json" \
     -d '{"node_id":"exit_E","field":"smoke","value":4.5}'
curl http://localhost:5000/api/data | python3 -m json.tool | grep -E '"4R"|"5L"|"5R"|alerts'

# 5. Push both floor-2 exits to DANGER, check stairs override
curl -X POST http://localhost:5000/api/override -H "Content-Type: application/json" \
     -d '{"node_id":"exit_A","field":"crowd","value":10}'
# (exit_A uses real sensors — this only moves crowd slider; temp/smoke are hardware)

# 6. Sensor logs
curl http://localhost:5000/api/logs/sensors | python3 -m json.tool | head -40

# 7. React UI accessible
curl http://localhost:5000/ | grep -i react
```

### Hardware Tests

- GPIO LED on `exit_A` turns red when real DHT22 reads temp > 65°C (hold heat source near sensor)
- GPIO LED on `exit_B` turns red when real MQ2 reads smoke > 2.0V equivalent
- GPIO LED blinks at 2 Hz when status = CRITICAL
- `mid_F2` LED goes to both-off when DHT22/MQ2 returns error (SENSOR_ERROR)
- React dashboard loads in Raspi Chromium within 3s on localhost
- MJPEG stream from `exit_A` (real webcam) renders live in VideoPanel
- Slider nodes (exit_C, exit_D, etc.) show current slider values in NodeCard
- Moving smoke slider on exit_D to max → risk score rises → sign 4R flips to blocked in UI
- AlertBanner appears when both floor exits reach DANGER via slider
- Sign badges update in FloorMap SVG within 2s of slider change

---

## Questions to Confirm Before Implementation

| Question | Default Assumption |
|----------|--------------------|
| Physical GPIO pin assignments correct? | Used table above — confirm |
| Flask + Vite run on same Raspi (served via Flask dist)? | Yes |
| Node.js available on Raspi? | Needed for `npm run build` |
| Real webcam is at `/dev/video0`? | Yes |
| Humidity sensor (DHT22) used or skipped in sim? | Skipped (all sim nodes return `humidity: null`) |
| Real webcam node: real temp/smoke too, or only webcam is real? | Only webcam is real; temp/smoke = simulated |
