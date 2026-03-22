"""
ui_dialogs.py — IceCat Show Companion v3.0
All modal dialogs:
  ColorPickerDialog    — colour swatch + hex + system picker
  ButtonSettingsDialog — name + button color + text color
  FXPanel              — pedalboard FX editor for soundboard slots
  PostShowDialog       — end-of-show reminder with title/description
  SettingsWindow       — full settings
"""

import os, sys, copy, webbrowser, logging, threading
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
import customtkinter as ctk
from pathlib import Path
from datetime import datetime

from config import (C, VERSION, APP_NAME, SHOW_NAME, PRANKCAST_URL,
                    DATA_DIR, SESSION_DIR, RECORDING_DIR, THEMES,
                    DEFAULT_FX, lighten, fs)

log = logging.getLogger("icecat.ui")

try:
    from pedalboard import Pedalboard
    HAS_PEDALBOARD = True
except ImportError:
    HAS_PEDALBOARD = False

try:
    import keyboard as kb
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

from PIL import Image
from config import ASSET_DIR


def load_logo(size=(48, 54)):
    try:
        img = Image.open(ASSET_DIR / "logo.png").convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        return ctk.CTkImage(img, size=size)
    except Exception:
        return None


def _detect_browsers():
    candidates = [
        ("Chrome",  r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        ("Chrome",  r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ("Firefox", r"C:\Program Files\Mozilla Firefox\firefox.exe"),
        ("Edge",    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        ("Edge",    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        ("Brave",   r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]
    found = [("Default (system)", "")]
    seen  = set()
    for label, path in candidates:
        if path and os.path.exists(path) and path not in seen:
            found.append((label, path))
            seen.add(path)
    return found


# ═══════════════════════════════════════════════════════════════
# COLOR PICKER
# ═══════════════════════════════════════════════════════════════

class ColorPickerDialog(ctk.CTkToplevel):
    PRESETS = [
        "#0e1c30","#1c3d78","#2a55a8","#4070c8",
        "#f0a020","#ffbb40","#ffd700","#ff8800",
        "#e02233","#cc0000","#ff6644","#ff4488",
        "#20b85a","#126835","#00bcd4","#00e5ff",
        "#9b59b6","#8855d5","#7040c8","#3d1c78",
        "#607d8b","#c8d8f0","#132238","#060b14",
    ]

    def __init__(self, parent, initial="#1c3d78", callback=None):
        super().__init__(parent)
        self.callback = callback
        self._color   = initial or "#1c3d78"
        self.title("Choose Colour")
        self.geometry("400x340")
        self.configure(fg_color=C["bg2"])
        self.grab_set()
        self.resizable(False, False)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🎨  Colour Picker",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=C["amber"]).pack(pady=(14, 6))

        self._swatch = tk.Label(self, bg=self._color,
                                width=20, height=3, relief="flat")
        self._swatch.pack(pady=(0, 6))

        hex_row = ctk.CTkFrame(self, fg_color="transparent")
        hex_row.pack(pady=(0, 8))
        ctk.CTkLabel(hex_row, text="#",
                     font=ctk.CTkFont("Consolas", 13),
                     text_color=C["text"]).pack(side="left")
        self._hex_var = ctk.StringVar(value=self._color.lstrip("#"))
        self._hex_var.trace_add("write", self._on_hex)
        ctk.CTkEntry(hex_row, textvariable=self._hex_var,
                     width=100, font=ctk.CTkFont("Consolas", 13)
                     ).pack(side="left", padx=4)
        ctk.CTkButton(hex_row, text="System Picker", width=120,
                      fg_color=C["blue"], font=ctk.CTkFont("Segoe UI", 11),
                      command=self._sys_picker).pack(side="left", padx=4)

        pf = ctk.CTkFrame(self, fg_color="transparent")
        pf.pack(pady=4)
        for i, col in enumerate(self.PRESETS):
            tk.Button(pf, bg=col, width=2, height=1,
                      relief="flat", bd=1, cursor="hand2",
                      command=lambda c=col: self._pick(c)
                      ).grid(row=i//8, column=i%8, padx=2, pady=2)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=10)
        ctk.CTkButton(row, text="✓  Use Colour", width=150, height=34,
                      fg_color=C["green"],
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      command=self._confirm).pack(side="left", padx=6)
        ctk.CTkButton(row, text="Cancel", width=80, height=34,
                      fg_color=C["surface"],
                      font=ctk.CTkFont("Segoe UI", 11),
                      command=self.destroy).pack(side="left", padx=6)

    def _pick(self, col):
        self._color = col
        self._swatch.configure(bg=col)
        self._hex_var.set(col.lstrip("#"))

    def _on_hex(self, *_):
        val = self._hex_var.get().strip()
        if len(val) == 6:
            try:
                int(val, 16)
                self._color = "#" + val
                self._swatch.configure(bg=self._color)
            except ValueError:
                pass

    def _sys_picker(self):
        col = colorchooser.askcolor(color=self._color, title="Pick Colour")
        if col and col[1]:
            self._pick(col[1])

    def _confirm(self):
        if self.callback:
            self.callback(self._color)
        self.destroy()


# ═══════════════════════════════════════════════════════════════
# BUTTON SETTINGS DIALOG
# ═══════════════════════════════════════════════════════════════

class ButtonSettingsDialog(ctk.CTkToplevel):
    """
    Combined Name + Button Colour + Text Colour dialog.
    allow_rename=False hides the label field (colour-only buttons).
    result = {label, color, text_color} or None if cancelled.
    """

    def __init__(self, parent, label="", color="",
                 text_color="", allow_rename=True):
        super().__init__(parent)
        self.result        = None
        self._label        = label
        self._color        = color or C["btn"]
        self._text_color   = text_color or ""
        self._allow_rename = allow_rename

        self.title("🎨  Customize Button")
        h = 370 if allow_rename else 300
        self.geometry(f"420x{h}")
        self.configure(fg_color=C["bg2"])
        self.grab_set()
        self.resizable(False, False)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🎨  Customize Button",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=C["amber"]).pack(pady=(14, 8))

        sf = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=8)
        sf.pack(fill="x", padx=16, pady=4)

        if self._allow_rename:
            ctk.CTkLabel(sf, text="Label:",
                         font=ctk.CTkFont("Segoe UI", 11),
                         text_color=C["text_dim"]).pack(
                             padx=12, pady=(10, 2), anchor="w")
            self._lv = ctk.StringVar(value=self._label)
            ctk.CTkEntry(sf, textvariable=self._lv,
                         width=360, font=ctk.CTkFont("Segoe UI", 12)
                         ).pack(padx=12, pady=(0, 8))

        # Button colour
        ctk.CTkLabel(sf, text="Button Colour:",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=C["text_dim"]).pack(
                         padx=12, pady=(8, 4), anchor="w")
        cr = ctk.CTkFrame(sf, fg_color="transparent")
        cr.pack(fill="x", padx=12, pady=(0, 8))
        self._cs = tk.Label(cr, bg=self._color, width=6, height=2,
                            relief="flat", bd=1)
        self._cs.pack(side="left", padx=(0, 8))
        ctk.CTkButton(cr, text="Choose", width=110, height=28,
                      fg_color=C["blue"],
                      command=lambda: ColorPickerDialog(
                          self, self._color, self._set_color)
                      ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(cr, text="Reset", width=60, height=28,
                      fg_color=C["surface"],
                      command=lambda: self._set_color("")
                      ).pack(side="left")

        # Text colour
        ctk.CTkLabel(sf, text="Text Colour:",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=C["text_dim"]).pack(
                         padx=12, pady=(4, 4), anchor="w")
        tr = ctk.CTkFrame(sf, fg_color="transparent")
        tr.pack(fill="x", padx=12, pady=(0, 10))
        self._ts = tk.Label(tr,
                            bg=self._text_color or C["text"],
                            width=6, height=2, relief="flat", bd=1)
        self._ts.pack(side="left", padx=(0, 8))
        ctk.CTkButton(tr, text="Choose", width=110, height=28,
                      fg_color=C["blue"],
                      command=lambda: ColorPickerDialog(
                          self, self._text_color or C["text"],
                          self._set_text_color)
                      ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(tr, text="Reset", width=60, height=28,
                      fg_color=C["surface"],
                      command=lambda: self._set_text_color("")
                      ).pack(side="left")

        # Buttons
        br = ctk.CTkFrame(self, fg_color="transparent")
        br.pack(pady=14)
        ctk.CTkButton(br, text="✓  Apply", width=120, height=34,
                      fg_color=C["green"],
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      command=self._confirm).pack(side="left", padx=6)
        ctk.CTkButton(br, text="Cancel", width=80, height=34,
                      fg_color=C["surface"],
                      command=self.destroy).pack(side="left", padx=6)

    def _set_color(self, c):
        self._color = c or ""
        self._cs.configure(bg=c if c else C["btn"])

    def _set_text_color(self, c):
        self._text_color = c or ""
        self._ts.configure(bg=c if c else C["text"])

    def _confirm(self):
        self.result = {
            "label":      (self._lv.get().strip()
                           if self._allow_rename else ""),
            "color":      self._color,
            "text_color": self._text_color,
        }
        self.destroy()


# ═══════════════════════════════════════════════════════════════
# FX PANEL
# ═══════════════════════════════════════════════════════════════

class FXPanel(ctk.CTkToplevel):
    """Pedalboard FX editor for a soundboard slot."""

    EFFECTS = [
        ("volume",   "Volume Boost",    0.0,    3.0,  1.0, 0.05),
        ("pitch",    "Pitch Shift",    -12.0,  12.0,  0.0, 0.5),
        ("speed",    "Speed",           0.25,   4.0,  1.0, 0.05),
        ("reverb",   "Reverb",          0.0,    1.0,  0.3, 0.05),
        ("echo",     "Echo / Delay",    0.0,    1.0,  0.3, 0.05),
        ("lowpass",  "Low-pass (Hz)", 500.0, 20000.0, 4000.0, 100.0),
        ("highpass", "High-pass (Hz)", 20.0,  2000.0,  200.0, 10.0),
    ]

    def __init__(self, parent, slot_source, idx, cfg, audio, on_apply=None):
        super().__init__(parent)
        self.cfg        = cfg
        self.audio      = audio
        self.slot_source = slot_source
        self.idx        = idx
        self.on_apply   = on_apply
        self.title(f"🎛  FX — {cfg.config[slot_source][idx].get('label','')}")
        self.geometry("460x480")
        self.configure(fg_color=C["bg2"])
        self.grab_set()
        self._build()

    def _build(self):
        if not HAS_PEDALBOARD:
            ctk.CTkLabel(
                self,
                text="⚠  pedalboard not installed.\n"
                     "Run: pip install pedalboard",
                font=ctk.CTkFont("Segoe UI", 12),
                text_color=C["amber"]).pack(pady=40)
            return

        ctk.CTkLabel(self, text="🎛  Effects",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=C["amber"]).pack(pady=(12, 6))

        sf = ctk.CTkScrollableFrame(self, fg_color="transparent")
        sf.pack(fill="both", expand=True, padx=12)

        slot       = self.cfg.config[self.slot_source][self.idx]
        fx_config  = slot.get("fx", {})
        self._vars = {}

        for key, label, mn, mx, default, res in self.EFFECTS:
            fx   = fx_config.get(key, {"enabled": False, "value": default})
            row  = ctk.CTkFrame(sf, fg_color=C["surface"], corner_radius=6)
            row.pack(fill="x", pady=2)

            en_var = ctk.BooleanVar(value=fx.get("enabled", False))
            ctk.CTkCheckBox(row, text=label, variable=en_var,
                            font=ctk.CTkFont("Segoe UI", 11),
                            text_color=C["text"],
                            fg_color=C["blue_mid"],
                            width=160).pack(side="left", padx=8, pady=6)

            val_var = ctk.DoubleVar(value=fx.get("value", default))
            val_lbl = ctk.CTkLabel(row, text=f"{val_var.get():.2f}",
                                   font=ctk.CTkFont("Consolas", 10),
                                   text_color=C["text_dim"], width=50)
            val_lbl.pack(side="right", padx=6)

            slider = ctk.CTkSlider(row, from_=mn, to=mx,
                                   variable=val_var, width=160,
                                   command=lambda v, vl=val_lbl,
                                   vv=val_var: vl.configure(
                                       text=f"{float(v):.2f}"))
            slider.pack(side="right", padx=4)
            self._vars[key] = (en_var, val_var)

        # Preview + apply
        br = ctk.CTkFrame(self, fg_color="transparent")
        br.pack(pady=10)
        ctk.CTkButton(br, text="▶ Preview", width=100, height=32,
                      fg_color=C["blue"],
                      command=self._preview).pack(side="left", padx=4)
        ctk.CTkButton(br, text="✓ Apply", width=100, height=32,
                      fg_color=C["green"],
                      command=self._apply).pack(side="left", padx=4)
        ctk.CTkButton(br, text="↩ Reset", width=80, height=32,
                      fg_color=C["surface"],
                      command=self._reset).pack(side="left", padx=4)
        ctk.CTkButton(br, text="Close", width=80, height=32,
                      fg_color=C["surface"],
                      command=self.destroy).pack(side="left", padx=4)

    def _collect(self) -> dict:
        return {k: {"enabled": ev.get(), "value": vv.get()}
                for k, (ev, vv) in self._vars.items()}

    def _preview(self):
        slot = self.cfg.config[self.slot_source][self.idx]
        path = slot.get("file", "")
        if not path or not os.path.exists(path):
            return
        fx = self._collect()
        self.audio.prepare(999, path, fx)
        self.audio.play(999)

    def _apply(self):
        fx = self._collect()
        self.cfg.config[self.slot_source][self.idx]["fx"] = fx
        self.cfg.save()
        if self.on_apply:
            self.on_apply()
        self.destroy()

    def _reset(self):
        from config import DEFAULT_FX
        import copy
        self.cfg.config[self.slot_source][self.idx]["fx"] = \
            copy.deepcopy(DEFAULT_FX)
        self.cfg.save()
        self.destroy()


# ═══════════════════════════════════════════════════════════════
# POST-SHOW DIALOG  — the new show reminder
# ═══════════════════════════════════════════════════════════════

class PostShowDialog(ctk.CTkToplevel):
    """
    Appears when the host ends the show.
    Forces a title + description before dismissing.
    Provides copy-to-clipboard and open-Prankcast buttons.
    """

    def __init__(self, parent, cfg, duration_str: str = "",
                 session_summary: str = ""):
        super().__init__(parent)
        self.cfg             = cfg
        self.duration_str    = duration_str
        self.session_summary = session_summary
        self._saved          = False

        self.title("📋  Post Your Show!")
        self.geometry("560x560")
        self.configure(fg_color=C["bg2"])
        self.grab_set()
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=0)
        hdr.pack(fill="x")

        ctk.CTkLabel(hdr,
                     text="🎙  Show Complete!  Don't forget to post.",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=C["amber"]).pack(
                         side="left", padx=16, pady=12)

        if self.duration_str:
            ctk.CTkLabel(hdr, text=f"⏱  {self.duration_str}",
                         font=ctk.CTkFont("Segoe UI", 11),
                         text_color=C["text_dim"]).pack(
                             side="right", padx=16)

        # Body
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=8)

        # Episode number row
        ep_row = ctk.CTkFrame(body, fg_color="transparent")
        ep_row.pack(fill="x", pady=(4, 8))
        ctk.CTkLabel(ep_row, text="Episode #:",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=C["text_dim"]).pack(side="left", padx=(0,8))
        self._ep_var = ctk.StringVar(
            value=str(self.cfg.config.get("episode_number", 1)))
        ctk.CTkEntry(ep_row, textvariable=self._ep_var,
                     width=70, font=ctk.CTkFont("Segoe UI", 11)
                     ).pack(side="left")

        # Title
        ctk.CTkLabel(body, text="Show Title:",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0, 4))

        default_title = self.cfg.format_title(self.duration_str)
        self._title_var = ctk.StringVar(value=default_title)

        title_row = ctk.CTkFrame(body, fg_color="transparent")
        title_row.pack(fill="x", pady=(0, 4))
        self._title_entry = ctk.CTkEntry(
            title_row, textvariable=self._title_var,
            font=ctk.CTkFont("Segoe UI", 12), height=36)
        self._title_entry.pack(side="left", fill="x", expand=True,
                               padx=(0, 6))
        ctk.CTkButton(title_row, text="📋", width=36, height=36,
                      fg_color=C["btn"], hover_color=C["btn_hover"],
                      font=ctk.CTkFont("Segoe UI", 13),
                      command=lambda: self._copy(
                          self._title_var.get())
                      ).pack(side="left")

        # Description
        ctk.CTkLabel(body, text="Show Description / Notes:",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["text"]).pack(
                         anchor="w", pady=(12, 4))
        ctk.CTkLabel(body,
                     text="Describe what happened on the show. "
                          "You can pull from your session log below.",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=C["text_dim"], justify="left"
                     ).pack(anchor="w", pady=(0, 4))

        self._desc_box = ctk.CTkTextbox(
            body, height=120,
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color=C["surface"], text_color=C["text"],
            border_color=C["border"], border_width=1)
        self._desc_box.pack(fill="x")

        # Session log highlights
        if self.session_summary:
            ctk.CTkLabel(body, text="Session Log (for reference):",
                         font=ctk.CTkFont("Segoe UI", 10, "bold"),
                         text_color=C["text_dim"]).pack(
                             anchor="w", pady=(12, 4))
            log_box = ctk.CTkTextbox(
                body, height=100,
                font=ctk.CTkFont("Consolas", 9),
                fg_color=C["bg"],
                text_color=C["text_dim"],
                state="normal")
            log_box.insert("1.0", self.session_summary)
            log_box.configure(state="disabled")
            log_box.pack(fill="x")

        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color=C["surface"],
                                  corner_radius=0)
        btn_frame.pack(fill="x", side="bottom")

        ctk.CTkButton(btn_frame,
                      text="📋  Copy All",
                      width=130, height=38,
                      fg_color=C["blue_mid"],
                      font=ctk.CTkFont("Segoe UI", 11, "bold"),
                      command=self._copy_all
                      ).pack(side="left", padx=8, pady=8)

        ctk.CTkButton(btn_frame,
                      text="🌐  Open Prankcast",
                      width=150, height=38,
                      fg_color=C["btn"],
                      hover_color=C["btn_hover"],
                      font=ctk.CTkFont("Segoe UI", 11),
                      command=lambda: webbrowser.open(
                          self.cfg.config.get("prankcast_url",
                                              PRANKCAST_URL))
                      ).pack(side="left", padx=4, pady=8)

        ctk.CTkButton(btn_frame,
                      text="✓  Done",
                      width=100, height=38,
                      fg_color=C["green"],
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      command=self._done
                      ).pack(side="right", padx=8, pady=8)

        ctk.CTkButton(btn_frame,
                      text="Dismiss",
                      width=90, height=38,
                      fg_color=C["surface"],
                      font=ctk.CTkFont("Segoe UI", 11),
                      command=self._on_close
                      ).pack(side="right", padx=4, pady=8)

    def _copy(self, text: str):
        try:
            import pyperclip
            pyperclip.copy(text)
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(text)

    def _copy_all(self):
        title = self._title_var.get().strip()
        desc  = self._desc_box.get("1.0", "end").strip()
        combined = f"{title}\n\n{desc}" if desc else title
        self._copy(combined)

    def _done(self):
        # Save episode number update
        try:
            ep = int(self._ep_var.get())
            self.cfg.config["episode_number"] = ep + 1
        except ValueError:
            self.cfg.increment_episode()
        self.cfg.save()
        self._saved = True
        self.destroy()

    def _on_close(self):
        if not self._saved:
            if not messagebox.askyesno(
                    "Skip Posting?",
                    "Are you sure you want to dismiss without posting?\n\n"
                    "The episode number will NOT be incremented.",
                    icon="warning"):
                return
        self.destroy()


# ═══════════════════════════════════════════════════════════════
# SETTINGS WINDOW
# ═══════════════════════════════════════════════════════════════

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, cfg, app):
        super().__init__(parent)
        self.cfg = cfg
        self.app = app
        self.title("⚙  Settings")
        self.geometry("700x720")
        self.configure(fg_color=C["bg2"])
        self.grab_set()
        self._browser_paths = {}
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="⚙  Settings",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=C["amber"]).pack(pady=(12, 4))

        tabs = ctk.CTkTabview(
            self, fg_color=C["surface"],
            segmented_button_fg_color=C["elevated"],
            segmented_button_selected_color=C["blue_mid"])
        tabs.pack(fill="both", expand=True, padx=12, pady=4)

        for n in ["Show", "Audio", "Soundboard",
                  "Hotkeys", "Websites", "Visual", "Integrations", "About"]:
            tabs.add(n)

        self._tab_show(tabs.tab("Show"))
        self._tab_audio(tabs.tab("Audio"))
        self._tab_soundboard(tabs.tab("Soundboard"))
        self._tab_hotkeys(tabs.tab("Hotkeys"))
        self._tab_websites(tabs.tab("Websites"))
        self._tab_visual(tabs.tab("Visual"))
        self._tab_integrations(tabs.tab("Integrations"))
        self._tab_about(tabs.tab("About"))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=8)
        ctk.CTkButton(row, text="💾  Save & Close",
                      fg_color=C["blue_mid"], width=160,
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      command=self._save).pack(side="left", padx=6)
        ctk.CTkButton(row, text="Cancel",
                      fg_color=C["surface"], width=90,
                      command=self.destroy).pack(side="left", padx=6)

    def _lbl(self, p, t, bold=False):
        ctk.CTkLabel(p, text=t,
                     font=ctk.CTkFont("Segoe UI", 10,
                                       "bold" if bold else "normal"),
                     text_color=C["text"] if bold else C["text_dim"],
                     anchor="w").pack(padx=12, pady=(8,1), anchor="w")

    # ── Show tab ──────────────────────────────────────────────────

    def _tab_show(self, p):
        sf = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sf.pack(fill="both", expand=True)

        self._lbl(sf, "Show Name:", bold=True)
        self._show_name = ctk.StringVar(
            value=self.cfg.config.get("show_name", ""))
        ctk.CTkEntry(sf, textvariable=self._show_name,
                     width=400).pack(padx=12, anchor="w")

        self._lbl(sf, "Current Episode Number:", bold=True)
        self._ep_num = ctk.StringVar(
            value=str(self.cfg.config.get("episode_number", 1)))
        ctk.CTkEntry(sf, textvariable=self._ep_num,
                     width=100).pack(padx=12, anchor="w")

        self._lbl(sf, "Title Template:", bold=True)
        ctk.CTkLabel(sf,
                     text="Variables: {n} = episode #, {date} = today's date,\n"
                          "{show} = show name, {duration} = show length",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=C["text_dim"], justify="left"
                     ).pack(padx=12, anchor="w")
        self._title_tmpl = ctk.StringVar(
            value=self.cfg.config.get(
                "title_template", "The Chill Episode {n} — {date}"))
        ctk.CTkEntry(sf, textvariable=self._title_tmpl,
                     width=500).pack(padx=12, anchor="w")

        ctk.CTkFrame(sf, height=1, fg_color=C["border"]).pack(
            fill="x", padx=12, pady=(16, 4))

        self._lbl(sf, "Prankcast URL:", bold=True)
        self._pc_url = ctk.StringVar(
            value=self.cfg.config.get("prankcast_url", PRANKCAST_URL))
        ctk.CTkEntry(sf, textvariable=self._pc_url,
                     width=400).pack(padx=12, anchor="w")

        self._lbl(sf, "Note Tabs (comma-separated):", bold=True)
        self._note_tabs = ctk.StringVar(
            value=", ".join(self.cfg.config.get(
                "note_tabs", ["Show Notes", "Premises & Ideas"])))
        ctk.CTkEntry(sf, textvariable=self._note_tabs,
                     width=400).pack(padx=12, anchor="w")

    # ── Audio tab ─────────────────────────────────────────────────

    def _tab_audio(self, p):
        sf = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sf.pack(fill="both", expand=True)

        # Output device
        ctk.CTkLabel(sf, text="🔊  Output Device (soundboard playback)",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["amber"]).pack(
                         padx=12, pady=(12,2), anchor="w")
        out_devs   = self.app.audio.get_output_devices()
        out_labels = [d[1] for d in out_devs]
        cur_out    = self.cfg.config.get(
            "audio_output_device", "Default (System)")
        self._out_dev = ctk.StringVar(
            value=cur_out if cur_out in out_labels else out_labels[0])
        ctk.CTkOptionMenu(sf, values=out_labels,
                          variable=self._out_dev, width=420,
                          ).pack(padx=12, anchor="w", pady=(0,8))

        # Input device
        ctk.CTkLabel(sf, text="🎙  Input Device (tape recorder capture)",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["amber"]).pack(
                         padx=12, pady=(4,2), anchor="w")
        ctk.CTkLabel(sf,
                     text="For full show recording: choose Voicemeeter Output or Stereo Mix.",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=C["text_dim"]).pack(padx=12, anchor="w")
        in_devs    = self.app.audio.get_input_devices()
        in_labels  = [d[1] for d in in_devs]
        cur_in     = self.cfg.config.get(
            "audio_input_device", "Default (System)")
        self._in_dev = ctk.StringVar(
            value=cur_in if cur_in in in_labels else in_labels[0])
        ctk.CTkOptionMenu(sf, values=in_labels,
                          variable=self._in_dev, width=420,
                          ).pack(padx=12, anchor="w", pady=(0,8))

        ctk.CTkFrame(sf, height=1, fg_color=C["border"]).pack(
            fill="x", padx=12, pady=(4,8))

        # Recordings folder
        ctk.CTkLabel(sf, text="📁  Recordings Folder",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["amber"]).pack(
                         padx=12, pady=(4,2), anchor="w")
        self._rec_folder = self.cfg.config.get(
            "recordings_folder", str(RECORDING_DIR))
        rr = ctk.CTkFrame(sf, fg_color="transparent")
        rr.pack(fill="x", padx=12, pady=(0,8))
        self._rec_lbl = ctk.CTkLabel(
            rr, text=self._rec_folder,
            font=ctk.CTkFont("Segoe UI", 9),
            text_color=C["text_dim"], anchor="w", wraplength=320)
        self._rec_lbl.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(rr, text="Browse", width=80, height=26,
                      fg_color=C["blue"],
                      command=self._pick_rec_folder).pack(side="right")

        # Recording format
        self._lbl(sf, "Recording Format:")
        self._rec_fmt = ctk.StringVar(
            value=self.cfg.config.get("recording_format", "wav"))
        fr = ctk.CTkFrame(sf, fg_color="transparent")
        fr.pack(fill="x", padx=12)
        for val, lbl in [("wav","WAV (lossless)"), ("mp3","MP3 (compressed)")]:
            ctk.CTkRadioButton(
                fr, text=lbl, variable=self._rec_fmt, value=val,
                fg_color=C["blue_mid"]).pack(side="left", padx=(0,16))

        ctk.CTkFrame(sf, height=1, fg_color=C["border"]).pack(
            fill="x", padx=12, pady=(12,8))

        self._lbl(sf, "Fade Out Duration (seconds):")
        self._fade = ctk.StringVar(
            value=str(self.cfg.config.get("fade_duration", 3.0)))
        ctk.CTkOptionMenu(sf, values=["1","2","3","5","8","10"],
                          variable=self._fade, width=100
                          ).pack(padx=12, anchor="w")

        self._lbl(sf, "Minimum sound duration to log (seconds):")
        self._log_min = ctk.StringVar(
            value=str(self.cfg.config.get("log_audio_min_secs", 30)))
        ctk.CTkOptionMenu(sf,
                          values=["0","5","10","15","20","30","45","60"],
                          variable=self._log_min, width=100
                          ).pack(padx=12, anchor="w")


        ctk.CTkFrame(sf, height=1, fg_color=C["border"]).pack(
            fill="x", padx=12, pady=(12, 8))

        # Mic input device
        ctk.CTkLabel(sf, text="🎙️  Mic Input Device",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["amber"]).pack(
                         padx=12, pady=(0, 2), anchor="w")
        ctk.CTkLabel(sf,
                     text="The Windows input device the Mute button controls.\n"
                          "For Voicemeeter: pick the strip your mic is on.",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=C["text_dim"],
                     justify="left").pack(padx=12, anchor="w", pady=(0, 4))
        mic_devs   = self.app.audio.get_input_devices()
        mic_labels = [d[1] for d in mic_devs]
        cur_mic    = self.cfg.config.get(
            "mic_input_device", "Default (System)")
        self._mic_dev = ctk.StringVar(
            value=cur_mic if cur_mic in mic_labels else mic_labels[0])
        ctk.CTkOptionMenu(sf, values=mic_labels,
                          variable=self._mic_dev, width=420
                          ).pack(padx=12, anchor="w", pady=(0, 10))

        # Duck level
        ctk.CTkLabel(sf, text="🎚  Duck Level",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["amber"]).pack(
                         padx=12, pady=(0, 2), anchor="w")
        ctk.CTkLabel(sf,
                     text="How far the VOL/FADE slider drops when you press Duck.",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=C["text_dim"]).pack(
                         padx=12, anchor="w", pady=(0, 4))
        self._duck_level = ctk.DoubleVar(
            value=self.cfg.config.get("mic_duck_level", 0.3))
        self._duck_level_lbl = ctk.CTkLabel(
            sf, text=f'{self._duck_level.get():.0%}',
            font=ctk.CTkFont("Segoe UI", 9), text_color=C["text_dim"])
        self._duck_level_lbl.pack(padx=12, anchor="w")
        ctk.CTkSlider(sf, from_=0.0, to=1.0, width=280,
                      variable=self._duck_level,
                      command=lambda v: self._duck_level_lbl.configure(
                          text=f"{float(v):.0%}")
                      ).pack(padx=12, anchor="w", pady=(0, 12))

    def _pick_rec_folder(self):
        f = filedialog.askdirectory(
            title="Choose Recordings Folder",
            initialdir=self._rec_folder)
        if f:
            self._rec_folder = f
            self._rec_lbl.configure(text=f)

    # ── Soundboard tab ────────────────────────────────────────────

    def _tab_soundboard(self, p):
        sf = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sf.pack(fill="both", expand=True)

        self._lbl(sf, "Pinned Row Button Count:")
        self._pinned = ctk.StringVar(
            value=str(self.cfg.config.get("pinned_count", 8)))
        ctk.CTkOptionMenu(sf,
                          values=["2","3","4","5","6","7","8","10","12"],
                          variable=self._pinned, width=100
                          ).pack(padx=12, anchor="w")

        self._lbl(sf, "Music Bank (for detailed logging):")
        groups = [g["name"] for g in
                  self.cfg.config.get("soundboard_groups", [])]
        self._music_bank = ctk.StringVar(
            value=self.cfg.config.get("music_bank_name", "Music"))
        if groups:
            ctk.CTkOptionMenu(sf, values=groups,
                              variable=self._music_bank, width=180
                              ).pack(padx=12, anchor="w")

        ctk.CTkFrame(sf, height=1, fg_color=C["border"]).pack(
            fill="x", padx=12, pady=(12,4))
        ctk.CTkLabel(sf, text="Bank Editor",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["amber"]).pack(padx=12, anchor="w")

        self._bank_frame  = ctk.CTkFrame(sf, fg_color="transparent")
        self._bank_frame.pack(fill="x", padx=12, pady=4)
        self._grp_entries = []
        self._redraw_banks()

        ctk.CTkButton(sf, text="+ Add Bank", width=100, height=28,
                      fg_color=C["blue_mid"],
                      command=self._add_bank).pack(
                          padx=12, anchor="w", pady=4)

    def _redraw_banks(self):
        for w in self._bank_frame.winfo_children():
            w.destroy()
        self._grp_entries.clear()
        for i, g in enumerate(self.cfg.config.get(
                "soundboard_groups", [])):
            row = ctk.CTkFrame(self._bank_frame,
                               fg_color=C["surface"], corner_radius=5)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{i+1}.", width=24,
                         text_color=C["text_dim"]).pack(
                             side="left", padx=(6,0))
            ne = ctk.CTkEntry(row, width=160)
            ne.insert(0, g.get("name",""))
            ne.pack(side="left", padx=4, pady=4)
            entries = [ne]
            for lbl, key, w in [("R","rows",48),("C","cols",48)]:
                ctk.CTkLabel(row, text=lbl, width=12,
                             text_color=C["text_dim"]).pack(side="left")
                e = ctk.CTkEntry(row, width=w)
                e.insert(0, str(g.get(key, 2 if key=="rows" else 8)))
                e.pack(side="left", padx=2, pady=4)
                entries.append(e)
            self._grp_entries.append((i, entries))
            ctk.CTkButton(row, text="🗑", width=28, height=28,
                          corner_radius=4, fg_color=C["surface"],
                          hover_color=C["red_dim"],
                          command=lambda idx=i: self._del_bank(idx)
                          ).pack(side="right", padx=4)

    def _add_bank(self):
        self.cfg.config["soundboard_groups"].append(
            {"name": f"Bank {len(self.cfg.config['soundboard_groups'])+1}",
             "rows": 2, "cols": 8, "color": ""})
        self._redraw_banks()

    def _del_bank(self, idx):
        grps = self.cfg.config["soundboard_groups"]
        if len(grps) > 1:
            grps.pop(idx)
            self._redraw_banks()

    # ── Hotkeys tab ───────────────────────────────────────────────

    def _tab_hotkeys(self, p):
        sf = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sf.pack(fill="both", expand=True)
        self._hk = {}
        hotkeys  = self.cfg.config.get("hotkeys", {})
        labels   = {
            "go_live":     "Go Live / End Live",
            "panic":       "Panic (Stop All)",
            "mute":        "Mute Toggle",
            "timestamp":   "Add Timestamp",
            "gold_moment": "Gold Moment",
            "mini_mode":   "Toggle Mini Mode",
        }
        for key, label in labels.items():
            self._lbl(sf, f"{label}:")
            e = ctk.CTkEntry(sf, width=200)
            e.insert(0, hotkeys.get(key, ""))
            e.pack(padx=12, anchor="w")
            self._hk[key] = e

    # ── Visual tab ────────────────────────────────────────────────

    # ── Mic tab ─────────────────────────────────

    def _tab_websites(self, p):
        sf = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sf.pack(fill="both", expand=True)

        ctk.CTkLabel(sf, text="🌐  Websites",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["amber"]).pack(
                         padx=12, pady=(12, 2), anchor="w")
        ctk.CTkLabel(sf,
                     text="These appear in the Quick Folders + Sites dropdown.",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=C["text_dim"]).pack(
                         padx=12, anchor="w", pady=(0, 6))

        self._web_frame = ctk.CTkFrame(sf, fg_color="transparent")
        self._web_frame.pack(fill="x", padx=12)
        self._web_entries = []
        self._redraw_websites()

        ctk.CTkButton(sf, text="+ Add Website",
                      width=130, height=28,
                      fg_color=C["blue_mid"],
                      command=self._add_website
                      ).pack(padx=12, anchor="w", pady=(6, 4))

    def _redraw_websites(self):
        for w in self._web_frame.winfo_children():
            w.destroy()
        self._web_entries.clear()
        sites = self.cfg.config.get("websites", [])
        for i, s in enumerate(sites):
            row = ctk.CTkFrame(self._web_frame,
                               fg_color=C["surface"], corner_radius=5)
            row.pack(fill="x", pady=2)
            le = ctk.CTkEntry(row, width=120, placeholder_text="Label")
            le.insert(0, s.get("label", ""))
            le.pack(side="left", padx=(6, 4), pady=4)
            ue = ctk.CTkEntry(row, width=260, placeholder_text="https://")
            ue.insert(0, s.get("url", ""))
            ue.pack(side="left", padx=(0, 4), pady=4)
            ctk.CTkButton(row, text="🗑", width=28, height=28,
                          corner_radius=4,
                          fg_color=C["surface"],
                          hover_color=C["red_dim"],
                          command=lambda ii=i: self._del_website(ii)
                          ).pack(side="right", padx=4)
            self._web_entries.append((le, ue))

    def _add_website(self):
        self._save_websites()
        self.cfg.config.setdefault("websites", []).append(
            {"label": "New Site", "url": "https://"})
        self._redraw_websites()

    def _del_website(self, idx):
        self._save_websites()
        sites = self.cfg.config.get("websites", [])
        if 0 <= idx < len(sites):
            sites.pop(idx)
        self._redraw_websites()

    def _save_websites(self):
        if not hasattr(self, "_web_entries"):
            return
        sites = []
        for le, ue in self._web_entries:
            lbl = le.get().strip()
            url = ue.get().strip()
            if lbl and url:
                sites.append({"label": lbl, "url": url})
        self.cfg.config["websites"] = sites

    def _tab_visual(self, p):
        sf = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sf.pack(fill="both", expand=True)

        ctk.CTkLabel(sf, text="Color Theme",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["amber"]).pack(
                         padx=12, pady=(12,2), anchor="w")
        ctk.CTkLabel(sf,
                     text="Theme change requires app restart.",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=C["text_dim"]).pack(padx=12, anchor="w")

        self._theme = ctk.StringVar(
            value=self.cfg.config.get("color_theme", "Default Blue"))
        tf = ctk.CTkFrame(sf, fg_color=C["surface"], corner_radius=8)
        tf.pack(fill="x", padx=12, pady=(4,12))

        for name in THEMES:
            pal = THEMES[name]
            row = ctk.CTkFrame(tf, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=3)
            ctk.CTkRadioButton(
                row, text=name, variable=self._theme, value=name,
                fg_color=C["blue_mid"], text_color=C["text"]
            ).pack(side="left", padx=(4,8))
            for key in ["bg2","blue_mid","amber","green","red"]:
                tk.Label(row, bg=pal.get(key,"#333"),
                         width=2, height=1, relief="flat", bd=1
                         ).pack(side="left", padx=1)

        ctk.CTkFrame(sf, height=1, fg_color=C["border"]).pack(
            fill="x", padx=12, pady=(0,8))

        self._lbl(sf, "Font Size:")
        self._font_size = ctk.StringVar(
            value=str(self.cfg.config.get("font_size", 13)))
        ctk.CTkOptionMenu(sf, values=["10","11","12","13","14","15"],
                          variable=self._font_size, width=100
                          ).pack(padx=12, anchor="w")

        self._lbl(sf, "Window Opacity:")
        self._opacity = ctk.DoubleVar(
            value=self.cfg.config.get("opacity", 1.0))
        ctk.CTkSlider(sf, from_=0.3, to=1.0, width=240,
                      variable=self._opacity,
                      command=lambda v: self.app.set_opacity(v)
                      ).pack(padx=12, anchor="w", pady=(0,12))

    # ── Integrations tab ──────────────────────────────────────────

    def _tab_integrations(self, p):
        sf = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sf.pack(fill="both", expand=True)

        ctk.CTkLabel(sf, text="Discord Webhook",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["amber"]).pack(
                         padx=12, pady=(12,2), anchor="w")
        self._discord_en = ctk.BooleanVar(
            value=self.cfg.config.get("discord_enabled", False))
        ctk.CTkCheckBox(sf, text="Enable go-live notification",
                        variable=self._discord_en,
                        fg_color=C["blue_mid"]
                        ).pack(padx=12, anchor="w")
        self._lbl(sf, "Webhook URL:")
        self._discord_url = ctk.StringVar(
            value=self.cfg.config.get("discord_webhook", ""))
        ctk.CTkEntry(sf, textvariable=self._discord_url,
                     width=450).pack(padx=12, anchor="w")
        self._lbl(sf, "Message ({url} = Prankcast link):")
        self._discord_msg = ctk.StringVar(
            value=self.cfg.config.get(
                "discord_message",
                "🧊 IceCat is LIVE on Prankcast! {url}"))
        ctk.CTkEntry(sf, textvariable=self._discord_msg,
                     width=450).pack(padx=12, anchor="w")

        ctk.CTkFrame(sf, height=1, fg_color=C["border"]).pack(
            fill="x", padx=12, pady=(16,8))

        # Browser preference
        ctk.CTkLabel(sf, text="Preferred Browser",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["amber"]).pack(
                         padx=12, pady=(4,2), anchor="w")
        browsers = _detect_browsers()
        for label, path in browsers:
            self._browser_paths[label] = path
        blabels  = [b[0] for b in browsers]
        cur_path = self.cfg.config.get("browser_preference", "")
        cur_lbl  = next(
            (l for l, p in self._browser_paths.items()
             if p == cur_path), "Default (system)")
        self._browser = ctk.StringVar(value=cur_lbl)
        ctk.CTkOptionMenu(sf, values=blabels,
                          variable=self._browser, width=220
                          ).pack(padx=12, anchor="w")

    # ── About tab ─────────────────────────────────────────────────

    def _tab_about(self, p):
        logo = load_logo((64, 72))
        if logo:
            ctk.CTkLabel(p, image=logo, text="").pack(pady=(16,4))
        ctk.CTkLabel(p, text=f"{APP_NAME}  v{VERSION}",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=C["amber"]).pack()
        ctk.CTkLabel(p, text=SHOW_NAME,
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=C["text_dim"]).pack(pady=4)

        # Help guide
        help_row = ctk.CTkFrame(p, fg_color="transparent")
        help_row.pack(pady=8)
        ctk.CTkButton(
            help_row, text="📖  Open Help Guide",
            fg_color=C["blue_mid"], width=180,
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            command=lambda: self._open_help(in_app=True)
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            help_row, text="🌐  Open in Browser",
            fg_color=C["surface"], width=150,
            command=lambda: self._open_help(in_app=False)
        ).pack(side="left", padx=4)

        ctk.CTkButton(p, text="🎙  Prankcast Profile",
                      fg_color=C["surface"],
                      command=lambda: webbrowser.open(PRANKCAST_URL)
                      ).pack(pady=4)
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(pady=4)
        ctk.CTkButton(row, text="🔒  Backup Config",
                      fg_color=C["surface"],
                      command=self._backup).pack(side="left", padx=4)
        ctk.CTkButton(row, text="📂  Data Folder",
                      fg_color=C["surface"],
                      command=lambda: os.startfile(str(DATA_DIR))
                      ).pack(side="left", padx=4)

    def _open_help(self, in_app: bool = True):
        from pathlib import Path
        html_path = Path(__file__).parent / "help.html"
        if not html_path.exists():
            messagebox.showerror("Help Not Found",
                f"help.html not found at:\n{html_path}")
            return
        if not in_app:
            webbrowser.open(html_path.as_uri())
            return
        # ── In-app viewer ──────────────────────────────────────
        win = ctk.CTkToplevel(self)
        win.title("IceCat Show Companion — Help Guide")
        win.geometry("1020x720")
        win.configure(fg_color="#ffffff")
        win.grab_set()

        # Toolbar
        tb = ctk.CTkFrame(win, fg_color="#f3f4f6", corner_radius=0)
        tb.pack(fill="x")
        ctk.CTkLabel(tb, text="📖  IceCat Show Companion — Help Guide",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color="#1f2937"
                     ).pack(side="left", padx=12, pady=8)
        ctk.CTkButton(
            tb, text="🌐 Open in Browser",
            fg_color="#1a73e8", hover_color="#1557b0",
            text_color="white", height=30,
            font=ctk.CTkFont("Segoe UI", 11),
            command=lambda: webbrowser.open(html_path.as_uri())
        ).pack(side="right", padx=12, pady=6)

        # Try embedded browser (Windows WebView2 via pywebview)
        loaded = False
        try:
            import webview  # type: ignore
            # pywebview needs its own window — fall through to text viewer
        except ImportError:
            pass

        if not loaded:
            # Fallback: styled scrollable text viewer
            import tkinter as _tk
            import html as _html
            import re as _re
            container = ctk.CTkScrollableFrame(
                win, fg_color="#ffffff")
            container.pack(fill="both", expand=True,
                           padx=0, pady=0)

            raw = html_path.read_text(encoding="utf-8")
            # Strip tags for plain-text display
            text = _re.sub(r"<style[^>]*>.*?</style>",
                           "", raw, flags=_re.S)
            text = _re.sub(r"<script[^>]*>.*?</script>",
                           "", text, flags=_re.S)
            text = _re.sub(r"<br\s*/?>|</p>|</li>|</tr>|</h[1-6]>",
                           "\n", text)
            text = _re.sub(r"<[^>]+>", "", text)
            text = _re.sub(r"\n{3,}", "\n\n", text)
            text = _html.unescape(text).strip()

            txt = _tk.Text(
                container, wrap="word",
                font=("Segoe UI", 12),
                bg="#ffffff", fg="#1f2937",
                relief="flat", bd=0,
                padx=40, pady=20,
                spacing1=2, spacing3=4)
            txt.pack(fill="both", expand=True)
            txt.insert("1.0", text)
            txt.configure(state="disabled")

            ctk.CTkLabel(
                win,
                text="Tip: Click \"Open in Browser\" above for the full "
                     "styled guide with diagrams and navigation.",
                font=ctk.CTkFont("Segoe UI", 10),
                text_color="#6b7280",
                fg_color="#f9fafb"
            ).pack(fill="x", pady=(0, 0))

    def _backup(self):
        p = self.cfg.backup()
        if p:
            messagebox.showinfo("Backup", f"Saved:\n{p}")
        else:
            messagebox.showerror("Error", "Backup failed.")

    # ── Save ──────────────────────────────────────────────────────

    def _save(self):
        c = self.cfg.config

        # Show
        c["show_name"]      = self._show_name.get().strip()
        try:
            c["episode_number"] = int(self._ep_num.get())
        except ValueError:
            pass
        c["title_template"] = self._title_tmpl.get().strip()
        c["prankcast_url"]  = self._pc_url.get().strip()
        tabs = [t.strip() for t in self._note_tabs.get().split(",") if t.strip()]
        if tabs:
            c["note_tabs"] = tabs

        # Audio
        new_out = self._out_dev.get()
        old_out = c.get("audio_output_device", "Default (System)")
        c["audio_output_device"] = new_out
        c["audio_input_device"]  = self._in_dev.get()
        c["recordings_folder"]   = self._rec_folder
        c["recording_format"]    = self._rec_fmt.get()
        try:
            c["fade_duration"] = float(self._fade.get())
        except ValueError:
            pass
        try:
            c["log_audio_min_secs"] = int(self._log_min.get())
        except ValueError:
            pass

        # Soundboard
        try:
            c["pinned_count"] = int(self._pinned.get())
        except ValueError:
            pass
        c["music_bank_name"] = self._music_bank.get()
        groups = []
        for i, entries in self._grp_entries:
            try: rows = max(1, int(entries[1].get()))
            except: rows = 2
            try: cols = max(1, int(entries[2].get()))
            except: cols = 8
            name = entries[0].get().strip() or f"Bank {i+1}"
            existing = (c["soundboard_groups"][i]
                        if i < len(c["soundboard_groups"]) else {})
            groups.append({"name": name, "rows": rows, "cols": cols,
                           "color": existing.get("color","")})
        if groups:
            c["soundboard_groups"] = groups

        # Hotkeys
        for key, entry in self._hk.items():
            c["hotkeys"][key] = entry.get().strip()

        # Websites
        self._save_websites()

        # Mic
        if hasattr(self, "_mic_dev"):
            new_mic = self._mic_dev.get()
            c["mic_input_device"] = new_mic
            # Reinit MicManager with new device
            try:
                self.app.mic.reinit(new_mic)
            except Exception:
                pass
        if hasattr(self, "_duck_level"):
            c["mic_duck_level"] = round(self._duck_level.get(), 2)

        # Visual
        new_theme = self._theme.get()
        old_theme = c.get("color_theme", "Default Blue")
        theme_changed = new_theme != old_theme
        if theme_changed:
            c["color_theme"] = new_theme
            if self.cfg.has_any_custom_colors():
                keep = messagebox.askyesno(
                    "Custom Button Colours",
                    "Keep your custom button colours with the new theme?\n\n"
                    "• Yes — keep\n• No — reset to theme defaults")
                if not keep:
                    self.cfg.clear_custom_colors()
        try:
            c["font_size"] = int(self._font_size.get())
        except ValueError:
            pass
        c["opacity"] = self._opacity.get()

        # Integrations
        c["discord_enabled"] = self._discord_en.get()
        c["discord_webhook"] = self._discord_url.get().strip()
        c["discord_message"] = self._discord_msg.get().strip()
        lbl = self._browser.get()
        c["browser_preference"] = self._browser_paths.get(lbl, "")

        self.cfg.save()

        # Reinit mixer if output device changed
        if new_out != old_out:
            self.app.audio.reinit(
                "" if new_out == "Default (System)" else new_out)

        # Apply recordings folder
        if hasattr(self.app, "recorder"):
            self.app.recorder.set_recordings_folder(self._rec_folder)

        self.app.register_hotkeys()
        self.app.apply_bg_color()
        try:
            self.app.soundboard.full_refresh()
        except Exception:
            pass

        self.destroy()

        if theme_changed:
            if messagebox.askyesno(
                    "Restart Required",
                    f"Theme changed to '{new_theme}'.\nRestart now?"):
                os.execv(sys.executable, [sys.executable] + sys.argv)
