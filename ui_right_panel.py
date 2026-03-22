"""
ui_right_panel.py — IceCat Show Companion v3.0
RightPanel      : fixed-width right column
ToolsSection    : Quick Folders + Website launcher
NotesSection    : two-tab notepad with autosave
SessionLogSection: timestamped session log
"""

import os, time, webbrowser, tkinter as tk, logging
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime
from pathlib import Path

from config import C, SESSION_DIR, lighten

log = logging.getLogger("icecat.panel")


# ═══════════════════════════════════════════════════════════════
# SECTION HEADER  — shared styled label
# ═══════════════════════════════════════════════════════════════

def _section_hdr(parent, icon: str, title: str):
    f = ctk.CTkFrame(parent, fg_color=C["elevated"],
                     corner_radius=0, height=26)
    f.pack(fill="x")
    f.pack_propagate(False)
    ctk.CTkLabel(f, text=f"  {icon}  {title.upper()}",
                 font=ctk.CTkFont("Segoe UI", 9, "bold"),
                 text_color=C["text_dim"]).pack(
                     side="left", padx=4)
    return f


# ═══════════════════════════════════════════════════════════════
# TOOLS SECTION
# ═══════════════════════════════════════════════════════════════

class ToolsSection(ctk.CTkFrame):
    def __init__(self, parent, cfg):
        super().__init__(parent, fg_color=C["bg2"], corner_radius=0)
        self.cfg = cfg
        _section_hdr(self, "📁", "Quick Folders + Sites")
        self._build()

    def _build(self):
        # 6 folder buttons in 2 rows of 3
        folders_f = ctk.CTkFrame(self, fg_color="transparent")
        folders_f.pack(fill="x", padx=4, pady=(4, 2))

        self._fbtns = []
        for i in range(6):
            d = self.cfg.config["folders"][i] if i < len(
                self.cfg.config["folders"]) else {}
            label = d.get("label", f"Folder {i+1}")
            color = d.get("color","") or C["btn"]
            tc    = d.get("text_color","") or C["text"]
            b = ctk.CTkButton(
                folders_f, text=label, height=26,
                corner_radius=5,
                fg_color=color, hover_color=lighten(color, 1.2),
                text_color=tc,
                font=ctk.CTkFont("Segoe UI", 10),
                command=lambda idx=i: self._open(idx))
            b.grid(row=i//3, column=i%3,
                   padx=2, pady=1, sticky="ew")
            b.bind("<Button-3>", lambda e, idx=i: self._ctx(e, idx))
            self._fbtns.append(b)
        for c in range(3):
            folders_f.grid_columnconfigure(c, weight=1)

        # Website launcher
        web_f = ctk.CTkFrame(self, fg_color="transparent")
        web_f.pack(fill="x", padx=4, pady=(2, 6))

        self._site_var = ctk.StringVar()
        self._site_menu = ctk.CTkOptionMenu(
            web_f, values=["(none)"],
            variable=self._site_var,
            width=170, height=26,
            font=ctk.CTkFont("Segoe UI", 10))
        self._site_menu.pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            web_f, text="Go", width=36, height=26,
            fg_color=C["blue_mid"],
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            command=self._launch
        ).pack(side="left", padx=(0, 2))
        ctk.CTkButton(
            web_f, text="+", width=26, height=26,
            corner_radius=5,
            fg_color=C["btn"],
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            command=self._add_site
        ).pack(side="left", padx=(0, 2))
        ctk.CTkButton(
            web_f, text="🗑", width=26, height=26,
            corner_radius=5,
            fg_color=C["btn"],
            font=ctk.CTkFont("Segoe UI", 10),
            command=self._del_site
        ).pack(side="left")
        self._refresh_sites()

    def _open(self, idx):
        folders = self.cfg.config.get("folders", [])
        if idx >= len(folders):
            return
        path = folders[idx].get("path", "")
        if not path:
            messagebox.showinfo("Empty",
                                "Right-click to assign a folder.")
            return
        if os.path.isdir(path):
            os.startfile(path)
        else:
            messagebox.showerror("Not Found",
                                 f"Folder not found:\n{path}")

    def _launch(self):
        label = self._site_var.get()
        sites = self.cfg.config.get("websites", [])
        for s in sites:
            if s["label"] == label:
                webbrowser.open(s["url"])
                return

    def _ctx(self, e, idx):
        m = tk.Menu(self, tearoff=0,
                    bg=C["surface"], fg=C["text"],
                    activebackground=C["blue_mid"],
                    font=("Segoe UI", 10))
        m.add_command(label="📂  Assign Folder",
                      command=lambda: self._assign(idx))
        m.add_command(label="🎨  Customize Button...",
                      command=lambda: self._customize(idx))
        m.add_command(label="🗑  Clear",
                      command=lambda: self._clear(idx))
        m.tk_popup(e.x_root, e.y_root)

    def _assign(self, idx):
        path = filedialog.askdirectory(title="Select Folder")
        if path:
            folders = self.cfg.config.setdefault("folders", [])
            while len(folders) <= idx:
                folders.append({"label":f"Folder {len(folders)+1}",
                                "path":"","color":"","text_color":""})
            label = Path(path).name[:12] or f"F{idx+1}"
            folders[idx]["path"]  = path
            folders[idx]["label"] = label
            self.cfg.save()
            self._fbtns[idx].configure(text=label)

    def _customize(self, idx):
        from ui_dialogs import ButtonSettingsDialog
        folders = self.cfg.config.get("folders", [])
        d = folders[idx] if idx < len(folders) else {}
        dlg = ButtonSettingsDialog(
            self.winfo_toplevel(),
            label=d.get("label",""),
            color=d.get("color",""),
            text_color=d.get("text_color",""),
            allow_rename=True)
        self.winfo_toplevel().wait_window(dlg)
        if dlg.result:
            while len(self.cfg.config["folders"]) <= idx:
                self.cfg.config["folders"].append(
                    {"label":f"Folder {idx+1}","path":"",
                     "color":"","text_color":""})
            self.cfg.config["folders"][idx].update({
                "label":      dlg.result["label"] or d.get("label",""),
                "color":      dlg.result["color"],
                "text_color": dlg.result["text_color"],
            })
            self.cfg.save()
            self._fbtns[idx].configure(
                text=self.cfg.config["folders"][idx]["label"],
                fg_color=dlg.result["color"] or C["btn"],
                text_color=dlg.result["text_color"] or C["text"])

    def _clear(self, idx):
        if idx < len(self.cfg.config.get("folders",[])):
            self.cfg.config["folders"][idx]["path"] = ""
            self.cfg.save()

    def refresh(self):
        folders = self.cfg.config.get("folders", [])
        for i, b in enumerate(self._fbtns):
            d = folders[i] if i < len(folders) else {}
            b.configure(text=d.get("label", f"Folder {i+1}"),
                        fg_color=d.get("color","") or C["btn"],
                        text_color=d.get("text_color","") or C["text"])
        self._refresh_sites()

    def _refresh_sites(self):
        sites  = self.cfg.config.get("websites", [])
        labels = [s["label"] for s in sites] or ["(none)"]
        self._site_menu.configure(values=labels)
        cur = self._site_var.get()
        if cur not in labels:
            self._site_var.set(labels[0])

    def _add_site(self):
        """Quick-add a website via a simple two-field dialog."""
        dlg = tk.Toplevel(self)
        dlg.title("Add Website")
        dlg.configure(bg=C["bg2"])
        dlg.resizable(False, False)
        dlg.grab_set()
        pad = dict(padx=10, pady=4)
        tk.Label(dlg, text="Label:", bg=C["bg2"],
                 fg=C["text"], font=("Segoe UI", 10)).grid(
                     row=0, column=0, sticky="e", **pad)
        lbl_e = tk.Entry(dlg, bg=C["surface"], fg=C["text"],
                         insertbackground=C["text"],
                         relief="flat", font=("Segoe UI", 10))
        lbl_e.grid(row=0, column=1, sticky="ew", **pad)
        tk.Label(dlg, text="URL:", bg=C["bg2"],
                 fg=C["text"], font=("Segoe UI", 10)).grid(
                     row=1, column=0, sticky="e", **pad)
        url_e = tk.Entry(dlg, width=32, bg=C["surface"],
                         fg=C["text"], insertbackground=C["text"],
                         relief="flat", font=("Segoe UI", 10))
        url_e.grid(row=1, column=1, sticky="ew", **pad)
        url_e.insert(0, "https://")

        def _ok():
            lbl = lbl_e.get().strip()
            url = url_e.get().strip()
            if not lbl or not url:
                return
            self.cfg.config.setdefault("websites", []).append(
                {"label": lbl, "url": url})
            self.cfg.save()
            self._refresh_sites()
            self._site_var.set(lbl)
            dlg.destroy()

        btn_f = tk.Frame(dlg, bg=C["bg2"])
        btn_f.grid(row=2, column=0, columnspan=2, pady=6)
        tk.Button(btn_f, text="Add", bg=C["blue_mid"],
                  fg=C["text_hi"], relief="flat",
                  padx=14, pady=4,
                  font=("Segoe UI", 10, "bold"),
                  command=_ok).pack(side="left", padx=4)
        tk.Button(btn_f, text="Cancel", bg=C["btn"],
                  fg=C["text"], relief="flat",
                  padx=10, pady=4,
                  font=("Segoe UI", 10),
                  command=dlg.destroy).pack(side="left", padx=4)
        url_e.bind("<Return>", lambda e: _ok())
        lbl_e.focus_set()

    def _del_site(self):
        """Delete the currently selected website."""
        label = self._site_var.get()
        sites = self.cfg.config.get("websites", [])
        new   = [s for s in sites if s["label"] != label]
        if len(new) == len(sites):
            return
        from tkinter import messagebox
        if messagebox.askyesno("Remove Site",
                               f"Remove '{label}'?"):
            self.cfg.config["websites"] = new
            self.cfg.save()
            self._refresh_sites()


