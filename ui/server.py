"""
server.py — Vision System Control Panel Backend
Run with: python server.py
"""

import subprocess
import sys
import os
import signal
import threading
import time
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "src" / "vision_pipeline"

SCRIPTS_DIR.mkdir(exist_ok=True)

# ── Script type config ─────────────────────────────────────────────────────────
# continuous  = runs until stopped (camera streams, loops)
# interactive = user interacts via the OpenCV window (calibration)
# oneshot     = runs, produces output, exits on its own
SCRIPT_CONFIG = {
    "camera_test_main": {
        "type":  "continuous",
        "label": "Camera Live View",
        "icon":  "📷",
        "desc":  "Streams live camera feed — press Q in the OpenCV window to quit",
    },
    "test5_main": {
        "type":  "continuous",
        "label": "Hole Detection",
        "icon":  "🔍",
        "desc":  "Live detection — press D to detect holes, Q to quit",
    },
    "calibrate_camera": {
        "type":  "interactive",
        "label": "Camera Calibration",
        "icon":  "📐",
        "desc":  "Freeze frame → click 2 points → enter real mm distance",
    },
    "send_to_plc": {
        "type":  "oneshot",
        "label": "Send to PLC",
        "icon":  "🏭",
        "desc":  "Sends hole_coordinates_mm.json data to Siemens PLC",
    },
}

DEFAULT_CONFIG = {"type": "oneshot", "label": None, "icon": "🐍", "desc": ""}

# script_id -> { proc, output[], lock, done }
running_procs = {}


def get_programs():
    programs = []
    for path in sorted(SCRIPTS_DIR.glob("*.py")):
        sid = path.stem
        cfg = SCRIPT_CONFIG.get(sid, DEFAULT_CONFIG)

        desc = cfg.get("desc", "")
        if not desc:
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("#"):
                            desc = line.lstrip("#").strip()
                            break
            except Exception:
                pass

        programs.append({
            "id":      sid,
            "name":    cfg.get("label") or sid.replace("_", " ").title(),
            "file":    path.name,
            "desc":    desc,
            "icon":    cfg.get("icon", "🐍"),
            "type":    cfg.get("type", "oneshot"),
            "running": sid in running_procs,
            "code":    path.read_text(encoding="utf-8", errors="replace"),
        })
    return programs


@app.route("/api/programs", methods=["GET"])
def list_programs():
    return jsonify(get_programs())


@app.route("/api/run/<script_id>", methods=["POST"])
def run_script(script_id):
    script = SCRIPTS_DIR / f"{script_id}.py"
    if not script.exists():
        return jsonify({"error": f"Script '{script_id}.py' not found."}), 404

    cfg   = SCRIPT_CONFIG.get(script_id, DEFAULT_CONFIG)
    stype = cfg.get("type", "oneshot")

    # Continuous / interactive — launch in background, return immediately
    if stype in ("continuous", "interactive"):
        if script_id in running_procs:
            return jsonify({"error": "Already running."}), 409

        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(
            [sys.executable, "-u", str(script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(SCRIPTS_DIR),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            **kwargs,
        )

        entry = {"proc": proc, "output": [], "lock": threading.Lock(), "done": False}
        running_procs[script_id] = entry

        def reader():
            for line in proc.stdout:
                with entry["lock"]:
                    entry["output"].append(line.rstrip())
            proc.wait()
            entry["done"] = True
            running_procs.pop(script_id, None)

        threading.Thread(target=reader, daemon=True).start()
        return jsonify({"status": "launched", "type": stype})

    # One-shot — block until done, return full output
    else:
        try:
            result = subprocess.run(
                [sys.executable, "-u", str(script)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                cwd=str(SCRIPTS_DIR),
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            return jsonify({
                "stdout":     result.stdout,
                "stderr":     result.stderr,
                "returncode": result.returncode,
            })
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Timed out after 30 s."}), 408
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/output/<script_id>", methods=["GET"])
def get_output(script_id):
    entry = running_procs.get(script_id)
    if not entry:
        return jsonify({"lines": [], "running": False})
    with entry["lock"]:
        lines = list(entry["output"])
        entry["output"].clear()
    return jsonify({"lines": lines, "running": not entry["done"]})


@app.route("/api/stop/<script_id>", methods=["POST"])
def stop_script(script_id):
    entry = running_procs.get(script_id)
    if not entry:
        return jsonify({"error": "Not running."}), 404

    proc = entry["proc"]
    try:
        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            time.sleep(0.4)
            if proc.poll() is None:
                proc.terminate()
        else:
            proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

    running_procs.pop(script_id, None)
    return jsonify({"status": "stopped"})


@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({"running": list(running_procs.keys())})


if __name__ == "__main__":
    print(f"Scripts folder : {SCRIPTS_DIR.resolve()}")
    print(f"Server         : http://localhost:5000")
    app.run(debug=False, port=5000)
