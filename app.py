# ─────────────────────────────────────────────
#  Emergency Exit Guidance System — Flask App v2
# ─────────────────────────────────────────────

import os
import sys
import time
import threading
import atexit

from flask import Flask, Response, jsonify, request, send_from_directory

from config   import ALL_NODES, NODE_FLOOR, NODE_LABEL, REAL_CAM_NODE, REFRESH_INTERVAL
from sensors  import get_all_data, get_latest_camera_frame, init_sensors
from scoring  import compute_risk, update_all_leds, cleanup_gpio
from decision import compute_signs
import slider_store
from logger   import log_api, get_sensor_logs, get_api_logs

app = Flask(__name__, static_folder="frontend/dist", static_url_path="")

# ── Init hardware ──────────────────────────────────────────
try:
    init_sensors()
except Exception as e:
    print(f"[FATAL] Sensor init failed: {e}", file=sys.stderr)
    sys.exit(1)

atexit.register(cleanup_gpio)

# ── Shared snapshot ────────────────────────────────────────
_snapshot: dict = {
    "nodes":           {},
    "signs":           {},
    "alerts":          [],
    "building_status": "BOOTING",
    "gpio_leds":       {},
    "ts":              None,
}
_snap_lock = threading.Lock()


# ── Background data loop ───────────────────────────────────
def _loop():
    while True:
        try:
            raw = get_all_data()

            # Wait until all nodes have had at least one read
            if any(v is None for v in raw.values()):
                time.sleep(0.3)
                continue

            nodes_out = {}
            node_list = []

            for nid in ALL_NODES:
                r  = raw[nid]
                sc = compute_risk(r)

                node = {
                    "node_id":    nid,
                    "label":      NODE_LABEL.get(nid, nid),
                    "floor":      NODE_FLOOR.get(nid, 0),
                    "temp":       r.get("temp"),
                    "humidity":   r.get("humidity"),
                    "smoke":      r.get("smoke"),
                    "crowd":      r.get("crowd"),
                    "camera":     r.get("camera"),
                    "risk":       sc["risk"],
                    "status":     sc["status"],
                    "has_gpio_led": r.get("has_gpio_led", False),
                    "source":     r.get("source"),
                    # Camera extras (only exit_A)
                    "density_pct":          r.get("density_pct"),
                    "motion_pixels":        r.get("motion_pixels"),
                    "edge_pixels":          r.get("edge_pixels"),
                    "camera_crowd_score":   r.get("camera_crowd_score"),
                    "camera_display_score": r.get("camera_display_score"),
                    "camera_status":        r.get("camera_status"),
                    "camera_ready":         r.get("camera_ready", False),
                    "camera_updated_at":    r.get("camera_updated_at"),
                }
                nodes_out[nid] = node
                node_list.append(node)

            # Decision logic (signs + alerts)
            node_states = {nid: {"risk": n["risk"], "status": n["status"]}
                           for nid, n in nodes_out.items()}
            decision = compute_signs(node_states)

            # Building status — worst across all nodes
            all_statuses = [n["status"] for n in node_list]
            for worst in ("CRITICAL", "DANGER", "SENSOR_ERROR", "CAUTION"):
                if worst in all_statuses:
                    building = worst
                    break
            else:
                building = "SAFE"

            # Drive GPIO LEDs (Floor 2 only — skipped silently for others)
            led_inputs = [{"node_id": n["node_id"], "status": n["status"]}
                          for n in node_list]
            led_states = update_all_leds(led_inputs)

            gpio_leds = {
                nid: {
                    "green_on": s.get("green_on", False),
                    "red_on":   s.get("red_on",   False),
                    "blink_hz": s.get("blink_hz",  0),
                }
                for nid, s in led_states.items()
                if s.get("has_gpio")
            }

            snap = {
                "nodes":           nodes_out,
                "signs":           decision["signs"],
                "alerts":          decision["alerts"],
                "building_status": building,
                "gpio_leds":       gpio_leds,
                "ts":              time.strftime("%Y-%m-%dT%H:%M:%S"),
            }

            with _snap_lock:
                _snapshot.clear()
                _snapshot.update(snap)

            log_api("INFO", f"Loop OK — building={building} alerts={len(decision['alerts'])}")

        except Exception as e:
            log_api("ERROR", f"Main loop: {e}")

        time.sleep(REFRESH_INTERVAL)


threading.Thread(target=_loop, daemon=True).start()


# ── Routes ─────────────────────────────────────────────────

# Serve React SPA (production build)
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    dist = app.static_folder
    if path and os.path.exists(os.path.join(dist, path)):
        return send_from_directory(dist, path)
    return send_from_directory(dist, "index.html")


@app.route("/api/data")
def api_data():
    with _snap_lock:
        return jsonify(_snapshot)


@app.route("/api/video/exit_A")
def camera_frame():
    frame_bytes, frame_mimetype = get_latest_camera_frame()
    resp = Response(frame_bytes, mimetype=frame_mimetype)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"]        = "no-cache"
    resp.headers["Expires"]       = "0"
    return resp


@app.route("/api/override", methods=["POST"])
def sensor_override():
    """Set a slider value for any node field (temp / smoke / crowd)."""
    data    = request.get_json(force=True)
    node_id = str(data.get("node_id", ""))
    field   = str(data.get("field",   ""))
    value   = data.get("value")

    if value is None:
        return jsonify({"ok": False, "error": "missing value"}), 400

    try:
        value = float(value)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "value must be numeric"}), 400

    ok = slider_store.set_value(node_id, field, value)
    if not ok:
        return jsonify({"ok": False, "error": f"unknown node_id '{node_id}' or field '{field}'"}), 400

    log_api("INFO", f"Override {node_id}.{field}={value}")
    return jsonify({"ok": True})


@app.route("/api/sliders")
def sliders_state():
    """Return current slider store values (for UI initialisation)."""
    return jsonify(slider_store.get_all())


@app.route("/api/logs/sensors")
def logs_sensors():
    return jsonify(get_sensor_logs())


@app.route("/api/logs/api")
def logs_api():
    return jsonify(get_api_logs())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
