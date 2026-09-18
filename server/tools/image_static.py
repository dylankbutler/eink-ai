"""Static image generation via Replicate (Flux).

Flux Schnell is fast and cheap, and its clean, high-contrast output dithers to
1-bit e-ink well. We append e-ink-friendly style guidance to every prompt since
1-bit conversion destroys subtle gradients and fine detail.
"""

import io

import requests
from PIL import Image

# Appended to every prompt — steer Flux toward output that survives 1-bit dithering.
EINK_STYLE_SUFFIX = (
    ", high contrast black and white, bold graphic shapes, clean silhouette, "
    "strong tonal separation, minimal fine detail, dramatic lighting"
)


def generate(prompt: str, *, api_token: str, model: str = "black-forest-labs/flux-schnell") -> Image.Image:
    """Generate an image from a text prompt. Returns a PIL Image (RGB).

    Uses the replicate Python client. Raises on failure so the caller can report
    a tool error back to the chat loop.
    """
    import replicate

    client = replicate.Client(api_token=api_token)
    styled_prompt = prompt.strip() + EINK_STYLE_SUFFIX

    output = client.run(
        model,
        input={
            "prompt": styled_prompt,
            "aspect_ratio": "4:3",   # closest common ratio to the panel's 648x480 (1.35)
            "output_format": "png",
            "num_outputs": 1,
        },
    )

    # replicate returns a list of file-like objects or URLs depending on version.
    item = output[0] if isinstance(output, list) else output
    if hasattr(item, "read"):
        data = item.read()
    else:
        data = requests.get(str(item), timeout=60).content

    return Image.open(io.BytesIO(data)).convert("RGB")
