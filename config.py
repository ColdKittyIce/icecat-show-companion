"""
config.py — IceCat Show Companion v3.0
Clean-slate rewrite. Handles all app constants, colour themes,
default config values, and the ConfigManager persistence layer.
"""

import json, shutil, copy, os
from pathlib import Path
from datetime import datetime

# ── Version ──────────────────────────────────────────────────────
VERSION       = "3.0.0"
APP_NAME      = "IceCat Show Companion"
SHOW_NAME     = "The Chill With IceCat"
PRANKCAST_URL = "https://prankcast.com/icecat"
STREAM_HOST   = "broadcast.dialtribe.com"
STREAM_PORT   = 80

# ── Paths ─────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
ASSET_DIR     = BASE_DIR / "assets"
DATA_DIR      = Path.home() / "IceCatCompanion_v3"
CONFIG_FILE   = DATA_DIR / "config.json"
SESSION_DIR   = DATA_DIR / "sessions"
RECORDING_DIR = DATA_DIR / "recordings"
AUTOSAVE_DIR  = DATA_DIR / "autosave"
LOG_DIR       = DATA_DIR / "logs"

# ── Colour themes ─────────────────────────────────────────────────
THEMES = {
    "Default Blue": {
        "bg":         "#060b14",
        "bg2":        "#0a1220",
        "surface":    "#0e1a2e",
        "elevated":   "#132238",
        "border":     "#1a2e4a",
        "border_hi":  "#1e3a5f",
        "blue":       "#1c3d78",
        "blue_mid":   "#2a55a8",
        "blue_light": "#4070c8",
        "blue_hi":    "#5585d5",
        "amber":      "#f0a020",
        "amber_hi":   "#ffbb40",
        "text":       "#c8d8f0",
        "text_dim":   "#4a6688",
        "text_hi":    "#e8f0ff",
        "red":        "#e02233",
        "red_dim":    "#881122",
        "green":      "#20b85a",
        "green_dim":  "#126835",
        "gold":       "#ffd700",
        "panic":      "#cc0000",
        "neutral":    "#112030",
        "btn":        "#0e1c30",
        "btn_hover":  "#162840",
        "pinned":     "#1a2e00",
    },
    "Midnight Purple": {
        "bg":         "#080612",
        "bg2":        "#0f0c1e",
        "surface":    "#14102a",
        "elevated":   "#1c1638",
        "border":     "#2a1a50",
        "border_hi":  "#381e6a",
        "blue":       "#3d1c78",
        "blue_mid":   "#5a2aa8",
        "blue_light": "#7040c8",
        "blue_hi":    "#8855d5",
        "amber":      "#00e5ff",
        "amber_hi":   "#80f0ff",
        "text":       "#e0d5f8",
        "text_dim":   "#6048a0",
        "text_hi":    "#f0eaff",
        "red":        "#ff2255",
        "red_dim":    "#991133",
        "green":      "#aa44ff",
        "green_dim":  "#661aaa",
        "gold":       "#bf80ff",
        "panic":      "#cc0044",
        "neutral":    "#16102a",
        "btn":        "#120e22",
        "btn_hover":  "#1c1630",
        "pinned":     "#1a0a30",
    },
    "Ice Blue": {
        "bg":         "#040c14",
        "bg2":        "#071220",
        "surface":    "#0a1828",
        "elevated":   "#0e2038",
        "border":     "#0e2c48",
        "border_hi":  "#123860",
        "blue":       "#0e4d7a",
        "blue_mid":   "#1a72b0",
        "blue_light": "#2e9fd4",
        "blue_hi":    "#48b8e8",
        "amber":      "#40c8e0",
        "amber_hi":   "#80e8f8",
        "text":       "#b8d8f0",
        "text_dim":   "#3a6080",
        "text_hi":    "#d8f0ff",
        "red":        "#ff4455",
        "red_dim":    "#992233",
        "green":      "#20d890",
        "green_dim":  "#0e8055",
        "gold":       "#60d8f0",
        "panic":      "#cc2233",
        "neutral":    "#08182a",
        "btn":        "#071420",
        "btn_hover":  "#0e2030",
        "pinned":     "#041820",
    },
    "Matrix Green": {
        "bg":         "#010800",
        "bg2":        "#020d01",
        "surface":    "#031202",
        "elevated":   "#041803",
        "border":     "#082808",
        "border_hi":  "#0c3a0c",
        "blue":       "#0a3d0a",
        "blue_mid":   "#145514",
        "blue_light": "#1e7a1e",
        "blue_hi":    "#289028",
        "amber":      "#00ff41",
        "amber_hi":   "#80ff90",
        "text":       "#88ee88",
        "text_dim":   "#2a6a2a",
        "text_hi":    "#ccffcc",
        "red":        "#ff4400",
        "red_dim":    "#992200",
        "green":      "#00ff41",
        "green_dim":  "#007a1e",
        "gold":       "#00cc33",
        "panic":      "#ff2200",
        "neutral":    "#031403",
        "btn":        "#020e02",
        "btn_hover":  "#071407",
        "pinned":     "#052805",
    },
}

