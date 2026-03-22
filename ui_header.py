"""
ui_header.py — IceCat Show Companion v3.0
HeaderFrame   : two-zone broadcast console header
MiniModeWindow: always-on-top compact strip
VU meters     : vertical (header) + horizontal (now-playing)
"""

import time, tkinter as tk, threading, logging
import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path

from config import C, VERSION, APP_NAME, lighten
from audio  import AudioManager, RecorderManager, CH_RECORDER, MicManager

log = logging.getLogger("icecat.header")


# ═══════════════════════════════════════════════════════════════
# VERTICAL VU METER
# ═══════════════════════════════════════════════════════════════

class VerticalVU(tk.Canvas):
    """Snappy vertical VU — bars fill bottom to top."""
    BARS         = 18
    W            = 12
    H            = 90
    ATTACK       = 0.95
    DECAY        = 0.18
    PEAK_HOLD_MS = 500
    TICK_MS      = 22

    def __init__(self, parent, level_fn):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=C["bg2"], highlightthickness=0)
        self._fn     = level_fn
        self._level  = 0.0
        self._peak   = 0
        self._ptimer = 0
        self._rects  = []
        self._prect  = None
        self._build()
        self._tick()

    def _build(self):
        bh = self.H // self.BARS - 1
        # top bars = red, mid = amber, low = green
        colours = ([C["red"]] * 2 + [C["amber_hi"]] * 3
                   + [C["green"]] * (self.BARS - 5))
        for i in range(self.BARS):
            y0 = i * (bh + 1)
            r  = self.create_rectangle(
                1, y0, self.W-1, y0+bh,
                fill=C["surface"], outline="")
            self._rects.append((r, colours[i]))
        self._prect = self.create_rectangle(
            0, 0, 0, 0, fill=C["amber_hi"], outline="")

    def _tick(self):
        try:
            target = float(self._fn())
        except Exception:
            target = 0.0
        bh = self.H // self.BARS - 1

        if target > self._level:
            self._level = (self._level * (1 - self.ATTACK)
                           + target * self.ATTACK)
        else:
            self._level = max(0.0, self._level - self.DECAY)

        active = int(self._level * self.BARS)
        for i, (r, col) in enumerate(self._rects):
            self.itemconfig(r, fill=col if (self.BARS - i) <= active
                            else C["surface"])

        if active >= self._peak:
            self._peak   = active
            self._ptimer = int(self.PEAK_HOLD_MS / self.TICK_MS)
        else:
            if self._ptimer > 0:
                self._ptimer -= 1
            else:
                self._peak = max(0, self._peak - 1)

        if self._peak > 0:
            row = self.BARS - self._peak
            py  = row * (bh + 1)
            self.coords(self._prect, 1, py, self.W-1, py+bh)
            self.itemconfig(self._prect,
                            fill=(C["red"] if self._peak >= self.BARS-1
                                  else C["amber_hi"]))
        else:
            self.coords(self._prect, 0, 0, 0, 0)

        if self.winfo_exists():
            self.after(self.TICK_MS, self._tick)


# ═══════════════════════════════════════════════════════════════
# TAPE RECORDER SECTION
# ═══════════════════════════════════════════════════════════════