# ═══════════════════════════════════════════════════════════════
# NOTES SECTION
# ═══════════════════════════════════════════════════════════════

class NotesSection(ctk.CTkFrame):
    def __init__(self, parent, cfg, get_elapsed=None,
                 get_is_live=None, session_log=None):
        super().__init__(parent, fg_color=C["bg2"], corner_radius=0)
        self.cfg         = cfg
        self.get_elapsed = get_elapsed or (lambda: "")
        self.get_is_live = get_is_live or (lambda: False)
        self.session_log = session_log
        self._boxes:  dict = {}
        self._tabs:   list = []
        self._cur_tab = 0
        self._autosave_job = None
        _section_hdr(self, "📝", "Notes")
        self._build()
        self._schedule_autosave()

    def _build(self):
        tab_names = self.cfg.config.get(
            "note_tabs", ["Show Notes", "Premises & Ideas"])

        # Tab buttons
        tab_bar = tk.Frame(self, bg=C["bg2"])
        tab_bar.pack(fill="x")
        self._tab_btns = []
        for i, name in enumerate(tab_names):
            b = tk.Button(
                tab_bar, text=name,
                bg=C["blue_mid"] if i == 0 else C["btn"],
                fg=C["text_hi"] if i == 0 else C["text_dim"],
                activebackground=C["blue_mid"],
                relief="flat", bd=0, padx=10,
                font=("Segoe UI", 9,
                       "bold" if i == 0 else "normal"),
                cursor="hand2",
                command=lambda idx=i: self._switch(idx))
            b.pack(side="left", fill="y", padx=1)
            self._tab_btns.append(b)

        # Clear + Save buttons on the right of the tab bar
        tk.Button(
            tab_bar, text="💾 Save",
            bg=C["btn"], fg=C["text_dim"],
            activebackground=C["btn_hover"],
            relief="flat", bd=0, padx=8,
            font=("Segoe UI", 9), cursor="hand2",
            command=self._save_and_export
        ).pack(side="right", padx=2, pady=1)

        tk.Button(
            tab_bar, text="🗑 Clear",
            bg=C["btn"], fg=C["text_dim"],
            activebackground=C["btn_hover"],
            relief="flat", bd=0, padx=8,
            font=("Segoe UI", 9), cursor="hand2",
            command=self._clear_current
        ).pack(side="right", padx=2, pady=1)

        # Text boxes (stacked, only current visible)
        self._box_frame = tk.Frame(self, bg=C["bg2"])
        self._box_frame.pack(fill="both", expand=True)

        content = self.cfg.config.get("notes_content", {})
        for i, name in enumerate(tab_names):
            box = tk.Text(
                self._box_frame,
                bg=C["surface"], fg=C["text"],
                insertbackground=C["amber"],
                selectbackground=C["blue_mid"],
                font=("Segoe UI", 10),
                relief="flat", bd=0,
                wrap="word", padx=6, pady=6)
            saved = content.get(name, "")
            if saved:
                box.insert("1.0", saved)
            self._boxes[name] = box
            self._tabs.append(name)

        # Show first tab
        self._switch(0)

    def _switch(self, idx: int):
        self._save_current()
        self._cur_tab = idx
        for name, box in self._boxes.items():
            box.pack_forget()
        tab_name = self._tabs[idx] if idx < len(self._tabs) else ""
        if tab_name in self._boxes:
            self._boxes[tab_name].pack(
                fill="both", expand=True)
        for i, b in enumerate(self._tab_btns):
            active = (i == idx)
            b.configure(
                bg=C["blue_mid"] if active else C["btn"],
                fg=C["text_hi"] if active else C["text_dim"],
                font=("Segoe UI", 9,
                       "bold" if active else "normal"))

    def _clear_current(self):
        """Clear the currently visible notes tab."""
        from tkinter import messagebox
        if self._cur_tab < len(self._tabs):
            name = self._tabs[self._cur_tab]
            if messagebox.askyesno("Clear Notes",
                                   f"Clear '{name}'?"):
                box = self._boxes.get(name)
                if box:
                    box.delete("1.0", "end")
                self.cfg.config.setdefault(
                    "notes_content", {})[name] = ""
                self.cfg.save()

    def _save_current(self):
        if self._cur_tab < len(self._tabs):
            name = self._tabs[self._cur_tab]
            if name in self._boxes:
                content = self._boxes[name].get("1.0", "end-1c")
                self.cfg.config.setdefault(
                    "notes_content", {})[name] = content

    def _insert_timestamp(self):
        fmt   = self.cfg.config.get("timestamp_format", "%H:%M:%S")
        ts    = datetime.now().strftime(fmt)
        elap  = self.get_elapsed()
        entry = f"\n[{ts}]" + (f" +{elap}" if elap else "") + " "
        if self._cur_tab < len(self._tabs):
            name = self._tabs[self._cur_tab]
            box  = self._boxes.get(name)
            if box:
                box.insert("end", entry)
                box.see("end")

    def _insert_gold(self):
        fmt   = self.cfg.config.get("timestamp_format", "%H:%M:%S")
        ts    = datetime.now().strftime(fmt)
        elap  = self.get_elapsed()
        entry = f"\n⭐ GOLD [{ts}]" + (f" +{elap}" if elap else "") + " "
        if self._cur_tab < len(self._tabs):
            name = self._tabs[self._cur_tab]
            box  = self._boxes.get(name)
            if box:
                box.insert("end", entry)
                box.see("end")
        if self.session_log:
            try:
                self.session_log.log_event("⭐ Gold Moment")
            except Exception:
                pass

    def save_all(self):
        """Save all tabs to config silently (no dialog)."""
        self._save_current()
        self.cfg.save()

    def _save_and_export(self):
        """Called by the Save button — saves config then prompts for .txt export."""
        self._save_current()
        self.cfg.save()
        self._export_to_file()

    def _export_to_file(self):
        """Export current tab's notes to a timestamped .txt file."""
        from tkinter import filedialog
        from datetime import datetime as _dt
        from pathlib import Path
        if self._cur_tab >= len(self._tabs):
            return
        name    = self._tabs[self._cur_tab]
        content = self.cfg.config.get(
            "notes_content", {}).get(name, "")
        if not content.strip():
            from tkinter import messagebox
            messagebox.showinfo("Nothing to Save",
                               "This notes tab is empty.")
            return
        ts       = _dt.now().strftime("%Y-%m-%d_%H%M")
        default  = f"notes_{name.replace(' ','_')}_{ts}.txt"
        path = filedialog.asksaveasfilename(
            title="Save Notes As",
            defaultextension=".txt",
            initialfile=default,
            filetypes=[("Text file", "*.txt"),
                       ("All files", "*.*")])
        if path:
            try:
                Path(path).write_text(content, encoding="utf-8")
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Save Failed", str(e))

    def get_all(self) -> dict:
        self._save_current()
        return self.cfg.config.get("notes_content", {})

    def _schedule_autosave(self):
        interval = max(30, self.cfg.config.get(
            "autosave_interval", 5)) * 60 * 1000
        self._autosave_job = self.after(interval, self._autosave)

    def _autosave(self):
        self.save_all()
        self._schedule_autosave()