# ── Live colour dict — updated by apply_theme() ───────────────────
C: dict = dict(THEMES["Default Blue"])

# ── FX defaults ───────────────────────────────────────────────────
DEFAULT_FX = {
    "volume":   {"enabled": False, "value": 1.0},
    "pitch":    {"enabled": False, "value": 0.0},
    "speed":    {"enabled": False, "value": 1.0},
    "reverb":   {"enabled": False, "value": 0.3},
    "echo":     {"enabled": False, "value": 0.3},
    "lowpass":  {"enabled": False, "value": 4000.0},
    "highpass": {"enabled": False, "value": 200.0},
}

# ── Recorder FX defaults ──────────────────────────────────────────
DEFAULT_RECORDER_FX = {
    "chipmunk": {"semitones": 6.0,   "speed": 1.35},
    "deep":     {"semitones": -6.0,  "speed": 0.72},
    "reverb":   {"room_size": 0.75,  "wet": 0.5},
    "echo":     {"delay": 0.4,       "feedback": 0.45, "mix": 0.5},
    "lofi":     {"lowpass": 3200.0,  "highpass": 500.0},
    "reverse":  {},
}

DEFAULT_GROUPS = [
    {"name": "Jingles", "rows": 2, "cols": 8, "color": ""},
    {"name": "Drops",   "rows": 2, "cols": 8, "color": ""},
    {"name": "Music",   "rows": 2, "cols": 8, "color": ""},
    {"name": "SFX",     "rows": 2, "cols": 8, "color": ""},
]


def _slot(i: int, pinned=False) -> dict:
    labels = ["Intro","Outro","Stinger","Break",
              "Bumper","Theme","Promo","Fanfare",
              "Pin 9","Pin 10"]
    return {
        "label":      (labels[i] if pinned and i < len(labels)
                       else f"Sound {i+1}"),
        "file":       "",
        "color":      "",
        "text_color": "",
        "loop":       False,
        "overlap":    False,
        "hotkey":     "",
        "fx":         copy.deepcopy(DEFAULT_FX),
    }


def _total_slots(groups: list) -> int:
    return sum(g.get("rows", 2) * g.get("cols", 8) for g in groups)