class TapeRecorderSection(ctk.CTkFrame):
    """
    Right zone of the header.
    Row 0: label | timer | status | recordings ▾
    Row 1: ⏺ REC  ▶ PLAY  ⏹ STOP  🔁 LOOP  | 📤 SaveAs  🗑 Del
    Row 2: FX buttons (toggle + right-click for settings)
    Row 3: Active FX sliders (inline, visible only when FX active)
    VU meter on left edge.
    """

    EFFECTS = [
        ("chipmunk", "🐿", "Chipmunk"),
        ("deep",     "🐋", "Deep"),
        ("reverb",   "🌊", "Reverb"),
        ("echo",     "🔊", "Echo"),
        ("lofi",     "📞", "Lo-Fi"),
        ("reverse",  "⏪", "Reverse"),
    ]
    PITCH_EXCLUSIVE = {"chipmunk", "deep"}

    FX_PARAMS = {
        "chipmunk": [("semitones","Pitch",2.0,12.0,6.0,0.5),
                     ("speed","Speed",1.1,2.0,1.35,0.05)],
        "deep":     [("semitones","Pitch",-12.0,-2.0,-6.0,0.5),
                     ("speed","Speed",0.4,0.9,0.72,0.05)],
        "reverb":   [("room_size","Room",0.1,1.0,0.75,0.05),
                     ("wet","Wet",0.1,0.9,0.5,0.05)],
        "echo":     [("delay","Delay",0.1,1.0,0.4,0.05),
                     ("feedback","Feed",0.1,0.9,0.45,0.05),
                     ("mix","Mix",0.1,0.9,0.5,0.05)],
        "lofi":     [("lowpass","LPF",500.0,6000.0,3200.0,100.0),
                     ("highpass","HPF",100.0,1500.0,500.0,50.0)],
        "reverse":  [],
    }

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=C["surface"],
                         corner_radius=10)
        self.app      = app
        self.recorder: RecorderManager = app.recorder
        self._loop    = False
        self._cur     = None      # currently loaded file path
        self._active_fx: set = set()
        self._fx_btns: dict  = {}
        self._popup   = None
        self._active_fx_key = None   # which fx sliders are shown
        self._fx_slider_vars: dict = {}
        self._build()
        self._tick()

    def _build(self):
        S9  = ctk.CTkFont("Segoe UI", 9)
        S10 = ctk.CTkFont("Segoe UI", 10)
        S11 = ctk.CTkFont("Segoe UI", 11)
        C10 = ctk.CTkFont("Courier New", 11, "bold")

        # ── Row 0: info bar ───────────────────────────────────────
        r0 = ctk.CTkFrame(self, fg_color="transparent")
        r0.pack(fill="x", padx=6, pady=(6, 0))

        ctk.CTkLabel(r0, text="⏺ RECORDER",
                     font=ctk.CTkFont("Segoe UI", 8, "bold"),
                     text_color=C["text_dim"]).pack(side="left")

        self._timer = ctk.CTkLabel(
            r0, text="00:00:00", font=C10,
            text_color=C["text"])
        self._timer.pack(side="left", padx=(8, 0))

        self._status = ctk.CTkLabel(
            r0, text="IDLE", font=S9,
            text_color=C["text_dim"])
        self._status.pack(side="left", padx=(6, 0))

        # Open recordings folder button
        ctk.CTkButton(
            r0, text="📂", width=26, height=18,
            corner_radius=4, fg_color=C["btn"],
            hover_color=C["btn_hover"], font=S9,
            command=self._open_recordings_folder
        ).pack(side="right")

        # ── Row 1: transport ──────────────────────────────────────
        r1 = ctk.CTkFrame(self, fg_color="transparent")
        r1.pack(fill="x", padx=6, pady=(3, 0))

        BTN = dict(width=36, height=22, corner_radius=5, font=S11)

        self._rec_btn = ctk.CTkButton(
            r1, text="⏺", fg_color="#6a1a1a",
            hover_color="#992222",
            command=self._on_rec, **BTN)
        self._rec_btn.pack(side="left", padx=(0,2))

        self._play_btn = ctk.CTkButton(
            r1, text="▶", fg_color=C["green_dim"],
            hover_color=C["green"],
            command=self._on_play, **BTN)
        self._play_btn.pack(side="left", padx=2)

        self._stop_btn = ctk.CTkButton(
            r1, text="⏹", fg_color=C["btn"],
            hover_color=C["btn_hover"],
            command=self._on_stop, **BTN)
        self._stop_btn.pack(side="left", padx=2)

        self._loop_btn = ctk.CTkButton(
            r1, text="🔁", fg_color=C["btn"],
            hover_color=C["btn_hover"],
            command=self._on_loop, **BTN)
        self._loop_btn.pack(side="left", padx=2)

        ctk.CTkFrame(r1, width=1, height=18,
                     fg_color=C["border"]).pack(side="left", padx=4)

        ctk.CTkButton(r1, text="📤",
                      fg_color=C["blue"], hover_color=C["blue_mid"],
                      command=self._on_save_as, **BTN
                      ).pack(side="left", padx=2)

        ctk.CTkButton(r1, text="🗑",
                      fg_color=C["btn"], hover_color=C["red_dim"],
                      command=self._on_delete, **BTN
                      ).pack(side="left", padx=2)

        # ── Row 2: FX buttons ─────────────────────────────────────
        r2 = ctk.CTkFrame(self, fg_color="transparent")
        r2.pack(fill="x", padx=6, pady=(3, 0))

        FXBTN = dict(width=36, height=16, corner_radius=4,
                     font=ctk.CTkFont("Segoe UI", 10))

        for key, emoji, tip in self.EFFECTS:
            b = ctk.CTkButton(
                r2, text=emoji,
                fg_color=C["btn"], hover_color=C["btn_hover"],
                text_color=C["text"],
                command=lambda k=key: self._toggle_fx(k),
                **FXBTN)
            b.pack(side="left", padx=1)
            b.bind("<Button-3>",
                   lambda e, k=key: self._open_fx_settings(e, k))
            self._fx_btns[key] = b

        # (FX settings via right-click popup — see _open_fx_settings)

        # DnD — drop audio file onto recorder to load it
        try:
            from tkinterdnd2 import DND_FILES
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_file_drop)
        except Exception:
            pass

    # ── FX toggle & sliders ───────────────────────────────────────

    def _open_recordings_folder(self):
        import os
        folder = self.app.cfg.config.get(
            "recordings_folder", str(self.recorder.recording_dir))
        try:
            if os.path.isdir(folder):
                os.startfile(folder)
        except Exception as e:
            log.warning(f"Open recordings folder: {e}")

    def _on_file_drop(self, event):
        """Load a dropped audio file into the recorder player."""
        raw   = event.data
        paths = self.tk.splitlist(raw)
        if not paths:
            return
        path = paths[0].strip().strip("{}")
        if Path(path).suffix.lower() in {".mp3",".wav",".ogg",".flac",".m4a"}:
            self._load_file(path)

    def _toggle_fx(self, key: str):
        if key in self._active_fx:
            self._active_fx.discard(key)
        else:
            if key in self.PITCH_EXCLUSIVE:
                for ex in self.PITCH_EXCLUSIVE:
                    self._active_fx.discard(ex)
                    self._fx_btns[ex].configure(
                        fg_color=C["btn"], text_color=C["text"])
            self._active_fx.add(key)

        on = key in self._active_fx
        self._fx_btns[key].configure(
            fg_color=C["amber"] if on else C["btn"],
            text_color=C["bg"] if on else C["text"])

    def _open_fx_settings(self, event, key: str):
        """Right-click popup with sliders for the effect's parameters."""
        params = self.FX_PARAMS.get(key, [])
        if not params:
            return

        if hasattr(self, "_fx_popup") and self._fx_popup and                 self._fx_popup.winfo_exists():
            self._fx_popup.destroy()

        fx_cfg   = self.app.cfg.config.get("recorder_fx_settings", {})
        cur_vals = fx_cfg.get(key, {})
        h = 60 + len(params) * 52
        w = 260
        self.update_idletasks()
        px = event.x_root
        py = event.y_root + 10

        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=C["elevated"])
        popup.geometry(f"{w}x{h}+{px}+{py}")
        popup.lift()
        self._fx_popup = popup

        lbl_map = {k: lbl for k, _, lbl in self.EFFECTS}
        tk.Label(popup,
                 text=f"  ⚙ {lbl_map.get(key, key).upper()} Settings",
                 bg=C["elevated"], fg=C["amber"],
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(
                     fill="x", padx=4, pady=(6, 2))
        tk.Frame(popup, bg=C["border"], height=1).pack(fill="x", padx=4)

        for param_key, param_lbl, p_min, p_max, p_def, p_res in params:
            cur = cur_vals.get(param_key, p_def)
            row = tk.Frame(popup, bg=C["elevated"])
            row.pack(fill="x", padx=8, pady=(6, 0))
            tk.Label(row, text=param_lbl, bg=C["elevated"], fg=C["text_dim"],
                     font=("Segoe UI", 8), anchor="w").pack(side="top", fill="x")
            val_var = tk.DoubleVar(value=cur)
            val_lbl = tk.Label(row, text=f"{cur:.2f}",
                               bg=C["elevated"], fg=C["text"],
                               font=("Courier New", 9), width=6)
            val_lbl.pack(side="right")

            def _on_slide(v, vv=val_var, vl=val_lbl,
                          pk=param_key, ek=key, res=p_res):
                snapped = round(float(v) / res) * res
                vv.set(snapped)
                vl.configure(text=f"{snapped:.2f}")
                self.app.cfg.config.setdefault("recorder_fx_settings", {})                     .setdefault(ek, {})[pk] = snapped
                self.app.cfg.save()

            import customtkinter as _ctk
            _ctk.CTkSlider(row, from_=p_min, to=p_max,
                           variable=val_var, command=_on_slide,
                           width=160, height=14).pack(
                               side="left", fill="x", expand=True)

        # Close on click outside
        popup.bind("<FocusOut>", lambda e: popup.destroy()
                   if popup.winfo_exists() else None)
        popup.focus_set()


    def _on_rec(self):
        if self.recorder.state == "recording":
            self._do_stop_save()
        else:
            dev = self.app.cfg.config.get("audio_input_device","")
            if dev == "Default (System)":
                dev = ""
            ok = self.recorder.start_recording(input_device=dev)
            if ok:
                self._rec_btn.configure(fg_color=C["red"])
                self._set_status("REC", C["red"])
            else:
                messagebox.showerror(
                    "Recorder Error",
                    "Could not start recording.\n\n"
                    "Settings → Audio → Input Device\n"
                    "Choose Voicemeeter Output or Stereo Mix.")

    def _on_play(self):
        if not self._cur:
            self._toggle_popup()
            return
        if self.recorder.state == "playing":
            self.recorder.stop_playback()
        if self._active_fx:
            self._set_status("PROCESSING...", C["amber"])
            self._play_btn.configure(state="disabled")
            fx_cfg = self.app.cfg.config.get("recorder_fx_settings",{})
            self.recorder.apply_effects_and_play(
                self._cur, set(self._active_fx), fx_cfg,
                loop=self._loop,
                on_done=self._after_play)
        else:
            ok = self.recorder.load_and_play(self._cur, loop=self._loop)
            if ok:
                self._set_status("PLAYING", C["green"])

    def _after_play(self, ok: bool):
        self.after(0, lambda: self._play_btn.configure(state="normal"))
        if ok:
            self.after(0, lambda: self._set_status("PLAYING", C["green"]))
        else:
            self.after(0, lambda: self._set_status("IDLE", C["text_dim"]))

    def _on_stop(self):
        if self.recorder.state == "recording":
            self._do_stop_save()
        elif self.recorder.state == "playing":
            self.recorder.stop_playback()
            self._set_status("IDLE", C["text_dim"])

    def _on_loop(self):
        self._loop = not self._loop
        self._loop_btn.configure(
            fg_color=C["amber"] if self._loop else C["btn"],
            text_color=C["bg"] if self._loop else C["text"])

    def _on_save_as(self):
        if not self._cur:
            messagebox.showinfo("Nothing Loaded",
                                "Record something first.")
            return
        import shutil
        src  = Path(self._cur)
        dest = filedialog.asksaveasfilename(
            title="Export Recording",
            initialfile=src.name,
            defaultextension=src.suffix,
            filetypes=[("WAV","*.wav"),("MP3","*.mp3"),
                       ("All","*.*")])
        if dest:
            try:
                shutil.copy2(str(src), dest)
            except Exception as e:
                messagebox.showerror("Export Failed", str(e))

    def _on_delete(self):
        if not self._cur:
            return
        name = Path(self._cur).name
        if not messagebox.askyesno(
                "Delete Recording",
                f"Delete '{name}'?\nThis cannot be undone."):
            return
        if self.recorder.state == "playing":
            self.recorder.stop_playback()
        self.recorder.delete_file(self._cur)
        self._cur = None
        self._set_status("IDLE", C["text_dim"])

    def _do_stop_save(self):
        self._rec_btn.configure(fg_color="#6a1a1a")
        self._set_status("SAVING...", C["amber"])
        fmt = self.app.cfg.config.get("recording_format","wav")

        def _work():
            path = self.recorder.stop_and_save(fmt=fmt)
            self.after(0, lambda: self._save_done(path))

        threading.Thread(target=_work, daemon=True).start()

    def _save_done(self, path):
        if path:
            self._cur = str(path)
            self._set_status("READY", C["green"])
        else:
            self._set_status("IDLE", C["text_dim"])
            messagebox.showerror(
                "Save Failed",
                "Could not save recording.\n"
                "Check Settings \u2192 Audio \u2192 Input Device.")

    # ── Timer tick ────────────────────────────────────────────────

    def _tick(self):
        state = self.recorder.state
        if state == "recording":
            s = int(self.recorder.get_elapsed())
            self._timer.configure(
                text=f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}",
                text_color=C["red"])
        elif state == "playing":
            pos  = self.recorder.get_playback_position()
            s    = int(pos)
            self._timer.configure(
                text=f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}",
                text_color=C["green"])
            if not self.recorder.is_playing() and not self._loop:
                self._set_status("IDLE", C["text_dim"])
        else:
            self._timer.configure(text_color=C["text"])
        self.after(200, self._tick)

    def _set_status(self, text, color=None):
        self._status.configure(
            text=text,
            text_color=color or C["text_dim"])

    def _toggle_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
        else:
            self._open_popup()

    def _open_popup(self):
        recs = self.recorder.list_recordings()[-10:][::-1]  # last 10, newest first
        self.update_idletasks()
        x = self._list_btn.winfo_rootx()
        y = self._list_btn.winfo_rooty() + \
            self._list_btn.winfo_height() + 2
        w = 380
        h = min(len(recs)*28 + 36, 280) if recs else 60

        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=C["elevated"])
        popup.geometry(f"{w}x{h}+{x}+{y}")
        popup.lift()
        self._popup = popup

        if not recs:
            tk.Label(popup, text="No recordings yet.",
                     bg=C["elevated"], fg=C["text_dim"],
                     font=("Segoe UI", 10)).pack(pady=16)
            popup.bind("<FocusOut>", lambda e: popup.destroy())
            popup.focus_set()
            return

        frame = tk.Frame(popup, bg=C["elevated"])
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        sb = tk.Scrollbar(frame, bg=C["surface"],
                          troughcolor=C["bg"], width=10)
        lb = tk.Listbox(frame, yscrollcommand=sb.set,
                        bg=C["elevated"], fg=C["text"],
                        selectbackground=C["blue_mid"],
                        selectforeground=C["text_hi"],
                        font=("Segoe UI", 10),
                        bd=0, highlightthickness=0,
                        activestyle="none")
        sb.config(command=lb.yview)
        sb.pack(side="right", fill="y")
        lb.pack(side="left", fill="both", expand=True)

        for r in recs:
            lb.insert(tk.END,
                      f"  {r['filename']}   {r['recorded_at']}")

        # Pre-select current
        if self._cur:
            for i, r in enumerate(recs):
                if r["path"] == self._cur:
                    lb.selection_set(i)
                    lb.see(i)
                    break

        def _select(e=None):
            sel = lb.curselection()
            if sel:
                rec = recs[sel[0]]
                self._load_file(rec["path"])
            popup.destroy()
            self._popup = None

        lb.bind("<ButtonRelease-1>", _select)
        lb.bind("<Return>",          _select)
        popup.bind("<FocusOut>", lambda e: popup.destroy())
        popup.focus_set()

    def _load_file(self, path: str):
        if self.recorder.state == "playing":
            self.recorder.stop_playback()
        self._cur = path
        import pygame
        try:
            snd = pygame.mixer.Sound(str(path))
            self.recorder._pb_snd = snd
            self.recorder._pb_len = snd.get_length()
        except Exception:
            pass
        short = Path(path).name
        short = short[:24] + "…" if len(short) > 24 else short
        self._set_status(short, C["blue_hi"])