# ═══════════════════════════════════════════════════════════════
# SESSION LOG SECTION
# ═══════════════════════════════════════════════════════════════

class SessionLogSection(ctk.CTkFrame):
    def __init__(self, parent, cfg,
                 notes_fn=None, get_elapsed=None,
                 get_is_live=None):
        super().__init__(parent, fg_color=C["bg2"], corner_radius=0)
        self.cfg         = cfg
        self.notes_fn    = notes_fn or (lambda: {})
        self.get_elapsed = get_elapsed or (lambda: "")
        self.get_is_live = get_is_live or (lambda: False)
        self._paused     = False
        self._entries:   list = []
        self._log_path   = None
        _section_hdr(self, "📋", "Session Log")
        self._build()
        self._schedule_autosave()

    def _build(self):
        # Action bar
        bar = tk.Frame(self, bg=C["bg2"])
        bar.pack(fill="x")

        self._pause_btn = tk.Button(
            bar, text="⏸ Pause",
            bg=C["btn"], fg=C["text_dim"],
            activebackground=C["btn_hover"],
            relief="flat", bd=0, padx=8,
            font=("Segoe UI", 9), cursor="hand2",
            command=self._toggle_pause)
        self._pause_btn.pack(side="left", padx=2, pady=2)

        tk.Button(bar, text="📋 Copy Summary",
                  bg=C["btn"], fg=C["text_dim"],
                  activebackground=C["btn_hover"],
                  relief="flat", bd=0, padx=8,
                  font=("Segoe UI", 9), cursor="hand2",
                  command=self._copy_summary
                  ).pack(side="left", padx=2, pady=2)

        tk.Button(bar, text="💾 Export",
                  bg=C["btn"], fg=C["text_dim"],
                  activebackground=C["btn_hover"],
                  relief="flat", bd=0, padx=8,
                  font=("Segoe UI", 9), cursor="hand2",
                  command=self._export
                  ).pack(side="left", padx=2, pady=2)

        tk.Button(bar, text="🗑 Clear",
                  bg=C["btn"], fg=C["text_dim"],
                  activebackground=C["btn_hover"],
                  relief="flat", bd=0, padx=8,
                  font=("Segoe UI", 9), cursor="hand2",
                  command=self._clear_log
                  ).pack(side="left", padx=2, pady=2)

        # ── Timestamp entry row (packed first — always visible) ────
        self._PLACEHOLDER = "note (optional)..."
        ts_row = tk.Frame(self, bg=C["bg2"])
        ts_row.pack(fill="x", padx=2, pady=(0, 2))

        # Log text
        log_outer = tk.Frame(self, bg=C["surface"])
        log_outer.pack(fill="both", expand=True, padx=2, pady=(0, 2))

        sb = tk.Scrollbar(log_outer, bg=C["surface"],
                          troughcolor=C["bg"], width=10)
        self._log = tk.Text(
            log_outer,
            bg=C["surface"], fg=C["text_dim"],
            insertbackground=C["text"],
            font=("Consolas", 9),
            relief="flat", bd=0,
            wrap="word", state="disabled",
            yscrollcommand=sb.set)
        sb.config(command=self._log.yview)
        sb.pack(side="right", fill="y")
        self._log.pack(side="left", fill="both", expand=True,
                       padx=4, pady=4)

        # Tags
        self._log.tag_config("ts",    foreground=C["text_dim"])
        self._log.tag_config("label", foreground=C["text"])
        self._log.tag_config("event", foreground=C["amber"])
        self._log.tag_config("live",  foreground=C["green"])
        self._log.tag_config("gold",  foreground=C["gold"])
        self._log.tag_config("music", foreground=C["blue_hi"])
        self._log.tag_config("stamp", foreground=C["amber_hi"])

        # ts_row contents:

        self._stamp_var = tk.StringVar()
        self._stamp_entry = tk.Entry(
            ts_row,
            textvariable=self._stamp_var,
            bg=C["surface"],
            fg=C["text_dim"],
            insertbackground=C["text"],
            relief="flat", bd=0,
            font=("Segoe UI", 9))
        self._stamp_entry.pack(side="left", fill="x", expand=True,
                               padx=(0, 4), ipady=4, ipadx=4)
        self._stamp_entry.bind("<Return>", lambda e: self._do_stamp())
        self._stamp_var.set(self._PLACEHOLDER)

        def _on_focus_in(e):
            if self._stamp_var.get() == self._PLACEHOLDER:
                self._stamp_var.set("")
                self._stamp_entry.configure(fg=C["text"])

        def _on_focus_out(e):
            if not self._stamp_var.get().strip():
                self._stamp_var.set(self._PLACEHOLDER)
                self._stamp_entry.configure(fg=C["text_dim"])

        self._stamp_entry.bind("<FocusIn>",  _on_focus_in)
        self._stamp_entry.bind("<FocusOut>", _on_focus_out)

        tk.Button(
            ts_row,
            text="📌 Timestamp",
            bg=C["btn"],
            fg=C["amber_hi"],
            activebackground=C["btn_hover"],
            activeforeground=C["text_hi"],
            relief="flat", bd=0,
            padx=10, pady=4,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=self._do_stamp,
        ).pack(side="right")

    def _do_stamp(self):
        raw  = self._stamp_var.get().strip()
        note = "" if raw == self._PLACEHOLDER else raw
        ts   = self._ts()
        text = f"📌 {note}" if note else "📌"
        self._entries.append({"ts": ts, "type": "stamp", "text": note})
        self._write([
            (f"[{ts}] ", "ts"),
            (text,       "stamp"),
        ])
        # Clear the entry
        self._stamp_var.set("")
        self._stamp_entry.configure(fg=C["text"])
        self._stamp_entry.focus_set()

    def _write(self, parts: list):
        """parts = list of (text, tag) tuples."""
        self._log.configure(state="normal")
        for text, tag in parts:
            self._log.insert("end", text, tag)
        self._log.insert("end", "\n")
        if not self._paused:
            self._log.see("end")
        self._log.configure(state="disabled")

    def _ts(self) -> str:
        """Always returns date + time. If live, appends elapsed."""
        from datetime import datetime as _dt
        wall = _dt.now().strftime("%b %d %H:%M:%S")
        if self.get_is_live():
            elap = self.get_elapsed()
            return f"{wall}  [{elap}]"
        return wall

    def _clear_log(self):
        from tkinter import messagebox
        if messagebox.askyesno("Clear Log", "Clear the session log?"):
            self._log.configure(state="normal")
            self._log.delete("1.0", "end")
            self._log.configure(state="disabled")
            self._entries.clear()
            # Reset paused state so the log is live again after clearing
            self._paused = False
            self._pause_btn.configure(
                text="⏸ Pause", fg=C["text_dim"])

    def log_event(self, text: str):
        ts = self._ts()
        self._entries.append({"ts": ts, "type": "event", "text": text})
        self._write([
            (f"[{ts}] ", "ts"),
            (text, "event"),
        ])

    def log_live_start(self):
        ts = self._ts()
        self._entries.append({"ts": ts, "type": "live_start"})
        self._write([
            (f"[{ts}] ", "ts"),
            ("🔴 WENT LIVE", "live"),
        ])

    def log_live_end(self, duration: str):
        ts = self._ts()
        self._entries.append({"ts": ts, "type": "live_end",
                               "duration": duration})
        self._write([
            (f"[{ts}] ", "ts"),
            (f"⏹ ENDED LIVE  ({duration})", "live"),
        ])

    def log_sound(self, label: str, path: str,
                  duration: float, from_queue: bool = False):
        """Log every audio play — soundboard and queue."""
        ts      = self._ts()
        dur_str = (f"{int(duration//60)}:{int(duration%60):02d}"
                   if duration > 0 else "--:--")
        src_tag = "Queue" if from_queue else "Board"
        self._entries.append({"ts": ts, "type": "sound",
                               "label": label, "duration": dur_str})
        self._write([
            (f"[{ts}] ", "ts"),
            (f"▶ {label}", "label"),
            (f"  ({dur_str}) [{src_tag}]", "ts"),
        ])

    def log_countdown_start(self, mm: int, ss: int):
        ts = self._ts()
        self._write([
            (f"[{ts}] ", "ts"),
            (f"⏱ Countdown started: {mm:02d}:{ss:02d}", "event"),
        ])

    def log_countdown_end(self):
        ts = self._ts()
        self._write([
            (f"[{ts}] ", "ts"),
            ("⏱ Countdown finished", "event"),
        ])

    def _toggle_pause(self):
        self._paused = not self._paused
        self._pause_btn.configure(
            text="▶ Resume" if self._paused else "⏸ Pause",
            fg=C["amber"] if self._paused else C["text_dim"])
        if not self._paused:
            self._log.see("end")

    def _copy_summary(self):
        try:
            import pyperclip
            pyperclip.copy(self._build_summary())
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(self._build_summary())

    def _build_summary(self) -> str:
        lines = []
        for e in self._entries:
            if e["type"] == "live_start":
                lines.append(f"[{e['ts']}] Went live")
            elif e["type"] == "live_end":
                lines.append(
                    f"[{e['ts']}] Ended ({e.get('duration','')})")
            elif e["type"] == "sound":
                lines.append(
                    f"[{e['ts']}] ▶ {e.get('label','')} "
                    f"({e.get('duration','')})")
            elif e["type"] == "event":
                lines.append(f"[{e['ts']}] {e.get('text','')}")
            elif e["type"] == "stamp":
                note = e.get("text", "")
                lines.append(f"[{e['ts']}] 📌 {note}" if note
                             else f"[{e['ts']}] 📌")
        return "\n".join(lines)

    def get_summary_text(self) -> str:
        return self._build_summary()

    def _export(self):
        from tkinter import filedialog
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="Export Session Log",
            initialfile=f"session_{ts}.txt",
            defaultextension=".txt",
            filetypes=[("Text","*.txt")])
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._build_summary())
            except Exception as e:
                import tkinter.messagebox as mb
                mb.showerror("Export Failed", str(e))

    def _schedule_autosave(self):
        interval = max(60, self.cfg.config.get(
            "log_autosave_interval", 120)) * 1000
        self.after(interval, self._autosave)

    def _autosave(self):
        try:
            SESSION_DIR.mkdir(parents=True, exist_ok=True)
            ts   = datetime.now().strftime("%Y%m%d")
            path = SESSION_DIR / f"session_{ts}.txt"
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._build_summary())
        except Exception as e:
            log.warning(f"Session autosave: {e}")
        self._schedule_autosave()


