"""
ui_bottom.py — IceCat Show Companion v3.0
BottomStrip   : full-width bottom bar
QueuePanel    : drag-and-drop music queue with transport
NowPlayingBar : current track + progress + waveform VU
"""

import os, time, tkinter as tk, tkinterdnd2 as dnd, logging
import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path

from config import C, lighten
from audio  import AudioManager, CH_QUEUE

log = logging.getLogger("icecat.bottom")

try:
    from tkinterdnd2 import DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False


# ═══════════════════════════════════════════════════════════════
# HORIZONTAL VU  (now-playing bar)
# ═══════════════════════════════════════════════════════════════

class HorizontalVU(tk.Canvas):
    BARS    = 24
    H       = 6
    ATTACK  = 0.88
    DECAY   = 0.20
    TICK_MS = 25

    def __init__(self, parent, level_fn):
        super().__init__(parent, height=self.H,
                         bg=C["bg"], highlightthickness=0)
        self._fn    = level_fn
        self._level = 0.0
        self._rects = []
        self.bind("<Configure>", self._on_resize)
        self._tick()

    def _on_resize(self, e=None):
        self.delete("all")
        self._rects.clear()
        w = self.winfo_width()
        if w < 10:
            return
        bw = w / self.BARS
        colours = ([C["green"]] * int(self.BARS * 0.6)
                   + [C["amber"]] * int(self.BARS * 0.25)
                   + [C["red"]]  * (self.BARS - int(self.BARS * 0.85)))
        for i in range(self.BARS):
            x0 = int(i * bw) + 1
            x1 = int((i + 1) * bw) - 1
            r  = self.create_rectangle(
                x0, 0, x1, self.H,
                fill=C["surface"], outline="")
            self._rects.append((r, colours[i]))

    def _tick(self):
        try:
            target = float(self._fn())
        except Exception:
            target = 0.0
        if target > self._level:
            self._level = self._level * (1-self.ATTACK) + target * self.ATTACK
        else:
            self._level = max(0.0, self._level - self.DECAY)
        active = int(self._level * self.BARS)
        for i, (r, col) in enumerate(self._rects):
            self.itemconfig(r, fill=col if i < active else C["surface"])
        if self.winfo_exists():
            self.after(self.TICK_MS, self._tick)


# ═══════════════════════════════════════════════════════════════
# NOW PLAYING BAR
# ═══════════════════════════════════════════════════════════════

class NowPlayingBar(ctk.CTkFrame):
    """
    Right side of the bottom strip.
    Shows current track, progress bar, elapsed/remaining, VU.
    """

    def __init__(self, parent, audio: AudioManager):
        super().__init__(parent, fg_color=C["surface"],
                         corner_radius=0)
        self.audio    = audio
        self._last_ch = None
        self._build()
        self._tick()

    def _build(self):
        # Label row
        top = tk.Frame(self, bg=C["surface"])
        top.pack(fill="x", padx=6, pady=(4, 0))

        tk.Label(top, text="NOW PLAYING",
                 bg=C["surface"], fg=C["text_dim"],
                 font=("Segoe UI", 7, "bold")).pack(side="left")

        self._np_lbl = tk.Label(
            top, text="—", bg=C["surface"],
            fg=C["text"], font=("Segoe UI", 10, "bold"),
            anchor="w")
        self._np_lbl.pack(side="left", padx=(8,0))

        self._time_lbl = tk.Label(
            top, text="", bg=C["surface"],
            fg=C["text_dim"], font=("Consolas", 9))
        self._time_lbl.pack(side="right")

        # VU
        self._vu = HorizontalVU(
            self, lambda: self.audio.get_vu_level())
        self._vu.pack(fill="x", padx=4, pady=(2,0))

        # Progress bar
        self._prog_outer = tk.Frame(
            self, bg=C["surface"], height=6)
        self._prog_outer.pack(fill="x", padx=4, pady=(2, 4))
        self._prog_outer.pack_propagate(False)

        self._prog_inner = tk.Frame(
            self._prog_outer, bg=C["blue_mid"], height=6)
        self._prog_inner.place(x=0, y=0, width=0, relheight=1)

        # Bank label
        self._bank_lbl = tk.Label(
            self, text="", bg=C["surface"],
            fg=C["text_dim"], font=("Segoe UI", 8))
        self._bank_lbl.pack(anchor="w", padx=6)

    def _tick(self):
        try:
            np = self.audio.get_now_playing()
            if np:
                ch, info = np
                label    = info.get("label", "")
                bank     = info.get("bank", "")
                start    = info.get("start", time.monotonic())
                dur      = info.get("duration", 0.0)
                elapsed  = time.monotonic() - start

                self._np_lbl.configure(text=label[:36])
                self._bank_lbl.configure(text=bank)

                if dur > 0:
                    frac  = min(1.0, elapsed / dur)
                    rem   = max(0.0, dur - elapsed)
                    r_s   = int(rem)
                    e_s   = int(elapsed)
                    self._time_lbl.configure(
                        text=f"{e_s//60}:{e_s%60:02d} / "
                             f"-{r_s//60}:{r_s%60:02d}")
                    # Update progress bar width
                    self._prog_outer.update_idletasks()
                    w = self._prog_outer.winfo_width()
                    self._prog_inner.place(
                        x=0, y=0, width=int(w*frac), relheight=1)
                    # Colour: amber when < 15s left
                    self._prog_inner.configure(
                        bg=C["amber"] if rem < 15 else C["blue_mid"])
                else:
                    self._time_lbl.configure(text="")
                    self._prog_inner.place(
                        x=0, y=0, width=0, relheight=1)
            else:
                self._np_lbl.configure(text="—")
                self._time_lbl.configure(text="")
                self._bank_lbl.configure(text="")
                self._prog_inner.place(x=0, y=0, width=0, relheight=1)
        except Exception:
            pass
        self.after(500, self._tick)


# ═══════════════════════════════════════════════════════════════
# BOTTOM STRIP  — notes panel (queue is beside soundboard)
# ═══════════════════════════════════════════════════════════════

class BottomStrip(ctk.CTkFrame):
    HEIGHT = 220

    def __init__(self, parent, cfg, audio: AudioManager,
                 session_log=None, get_elapsed=None, get_is_live=None):
        super().__init__(parent, fg_color=C["bg"],
                         corner_radius=0, height=self.HEIGHT)
        self.cfg         = cfg
        self.audio       = audio
        self.session_log = session_log
        self.get_elapsed = get_elapsed or (lambda: "")
        self.get_is_live = get_is_live or (lambda: False)
        self.pack_propagate(False)
        self._build()

    def _build(self):
        from ui_right_panel import NotesSection, SnippetsSection

        # Quick Copy — far right, fixed width
        self.snippets = SnippetsSection(self, self.cfg)
        self.snippets.pack(side="right", fill="y")

        tk.Frame(self, bg=C["border"], width=1).pack(side="right", fill="y")

        # Now Playing — right of notes, fixed width
        self.now_playing = NowPlayingBar(self, self.audio)
        self.now_playing.configure(width=300)
        self.now_playing.pack(side="right", fill="y", padx=(3, 3))

        tk.Frame(self, bg=C["border"], width=1).pack(side="right", fill="y")

        # Notes — left, fills remaining space
        self.notes = NotesSection(
            self, self.cfg,
            get_elapsed=self.get_elapsed,
            get_is_live=self.get_is_live,
            session_log=self.session_log)
        self.notes.pack(side="left", fill="both", expand=True)
