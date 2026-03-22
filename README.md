<div align="center">

<img src="https://raw.githubusercontent.com/ColdKittyIce/icecat-show-companion/main/assets/banner.png" alt="IceCat Show Companion" width="100%">

# 🧊 IceCat Show Companion

### Professional live radio show production tool for Prankcast

[![Build](https://github.com/ColdKittyIce/icecat-show-companion/actions/workflows/build.yml/badge.svg)](https://github.com/ColdKittyIce/icecat-show-companion/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/ColdKittyIce/icecat-show-companion?label=latest%20release&color=blue)](https://github.com/ColdKittyIce/icecat-show-companion/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/ColdKittyIce/icecat-show-companion/total?color=green)](https://github.com/ColdKittyIce/icecat-show-companion/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/platform-Windows%2010%2F11-blue?logo=windows)](https://github.com/ColdKittyIce/icecat-show-companion/releases/latest)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

**Built for [The Chill With IceCat](https://prankcast.com/icecat) on Prankcast — 277+ episodes of the best prank calls on the internet.**

<br>

## ⬇️ Download

<a href="https://github.com/ColdKittyIce/icecat-show-companion/releases/latest">
  <img src="https://img.shields.io/badge/Download%20for%20Windows-IceCat%20Companion%20v3.0-blue?style=for-the-badge&logo=windows&logoColor=white" alt="Download for Windows" height="48">
</a>

*No Python required — just download and run*

</div>

---

## ✨ What Is This?

IceCat Show Companion is an all-in-one live show production tool designed for **Prankcast hosts** and internet radio broadcasters. It replaces a messy desk of open programs with one clean window that has everything you need to run a smooth show.

Works alongside your existing setup — **Voicemeeter, Rocket Broadcaster, Mixxx, OBS, MicroSIP, Discord** — without getting in the way.

---

## 🎛️ Features

### Soundboard
- **Multi-bank button grid** — organise sounds into named banks with instant switching
- **Drag & drop** audio files onto buttons — supports MP3, WAV, OGG, FLAC, M4A
- **Per-button FX** — reverb, pitch shift, delay and more via right-click
- **Pinned row** — sounds that stay visible across all banks
- **Lock mode** — prevents accidental changes during a live show
- **Export/import banks** as JSON for backup or sharing

### Music Queue
- **Auto-advancing playlist** — drop in tracks, hit play, forget about it
- **Drag to reorder** tracks mid-show with a visual insert indicator
- **Full transport controls** — ⏮ ▶ ⏸ ⏹ ⏭
- **VOL/FADE slider** — duck music independently of soundboard effects

### Tape Recorder
- **Record your show** directly from any Windows input device
- **Save as WAV or MP3**
- **Play back recordings** — load any saved file and play it live
- **Drag & drop audio files** onto the recorder to play them

### Mic Panel
- **Mute/unmute** your actual Windows input device (works with Voicemeeter)
- **Gain slider** — OS-level mic volume control
- **Live VU meter** — always know if your mic is hot
- **🎚 Duck button** — smoothly fades your music down and back up

### Session Log
- **Auto-timestamps** every sound played, call started/ended, and live event
- **Custom stamps** — type a note and hit 📌 to mark your best bits
- **Export** the full log as a text file after the show
- **Gold moments** — mark standout moments with ⭐

### Bits Board
- **Show idea scratchpad** — store bit ideas with title and notes
- **Done tracking** — mark bits as completed during the show
- **Random picker** — stuck for ideas? Hit 🎲

### Mini Mode
- **Compact always-on-top strip** for dual-screen setups
- Shows ON AIR status, live timer, mic mute, now playing, queue transport, VU meters, and a stamp button
- Drag anywhere on screen

### And more...
- 📝 **Multi-tab Notes** with export to .txt
- 📁 **Quick Folders** — six programmable folder buttons
- 🌐 **Website launcher** dropdown
- 📞 **Call timer** with session log stamping
- ⏱️ **Countdown timer** with quick presets
- ⌨️ **Fully customisable hotkeys**
- 🎨 **4 colour themes**
- 💾 **Auto-saves** config on every change, startup backups

---

## 🖥️ System Requirements

| | Minimum |
|---|---|
| **OS** | Windows 10 or 11 (64-bit) |
| **RAM** | 4GB |
| **Storage** | 200MB |
| **Audio** | Any Windows audio device |

**Recommended:** [Voicemeeter](https://vb-audio.com/Voicemeeter/) for full audio routing control

---

## 🚀 Getting Started

### Option A — Download the EXE (recommended)

1. **[Download the latest release](https://github.com/ColdKittyIce/icecat-show-companion/releases/latest)**
2. Double-click `IceCat_Companion_v3.0.exe` to run
3. If Windows SmartScreen appears — click **More info → Run anyway**
   *(This happens because the app isn't code-signed yet — it's safe)*
4. Go to **Settings → Audio** and select your output and mic devices
5. Right-click soundboard buttons to assign audio files
6. Hit **GO LIVE** when your stream starts — you're running!

### Option B — Run from source

```bash
# Clone the repo
git clone https://github.com/ColdKittyIce/icecat-show-companion.git
cd icecat-show-companion

# Install dependencies
pip install -r requirements.txt

# Launch
python main.py
```

> Requires Python 3.11+ — download from [python.org](https://python.org)

---

## 📚 Help & Documentation

The full help guide is built into the app:

**Settings → About → 📖 Open Help Guide**

Covers every feature, all settings, keyboard shortcuts, and a troubleshooting FAQ. Can also be opened in your browser for the full styled version with diagrams.

---

## ⌨️ Default Hotkeys

| Action | Shortcut |
|---|---|
| Go Live / End Live | `Ctrl+Shift+L` |
| Panic (Stop All) | `Ctrl+Shift+P` |
| Mute Toggle | `Ctrl+Shift+M` |
| Add Timestamp | `Ctrl+Shift+T` |
| Gold Moment | `Ctrl+Shift+G` |
| Toggle Mini Mode | `Ctrl+Shift+Z` |

All hotkeys are customisable in Settings → Hotkeys.

---

## 🔧 For Developers

### Project structure

```
main.py              — App entry point and orchestration
config.py            — ConfigManager, themes, defaults
audio.py             — AudioManager, RecorderManager, MicManager
network.py           — Stream health monitor
ui_header.py         — Header, tape recorder, mic panel, mini mode
ui_soundboard.py     — Soundboard grid, queue, pinned row
ui_right_panel.py    — Tools, bits board, session log, notes, snippets
ui_bottom.py         — Bottom strip (notes, now playing, quick copy)
ui_dialogs.py        — Settings window, all dialogs
help.html            — Built-in help guide
```

### Building the EXE yourself

```bash
pip install pyinstaller
pyinstaller IceCat_Companion.spec --clean --noconfirm
# Output: dist/IceCat_Companion_v3.0.exe
```

### Releasing a new version

```bash
git tag v3.0.1
git push origin v3.0.1
# GitHub Actions automatically builds and creates a release
```

---

## 🎙️ About The Show

**The Chill With IceCat** is a live prank call show broadcasting every Thursday 7–9pm EST on [Prankcast](https://prankcast.com/icecat). Over 277 episodes of unscripted chaos, killer bits, and the best callers on the internet.

This tool was built to make running the show smoother — and then got good enough to share.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

Free to use, modify, and distribute. If you build something cool with it, let me know.

---

<div align="center">

Made with ❄️ by [ColdKittyIce](https://github.com/ColdKittyIce) &nbsp;·&nbsp;
[Prankcast](https://prankcast.com/icecat) &nbsp;·&nbsp;
[Report a Bug](https://github.com/ColdKittyIce/icecat-show-companion/issues) &nbsp;·&nbsp;
[Request a Feature](https://github.com/ColdKittyIce/icecat-show-companion/issues)

</div>
