"""
E-ink display driver for the Waveshare 5.83" V2 e-Paper HAT (648x480, 1-bit).

Ported from the proven surf-frame driver. Wraps the Waveshare library with a
graceful fallback when not running on a Pi, so the agent can be developed and
tested off-device.

The Waveshare library is installed on the Pi from the waveshare/e-Paper repo:
    git clone https://github.com/waveshare/e-Paper.git
    pip install e-Paper/RaspberryPi_JetsonNano/python/ --break-system-packages
"""

import logging
import threading

from PIL import Image

logger = logging.getLogger(__name__)

# Try to import the Waveshare driver — fails on non-Pi systems.
try:
    from waveshare_epd import epd5in83_V2
    HAS_EPD = True
except ImportError:
    HAS_EPD = False
    logger.info("Waveshare EPD library not available — running in stub mode")


class EPDController:
    """Controls the Waveshare 5.83" V2 e-Paper display.

    Panel init is lazy: the hardware is only touched on the first display() call,
    never at import or construction. This avoids the boot-time SPI init that made
    the earlier InkyPi setup crash-loop the Pi.

    A lock serializes access so concurrent HTTP pushes can't collide on the SPI bus.
    """

    WIDTH = 648
    HEIGHT = 480

    def __init__(self):
        self._epd = None
        self._lock = threading.Lock()
        self._initialized = False
        # Whether the panel supports fast partial refresh (used in the animation phase).
        self.has_partial = False

    def _ensure_init(self):
        """Initialize the panel hardware on first use."""
        if self._initialized:
            return
        if not HAS_EPD:
            raise RuntimeError(
                "Waveshare EPD library not installed. This must run on the Pi."
            )
        self._epd = epd5in83_V2.EPD()
        self._epd.init()
        self.has_partial = hasattr(self._epd, "init_Part") and hasattr(
            self._epd, "display_Partial"
        )
        self._initialized = True
        logger.info("E-ink display initialized (partial refresh: %s)", self.has_partial)

    def display(self, image: Image.Image):
        """Push a PIL Image to the display.

        The image is resized to the panel and converted to 1-bit if needed, then
        the panel is put back to sleep (e-ink retains the image with no power).
        """
        with self._lock:
            self._ensure_init()

            if image.size != (self.WIDTH, self.HEIGHT):
                image = image.resize((self.WIDTH, self.HEIGHT))
            if image.mode != "1":
                image = image.convert("1")

            # A sleeping panel needs a re-init before it will accept a new frame.
            self._epd.init()
            self._epd.display(self._epd.getbuffer(image))
            self._epd.sleep()
            logger.info("Image pushed to e-ink display")

    def clear(self):
        """Clear the display to white."""
        with self._lock:
            self._ensure_init()
            self._epd.init()
            self._epd.Clear()
            self._epd.sleep()
            logger.info("Display cleared")

    def cleanup(self):
        """Release GPIO resources. Safe to call when never initialized."""
        if not HAS_EPD or not self._initialized:
            return
        try:
            epd5in83_V2.epdconfig.module_exit(cleanup=True)
            logger.info("GPIO cleanup complete")
        except Exception as e:  # noqa: BLE001 - cleanup must never raise
            logger.warning("GPIO cleanup error: %s", e)
