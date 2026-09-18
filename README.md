# E-Ink AI Generator

Chat with an LLM to generate 1-bit images (later animations) and push them to a
Waveshare 5.83" V2 e-Paper panel (648×480) on a Raspberry Pi Zero 2W.

Two halves that talk over the LAN:

- **`server/`** runs on your Mac — the web app, the Claude chat loop, Flux image
  generation, and 1-bit dithering.
- **`agent/`** runs on the Pi — a tiny Flask service that receives a finished PNG
  and pushes it to the panel. It does nothing else.

```
Mac (server/)  ──HTTP POST /display (PNG)──▶  Pi (agent/)  ──SPI──▶  e-ink panel
     ▲  Claude + Flux + dither                 ▲ mDNS _einkdisplay._tcp
     └── web UI: chat / draw / devices          └── EPDController (proven surf-frame driver)
```

## Setup — Mac

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml   # add your Anthropic + Replicate keys
python3 -m server.app                # http://localhost:5001
```

## Setup — Pi (display agent)

Flash Raspberry Pi OS Lite 64-bit (Imager: hostname `koipond`, user `dylanbutler`,
enable SSH + wifi). Then, on the Pi:

```bash
git clone <this repo> ~/eink-ai
cd ~/eink-ai
sudo bash agent/setup.sh    # installs SPI, the proven Waveshare driver, systemd service
sudo reboot                 # if SPI was just enabled
```

Verify from the Mac:

```bash
curl http://koipond.local:8080/status
# push a test image
curl -X POST --data-binary @test.png http://koipond.local:8080/display
```

## Why not InkyPi?

This started as an InkyPi fork. InkyPi's installer pulls a single, mislabeled
Waveshare driver that never drove this panel, and it's too heavy for the Pi Zero 2W
(boot loops under load). The display driver here is ported from the `surf-frame`
project, which drives this exact panel using the `waveshare/e-Paper` pip package —
a different, proven driver. See the plan for full context.

## Build phases

- [x] Phase 0 — Pi display agent (this)
- [ ] Phase 1 — mDNS device picker, empirical refresh timings
- [ ] Phase 2 — chat → Flux → dither → push (MVP)
- [ ] Phase 3 — constraint-aware generation
- [ ] Phase 4 — animation (living image + frame sequence)
- [ ] Phase 5 — drawing canvas polish
- [ ] Phase 6 — external tools (Google Calendar, weather)