DEFAULT_CONFIG = {
    # Meta
    "version":              VERSION,
    "first_run":            True,

    # Window
    "window_width":         1600,
    "window_height":        960,
    "opacity":              1.0,
    "font_size":            13,

    # Visual
    "color_theme":          "Default Blue",
    "bg_color":             "#060b14",

    # Show profile
    "show_name":            "The Chill With IceCat",
    "episode_number":       1,
    "title_template":       "The Chill Episode {n} — {date}",
    "prankcast_url":        PRANKCAST_URL,

    # Audio
    "audio_output_device":  "Default (System)",
    "audio_input_device":   "Default (System)",
    "recording_format":     "wav",
    "recordings_folder":    str(RECORDING_DIR),
    "fade_duration":        3.0,
    "log_audio_min_secs":   30,

    # Autosave
    "autosave_interval":    5,
    "log_autosave_interval":120,

    # Soundboard
    "soundboard_groups":    DEFAULT_GROUPS,
    "soundboard_locked":    False,
    "pinned_count":         8,
    "music_bank_name":      "Music",

    # Hotkeys
    "hotkeys": {
        "go_live":      "ctrl+shift+l",
        "panic":        "ctrl+shift+p",
        "mute":         "ctrl+shift+m",
        "timestamp":    "ctrl+shift+t",
        "gold_moment":  "ctrl+shift+g",
        "mini_mode":    "ctrl+shift+z",
    },

    # Mic
    "mic_input_device":     "Default (System)",
    "mic_duck_level":       0.3,

    # Notes
    "note_tabs":            ["Show Notes", "Premises & Ideas"],
    "notes_content":        {"Show Notes": "", "Premises & Ideas": ""},

    # Countdown
    "countdown_presets":    [5, 10, 15, 30],

    # Quick Folders
    "folders": [
        {"label": f"Folder {i+1}", "path": "", "color": "", "text_color": ""}
        for i in range(6)
    ],

    # Websites
    "websites": [
        {"label": "Prankcast",  "url": "https://prankcast.com/icecat"},
        {"label": "Radio.co",   "url": "https://radio.co"},
        {"label": "TuneIn",     "url": "https://tunein.com"},
    ],

    # Discord
    "discord_webhook":      "",
    "discord_message":      "🧊 IceCat is LIVE on Prankcast! {url}",
    "discord_enabled":      False,

    # Snippets (kept for copy-paste blocks)
    "snippets": [
        {"label": "Prankcast Link", "text": "https://prankcast.com/icecat"},
        {"label": "Patreon",        "text": "Support the show: https://patreon.com/icecat"},
    ],

    # Browser preference
    "browser_preference":   "",

    # Session
    "timestamp_format":     "%H:%M:%S",
    "session_folder":       str(SESSION_DIR),

    # Recorder FX
    "recorder_fx_settings": copy.deepcopy(DEFAULT_RECORDER_FX),

    # Button customisation {type:index → {color, text_color, label}}
    "button_custom":        {},

    # Soundboard data
    "soundboard":   [_slot(i) for i in range(256)],
    "pinned_slots": [_slot(i, pinned=True) for i in range(10)],
}


# ═══════════════════════════════════════════════════════════════
# CONFIG MANAGER
# ═══════════════════════════════════════════════════════════════