# ═══════════════════════════════════════════════════════════════
# MIC PANEL
# ═══════════════════════════════════════════════════════════════

class MicPanel(ctk.CTkFrame):
    """
    Compact mic control strip — sits between PANIC and tape recorder.
    Row 0: MIC label + horizontal VU meter
    Row 1: 🎙 LIVE/MUTED  |  PTT (hold)
    Row 2: 🎚 Duck (toggle)  |  🎚 Hold (momentary)
    Row 3: GAIN slider
    """

    W = 176

    def __init__(self, parent, app, mic: MicManager):
        super().__init__(parent, fg_color=C["surface"],
                         corner_radius=8, width=self.W)
        self.app          = app
        self.mic          = mic
        self._duck_toggled = False   # state for toggle-duck button
        self.pack_propagate(False)
        self._build()
        self._tick()

    def _fade_setter(self, v: float):
        """Push a value into both the audio engine and the soundboard slider."""
        try:
            self.app.audio.set_performance_fade(v)
            self.app.soundboard._set_fade(v)
        except Exception:
            pass

    def _fade_getter(self) -> float:
        try:
            return self.app.audio.get_performance_fade()
        except Exception:
            return 1.0

    def _duck_duration(self) -> float:
        return float(self.app.cfg.config.get("fade_duration", 3.0))

    def _build(self):
        S8  = ctk.CTkFont("Segoe UI", 8)
        S9B = ctk.CTkFont("Segoe UI", 9, "bold")

        # ── Row 0: label + VU ─────────────────────────────────────
        r0 = ctk.CTkFrame(self, fg_color="transparent")
        r0.pack(fill="x", padx=6, pady=(6, 2))

        self._mic_status_lbl = ctk.CTkLabel(
            r0, text="🎙 MIC",
            font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color=C["text_dim"])
        self._mic_status_lbl.pack(side="left")

        self._vu_canvas = tk.Canvas(
            r0, height=8, bg=C["elevated"],
            highlightthickness=0)
        self._vu_canvas.pack(side="left", fill="x",
                              expand=True, padx=(6, 0))
        self._vu_bar = self._vu_canvas.create_rectangle(
            0, 0, 0, 8, fill=C["green"], outline="")

        # ── Row 1: Mute + PTT ─────────────────────────────────────
        r1 = ctk.CTkFrame(self, fg_color="transparent")
        r1.pack(fill="x", padx=6, pady=(0, 2))

        self._mute_btn = ctk.CTkButton(
            r1, text="🎙 LIVE", width=140, height=26,
            corner_radius=5,
            fg_color=C["green"], hover_color=C["green_dim"],
            font=S9B, command=self._toggle_mute)
        self._mute_btn.pack(side="left", fill="x", expand=True)

        # ── Row 2: Duck toggle + Duck hold ────────────────────────
        r2 = ctk.CTkFrame(self, fg_color="transparent")
        r2.pack(fill="x", padx=6, pady=(0, 2))

        self._duck_tog_btn = ctk.CTkButton(
            r2, text="🎚 Duck", width=140, height=26,
            corner_radius=5,
            fg_color=C["btn"], hover_color=C["btn_hover"],
            font=S9B, command=self._duck_toggle)
        self._duck_tog_btn.pack(side="left", fill="x", expand=True)

        # ── Row 3: Gain slider ────────────────────────────────────
        r3 = ctk.CTkFrame(self, fg_color="transparent")
        r3.pack(fill="x", padx=6, pady=(0, 6))

        ctk.CTkLabel(r3, text="GAIN",
                     font=S8, text_color=C["text_dim"]).pack(
                         side="left", padx=(0, 4))

        self._gain_var = ctk.DoubleVar(value=self.mic.get_gain())
        ctk.CTkSlider(
            r3, from_=0.0, to=1.0,
            variable=self._gain_var,
            command=lambda v: self.mic.set_gain(float(v)),
            height=14).pack(side="left", fill="x", expand=True)

    # ── Mute / PTT ────────────────────────────────────────────────

    def _toggle_mute(self):
        if not self.mic.is_bound:
            # Not bound — prompt user to set device in Settings
            try:
                from tkinter import messagebox
                messagebox.showwarning(
                    "No Mic Device",
                    "No mic input device is bound.\n\n"
                    "Go to Settings \u2192 Audio \u2192 Mic Input Device "
                    "and select your microphone.")
            except Exception:
                pass
            return
        muted = self.mic.toggle_mute()
        self._update_mute_btn(muted)

    def _update_mute_btn(self, muted: bool):
        if muted:
            self._mute_btn.configure(
                text="🔴 MUTED",
                fg_color=C["red_dim"], hover_color=C["red_dim"])
        else:
            self._mute_btn.configure(
                text="🎙 LIVE",
                fg_color=C["green"], hover_color=C["green_dim"])

    # ── Duck toggle ───────────────────────────────────────────────

    def _duck_toggle(self):
        """Toggle duck: press to fade down, press again to fade back up."""
        dur = self._duck_duration()
        if not self._duck_toggled:
            # Duck down
            self._duck_toggled      = True
            self.mic._duck_active   = True
            self.mic._pre_duck_fade = self._fade_getter()
            target = float(self.app.cfg.config.get("mic_duck_level", 0.3))
            self._duck_tog_btn.configure(
                fg_color=C["amber"], text_color=C["bg"],
                text="🎚 Ducked")
            self.mic.duck_smooth(
                self._fade_getter(), target, dur,
                self.after, self._fade_setter)
        else:
            # Unduck
            self._duck_toggled    = False
            self.mic._duck_active = False
            self._duck_tog_btn.configure(
                fg_color=C["btn"], text_color=C["text"],
                text="🎚 Duck")
            self.mic.duck_smooth(
                self._fade_getter(), self.mic._pre_duck_fade, dur,
                self.after, self._fade_setter)

    # ── Tick ──────────────────────────────────────────────────────

    def _tick(self):
        try:
            level = self.mic.get_level()
            self._vu_canvas.update_idletasks()
            w = self._vu_canvas.winfo_width()
            if w > 4:
                fill_w = int(w * level)
                col = (C["red"]   if level > 0.75 else
                       C["amber"] if level > 0.45 else
                       C["green"])
                self._vu_canvas.coords(self._vu_bar, 0, 0, fill_w, 8)
                self._vu_canvas.itemconfig(self._vu_bar, fill=col)
            # Bind status on label
            if self.mic.is_bound:
                self._mic_status_lbl.configure(
                    text="🎙 MIC", text_color=C["text_dim"])
            else:
                self._mic_status_lbl.configure(
                    text="🎙 NO DEVICE", text_color=C["red_dim"])
        except Exception:
            pass
        if self.winfo_exists():
            self.after(80, self._tick)




