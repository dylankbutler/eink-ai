"""
E-ink display agent — runs ON the Pi.

A deliberately tiny Flask service. It receives finished PNGs from the Mac-side
orchestrator and pushes them to the panel. It does no image generation, no LLM
work, no dithering — the Pi does exactly one job.

Endpoints:
    POST /display   — body: PNG bytes (or multipart 'image'); pushes to panel
    POST /clear     — clear panel to white
    GET  /status    — { online, device_id, resolution, busy, has_partial }
    GET  /profile   — the device profile JSON

Run:
    python3 -m agent.app          (from the repo root on the Pi)
"""

import io
import json
import logging
import os
import threading

from flask import Flask, jsonify, request
from PIL import Image

from agent.epd import EPDController
from agent import mdns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("display-agent")

DEVICE_ID = os.environ.get("EINK_DEVICE_ID", "koipond")
DEVICE_NAME = os.environ.get("EINK_DEVICE_NAME", "Koi Pond E-Ink")
PORT = int(os.environ.get("EINK_AGENT_PORT", "8080"))

_PROFILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "device_profiles",
    "waveshare_5in83_v2.json",
)

app = Flask(__name__)
epd = EPDController()
_busy = threading.Lock()


def _load_profile() -> dict:
    try:
        with open(_PROFILE_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"device_id": DEVICE_ID, "resolution": [EPDController.WIDTH, EPDController.HEIGHT]}


def _read_image() -> Image.Image:
    """Accept either a raw PNG body or a multipart 'image' file."""
    if "image" in request.files:
        return Image.open(request.files["image"].stream)
    if request.data:
        return Image.open(io.BytesIO(request.data))
    raise ValueError("no image supplied (send PNG bytes as body or multipart 'image')")


@app.post("/display")
def display():
    if _busy.locked():
        return jsonify(error="display busy"), 409
    with _busy:
        try:
            img = _read_image()
        except Exception as e:  # noqa: BLE001
            return jsonify(error=f"bad image: {e}"), 400
        try:
            epd.display(img)
        except Exception as e:  # noqa: BLE001
            logger.exception("display failed")
            return jsonify(error=str(e)), 500
    return jsonify(success=True)


@app.post("/clear")
def clear():
    with _busy:
        try:
            epd.clear()
        except Exception as e:  # noqa: BLE001
            return jsonify(error=str(e)), 500
    return jsonify(success=True)


@app.get("/status")
def status():
    return jsonify(
        online=True,
        device_id=DEVICE_ID,
        name=DEVICE_NAME,
        resolution=[EPDController.WIDTH, EPDController.HEIGHT],
        busy=_busy.locked(),
        has_partial=epd.has_partial,
    )


@app.get("/profile")
def profile():
    return jsonify(_load_profile())


def main():
    zc, _ = mdns.advertise(DEVICE_ID, DEVICE_NAME, PORT)
    try:
        # threaded=False keeps SPI access strictly serial on top of the epd lock.
        app.run(host="0.0.0.0", port=PORT, threaded=True)
    finally:
        if zc:
            zc.close()
        epd.cleanup()


if __name__ == "__main__":
    main()
