"""Mac-side web app: chat UI, drawing canvas, device picker, and the orchestrator.

Run from the repo root:
    python3 -m server.app
Then open http://localhost:5001
"""

import base64
import io
import logging

from flask import Flask, jsonify, request, render_template, send_file
from PIL import Image

from server.config import Config
from server import devices as devices_mod
from server import pipeline
from server.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eink-server")

app = Flask(__name__)

config = Config.load()
image_store = {}  # image_id -> {"image", "preview", "prompt"}
orchestrator = Orchestrator(config, image_store)
registry = devices_mod.DeviceRegistry(
    fallback_host=config.device.fallback_host,
    fallback_port=config.device.fallback_port,
)
registry.start_discovery()


# ---- pages ----

@app.get("/")
def index():
    return render_template("chat.html")


@app.get("/devices")
def devices_page():
    return render_template("devices.html")


@app.get("/draw")
def draw_page():
    return render_template("draw.html")


# ---- chat ----

@app.post("/api/chat")
def api_chat():
    data = request.get_json(force=True)
    session_id = data.get("session_id", "default")
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify(error="empty message"), 400
    try:
        result = orchestrator.chat(session_id, message)
    except Exception as e:  # noqa: BLE001
        logger.exception("chat failed")
        return jsonify(error=str(e)), 500

    images = [{"id": iid, "preview_url": f"/api/image/{iid}/preview"} for iid in result["images"]]
    return jsonify(reply=result["reply"], images=images)


# ---- image previews ----

def _send_pil(img, fmt="PNG"):
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.get("/api/image/<image_id>/preview")
def api_image_preview(image_id):
    entry = image_store.get(image_id)
    if not entry:
        return jsonify(error="not found"), 404
    # Show the actual 1-bit preview so the user sees what the panel will show.
    return _send_pil(entry["preview"])


# ---- devices ----

@app.get("/api/devices")
def api_devices():
    out = []
    for d in registry.list_devices():
        status = devices_mod.check_status(d)
        out.append(d.to_dict(online=status is not None))
    return jsonify(devices=out)


# ---- push to display ----

@app.post("/api/push")
def api_push():
    data = request.get_json(force=True)
    image_id = data.get("image_id")
    device_id = data.get("device_id")

    entry = image_store.get(image_id)
    if not entry:
        return jsonify(error="image not found"), 404

    device = registry.get(device_id) if device_id else registry.list_devices()[0]
    try:
        devices_mod.push_image(device, entry["preview"])
    except Exception as e:  # noqa: BLE001
        logger.exception("push failed")
        return jsonify(error=str(e)), 502
    return jsonify(success=True, device=device.to_dict())


# ---- drawing canvas ----

@app.post("/api/draw/push")
def api_draw_push():
    data = request.get_json(force=True)
    device_id = data.get("device_id")
    # dataURL: "data:image/png;base64,...."
    data_url = data.get("image", "")
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    raw = base64.b64decode(data_url)
    img = Image.open(io.BytesIO(raw)).convert("RGB")

    # Drawings are line art — threshold gives cleaner edges than dithering.
    epaper = pipeline.to_epaper(img, size=config.render.resolution, dither="threshold")

    device = registry.get(device_id) if device_id else registry.list_devices()[0]
    try:
        devices_mod.push_image(device, epaper)
    except Exception as e:  # noqa: BLE001
        logger.exception("draw push failed")
        return jsonify(error=str(e)), 502
    return jsonify(success=True)


def main():
    app.run(host="0.0.0.0", port=5001, debug=True)


if __name__ == "__main__":
    main()