# ═══════════════════════════════════════════════════════════════
# HEADER FRAME
# ═══════════════════════════════════════════════════════════════

class HeaderFrame(ctk.CTkFrame):
    """
    Two-zone broadcast console header.

    Zone A (left, ~65% width):
      [VU] Logo | Show info | ON AIR | LIVE timer | GO LIVE
           ---- second row ----
           COUNTDOWN | VOL | MUTE | PANIC

    Zone B (right, ~35% width):
      [VU] Tape Recorder section
    """

    HEIGHT = 100

    def __init__(self, parent, app):
        super().__init__(parent,
                         fg_color=C["bg2"], corner_radius=0)
        self.app = app
        self.configure(height=self.HEIGHT)
        self.pack_propagate(False)

        self._call_running = False
        self._call_start   = None

        self._build()

    # ── Build ─────────────────────────────────────────────────────

    def _build(self):
        from ui_dialogs import load_logo

        # ── LEFT: Logo + Branding ────────────────────────────────
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=(6, 0), pady=4)

        brand_f = ctk.CTkFrame(left, fg_color="transparent")
        brand_f.pack(side="left")
        logo = load_logo((44, 50))
        if logo:
            ctk.CTkLabel(brand_f, image=logo, text="").pack(side="left", padx=(0, 6))
        brand_txt = ctk.CTkFrame(brand_f, fg_color="transparent")
        brand_txt.pack(side="left")
        ctk.CTkLabel(brand_txt, text=APP_NAME,
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(brand_txt,
                     text=(f"{self.app.cfg.config.get('show_name', 'The Chill With IceCat')}"
                           f"  •  v{VERSION}"),
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=C["text_dim"]).pack(anchor="w")

        # ── CENTRE: all broadcast controls in one row ─────────────
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=4)

        # ON AIR badge
        self.onair_frame = ctk.CTkFrame(
            mid, width=96, height=36, corner_radius=6, fg_color=C["surface"])
        self.onair_frame.pack(side="left", padx=(0, 6))
        self.onair_frame.pack_propagate(False)
        self.onair_lbl = ctk.CTkLabel(
            self.onair_frame, text="● OFF AIR",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color=C["text_dim"])
        self.onair_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # LIVE timer block
        live_blk = ctk.CTkFrame(mid, fg_color="transparent")
        live_blk.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(live_blk, text="LIVE",
                     font=ctk.CTkFont("Segoe UI", 7),
                     text_color=C["text_dim"]).pack(anchor="w")
        self.live_lbl = ctk.CTkLabel(
            live_blk, text="00:00:00",
            font=ctk.CTkFont("Courier New", 17, "bold"),
            text_color=C["text"])
        self.live_lbl.pack(anchor="w")

        # GO LIVE button
        _gl = self.app.cfg.get_btn_custom("golive", 0)
        self.golive_btn = ctk.CTkButton(
            mid, text=_gl.get("label", "GO LIVE"),
            width=82, height=36, corner_radius=6,
            fg_color=_gl.get("color", C["blue"]) or C["blue"],
            text_color=_gl.get("text_color", C["text_hi"]) or C["text_hi"],
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            command=self.app.manual_go_live)
        self.golive_btn.pack(side="left", padx=(0, 8))
        self.golive_btn.bind("<Button-3>",
            lambda e: self._btn_ctx(e, "golive", 0, allow_rename=True))

        ctk.CTkFrame(mid, width=1, height=36, fg_color=C["border"]).pack(side="left", padx=6)

        # CALL block
        call_blk = ctk.CTkFrame(mid, fg_color="transparent")
        call_blk.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(call_blk, text="CALL",
                     font=ctk.CTkFont("Segoe UI", 7),
                     text_color=C["text_dim"]).pack(anchor="w")
        self.call_lbl = ctk.CTkLabel(
            call_blk, text="00:00",
            font=ctk.CTkFont("Courier New", 14, "bold"),
            text_color=C["text_dim"])
        self.call_lbl.pack(anchor="w")
        self.call_btn = ctk.CTkButton(
            call_blk, text="📞 Start", width=70, height=18,
            corner_radius=4, fg_color=C["btn"],
            font=ctk.CTkFont("Segoe UI", 8),
            command=self._toggle_call)
        self.call_btn.pack(anchor="w")

        ctk.CTkFrame(mid, width=1, height=36, fg_color=C["border"]).pack(side="left", padx=6)

        # COUNTDOWN block
        cd_blk = ctk.CTkFrame(mid, fg_color="transparent")
        cd_blk.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(cd_blk, text="COUNTDOWN",
                     font=ctk.CTkFont("Segoe UI", 7),
                     text_color=C["text_dim"]).pack(anchor="w")
        self.cd_lbl = ctk.CTkLabel(
            cd_blk, text="00:00",
            font=ctk.CTkFont("Courier New", 14, "bold"),
            text_color=C["text"])
        self.cd_lbl.pack(anchor="w")
        cd_ctrl = ctk.CTkFrame(cd_blk, fg_color="transparent")
        cd_ctrl.pack(anchor="w")
        self.cd_entry = ctk.CTkEntry(
            cd_ctrl, width=46, height=18,
            placeholder_text="MM:SS",
            font=ctk.CTkFont("Segoe UI", 8))
        self.cd_entry.pack(side="left", padx=(0, 2))
        ctk.CTkButton(cd_ctrl, text="▶", width=20, height=18,
                      corner_radius=3, fg_color=C["green"],
                      font=ctk.CTkFont("Segoe UI", 8),
                      command=self.app.start_countdown).pack(side="left", padx=1)
        ctk.CTkButton(cd_ctrl, text="5m", width=22, height=18,
                      corner_radius=3, fg_color=C["btn"],
                      font=ctk.CTkFont("Segoe UI", 8),
                      command=lambda: self.app.quick_countdown(5)).pack(side="left", padx=1)
        ctk.CTkButton(cd_ctrl, text="10m", width=26, height=18,
                      corner_radius=3, fg_color=C["btn"],
                      font=ctk.CTkFont("Segoe UI", 8),
                      command=lambda: self.app.quick_countdown(10)).pack(side="left", padx=1)

        ctk.CTkFrame(mid, width=1, height=36, fg_color=C["border"]).pack(side="left", padx=6)

        # VOL slider
        vol_blk = ctk.CTkFrame(mid, fg_color="transparent")
        vol_blk.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(vol_blk, text="VOL",
                     font=ctk.CTkFont("Segoe UI", 7),
                     text_color=C["text_dim"]).pack(anchor="w")
        self.vol_slider = ctk.CTkSlider(
            vol_blk, from_=0.0, to=1.0, width=100,
            command=self.app.set_master_volume)
        self.vol_slider.set(1.0)
        self.vol_slider.pack(anchor="w")

        # MUTE
        _mu = self.app.cfg.get_btn_custom("mute", 0)
        self.mute_btn = ctk.CTkButton(
            mid, text="🔇 MUTE", width=78, height=30,
            corner_radius=5,
            fg_color=_mu.get("color", C["btn"]) or C["btn"],
            text_color=_mu.get("text_color", C["text"]) or C["text"],
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            command=self.app.toggle_mute)
        self.mute_btn.pack(side="left", padx=(0, 6))
        self.mute_btn.bind("<Button-3>",
            lambda e: self._btn_ctx(e, "mute", 0, allow_rename=False))

        # PANIC
        _pa = self.app.cfg.get_btn_custom("panic", 0)
        self.panic_btn = ctk.CTkButton(
            mid, text="🚨 PANIC", width=86, height=36,
            corner_radius=6,
            fg_color=_pa.get("color", C["panic"]) or C["panic"],
            text_color=_pa.get("text_color", C["text_hi"]) or C["text_hi"],
            hover_color="#ff0000",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            command=self.app.panic)
        self.panic_btn.pack(side="left")
        self.panic_btn.bind("<Button-3>",
            lambda e: self._btn_ctx(e, "panic", 0, allow_rename=False))

        # ── MIC PANEL ────────────────────────────────────────────
        ctk.CTkFrame(mid, width=1, height=36,
                     fg_color=C["border"]).pack(side="left", padx=6)

        self.mic_panel = MicPanel(mid, self.app, self.app.mic)
        self.mic_panel.pack(side="left", fill="y", pady=4)

        # ── RIGHT: divider + recorder VU + tape recorder ──────────
        ctk.CTkFrame(self, width=1, height=self.HEIGHT - 12,
                     fg_color=C["border"]).pack(side="left", padx=6, pady=6)

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="left", fill="y", padx=(0, 4), pady=4)

        self._vu_recorder = VerticalVU(right,
            lambda: self.app.audio.get_recorder_vu_level())
        self._vu_recorder.pack(side="left", padx=(0, 6))

        self.tape_recorder = TapeRecorderSection(right, self.app)
        self.tape_recorder.pack(side="left", fill="y")



    def _toggle_call(self):
        import time as _t
        if self._call_running:
            # End call — log duration
            self._call_running = False
            self.call_btn.configure(text="📞 Start", fg_color=C["btn"])
            self.call_lbl.configure(text_color=C["text_dim"])
            e   = int(_t.monotonic() - self._call_start)
            dur = f"{e//60:02d}:{e%60:02d}"
            self.call_lbl.configure(text="00:00")
            try:
                sl = self.app.right_panel.session_log
                sl.log_event(f"📞 Call ended — duration {dur}")
            except Exception:
                pass
        else:
            self._call_start   = _t.monotonic()
            self._call_running = True
            self.call_btn.configure(text="⏹ End Call",
                                    fg_color=C["red_dim"])
            self.call_lbl.configure(text_color=C["green"])
            self._tick_call()
            try:
                sl = self.app.right_panel.session_log
                sl.log_event("📞 Call started")
            except Exception:
                pass

    def _tick_call(self):
        if not self._call_running:
            return
        import time as _t
        e = int(_t.monotonic() - self._call_start)
        self.call_lbl.configure(text=f"{e//60:02d}:{e%60:02d}")
        self.after(1000, self._tick_call)

    def _btn_ctx(self, e, btn_type, idx, allow_rename):
        from ui_dialogs import ButtonSettingsDialog
        m = tk.Menu(self, tearoff=0,
                    bg=C["surface"], fg=C["text"],
                    activebackground=C["blue_mid"],
                    font=("Segoe UI", 10))
        m.add_command(
            label="🎨  Customize...",
            command=lambda: self._open_customize(
                btn_type, idx, allow_rename))
        m.add_command(label="↩  Reset",
                      command=lambda: self._reset_custom(
                          btn_type, idx))
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _open_customize(self, btn_type, idx, allow_rename):
        from ui_dialogs import ButtonSettingsDialog
        custom = self.app.cfg.get_btn_custom(btn_type, idx)
        defs   = {
            "golive": ("GO LIVE",  C["blue"],  C["text_hi"]),
            "panic":  ("🚨 PANIC", C["panic"], C["text_hi"]),
            "mute":   ("🔇 MUTE",  C["btn"],   C["text"]),
        }
        dl, dc, dt = defs.get(btn_type, ("", C["btn"], C["text"]))
        dlg = ButtonSettingsDialog(
            self,
            label=custom.get("label", dl),
            color=custom.get("color", dc),
            text_color=custom.get("text_color", dt),
            allow_rename=allow_rename)
        self.wait_window(dlg)
        if dlg.result:
            data = {"color":      dlg.result["color"],
                    "text_color": dlg.result["text_color"]}
            if allow_rename:
                data["label"] = dlg.result["label"]
            self.app.cfg.set_btn_custom(btn_type, idx, data)
            self.app.cfg.save()
            self._apply_custom(btn_type, idx)

    def _reset_custom(self, btn_type, idx):
        self.app.cfg.set_btn_custom(btn_type, idx, {})
        self.app.cfg.save()
        self._apply_custom(btn_type, idx)

    def _apply_custom(self, btn_type, idx):
        c = self.app.cfg.get_btn_custom(btn_type, idx)
        if btn_type == "golive":
            self.golive_btn.configure(
                text=c.get("label","GO LIVE") or "GO LIVE",
                fg_color=c.get("color",C["blue"]) or C["blue"],
                text_color=c.get("text_color",C["text_hi"]) or C["text_hi"])
        elif btn_type == "mute":
            self.mute_btn.configure(
                fg_color=c.get("color",C["btn"]) or C["btn"],
                text_color=c.get("text_color",C["text"]) or C["text"])
        elif btn_type == "panic":
            self.panic_btn.configure(
                fg_color=c.get("color",C["panic"]) or C["panic"],
                text_color=c.get("text_color",C["text_hi"]) or C["text_hi"])

    # ── Public update methods ─────────────────────────────────────

    def set_on_air(self, live: bool):
        c = self.app.cfg.get_btn_custom("golive", 0)
        if live:
            self.onair_lbl.configure(text="● ON AIR",
                                      text_color=C["red"])
            self.onair_frame.configure(fg_color="#3a0808")
            self.golive_btn.configure(text="END LIVE",
                                       fg_color=C["red_dim"])
        else:
            self.onair_lbl.configure(text="● OFF AIR",
                                      text_color=C["text_dim"])
            self.onair_frame.configure(fg_color=C["surface"])
            self.golive_btn.configure(
                text=c.get("label","GO LIVE") or "GO LIVE",
                fg_color=c.get("color",C["blue"]) or C["blue"])

    def update_live(self, hh, mm, ss):
        self.live_lbl.configure(
            text=f"{hh:02d}:{mm:02d}:{ss:02d}")

    def update_countdown(self, mm, ss, urgent=False):
        self.cd_lbl.configure(
            text=f"{mm:02d}:{ss:02d}",
            text_color=C["red"] if urgent else C["text"])

    def set_mute_state(self, muted: bool):
        if muted:
            self.mute_btn.configure(text="🔊 UNMUTE",
                                     fg_color=C["amber"],
                                     text_color=C["bg"])
        else:
            c = self.app.cfg.get_btn_custom("mute", 0)
            self.mute_btn.configure(
                text="🔇 MUTE",
                fg_color=c.get("color",C["btn"]) or C["btn"],
                text_color=c.get("text_color",C["text"]) or C["text"])

    def flash_red(self):
        self._flash(6)

    def _flash(self, n):
        if n <= 0:
            self.configure(fg_color=C["bg2"])
            return
        self.configure(fg_color="#350000" if n%2 else C["bg2"])
        self.after(300, lambda: self._flash(n-1))


