#!/bin/bash
# Bootstrap the e-ink display agent on a fresh Raspberry Pi OS Lite install.
# Run from the repo root on the Pi:
#     sudo bash agent/setup.sh
#
# Installs the PROVEN Waveshare driver (waveshare/e-Paper repo, not the single
# mislabeled file InkyPi used), enables SPI, and installs the systemd service.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="${SUDO_USER:-dylanbutler}"

echo "==> Installing system packages"
apt-get update
apt-get install -y python3-pip python3-pil python3-numpy python3-dev git \
    libopenjp2-7 libtiff6 python3-flask python3-zeroconf

echo "==> Enabling SPI"
raspi-config nonint do_spi 0

echo "==> Installing Waveshare e-Paper library (proven source)"
if ! python3 -c "import waveshare_epd" 2>/dev/null; then
    rm -rf /tmp/e-Paper
    git clone --depth 1 https://github.com/waveshare/e-Paper.git /tmp/e-Paper
    pip3 install /tmp/e-Paper/RaspberryPi_JetsonNano/python/ --break-system-packages
fi

echo "==> Installing agent Python deps"
pip3 install -r "$REPO_DIR/agent/requirements.txt" --break-system-packages || true

echo "==> Installing systemd service"
sed "s#/home/dylanbutler/eink-ai#$REPO_DIR#g; s#User=dylanbutler#User=$USER_NAME#g" \
    "$REPO_DIR/agent/eink-agent.service" > /etc/systemd/system/eink-agent.service
systemctl daemon-reload
systemctl enable eink-agent
systemctl restart eink-agent

echo "==> Done. SPI needs a reboot to fully enable if it was just turned on."
echo "    Check status:  sudo systemctl status eink-agent"
echo "    Test:          curl http://localhost:8080/status"
