<div align="center">

# transparent-bg

**A Telegram bot that strips the background out of any photo you send it and hands back a transparent PNG.**

![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-AGPLv3%20%2B%20Commercial-00D4C8.svg)

</div>

---

## What it does

Send a photo (uploaded, forwarded, or sent as a file) to the bot and get back a transparent PNG with the background removed. It uses [`rembg`](https://github.com/danielgatis/rembg) (ONNX `u2net`/`isnet` models) running locally — no external API calls, no per-call cost, no image data leaving the process.

## Features

- Handles both compressed photo uploads (`filters.PHOTO`) and images sent as files (`filters.Document.IMAGE`, e.g. `.png`/`.jpg`)
- Downloads the largest available resolution before processing
- Sends the result back with `send_document` (not `send_photo`) so Telegram doesn't flatten the alpha channel
- Model is swappable via an environment variable — `u2net` (default, fast) or `isnet-general-use` (slower, sharper edges)
- Handles group shots out of the box — `rembg` keeps everything it detects as foreground, no per-subject selection needed

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python |
| Bot framework | [python-telegram-bot](https://python-telegram-bot.org/) |
| Background removal | [rembg](https://github.com/danielgatis/rembg) (ONNX `u2net`/`isnet` models via `onnxruntime`) |
| Image handling | Pillow |
| Deployment | Zeabur (`zbpack.json`) |

## Screenshots

_Screenshots coming soon._

## Quick Start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in BOT_TOKEN from @BotFather
export $(cat .env | xargs)
python main.py
```

First run downloads the ONNX model (~170MB for u2net), cached in `~/.u2net/` afterwards.

### Environment variables

| Variable | Required | Notes |
|---|---|---|
| `BOT_TOKEN` | yes | From [@BotFather](https://t.me/BotFather). |
| `REMBG_MODEL` | no | `u2net` (default) or `isnet-general-use` for cleaner edges on hair/fur at the cost of a few extra seconds per image. |

### Deploying (Zeabur)

Same pattern as the rest of the bot fleet — polling, no webhook:

1. Push this folder to a GitHub repo
2. Create a new Zeabur service from that repo (picks up `zbpack.json`)
3. Set `BOT_TOKEN` (and optionally `REMBG_MODEL`) in Zeabur env vars
4. Deploy — the model downloads on first boot, so the first request after a fresh deploy will be slower (~10-20s)

## Status / Roadmap

- [x] Photo and image-document background removal via `rembg`
- [x] Alpha-preserving delivery via `send_document`
- [x] Configurable model (`u2net` / `isnet-general-use`)
- [ ] Persistent volume mount for the ONNX model cache on Zeabur (currently re-downloads on every redeploy unless a volume is mounted manually)
- [ ] Per-subject selection for group shots

## Changelog

- **2026-09-06** — Initial release: Telegram bot that removes photo backgrounds via `rembg`, deployable to Zeabur.

## License

This project is dual licensed.

- Community Edition — [GNU Affero General Public License v3 (AGPLv3)](LICENSE). Free to use, modify, and self-host. If you distribute a modified version or run it as a network service, you must make the corresponding source available.
- Commercial License — for organisations that want to embed, modify, or distribute this software without AGPLv3's obligations. See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md).

---

<div align="center">
<sub>Built by <a href="https://github.com/TheBooleanJulian">@TheBooleanJulian</a></sub>
</div>
