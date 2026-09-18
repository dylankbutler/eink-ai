"""
mDNS/zeroconf advertisement for the display agent.

Advertises the service as _einkdisplay._tcp.local so the Mac-side orchestrator
can discover this Pi on the LAN without knowing its IP in advance.
"""

import logging
import socket

logger = logging.getLogger(__name__)


def _local_ip() -> str:
    """Best-effort LAN IP for this host (works without external connectivity)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually send anything; just picks the outbound interface.
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:  # noqa: BLE001
        return "127.0.0.1"
    finally:
        s.close()


def advertise(device_id: str, name: str, port: int):
    """Register the display agent over mDNS. Returns (Zeroconf, ServiceInfo).

    Keep the returned handles alive for the life of the process; call
    zeroconf.close() on shutdown.
    """
    try:
        from zeroconf import ServiceInfo, Zeroconf
    except ImportError:
        logger.warning("zeroconf not installed — mDNS advertisement disabled")
        return None, None

    ip = _local_ip()
    hostname = socket.gethostname()
    info = ServiceInfo(
        "_einkdisplay._tcp.local.",
        f"{device_id}._einkdisplay._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={
            "device_id": device_id,
            "name": name,
            "hostname": f"{hostname}.local",
        },
        server=f"{hostname}.local.",
    )
    zc = Zeroconf()
    zc.register_service(info)
    logger.info("Advertising %s over mDNS at %s:%d", device_id, ip, port)
    return zc, info
