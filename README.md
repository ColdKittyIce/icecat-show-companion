**Download (Windows EXE):** See the latest on the [Releases](https://github.com/ColdKittyIce/icecat-show-companion/releases) page.

[![Build](https://github.com/ColdKittyIce/icecat-show-companion/actions/workflows/build.yml/badge.svg)](https://github.com/ColdKittyIce/icecat-show-companion/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/ColdKittyIce/icecat-show-companion)](https://github.com/ColdKittyIce/icecat-show-companion/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/ColdKittyIce/icecat-show-companion/total?color=green)](https://github.com/ColdKittyIce/icecat-show-companion/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Issues](https://img.shields.io/github/issues/ColdKittyIce/icecat-show-companion)](https://github.com/ColdKittyIce/icecat-show-companion/issues)

# 🧊 IceCat Show Companion

All-in-one live radio show production tool for Prankcast hosts and internet broadcasters. Replaces a messy desk of open programs with one clean window — soundboard, music queue, tape recorder, session log, mic control, and more.

Built for **[The Chill With IceCat](https://prankcast.com/icecat)** on Prankcast.

> 📺 **[Watch the setup tutorial on YouTube](https://www.youtube.com/watch?v=D2DV7TiNq1g)** 

---

## Screenshot

![IceCat Show Companion](docs/IceCat_Screenshot.png "Main window")

---

## Features

**Soundboard**
- Multi-bank button grid with drag & drop audio assignment
- Per-button FX — reverb, pitch shift, delay (right-click any button)
- Pinned row for sounds you need in every segment
- Lock mode to prevent accidental changes during a live show
- Export/import banks as JSON

**Music Queue**
- Auto-advancing playlist with drag-to-reorder
- Full transport controls — ⏮ ▶ ⏸ ⏹ ⏭
- VOL/FADE slider to duck music independently of soundboard

**Tape Recorder**
- Record your show from any Windows input device
- Save as WAV or MP3
- Drag & drop audio files onto the recorder to play them back

**Mic Panel**
- Mute/unmute your actual Windows input device (Voicemeeter compatible)
- Live VU meter, gain slider
- 🎚 Duck button — smoothly fades music down and back up

**Session Log**
- Auto-timestamps every sound played, call start/end, and live event
- Custom 📌 stamp notes mid-show
- Export full log as text after the show

**Bits Board**
- Show idea scratchpad with done tracking and random picker

**Mini Mode**
- Compact always-on-top strip for dual-screen setups
- ON AIR status, live timer, mic mute, now playing, queue transport, VU meters, stamp input

**And more** — Notes tabs, Quick Folders, Website launcher, Call timer, Countdown, Hotkeys, 4 colour themes

---

## Download

Grab the latest `.exe` from **[Releases](https://github.com/ColdKittyIce/icecat-show-companion/releases)** on GitHub. No Python required.

> **First time on Windows?** SmartScreen may warn you — click **More info → Run anyway**. This is a PyInstaller build and is safe.

---

## Run from Source (Python 3.11+)

1. Install Python from https://python.org (ensure "Add Python to PATH" is checked)
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run:
   ```
   python main.py
   ```

---

## Quick Setup

1. Launch the app
2. Go to **Settings → Audio** and select your output device and mic input device
3. Right-click any soundboard button to assign an audio file
4. Click **GO LIVE** when your stream starts
5. Hit **Ctrl+Shift+P** (Panic) to stop all audio at any time

Full documentation is built in — open **Settings → About → 📖 Open Help Guide**

---

## Hotkeys

| Action | Default |
|---|---|
| Go Live / End Live | `Ctrl+Shift+L` |
| Panic (Stop All) | `Ctrl+Shift+P` |
| Mute Toggle | `Ctrl+Shift+M` |
| Add Timestamp | `Ctrl+Shift+T` |
| Gold Moment | `Ctrl+Shift+G` |
| Toggle Mini Mode | `Ctrl+Shift+Z` |

All hotkeys are customisable in **Settings → Hotkeys**

---

## Compatible With

Works alongside your existing broadcast stack:

- [Voicemeeter](https://vb-audio.com/Voicemeeter/) — audio routing
- Rocket Broadcaster — streaming
- Mixxx — DJ software
- MicroSIP — VoIP calls
- OBS — video/streaming
- Discord — guests

---

## Build a Standalone EXE

```
pip install pyinstaller
pyinstaller IceCat_Companion.spec --clean --noconfirm
```

EXE will be in `dist/`. Attach to a GitHub Release — don't commit it to the repo.

---

## Requirements

- Windows 10 or 11 (64-bit)
- Python 3.11+ (if running from source)
- See `requirements.txt` for full package list

---

## Known Issues / Troubleshooting

- **Antivirus flagging** — PyInstaller builds sometimes trigger generic AV warnings. The source code is fully open above.
- **Mic mute not working** — Go to Settings → Audio → Mic Input Device and select your actual microphone device
- **Soundboard not playing** — Check Settings → Audio → Output Device and select your correct playback device
- **Logs** — Check `%USERPROFILE%\IceCatCompanion_v3\logs\icecat.log` for error details

---

## About

The Chill With IceCat airs every Thursday 7–9pm EST on [Prankcast](https://prankcast.com/icecat). 277+ episodes of live prank calls. This tool was built to run the show and got good enough to share.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
