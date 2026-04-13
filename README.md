# AEGIS — Dynamic Emergency Exit Guidance System
## Raspberry Pi 4 · Flask · DHT22 · MQ2 · MCP3008

---

## 📁 Project Structure

```
emergency_exit/
├── app.py            ← Flask server (main entry point)
├── config.py         ← All thresholds, weights, GPIO pins
├── sensors.py        ← DHT22 / MQ2 / Crowd sensor reads
├── scoring.py        ← Weighted risk scoring + LED control
├── requirements.txt
└── templates/
    └── index.html    ← Real-time web dashboard (SSE)
```

---

## ⚡ Quick Start

### Development / Simulation (no hardware needed)
```bash
pip install flask
SIMULATE=1 python app.py
# Open http://localhost:5000
```

### Real Hardware (Raspberry Pi)
```bash
pip install flask Adafruit_DHT spidev RPi.GPIO
SIMULATE=0 python app.py
```

---

## 🔌 Wiring Guide

### DHT22 Sensors (one per exit)
| Exit | DHT22 Data Pin | RPi GPIO |
|------|---------------|----------|
|  1   | GPIO 4        | Pin 7    |
|  2   | GPIO 5        | Pin 29   |
|  3   | GPIO 6        | Pin 31   |

> Each DHT22: VCC→3.3V, GND→GND, DATA→GPIO (with 10kΩ pull-up to VCC)

### MCP3008 ADC (for MQ2 analog output)
```
MCP3008 Pin    →  RPi
VDD  (16)      →  3.3V
VREF (15)      →  3.3V
AGND (14)      →  GND
CLK  (13)      →  GPIO11 (SCLK, Pin 23)
DOUT (12)      →  GPIO9  (MISO, Pin 21)
DIN  (11)      →  GPIO10 (MOSI, Pin 19)
CS   (10)      →  GPIO8  (CE0,  Pin 24)
DGND ( 9)      →  GND
CH0            →  MQ2 Exit 1 AOUT
CH1            →  MQ2 Exit 2 AOUT
CH2            →  MQ2 Exit 3 AOUT
```

### MQ2 Sensors (one per exit)
| Exit | MQ2 AOUT | MCP3008 Channel |
|------|----------|-----------------|
|  1   | AOUT     | CH0             |
|  2   | AOUT     | CH1             |
|  3   | AOUT     | CH2             |

> Each MQ2: VCC→5V, GND→GND, AOUT→MCP3008 channel

### LEDs (one green + one red per exit)
| Exit | Green GPIO | Red GPIO | Notes              |
|------|-----------|----------|--------------------|
|  1   | GPIO 17   | GPIO 27  | 220Ω resistor each |
|  2   | GPIO 22   | GPIO 23  | 220Ω resistor each |
|  3   | GPIO 24   | GPIO 25  | 220Ω resistor each |

> Each LED: Anode→GPIO (via 220Ω), Cathode→GND

---

## ⚖️ Scoring Weights

| Sensor      | Weight | Rationale                        |
|-------------|--------|----------------------------------|
| Smoke/Gas   | 40%    | Most critical fire indicator     |
| Temperature | 30%    | Fire and heat detection          |
| Crowd       | 20%    | Evacuation bottleneck risk       |
| Humidity    | 10%    | Low humidity accelerates fire    |

Risk score: **0.0** (fully safe) → **1.0** (maximum danger)

| Score Range | Status   | LEDs            |
|-------------|----------|-----------------|
| 0.00 – 0.35 | SAFE     | Green ON, Red OFF |
| 0.35 – 0.65 | MODERATE | Both ON          |
| 0.65 – 1.00 | DANGER   | Green OFF, Red ON |

---

## 🌐 API Endpoints

| Method | Route         | Description              |
|--------|--------------|--------------------------|
| GET    | /            | Live dashboard UI        |
| GET    | /api/status  | Full JSON snapshot       |
| GET    | /api/stream  | Server-Sent Events (SSE) |

---

## 🔧 Customisation (config.py)

Edit `config.py` to adjust:
- `THRESHOLDS` — change safe/warning/danger levels per sensor
- `WEIGHTS` — rebalance scoring (must sum to 1.0)
- `GPIO_PINS` — remap LED pins
- `DHT22_PINS` / `MQ2_CHANNELS` — remap sensor connections