# ═══════════════════════════════════════════════════════════════
# MINI MODE WINDOW
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# MENU BAR
# ═══════════════════════════════════════════════════════════════

class MenuBarFrame(ctk.CTkFrame):
    """
    Custom dark-themed menu bar that sits between the title bar and
    the header.  Uses CTkButton tabs that pop up tk.Menu dropdowns.

    Menus
    -----
    File  — Save Notes, Export Bank, Import Bank, Export Session Log, Exit
    Edit  — Undo, Lock/Unlock Board, Settings
    View  — Opacity submenu
    Tools — Quick Folders submenu, Edit Websites, Discord Settings
    Help  — About, Prankcast link, Open Data Folder
    """

    HEIGHT = 26

    def __init__(self, parent, app):
        super().__init__(parent,
                         fg_color=C["bg2"],
                         corner_radius=0,
                         height=self.HEIGHT)
        self.app = app
        self.pack_propagate(False)
        self._build()

    # ── Build ─────────────────────────────────────────────────────

    def _build(self):
        labels = ["  File  ", "  Edit  ", "  View  ", "  Tools  ", "  Help  "]
        builders = [
            self._build_file,
            self._build_edit,
            self._build_view,
            self._build_tools,
            self._build_help,
        ]
        for lbl, fn in zip(labels, builders):
            btn = tk.Button(
                self,
                text=lbl,
                font=("Segoe UI", 9),
                bg=C["bg2"],
                fg=C["text"],
                activebackground=C["elevated"],
                activeforeground=C["text_hi"],
                bd=0,
                padx=4,
                pady=3,
                cursor="hand2",
                relief="flat",
            )
            btn.pack(side="left")
            btn.configure(command=lambda b=btn, f=fn: self._popup(b, f))

        # Thin border bottom
        tk.Frame(self, bg=C["border"], height=1).pack(
            side="bottom", fill="x")

    def _menu_style(self):
        return dict(
            bg=C["elevated"],
            fg=C["text"],
            activebackground=C["blue_mid"],
            activeforeground=C["text_hi"],
            relief="flat",
            bd=0,
            tearoff=False,
        )

    def _popup(self, btn, builder):
        """Position and display the menu below the clicked button."""
        m = builder()
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height()
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    # ── Menu builders ─────────────────────────────────────────────

    def _build_file(self):
        m = tk.Menu(self, **self._menu_style())

        m.add_command(label="💾  Save Notes",
                      command=self._save_notes)
        m.add_separator()
        m.add_command(label="📤  Export Bank",
                      command=self._export_bank)
        m.add_command(label="📥  Import Bank",
                      command=self._import_bank)
        m.add_separator()
        m.add_command(label="📋  Export Session Log",
                      command=self._export_session_log)
        m.add_separator()
        m.add_command(label="✖  Exit",
                      command=self.app._on_close)
        return m

    def _build_edit(self):
        m = tk.Menu(self, **self._menu_style())

        m.add_command(label="↩  Undo",
                      command=self.app.undo_last)
        m.add_separator()

        locked = self.app.cfg.config.get("soundboard_locked", False)
        lock_lbl = "🔓  Unlock Board" if locked else "🔒  Lock Board"
        m.add_command(label=lock_lbl,
                      command=self._toggle_lock)
        m.add_separator()
        m.add_command(label="⚙  Settings",
                      command=self.app.open_settings)
        return m

    def _build_view(self):
        m = tk.Menu(self, **self._menu_style())

        opacity_menu = tk.Menu(m, **self._menu_style())
        for label, value in [
            ("100%  (Full)",  1.0),
            ("90%",           0.9),
            ("80%",           0.8),
            ("70%",           0.7),
            ("50%  (Ghost)",  0.5),
        ]:
            opacity_menu.add_command(
                label=label,
                command=lambda v=value: self.app.set_opacity(v))

        m.add_cascade(label="🔆  Opacity", menu=opacity_menu)
        return m

    def _build_tools(self):
        m = tk.Menu(self, **self._menu_style())

        # Quick Folders submenu
        folder_menu = tk.Menu(m, **self._menu_style())
        import os
        folders = self.app.cfg.config.get("folders", [])
        any_folder = False
        for f in folders:
            path  = f.get("path", "")
            label = f.get("label", "")
            if path:
                any_folder = True
                folder_menu.add_command(
                    label=f"📁  {label}",
                    command=lambda p=path: (
                        os.startfile(p) if os.path.isdir(p) else None))
            else:
                folder_menu.add_command(
                    label=f"     {label} (empty)",
                    state="disabled")
        if not any_folder:
            folder_menu.add_command(
                label="     (no folders configured)",
                state="disabled")
        m.add_cascade(label="📁  Quick Folders", menu=folder_menu)
        m.add_separator()

        m.add_command(label="🌐  Edit Websites",
                      command=lambda: self.app.open_settings(tab="tools"))
        m.add_separator()
        m.add_command(label="📡  Discord Settings",
                      command=lambda: self.app.open_settings(tab="discord"))
        return m

    def _build_help(self):
        m = tk.Menu(self, **self._menu_style())

        import webbrowser
        prankcast_url = self.app.cfg.config.get(
            "prankcast_url", "https://prankcast.com/icecat")

        m.add_command(label=f"ℹ  {APP_NAME}  v{VERSION}",
                      state="disabled")
        m.add_separator()
        m.add_command(label="🌐  Open Prankcast",
                      command=lambda: webbrowser.open(prankcast_url))
        m.add_separator()
        m.add_command(label="📂  Open Data Folder",
                      command=self._open_data_dir)
        return m

    # ── Action callbacks ──────────────────────────────────────────

    def _save_notes(self):
        try:
            self.app.right_panel.notes.save_all()
        except Exception as e:
            log.warning(f"MenuBar save_notes: {e}")

    def _export_bank(self):
        try:
            sb = self.app.soundboard
            sb._export_bank(sb._current_bank)
        except Exception as e:
            log.warning(f"MenuBar export_bank: {e}")

    def _import_bank(self):
        try:
            sb = self.app.soundboard
            sb._import_bank(sb._current_bank)
        except Exception as e:
            log.warning(f"MenuBar import_bank: {e}")

    def _export_session_log(self):
        try:
            self.app.right_panel.session_log._export()
        except Exception as e:
            log.warning(f"MenuBar export_session_log: {e}")

    def _toggle_lock(self):
        try:
            self.app.soundboard._toggle_lock()
        except Exception as e:
            log.warning(f"MenuBar toggle_lock: {e}")

    def _open_data_dir(self):
        import os
        from config import DATA_DIR
        path = str(DATA_DIR)
        try:
            if os.path.isdir(path):
                os.startfile(path)
        except Exception as e:
            log.warning(f"MenuBar open_data_dir: {e}")


