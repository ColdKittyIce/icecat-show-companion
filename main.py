"""
main.py — IceCat Show Companion v3.0
Application entry point and main window orchestrator.
"""

import os, sys, time, logging, threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── CustomTkinter appearance ──────────────────────────────────────
import customtkinter as ctk
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

import tkinter as tk
from tkinter import messagebox

# ── Project imports ───────────────────────────────────────────────
from config import (
    ConfigManager, C, VERSION, APP_NAME,
    LOG_DIR, DATA_DIR, STREAM_HOST, STREAM_PORT
)
from audio   import AudioManager, RecorderManager, MicManager
from network import NetworkMonitor, DiscordWebhook

# ── DnD ───────────────────────────────────────────────────────────
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

# ── Hotkeys ───────────────────────────────────────────────────────
try:
    import keyboard as kb
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False


def _setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fh = RotatingFileHandler(
        LOG_DIR / "icecat.log",
        maxBytes=2_000_000, backupCount=3,
        encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s"))
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    root.addHandler(fh)
    root.addHandler(ch)


log = logging.getLogger("icecat.main")


# ═══════════════════════════════════════════════════════════════
# APPLICATION
# ═══════════════════════════════════════════════════════════════

class IceCatApp(ctk.CTk if not HAS_DND else TkinterDnD.Tk):

    def __init__(self):
        super().__init__()

        # ── Config + theme ────────────────────────────────────────
        self.cfg      = ConfigManager()
        self.cfg.startup_backup()   # auto-backup on every launch (keeps last 5)
        self.cfg.apply_theme()

        # ── Audio ─────────────────────────────────────────────────
        out_dev = self.cfg.config.get("audio_output_device","")
        if out_dev == "Default (System)": out_dev = ""
        self.audio    = AudioManager()
        if out_dev:
            self.audio.reinit(out_dev)
        self.recorder = RecorderManager(
            self.cfg.config.get(
                "recordings_folder",
                str(DATA_DIR / "recordings")))
        self.mic = MicManager(self.cfg)

        # ── Network ───────────────────────────────────────────────
        self.net     = NetworkMonitor(STREAM_HOST, STREAM_PORT)
        self.discord = DiscordWebhook()

        # ── State ─────────────────────────────────────────────────
        self._live         = False
        self._live_start   = None
        self._live_h = self._live_m = self._live_s = 0
        self._cd_running   = False
        self._cd_total     = 0
        self._cd_end       = 0.0
        self._mini_mode    = False
        self._mini_win     = None
        self._undo_stack:  list = []

        # ── Window ────────────────────────────────────────────────
        w = self.cfg.config.get("window_width",  1600)
        h = self.cfg.config.get("window_height",  960)
        self.title(f"{APP_NAME}  v{VERSION}")
        self.geometry(f"{w}x{h}")
        self.minsize(1100, 700)
        self.configure(bg=C["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        op = self.cfg.config.get("opacity", 1.0)
        if op < 1.0:
            self.attributes("-alpha", op)

        # Store app ref on root for child widgets
        self._app = self

        # ── Build UI ──────────────────────────────────────────────
        self._build_ui()

        # ── DnD root handler ─────────────────────────────────────
        if HAS_DND:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind("<<Drop>>", self._on_dnd_drop)
            except Exception as e:
                log.warning(f"DnD register: {e}")

        # ── Hotkeys ───────────────────────────────────────────────
        self.register_hotkeys()

        # ── Network monitor ───────────────────────────────────────
        self.net.start(on_change=self._on_net_change)

        # ── Timers ───────────────────────────────────────────────
        self.after(500,  self._tick_live)
        self.after(750,  self._tick_countdown)
        self.after(5000, self._autosave_config)

        log.info(f"{APP_NAME} v{VERSION} started")

    # ── UI Build ──────────────────────────────────────────────────

    def _build_ui(self):
        from ui_header      import HeaderFrame, MenuBarFrame
        from ui_soundboard  import SoundboardFrame
        from ui_right_panel import RightPanel
        from ui_bottom      import BottomStrip

        # Menu bar — sits just below the title bar
        self.menu_bar = MenuBarFrame(self, self)
        self.menu_bar.pack(fill="x", side="top")

        # Header — top, full width
        self.header = HeaderFrame(self, self)
        self.header.pack(fill="x", side="top")

        # Thin separator
        tk.Frame(self, bg=C["border"], height=1).pack(
            fill="x", side="top")

        # Bottom strip — bottom, full width
        self.bottom = BottomStrip(
            self, self.cfg, self.audio,
            get_elapsed=self._get_elapsed_str,
            get_is_live=lambda: self._live)
        self.bottom.pack(fill="x", side="bottom")

        tk.Frame(self, bg=C["border"], height=1).pack(
            fill="x", side="bottom")

        # Middle row: soundboard (left) + right panel (right)
        mid = tk.Frame(self, bg=C["bg"])
        mid.pack(fill="both", expand=True, side="top")

        self.right_panel = RightPanel(
            mid, self.cfg, self.audio,
            get_elapsed=self._get_elapsed_str,
            get_is_live=lambda: self._live)
        self.right_panel.pack(side="right", fill="y")

        tk.Frame(mid, bg=C["border"], width=1).pack(
            side="right", fill="y")

        self.soundboard = SoundboardFrame(
            mid, self.cfg, self.audio,
            session_log=self.right_panel.session_log)
        self.soundboard.pack(
            side="left", fill="both", expand=True)

        # Wire session log into soundboard queue
        self.soundboard.queue.session_log = \
            self.right_panel.session_log

        # Wire session log into bottom notes
        self.bottom.session_log = \
            self.right_panel.session_log
        self.bottom.notes.session_log = \
            self.right_panel.session_log

        # Keep a top-level ref so DnD can find the queue
        self.queue_panel = self.soundboard.queue

    # ── Live / broadcast ──────────────────────────────────────────

    def manual_go_live(self):
        if self._live:
            self._end_live()
        else:
            self._start_live()

    def _start_live(self):
        self._live       = True
        self._live_start = time.monotonic()
        self._live_h = self._live_m = self._live_s = 0
        self.header.set_on_air(True)
        self.right_panel.session_log.log_live_start()

        # Discord notification
        if self.cfg.config.get("discord_enabled"):
            self.discord.fire(
                self.cfg.config.get("discord_webhook",""),
                self.cfg.config.get("discord_message",""),
                self.cfg.config.get("prankcast_url",""))
        log.info("LIVE started")

    def _end_live(self):
        self._live = False
        dur_str    = (f"{self._live_h:02d}:"
                      f"{self._live_m:02d}:"
                      f"{self._live_s:02d}")
        self.header.set_on_air(False)
        self.right_panel.session_log.log_live_end(dur_str)
        self._live_h = self._live_m = self._live_s = 0
        self.header.update_live(0, 0, 0)
        log.info(f"LIVE ended — {dur_str}")
        self._show_post_dialog(dur_str)

    def _tick_live(self):
        if self._live and self._live_start:
            elapsed      = time.monotonic() - self._live_start
            self._live_h = int(elapsed // 3600)
            self._live_m = int((elapsed % 3600) // 60)
            self._live_s = int(elapsed % 60)
            self.header.update_live(
                self._live_h, self._live_m, self._live_s)
        self.after(500, self._tick_live)

    def _get_elapsed_str(self) -> str:
        if not self._live:
            return ""
        return (f"{self._live_h:02d}:"
                f"{self._live_m:02d}:"
                f"{self._live_s:02d}")

    # ── Post-show dialog ──────────────────────────────────────────

    def _show_post_dialog(self, dur_str: str):
        from ui_dialogs import PostShowDialog
        summary = self.right_panel.session_log.get_summary_text()
        # Small delay so the header animation settles first
        self.after(400, lambda: PostShowDialog(
            self, self.cfg,
            duration_str=dur_str,
            session_summary=summary))

    # ── Panic ─────────────────────────────────────────────────────

    def panic(self):
        self.audio.stop_all()
        self.soundboard.stop_all()
        if self.recorder.state == "playing":
            self.recorder.stop_playback()
        self.header.flash_red()
        self.right_panel.session_log.log_event("🚨 PANIC")
        log.warning("PANIC fired")

    # ── Mute ─────────────────────────────────────────────────────

    def toggle_mute(self):
        muted = self.audio.toggle_mute()
        self.header.set_mute_state(muted)
        if self._mini_win:
            try:
                self._mini_win.update_mute(muted)
            except Exception:
                pass

    # ── Volume ────────────────────────────────────────────────────

    def set_master_volume(self, v):
        self.audio.set_master_volume(float(v))

    # ── Countdown ────────────────────────────────────────────────

    def start_countdown(self):
        raw = self.header.cd_entry.get().strip()
        parts = raw.split(":")
        try:
            if len(parts) == 2:
                mm, ss = int(parts[0]), int(parts[1])
            elif len(parts) == 1:
                mm, ss = int(parts[0]), 0
            else:
                return
        except ValueError:
            return
        total = mm * 60 + ss
        if total <= 0:
            return
        self._cd_total   = total
        self._cd_end     = time.monotonic() + total
        self._cd_running = True
        self.right_panel.session_log.log_countdown_start(mm, ss)

    def quick_countdown(self, minutes: int):
        self._cd_total   = minutes * 60
        self._cd_end     = time.monotonic() + self._cd_total
        self._cd_running = True

    def _tick_countdown(self):
        if self._cd_running:
            remaining = self._cd_end - time.monotonic()
            if remaining <= 0:
                self._cd_running = False
                self.header.update_countdown(0, 0, urgent=False)
                self.right_panel.session_log.log_countdown_end()
            else:
                mm = int(remaining // 60)
                ss = int(remaining % 60)
                self.header.update_countdown(
                    mm, ss, urgent=remaining <= 30)
        self.after(500, self._tick_countdown)

    # ── Mini mode ─────────────────────────────────────────────────

    def toggle_mini_mode(self):
        if self._mini_mode:
            self._exit_mini()
        else:
            self._enter_mini()

    def _enter_mini(self):
        from ui_header import MiniModeWindow
        self._mini_mode = True
        self.withdraw()
        self._mini_win  = MiniModeWindow(self, self)

    def _exit_mini(self):
        self._mini_mode = False
        if self._mini_win:
            try:
                self._mini_win.destroy()
            except Exception:
                pass
            self._mini_win = None
        self.deiconify()
        self.lift()

    # ── DnD ───────────────────────────────────────────────────────

    def _on_dnd_drop(self, e):
        raw   = e.data
        paths = self.tk.splitlist(raw)
        x, y  = e.x_root, e.y_root
        w     = self.winfo_containing(x, y)

        for path in paths:
            path = path.strip().strip("{}")
            if not path:
                continue

            # Route to soundboard button
            if w and hasattr(w, "handle_drop"):
                w.handle_drop(path)
                continue

            # Walk up widget tree
            parent = w
            while parent:
                if hasattr(parent, "route_drop"):
                    parent.route_drop(w, path)
                    break
                try:
                    parent = parent.master
                except Exception:
                    break
            else:
                # Default: add to queue
                self.soundboard.queue.add_file(path)

    # ── Network callback ──────────────────────────────────────────

    def _on_net_change(self, connected: bool):
        pass  # Could add a status indicator in future

    # ── Hotkeys ───────────────────────────────────────────────────

    def register_hotkeys(self):
        if not HAS_KEYBOARD:
            return
        try:
            kb.unhook_all()
        except Exception:
            pass
        hk = self.cfg.config.get("hotkeys", {})
        bindings = {
            "go_live":     self.manual_go_live,
            "panic":       self.panic,
            "mute":        self.toggle_mute,
            "timestamp":   self._hotkey_timestamp,
            "gold_moment": self._hotkey_gold,
            "mini_mode":   self.toggle_mini_mode,
        }
        for key, fn in bindings.items():
            combo = hk.get(key, "")
            if combo:
                try:
                    kb.add_hotkey(combo, fn, suppress=False)
                except Exception as e:
                    log.warning(f"Hotkey '{combo}': {e}")

    def _hotkey_timestamp(self):
        try:
            self.bottom.notes._insert_timestamp()
        except Exception:
            pass

    def _hotkey_gold(self):
        try:
            self.bottom.notes._insert_gold()
        except Exception:
            pass

    # ── Window opacity ────────────────────────────────────────────

    def set_opacity(self, v: float):
        self.attributes("-alpha", max(0.2, min(1.0, float(v))))

    def apply_bg_color(self):
        self.configure(bg=C["bg"])

    # ── Config autosave ───────────────────────────────────────────

    def _autosave_config(self):
        try:
            self.bottom.notes.save_all()
            self.cfg.config["window_width"]  = self.winfo_width()
            self.cfg.config["window_height"] = self.winfo_height()
            self.cfg.save()
        except Exception as e:
            log.warning(f"Autosave: {e}")
        self.after(5 * 60 * 1000, self._autosave_config)

    # ── Undo ─────────────────────────────────────────────────────

    def undo_last(self):
        if not self._undo_stack:
            return
        source, idx, slot = self._undo_stack.pop()
        self.cfg.config[source][idx] = slot
        self.cfg.save()
        try:
            self.soundboard.full_refresh()
        except Exception:
            pass

    # ── Settings ─────────────────────────────────────────────────

    def open_settings(self, tab: str = None):
        from ui_dialogs import SettingsWindow
        sw = SettingsWindow(self, self.cfg, self)
        if tab:
            try:
                sw._tabs.set(tab)
            except Exception:
                pass

    # ── Close ────────────────────────────────────────────────────

    def _on_close(self):
        if self._live:
            if not messagebox.askyesno(
                    "Still Live!",
                    "You are currently LIVE.\n\n"
                    "End the show and exit?",
                    icon="warning"):
                return
            self._end_live()

        try:
            self.bottom.notes.save_all()
        except Exception:
            pass
        self.cfg.config["window_width"]  = self.winfo_width()
        self.cfg.config["window_height"] = self.winfo_height()
        self.cfg.save()

        if HAS_KEYBOARD:
            try:
                kb.unhook_all()
            except Exception:
                pass
        self.net.stop()

        # Always restore mic to unmuted on exit so it isn't left hard-muted
        try:
            self.mic.set_mute(False)
        except Exception:
            pass

        self.destroy()


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    _setup_logging()
    log.info(f"Starting {APP_NAME} v{VERSION}")

    try:
        app = IceCatApp()

        # Ctrl+Z undo
        app.bind("<Control-z>", lambda e: app.undo_last())
        # Ctrl+, settings
        app.bind("<Control-comma>",
                 lambda e: app.open_settings())
        # Ctrl+Shift+Z mini mode (keyboard fallback)
        app.bind("<Control-Shift-Z>",
                 lambda e: app.toggle_mini_mode())

        app.mainloop()
    except Exception as e:
        log.critical(f"Fatal error: {e}", exc_info=True)
        try:
            messagebox.showerror(
                "Fatal Error",
                f"{APP_NAME} encountered a fatal error:\n\n{e}\n\n"
                f"Check logs at:\n{LOG_DIR}")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
