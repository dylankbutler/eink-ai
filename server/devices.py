"""Device discovery (mDNS) and the HTTP client for pushing images to a Pi agent.

Browses for _einkdisplay._tcp services advertised by the Pi display agent. Falls
back to a configured host:port if mDNS is flaky (common on phone hotspots).
"""

import io
import logging
import socket
import threading
import time

import requests

logger = logging.getLogger(__name__)


class Device:
    def __init__(self, device_id, name, host, port):
        self.device_id = device_id
        self.name = name
        self.host = host
        self.port = port

    @property
    def base_url(self):
        return f"http://{self.host}:{self.port}"

    def to_dict(self, online=None):
        return {
            "device_id": self.device_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "online": online,
        }


class DeviceRegistry:
    """Discovers and tracks display-agent devices on the LAN."""

    def __init__(self, fallback_host="koipond.local", fallback_port=8080):
        self._devices = {}
        self._lock = threading.Lock()
        self._zc = None
        self._fallback = Device("fallback", fallback_host, fallback_host, fallback_port)

    def start_discovery(self):
        try:
            from zeroconf import ServiceBrowser, Zeroconf
        except ImportError:
            logger.warning("zeroconf not installed — using fallback host only")
            return

        self._zc = Zeroconf()
        ServiceBrowser(self._zc, "_einkdisplay._tcp.local.", handlers=[self._on_change])

    def _on_change(self, zeroconf, service_type, name, state_change):
        from zeroconf import ServiceStateChange

        if state_change is ServiceStateChange.Removed:
            with self._lock:
                self._devices.pop(name, None)
            return

        info = zeroconf.get_service_info(service_type, name)
        if not info or not info.addresses:
            return
        host = socket.inet_ntoa(info.addresses[0])
        props = {k.decode(): v.decode() for k, v in info.properties.items() if v}
        device = Device(
            device_id=props.get("device_id", name),
            name=props.get("name", name),
            host=props.get("hostname", host),
            port=info.port,
        )
        with self._lock:
            self._devices[name] = device
        logger.info("Discovered device %s at %s:%d", device.device_id, device.host, device.port)

    def list_devices(self):
        with self._lock:
            devices = list(self._devices.values())
        if not devices:
            devices = [self._fallback]
        return devices

    def get(self, device_id):
        for d in self.list_devices():
            if d.device_id == device_id:
                return d
        return self._fallback


def check_status(device: Device, timeout=3):
    try:
        r = requests.get(f"{device.base_url}/status", timeout=timeout)
        return r.json() if r.ok else None
    except requests.RequestException:
        return None


def push_image(device: Device, image, timeout=60):
    """POST a 1-bit PIL image to the device's /display endpoint as PNG bytes."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    r = requests.post(
        f"{device.base_url}/display",
        data=buf.getvalue(),
        headers={"Content-Type": "image/png"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()