class MiniModeWindow(tk.Toplevel):
    """
    Always-on-top compact mini console.
    Two rows:
      Row 1: ON AIR badge | LIVE timer | GO LIVE | MIC MUTE | Mic VU
      Row 2: Now Playing label | ⏮▶⏸⏹ | Sound VU | VOL slider | STOP ALL | 🚨 PANIC | ⛶
    Plus a timestamp row at the bottom.
    """

    W  = 780
    H  = 160

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app       = app
        self._tick_job = None
        self._vu_rects_snd = []
        self._vu_rects_mic = []
        self._vu_snd = 0.0
        self._vu_mic = 0.0
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=C["bg2"])
        self.geometry(f"{self.W}x{self.H}+50+50")
        self._drag_x = self._drag_y = 0
        self._build()
        self._tick()
        for w in (self, ):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_move)

    # ── Build ─────────────────────────────────────────────────────

    def _build(self):
        BG   = C["bg2"]
        SRF  = C["surface"]
        S8   = ("Segoe UI", 8)
        S9   = ("Segoe UI", 9)
        S9B  = ("Segoe UI", 9, "bold")
        S10B = ("Segoe UI", 10, "bold")
        S11B = ("Segoe UI", 11, "bold")
        CNB  = ("Courier New", 14, "bold")

        outer = tk.Frame(self, bg=BG, bd=1, relief="solid",
                         highlightbackground=C["border"],
                         highlightthickness=1)
        outer.pack(fill="both", expand=True)

        # ── Title bar ─────────────────────────────────────────────
        bar = tk.Frame(outer, bg=SRF, height=18)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text=f"  {APP_NAME} — Mini Mode",
                 bg=SRF, fg=C["text_dim"], font=S8).pack(side="left")
        tk.Button(bar, text="⛶ Expand",
                  bg=SRF, fg=C["blue_hi"],
                  activebackground=C["btn_hover"],
                  relief="flat", bd=0, padx=8,
                  font=S8, cursor="hand2",
                  command=self._expand).pack(side="right")
        for w in (bar,):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_move)

        # ── Row 1: Broadcast controls ─────────────────────────────
        r1 = tk.Frame(outer, bg=BG)
        r1.pack(fill="x", padx=6, pady=(4, 2))

        # ON AIR badge
        self._onair = tk.Label(r1, text="● OFF AIR",
                                bg=SRF, fg=C["text_dim"],
                                font=S11B, width=10,
                                relief="flat", bd=0)
        self._onair.pack(side="left", padx=(0, 6), ipady=5)

        # LIVE timer
        lv_f = tk.Frame(r1, bg=BG)
        lv_f.pack(side="left", padx=(0, 6))
        tk.Label(lv_f, text="LIVE", bg=BG,
                 fg=C["text_dim"], font=S8).pack(anchor="w")
        self._live = tk.Label(lv_f, text="00:00:00",
                               bg=BG, fg=C["text"], font=CNB)
        self._live.pack(anchor="w")

        # GO LIVE
        self._golive = tk.Button(
            r1, text="GO LIVE",
            bg=C["blue"], fg=C["text_hi"],
            activebackground=C["blue_mid"],
            font=S10B, relief="flat", bd=0,
            padx=12, pady=4, cursor="hand2",
            command=self.app.manual_go_live)
        self._golive.pack(side="left", padx=(0, 8))

        # Separator
        tk.Frame(r1, bg=C["border"], width=1).pack(
            side="left", fill="y", padx=4)

        # MIC MUTE
        self._mic_mute = tk.Button(
            r1, text="🎙 LIVE",
            bg=C["green"], fg=C["bg"],
            activebackground=C["green_dim"],
            font=S9B, relief="flat", bd=0,
            padx=10, pady=4, cursor="hand2",
            command=self._toggle_mic_mute)
        self._mic_mute.pack(side="left", padx=(0, 6))

        # Mic VU (horizontal, 8px tall)
        mic_vu_f = tk.Frame(r1, bg=BG)
        mic_vu_f.pack(side="left", padx=(0, 6))
        tk.Label(mic_vu_f, text="MIC", bg=BG,
                 fg=C["text_dim"], font=S8).pack(anchor="w")
        self._mic_vu_c = tk.Canvas(
            mic_vu_f, width=80, height=10,
            bg=C["elevated"], highlightthickness=0)
        self._mic_vu_c.pack(anchor="w")
        self._mic_vu_bar = self._mic_vu_c.create_rectangle(
            0, 0, 0, 10, fill=C["green"], outline="")

        # Mic gain slider
        mic_sl_f = tk.Frame(r1, bg=BG)
        mic_sl_f.pack(side="left", padx=(0, 8))
        tk.Label(mic_sl_f, text="GAIN", bg=BG,
                 fg=C["text_dim"], font=S8).pack(anchor="w")
        self._mic_sl = tk.Scale(
            mic_sl_f, from_=0.0, to=1.0, resolution=0.02,
            orient="horizontal", length=80,
            bg=BG, fg=C["text_dim"],
            troughcolor=C["surface"],
            highlightthickness=0, bd=0, showvalue=False,
            command=lambda v: self.app.mic.set_gain(float(v)))
        try:
            self._mic_sl.set(self.app.mic.get_gain())
        except Exception:
            self._mic_sl.set(1.0)
        self._mic_sl.pack(anchor="w")

        # ── Row 2: Now Playing + transport + sound controls ───────
        r2 = tk.Frame(outer, bg=BG)
        r2.pack(fill="x", padx=6, pady=(0, 2))

        # Now Playing label
        np_f = tk.Frame(r2, bg=BG)
        np_f.pack(side="left", padx=(0, 6))
        tk.Label(np_f, text="NOW PLAYING", bg=BG,
                 fg=C["text_dim"], font=S8).pack(anchor="w")
        self._np = tk.Label(np_f, text="—",
                             bg=BG, fg=C["text"],
                             font=S9B, width=22, anchor="w")
        self._np.pack(anchor="w")

        # Queue transport: ⏮ ▶ ⏸ ⏹ ⏭
        tp_f = tk.Frame(r2, bg=BG)
        tp_f.pack(side="left", padx=(0, 8))
        for sym, cmd in [
            ("⏮", lambda: self._queue_cmd("prev")),
            ("▶", lambda: self._queue_cmd("play")),
            ("⏸", lambda: self._queue_cmd("pause")),
            ("⏹", lambda: self._queue_cmd("stop")),
            ("⏭", lambda: self._queue_cmd("next")),
        ]:
            tk.Button(tp_f, text=sym,
                      bg=C["btn"], fg=C["text"],
                      activebackground=C["btn_hover"],
                      relief="flat", bd=0,
                      padx=6, pady=2,
                      font=("Segoe UI", 11),
                      cursor="hand2",
                      command=cmd).pack(side="left", padx=1)

        # Separator
        tk.Frame(r2, bg=C["border"], width=1).pack(
            side="left", fill="y", padx=6)

        # Sound VU
        snd_vu_f = tk.Frame(r2, bg=BG)
        snd_vu_f.pack(side="left", padx=(0, 4))
        tk.Label(snd_vu_f, text="SND", bg=BG,
                 fg=C["text_dim"], font=S8).pack(anchor="w")
        self._snd_vu_c = tk.Canvas(
            snd_vu_f, width=80, height=10,
            bg=C["elevated"], highlightthickness=0)
        self._snd_vu_c.pack(anchor="w")
        self._snd_vu_bar = self._snd_vu_c.create_rectangle(
            0, 0, 0, 10, fill=C["green"], outline="")

        # Master volume slider
        vol_f = tk.Frame(r2, bg=BG)
        vol_f.pack(side="left", padx=(0, 8))
        tk.Label(vol_f, text="VOL", bg=BG,
                 fg=C["text_dim"], font=S8).pack(anchor="w")
        self._vol_sl = tk.Scale(
            vol_f, from_=0.0, to=1.0, resolution=0.02,
            orient="horizontal", length=90,
            bg=BG, fg=C["text_dim"],
            troughcolor=C["surface"],
            highlightthickness=0, bd=0, showvalue=False,
            command=self.app.set_master_volume)
        self._vol_sl.set(self.app.audio.master_vol)
        self._vol_sl.pack(anchor="w")

        # STOP ALL
        tk.Button(r2, text="⏹ Stop All",
                  bg=C["btn"], fg=C["text"],
                  activebackground=C["btn_hover"],
                  font=S9B, relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2",
                  command=self.app.panic).pack(
                      side="left", padx=(0, 6))

        # PANIC
        tk.Button(r2, text="🚨 PANIC",
                  bg=C["panic"], fg=C["text_hi"],
                  activebackground="#ff0000",
                  font=S10B, relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2",
                  command=self.app.panic).pack(
                      side="left", padx=(0, 4))

        # ── Row 3: Timestamp input ────────────────────────────────
        r3 = tk.Frame(outer, bg=BG)
        r3.pack(fill="x", padx=6, pady=(0, 4))

        self._ts_entry = tk.Entry(
            r3, bg=C["surface"], fg=C["text"],
            insertbackground=C["text"],
            relief="flat", font=("Segoe UI", 9),
            width=34)
        self._ts_entry.pack(side="left", padx=(0, 4),
                            ipady=3, ipadx=4)
        self._ts_entry.insert(0, "note...")
        self._ts_entry.configure(fg=C["text_dim"])
        self._ts_entry.bind("<FocusIn>", self._ts_focus_in)
        self._ts_entry.bind("<FocusOut>", self._ts_focus_out)
        self._ts_entry.bind("<Return>", lambda e: self._do_stamp())

        tk.Button(r3, text="📌 Stamp",
                  bg=C["btn"], fg=C["amber_hi"],
                  activebackground=C["btn_hover"],
                  relief="flat", bd=0,
                  padx=10, pady=3,
                  font=S9B, cursor="hand2",
                  command=self._do_stamp).pack(side="left")

    # ── Helpers ───────────────────────────────────────────────────

    def _toggle_mic_mute(self):
        try:
            muted = self.app.mic.toggle_mute()
            self.update_mute(muted)
            # sync main window
            self.app.header.mic_panel._update_mute_btn(muted)
        except Exception:
            pass

    def _queue_cmd(self, cmd):
        try:
            q = self.app.soundboard.queue
            {"prev":  q._prev,
             "play":  q._play_current,
             "pause": q._toggle_pause,
             "stop":  q._stop,
             "next":  q._next}[cmd]()
        except Exception:
            pass

    def _ts_focus_in(self, e):
        if self._ts_entry.get() == "note...":
            self._ts_entry.delete(0, "end")
            self._ts_entry.configure(fg=C["text"])

    def _ts_focus_out(self, e):
        if not self._ts_entry.get().strip():
            self._ts_entry.insert(0, "note...")
            self._ts_entry.configure(fg=C["text_dim"])

    def _do_stamp(self):
        raw  = self._ts_entry.get().strip()
        note = "" if raw == "note..." else raw
        try:
            self.app.right_panel.session_log._do_stamp_from(note)
        except Exception:
            try:
                sl = self.app.right_panel.session_log
                from datetime import datetime as _dt
                wall = _dt.now().strftime("%b %d %H:%M:%S")
                text = f"📌 {note}" if note else "📌"
                sl._write([(f"[{wall}] ", "ts"), (text, "stamp")])
            except Exception:
                pass
        self._ts_entry.delete(0, "end")
        self._ts_entry.insert(0, "note...")
        self._ts_entry.configure(fg=C["text_dim"])

    # ── Tick ──────────────────────────────────────────────────────

    def _tick(self):
        try:
            # Row 1: ON AIR + LIVE timer + GO LIVE
            if self.app._live:
                self._onair.configure(
                    text="● ON AIR", bg="#3a0808", fg=C["red"])
                self._golive.configure(
                    text="END LIVE", bg=C["red_dim"])
            else:
                self._onair.configure(
                    text="● OFF AIR", bg=C["surface"],
                    fg=C["text_dim"])
                self._golive.configure(text="GO LIVE", bg=C["blue"])
            h = getattr(self.app, "_live_h", 0)
            m = getattr(self.app, "_live_m", 0)
            s = getattr(self.app, "_live_s", 0)
            self._live.configure(text=f"{h:02d}:{m:02d}:{s:02d}")

            # Mic mute sync
            try:
                muted = self.app.mic.is_muted()
                self._mic_mute.configure(
                    text="🔴 MUTED" if muted else "🎙 LIVE",
                    bg=C["red_dim"] if muted else C["green"],
                    fg=C["text_hi"] if muted else C["bg"])
            except Exception:
                pass

            # Mic VU
            try:
                lv = float(self.app.mic.get_level())
                col = (C["red"] if lv > 0.75 else
                       C["amber"] if lv > 0.45 else C["green"])
                self._mic_vu_c.coords(
                    self._mic_vu_bar, 0, 0,
                    int(80 * lv), 10)
                self._mic_vu_c.itemconfig(
                    self._mic_vu_bar, fill=col)
            except Exception:
                pass

            # Sound VU
            try:
                lv = float(self.app.audio.get_vu_level())
                col = (C["red"] if lv > 0.75 else
                       C["amber"] if lv > 0.45 else C["green"])
                self._snd_vu_c.coords(
                    self._snd_vu_bar, 0, 0,
                    int(80 * lv), 10)
                self._snd_vu_c.itemconfig(
                    self._snd_vu_bar, fill=col)
            except Exception:
                pass

            # Now playing
            np = self.app.audio.get_now_playing()
            if np:
                _, info = np
                self._np.configure(
                    text=info.get("label","")[:24],
                    fg=C["text"])
            else:
                self._np.configure(text="—", fg=C["text_dim"])

            # Vol slider sync
            self._vol_sl.set(self.app.audio.master_vol)

        except Exception:
            pass
        if self.winfo_exists():
            self._tick_job = self.after(200, self._tick)

    # ── Drag + expand ─────────────────────────────────────────────

    def _expand(self):
        if self._tick_job:
            try: self.after_cancel(self._tick_job)
            except Exception: pass
        self.app.toggle_mini_mode()

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.winfo_x()
        self._drag_y = e.y_root - self.winfo_y()

    def _drag_move(self, e):
        self.geometry(f"+{e.x_root - self._drag_x}"
                      f"+{e.y_root - self._drag_y}")

    def update_mute(self, muted: bool):
        """Called from main toggle_mute so mini stays in sync."""
        try:
            self._mic_mute.configure(
                text="🔴 MUTED" if muted else "🎙 LIVE",
                bg=C["red_dim"] if muted else C["green"],
                fg=C["text_hi"] if muted else C["bg"])
        except Exception:
            pass
