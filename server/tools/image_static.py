"""Static image generation via Replicate (Flux).

Flux Schnell is fast and cheap, and its clean, high-contrast output dithers to
1-bit e-ink well. We append e-ink-friendly style guidance to every prompt since
1-bit conversion destroys subtle gradients and fine detail.
"""

import io
import time

import requests
from PIL import Image

# Appended to every prompt — steer Flux toward output that survives 1-bit dithering.
EINK_STYLE_SUFFIX = (
    ", high contrast black and white, bold graphic shapes, clean silhouette, "
    "strong tonal separation, minimal fine detail, dramatic lighting"
)

_API_BASE = "https://api.replicate.com/v1"


def generate(prompt: str, *, api_token: str, model: str = "black-forest-labs/flux-schnell") -> Image.Image:
    """Generate an image from a text prompt. Returns a PIL Image (RGB).

    Calls Replicate's HTTP API directly (create → poll → download) rather than the
    Python SDK, which avoids SDK-version drift around "official model" responses.
    Raises on failure so the caller can report a tool error back to the chat loop.
    """
    styled_prompt = prompt.strip() + EINK_STYLE_SUFFIX
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    payload = {
        "input": {
            "prompt": styled_prompt,
            "aspect_ratio": "4:3",  # closest common ratio to the panel's 648x480 (1.35)
            "output_format": "png",
            "num_outputs": 1,
        }
    }

    # Official-model prediction endpoint.
    resp = requests.post(
        f"{_API_BASE}/models/{model}/predictions", json=payload, headers=headers, timeout=60
    )
    resp.raise_for_status()
    pred = resp.json()

    # Poll until the prediction finishes (Flux Schnell is fast; cold starts aside).
    get_url = pred.get("urls", {}).get("get")
    deadline = time.time() + 240
    while pred.get("status") not in ("succeeded", "failed", "canceled"):
        if time.time() > deadline:
            raise TimeoutError("Replicate prediction timed out")
        time.sleep(1.5)
        r = requests.get(get_url, headers=headers, timeout=60)
        r.raise_for_status()
        pred = r.json()

    if pred.get("status") != "succeeded":
        raise RuntimeError(f"Replicate prediction {pred.get('status')}: {pred.get('error')}")

    output = pred["output"]
    img_url = output[0] if isinstance(output, list) else output
    data = requests.get(img_url, timeout=120).content
    return Image.open(io.BytesIO(data)).convert("RGB")
