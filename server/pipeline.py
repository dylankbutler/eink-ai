"""Image pipeline: fit an arbitrary image to the panel and convert it to 1-bit.

For photographic / AI-generated images, Floyd-Steinberg dithering (PIL's default
for convert("1")) preserves tonal detail far better than a hard threshold. For
graphic / line-art prompts, a threshold gives cleaner edges. surf-frame used
threshold because it was rendering line art; we default to dithering here.
"""

from PIL import Image

PANEL_SIZE = (648, 480)


def fit_to_panel(img: Image.Image, size=PANEL_SIZE, background=255) -> Image.Image:
    """Resize an image to cover the panel, center-cropping any overflow.

    Cover (not letterbox) so the panel is fully used; the AI images are framed
    loosely enough that a center crop reads fine.
    """
    target_w, target_h = size
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = round(src_w * scale), round(src_h * scale)
    resized = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def to_epaper(img: Image.Image, size=PANEL_SIZE, dither="floyd-steinberg") -> Image.Image:
    """Fit to the panel and convert to a 1-bit image the display agent can push."""
    img = img.convert("L")
    img = fit_to_panel(img, size)

    if dither == "threshold":
        return img.point(lambda p: 0 if p < 128 else 255, mode="1")
    # Floyd-Steinberg is PIL's default dither for convert("1").
    return img.convert("1")