# ═══════════════════════════════════════════════════════════════
# BITS BOARD SECTION
# ═══════════════════════════════════════════════════════════════

class BitsBoardSection(ctk.CTkFrame):
    """
    Bits board — stores show bit ideas with title, notes, done state.
    Bits are saved to config.json automatically on every change.
    """
    def __init__(self, parent, cfg):
        super().__init__(parent, fg_color=C["bg2"], corner_radius=8)
        self.cfg = cfg
        self.idx = 0
        # Ensure at least one bit exists in config
        if not self.cfg.config.get("bits"):
            self.cfg.config["bits"] = [
                {"title": "Bit 1", "content": "", "done": False}]
        self._build()
        self._load()

    def _build(self):
        # ── Header ───────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(hdr, text="📌  BITS BOARD",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=C["text"]).pack(side="left")
        # Right-side header buttons
        for txt, cmd, col in [
            ("🎲", self._random,    C["btn"]),
            ("↺ Reset", self._reset_all, C["btn"]),
            ("🗑 Delete", self._del,    C["btn"]),
            ("+ Add Bit", self._new,  C["blue_mid"]),
        ]:
            ctk.CTkButton(hdr, text=txt, height=24, corner_radius=5,
                          fg_color=col, font=ctk.CTkFont("Segoe UI", 10),
                          command=cmd).pack(side="right", padx=2)

        # ── Nav row: prev | title entry | next | counter ─────────
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=8, pady=(2, 0))

        ctk.CTkButton(nav, text="◀", width=28, height=26,
                      corner_radius=5, fg_color=C["btn"],
                      command=self._prev).pack(side="left")

        self.title_e = ctk.CTkEntry(nav, height=26,
                                     font=ctk.CTkFont("Segoe UI", 11),
                                     placeholder_text="Bit title…")
        self.title_e.pack(side="left", padx=3, fill="x", expand=True)

        ctk.CTkButton(nav, text="▶", width=28, height=26,
                      corner_radius=5, fg_color=C["btn"],
                      command=self._next_bit).pack(side="left")

        self.count_lbl = ctk.CTkLabel(nav, text="1/1", width=36,
                                       font=ctk.CTkFont("Segoe UI", 10),
                                       text_color=C["text_dim"])
        self.count_lbl.pack(side="left", padx=4)

        # ── Done + Save row ───────────────────────────────────────
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=8, pady=(2, 2))

        self.done_var = ctk.BooleanVar()
        ctk.CTkCheckBox(ctrl, text="✓ Mark Done",
                        variable=self.done_var,
                        font=ctk.CTkFont("Segoe UI", 10),
                        fg_color=C["green"],
                        command=self._toggle_done
                        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(ctrl, text="💾 Save Bit", height=26,
                      corner_radius=5, fg_color=C["blue"],
                      font=ctk.CTkFont("Segoe UI", 10, "bold"),
                      command=self._save
                      ).pack(side="right")

        # ── Content textbox ───────────────────────────────────────
        self.content = ctk.CTkTextbox(
            self, height=72, fg_color=C["bg"],
            text_color=C["text"], font=ctk.CTkFont("Consolas", 11),
            wrap="word")
        self.content.pack(fill="both", expand=True,
                          padx=4, pady=(2, 4))

    # ── Data helpers ──────────────────────────────────────────────

    def _bits(self) -> list:
        """Always returns the live bits list, initialising if needed."""
        bits = self.cfg.config.setdefault("bits", [])
        if not bits:
            bits.append({"title": "Bit 1", "content": "", "done": False})
        return bits

    def _load(self):
        bits = self._bits()
        self.idx = max(0, min(self.idx, len(bits) - 1))
        bit  = bits[self.idx]
        done = bit.get("done", False)
        self.title_e.delete(0, "end")
        self.title_e.insert(0, bit.get("title", ""))
        self.content.delete("1.0", "end")
        self.content.insert("1.0", bit.get("content", ""))
        self.done_var.set(done)
        self.count_lbl.configure(text=f"{self.idx+1}/{len(bits)}")
        col = C["text_dim"] if done else C["text"]
        self.title_e.configure(text_color=col)
        self.content.configure(text_color=col)

    def _save(self):
        """Persist current bit to config.json."""
        bits = self._bits()
        bits[self.idx] = {
            "title":   self.title_e.get().strip() or f"Bit {self.idx+1}",
            "content": self.content.get("1.0", "end-1c"),
            "done":    self.done_var.get(),
        }
        self.cfg.save()

    # ── Actions ───────────────────────────────────────────────────

    def _toggle_done(self):
        self._save()
        self._load()

    def _new(self):
        self._save()
        bits = self._bits()
        bits.append({"title": f"Bit {len(bits)+1}",
                     "content": "", "done": False})
        self.idx = len(bits) - 1
        self.cfg.save()
        self._load()

    def _del(self):
        from tkinter import messagebox
        bits = self._bits()
        if len(bits) <= 1:
            messagebox.showinfo("Can't Delete",
                                "Need at least one bit.")
            return
        name = bits[self.idx].get("title", f"Bit {self.idx+1}")
        if messagebox.askyesno("Delete Bit",
                               f'Delete {name!r}?'):
            bits.pop(self.idx)
            self.idx = max(0, self.idx - 1)
            self.cfg.save()
            self._load()

    def _prev(self):
        self._save()
        bits = self._bits()
        self.idx = (self.idx - 1) % len(bits)
        self._load()

    def _next_bit(self):
        self._save()
        bits = self._bits()
        self.idx = (self.idx + 1) % len(bits)
        self._load()

    def _random(self):
        import random
        self._save()
        bits = self._bits()
        if len(bits) > 1:
            choices = [i for i in range(len(bits)) if i != self.idx]
            self.idx = random.choice(choices)
        self._load()

    def _reset_all(self):
        from tkinter import messagebox
        if messagebox.askyesno("Reset All",
                               "Clear all Done marks?"):
            for bit in self._bits():
                bit["done"] = False
            self.cfg.save()
            self._load()



# ═══════════════════════════════════════════════════════════════
# QUICK COPY SNIPPETS
# ═══════════════════════════════════════════════════════════════

class SnippetsSection(ctk.CTkFrame):
    def __init__(self, parent, cfg):
        super().__init__(parent, fg_color=C["bg2"], corner_radius=0)
        self.cfg = cfg
        self._build()

    def _build(self):
        _section_hdr(self, "📎", "Quick Copy")
        hdr2 = tk.Frame(self, bg=C["bg2"])
        hdr2.pack(fill="x", padx=4, pady=(0, 2))
        tk.Button(hdr2, text="+ Add",
                  bg=C["btn"], fg=C["text_dim"],
                  activebackground=C["btn_hover"],
                  relief="flat", bd=0, padx=8,
                  font=("Segoe UI", 9), cursor="hand2",
                  command=self._add).pack(side="right", padx=2, pady=1)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                               height=90)
        self._scroll.pack(fill="x", padx=2, pady=(0, 4))
        self._populate()

    def _populate(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        for i, s in enumerate(self.cfg.config.get("snippets", [])):
            row = tk.Frame(self._scroll, bg=C["bg2"])
            row.pack(fill="x", pady=1)
            tk.Button(row, text=s["label"], anchor="w",
                      bg=C["btn"], fg=C["text"],
                      activebackground=C["btn_hover"],
                      relief="flat", bd=0, padx=8, pady=3,
                      font=("Segoe UI", 9), cursor="hand2",
                      command=lambda t=s["text"]: self._copy(t)
                      ).pack(side="left", fill="x", expand=True, padx=(0,2))
            tk.Button(row, text="✏", width=3,
                      bg=C["btn"], fg=C["text_dim"],
                      activebackground=C["btn_hover"],
                      relief="flat", bd=0,
                      font=("Segoe UI", 9), cursor="hand2",
                      command=lambda idx=i: self._edit(idx)
                      ).pack(side="left", padx=1)
            tk.Button(row, text="🗑", width=3,
                      bg=C["btn"], fg=C["text_dim"],
                      activebackground=C["btn_hover"],
                      relief="flat", bd=0,
                      font=("Segoe UI", 9), cursor="hand2",
                      command=lambda idx=i: self._delete(idx)
                      ).pack(side="left", padx=1)

    def _copy(self, text: str):
        try:
            import pyperclip
            pyperclip.copy(text)
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(text)

    def _add(self): self._editor(None)
    def _edit(self, i): self._editor(i)

    def _editor(self, idx):
        import customtkinter as _ctk
        w = _ctk.CTkToplevel(self)
        w.title("Quick Copy Snippet")
        w.geometry("360x200")
        w.configure(fg_color=C["bg2"])
        w.grab_set()
        _ctk.CTkLabel(w, text="Label:", font=_ctk.CTkFont("Segoe UI", 12)).pack(pady=(14,0))
        le = _ctk.CTkEntry(w, width=310, font=_ctk.CTkFont("Segoe UI", 12))
        le.pack(pady=4)
        _ctk.CTkLabel(w, text="Text:", font=_ctk.CTkFont("Segoe UI", 12)).pack()
        te = _ctk.CTkEntry(w, width=310, font=_ctk.CTkFont("Segoe UI", 12))
        te.pack(pady=4)
        if idx is not None:
            s = self.cfg.config["snippets"][idx]
            le.insert(0, s["label"]); te.insert(0, s["text"])
        def save():
            l, t = le.get().strip(), te.get().strip()
            if l and t:
                sn = {"label": l, "text": t}
                if idx is not None:
                    self.cfg.config["snippets"][idx] = sn
                else:
                    self.cfg.config.setdefault("snippets", []).append(sn)
                self.cfg.save(); self._populate(); w.destroy()
        _ctk.CTkButton(w, text="Save", fg_color=C["blue_mid"],
                       font=_ctk.CTkFont("Segoe UI", 12),
                       command=save).pack(pady=8)

    def _delete(self, idx):
        from tkinter import messagebox
        if messagebox.askyesno("Delete", "Remove this snippet?"):
            self.cfg.config.get("snippets", []).pop(idx)
            self.cfg.save(); self._populate()



# ═══════════════════════════════════════════════════════════════
# RIGHT PANEL  — assembles all sections
# ═══════════════════════════════════════════════════════════════

class RightPanel(ctk.CTkFrame):
    """
    Fixed-width right column.
    Sections stacked vertically with appropriate weighting.
    """

    WIDTH = 340

    def __init__(self, parent, cfg, audio,
                 get_elapsed=None, get_is_live=None):
        super().__init__(parent, fg_color=C["bg2"],
                         corner_radius=0, width=self.WIDTH)
        self.cfg         = cfg
        self.audio       = audio
        self.get_elapsed = get_elapsed or (lambda: "")
        self.get_is_live = get_is_live or (lambda: False)
        self.pack_propagate(False)
        self._build()

    def _build(self):
        # Tools
        self.tools = ToolsSection(self, self.cfg)
        self.tools.pack(fill="x")

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        # Bits Board
        self.bits_board = BitsBoardSection(self, self.cfg)
        self.bits_board.pack(fill="x")

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        # Session log (expands)
        self.session_log = SessionLogSection(
            self, self.cfg,
            get_elapsed=self.get_elapsed,
            get_is_live=self.get_is_live)
        self.session_log.pack(fill="both", expand=True)