class ConfigManager:

    def __init__(self):
        for d in [DATA_DIR, SESSION_DIR, RECORDING_DIR, AUTOSAVE_DIR, LOG_DIR]:
            d.mkdir(parents=True, exist_ok=True)
        self.config = self._load()

    # ── Load / save ───────────────────────────────────────────────

    def _load(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    saved = json.load(f)
                base = copy.deepcopy(DEFAULT_CONFIG)
                self._deep_merge(base, saved)
                self._migrate(base)
                return base
            except Exception as e:
                print(f"Config load error: {e}")
        return copy.deepcopy(DEFAULT_CONFIG)

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")

    def backup(self) -> str | None:
        """Manual backup — called from Settings dialog."""
        self.save()
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = DATA_DIR / f"config_backup_{ts}.json"
        try:
            shutil.copy2(CONFIG_FILE, dst)
            return str(dst)
        except Exception:
            return None

    def startup_backup(self, keep: int = 5):
        """Automatic backup on every launch — keeps the last `keep` copies."""
        if not CONFIG_FILE.exists():
            return
        try:
            backup_dir = DATA_DIR / "config_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst = backup_dir / f"config_{ts}.json"
            shutil.copy2(CONFIG_FILE, dst)
            backups = sorted(backup_dir.glob("config_*.json"), reverse=True)
            for old in backups[keep:]:
                try:
                    old.unlink()
                except Exception:
                    pass
        except Exception:
            pass

    # ── Migration from older versions ─────────────────────────────

    def _migrate(self, cfg: dict):
        """Bring any older config up to current schema."""
        # Ensure all soundboard slots exist
        needed = max(_total_slots(cfg["soundboard_groups"]), 256)
        while len(cfg["soundboard"]) < needed:
            cfg["soundboard"].append(_slot(len(cfg["soundboard"])))

        # Ensure fx + text_color on all slots
        for slot in cfg["soundboard"] + cfg.get("pinned_slots", []):
            slot.setdefault("fx", copy.deepcopy(DEFAULT_FX))
            slot.setdefault("text_color", "")
            slot.setdefault("color", "")

        # Ensure pinned slots match count
        pc = cfg.get("pinned_count", 8)
        while len(cfg["pinned_slots"]) < pc:
            cfg["pinned_slots"].append(
                _slot(len(cfg["pinned_slots"]), pinned=True))

        # Ensure note_tabs and notes_content aligned
        for tab in cfg.get("note_tabs", []):
            cfg.setdefault("notes_content", {}). \
                setdefault(tab, "")

        # Ensure groups have color field
        for g in cfg.get("soundboard_groups", []):
            g.setdefault("color", "")

        # Migrate old audio_device key
        if "audio_device" in cfg:
            cfg.setdefault("audio_output_device", cfg.pop("audio_device"))

        # v3.0 new fields with safe defaults
        cfg.setdefault("show_name",         SHOW_NAME)
        cfg.setdefault("episode_number",    1)
        cfg.setdefault("title_template",    "The Chill Episode {n} — {date}")
        cfg.setdefault("recorder_fx_settings",
                       copy.deepcopy(DEFAULT_RECORDER_FX))
        cfg.setdefault("button_custom",     {})
        cfg.setdefault("countdown_presets", [5, 10, 15, 30])
        cfg.setdefault("recordings_folder", str(RECORDING_DIR))
        cfg.setdefault("recording_format",  "wav")
        cfg.setdefault("websites",          DEFAULT_CONFIG["websites"])
        cfg.setdefault("color_theme",       "Default Blue")
        cfg.setdefault("note_tabs",
                       ["Show Notes", "Premises & Ideas"])

    def _deep_merge(self, base: dict, override: dict):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v

    # ── Theme ─────────────────────────────────────────────────────

    def apply_theme(self, name: str = None):
        """Update global C dict with chosen theme palette."""
        n       = name or self.config.get("color_theme", "Default Blue")
        palette = THEMES.get(n, THEMES["Default Blue"])
        C.update(palette)
        self.config["bg_color"] = palette["bg"]
        return palette

    # ── Soundboard helpers ────────────────────────────────────────

    def bank_range(self, bank_idx: int) -> tuple[int, int]:
        start = 0
        for i, g in enumerate(self.config["soundboard_groups"]):
            size = g.get("rows", 2) * g.get("cols", 8)
            if i == bank_idx:
                return start, size
            start += size
        return 0, 16

    def export_bank(self, bank_idx: int) -> dict:
        start, count = self.bank_range(bank_idx)
        g = self.config["soundboard_groups"][bank_idx]
        return {
            "name":  g["name"],
            "rows":  g["rows"],
            "cols":  g["cols"],
            "color": g.get("color", ""),
            "slots": copy.deepcopy(
                self.config["soundboard"][start:start + count]),
        }

    def import_bank(self, bank_idx: int, data: dict):
        start, count = self.bank_range(bank_idx)
        for j, slot in enumerate(data.get("slots", [])[:count]):
            if start + j < len(self.config["soundboard"]):
                self.config["soundboard"][start + j] = slot

    # ── Button custom helpers ─────────────────────────────────────

    def get_btn_custom(self, btn_type: str, index: int = 0) -> dict:
        key = f"{btn_type}:{index}"
        return self.config.get("button_custom", {}).get(key, {})

    def set_btn_custom(self, btn_type: str, index: int, data: dict):
        key = f"{btn_type}:{index}"
        bc  = self.config.setdefault("button_custom", {})
        if data:
            bc[key] = data
        else:
            bc.pop(key, None)

    def has_any_custom_colors(self) -> bool:
        return any("color" in v
                   for v in self.config.get("button_custom", {}).values())

    def clear_custom_colors(self):
        for d in self.config.get("button_custom", {}).values():
            d.pop("color", None)
            d.pop("text_color", None)

    # ── Post-show helpers ─────────────────────────────────────────

    def format_title(self, duration_str: str = "") -> str:
        """Render title template with current episode number and date."""
        tmpl = self.config.get(
            "title_template", "The Chill Episode {n} — {date}")
        n    = self.config.get("episode_number", 1)
        date = datetime.now().strftime("%B %d, %Y")
        return (tmpl
                .replace("{n}",        str(n))
                .replace("{date}",     date)
                .replace("{duration}", duration_str)
                .replace("{show}",     self.config.get("show_name", SHOW_NAME)))

    def increment_episode(self):
        self.config["episode_number"] = \
            self.config.get("episode_number", 1) + 1


# ── Colour utilities ──────────────────────────────────────────────

def lighten(hex_col: str, factor: float = 1.3) -> str:
    h       = hex_col.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "#{:02x}{:02x}{:02x}".format(
        min(255, int(r * factor)),
        min(255, int(g * factor)),
        min(255, int(b * factor)))


def darken(hex_col: str, factor: float = 0.7) -> str:
    return lighten(hex_col, factor)


def fs(cfg, delta: int = 0) -> int:
    return max(8, cfg.config.get("font_size", 13) + delta)
