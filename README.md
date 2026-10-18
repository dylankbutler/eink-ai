# E-Ink AI Generator

Chat with an AI to generate **1-bit images** and push them to a **Waveshare 5.83"
V2 e-Paper panel** (648×480) on a Raspberry Pi. Describe a scene in the web UI; an
agent generates it with Flux, dithers it to pure black-and-white, and sends it to
the panel over your LAN.

```
Mac/server (server/)  ──HTTP POST /display (PNG)──▶  Pi (agent/)  ──SPI──▶  e-ink panel
     ▲  Claude (agent) + Flux + 1-bit dither          ▲ mDNS _einkdisplay._tcp
     └── web UI: chat / draw / devices                 └── Waveshare EPD driver
```

Two halves that talk over the network:

- **`server/`** — runs on any Mac/Linux machine: the web app, the Claude chat/tool
  loop, Flux image generation (via Replicate), and 1-bit dithering.
- **`agent/`** — runs on the Raspberry Pi: a tiny Flask service that receives a
  finished PNG and pushes it to the panel. Nothing else.

> You can run the **server by itself** to generate and preview images in the
> browser — the Raspberry Pi is only needed to actually display them on a panel.

---

## 1. What you'll need

- A machine to run the server (macOS or Linux, Python 3.10+).
- **API keys** (both have free credit / cheap pay-as-you-go):
  - **Anthropic** — the chat agent. https://console.anthropic.com → API Keys.
  - **Replicate** — runs Flux for image generation. https://replicate.com/account/api-tokens
    (add a few dollars of credit under Billing; Flux Schnell is ~$0.003/image).
- **Optional, for the physical display:**
  - Raspberry Pi (Zero 2 W or any Pi with SPI) running Raspberry Pi OS Lite.
  - Waveshare 5.83" V2 e-Paper HAT (648×480).

---

## 2. Run the server (generate + preview)

```bash
git clone https://github.com/dylankbutler/eink-ai.git
cd eink-ai

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml   # then add your keys (see below)
python3 -m server.app                # open http://localhost:5001
```

Open **http://localhost:5001**, type a prompt in the chat, and you'll get a 1-bit
preview of what the panel would show.

### Configure (`config.yaml`)

`config.yaml` is git-ignored, so your keys stay out of version control. Secrets can
also be provided as environment variables (`ANTHROPIC_API_KEY`,
`REPLICATE_API_TOKEN`, `EINK_PASSWORD`), which take precedence.

```yaml
llm:
  anthropic_api_key: "sk-ant-..."     # your Anthropic key
  model: claude-sonnet-4-6

image_gen:
  provider: replicate
  replicate_api_token: "r8_..."       # your Replicate token
  model: black-forest-labs/flux-schnell

device:
  discovery: mdns                      # finds the Pi agent on your LAN
  fallback_host: koipond.local         # used if mDNS is flaky; set to your Pi's hostname
  fallback_port: 8080

render:
  resolution: [648, 480]
  dither: floyd-steinberg              # or "threshold" for line art

auth:
  password: ""                         # set a password to gate the web UI (recommended if exposed)
```

### Password-protecting the UI

If you ever expose the server beyond your own machine, set a password so strangers
can't burn your image-generation credits:

```yaml
auth:
  password: "choose-something"
```

(or `EINK_PASSWORD=choose-something`). Visitors then hit a login page before they
can generate. Leave it empty for open local use.

---

## 3. Set up the Raspberry Pi (to display on a real panel)

Wire the Waveshare 5.83" V2 HAT to the Pi, then flash **Raspberry Pi OS Lite
(64-bit)**. In the Raspberry Pi Imager, set a hostname (e.g. `koipond`), your user,
and enable **SSH** + **Wi-Fi**. Then SSH in and:

```bash
git clone https://github.com/dylankbutler/eink-ai.git ~/eink-ai
cd ~/eink-ai
sudo bash agent/setup.sh    # enables SPI, installs the Waveshare driver + a systemd service
sudo reboot                 # if SPI was just enabled
```

Verify from your server machine (replace the hostname with your Pi's):

```bash
curl http://koipond.local:8080/status
```

The server auto-discovers the agent over mDNS (`_einkdisplay._tcp`); if discovery is
flaky on your network, set `device.fallback_host` to your Pi's hostname in
`config.yaml`. Then use the **Devices** page in the web UI to pick it, and **push to
display** from any generated image.

---

## 4. Using it

- **Chat** (`/`) — describe an image; the agent generates and previews a 1-bit
  version. Push it to the panel when you like it.
- **Draw** (`/draw`) — sketch on a canvas and push the drawing straight to the panel
  (uses threshold rather than dithering for clean line art).
- **Devices** (`/devices`) — see discovered panels and their status.

Prompts that survive 1-bit conversion best are high-contrast with bold shapes — the
server appends e-ink-friendly style guidance to every prompt automatically.

---

## Notes

- **Cost:** image generation is pay-per-use on Replicate (Flux Schnell ≈ $0.003 each).
- **No Pi?** Everything except "push to display" works — generate and preview in the
  browser.
- The display driver is ported from the [`surf-frame`](https://github.com/dylankbutler/surf-frame)
  project, which drives this exact panel reliably.

## Roadmap

- [x] Pi display agent
- [x] mDNS device picker
- [x] Chat → Flux → dither → push
- [ ] Constraint-aware generation (prompt tuning per panel)
- [ ] Animation (frame sequences)
- [ ] Drawing canvas polish
- [ ] External tools (calendar, weather)
