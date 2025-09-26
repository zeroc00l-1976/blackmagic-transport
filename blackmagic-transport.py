# hyperdeck_gui.py
import os, certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
import re
import json
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import urljoin
import requests

POLL_INTERVAL_MS = 1000
TIMEOUT = 2.5

# Deck presets
DECK_CHOICES = {
    "Deck 1 (x.x.x.x)": "http://x.x.x.x/control/api/v1/",
    "Deck 2 (x.x.x.x)": "http://x.x.x.x/control/api/v1/",
    "Custom": "",  # enabled via text field
}

# Accepts ip, host, with or without scheme, with or without trailing path
# Returns normalized base url like http://x.x.x.x/control/api/v1/
def normalize_base_url(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    # If user typed only IP or hostname, add http://
    if not re.match(r"^https?://", s, re.I):
        s = "http://" + s
    # If user provided just host, host:port, or host with slash, ensure path
    # Strip any trailing spaces
    s = s.strip()
    # If they already included /control/api/v1 or /control/api/v1/, normalize trailing slash
    if re.search(r"/control/api/v1/?$", s, re.I):
        return re.sub(r"/?$", "/", s)
    # If they gave a bare host or arbitrary root, append the control path
    # Remove trailing slash before appending
    s = re.sub(r"/+$", "", s)
    return s + "/control/api/v1/"

class HyperDeckClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/") + "/"

    def _get(self, path: str):
        url = urljoin(self.base_url, path.lstrip("/"))
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, payload: dict | None = None):
        url = urljoin(self.base_url, path.lstrip("/"))
        r = requests.post(url, json=payload or {}, timeout=TIMEOUT)
        if r.status_code == 204 or not r.content:
            return {}
        r.raise_for_status()
        try:
            return r.json()
        except ValueError:
            return {"ok": True, "raw": r.text}

    def get_transport(self, idx: int = 0):
        return self._get(f"transports/{idx}")

    def get_active_clip(self, idx: int = 0):
        try:
            return self._get("clips/active")
        except Exception:
            try:
                clips = self._get("clips")
                items = clips.get("items") if isinstance(clips, dict) else clips
                if isinstance(items, list):
                    for c in items:
                        if c.get("active") is True:
                            return c
            except Exception:
                pass
        return None

    def play(self, idx: int = 0):
        return self._post(f"transports/{idx}/play")

    def stop(self, idx: int = 0):
        return self._post(f"transports/{idx}/stop")

    def record(self, idx: int = 0):
        return self._post(f"transports/{idx}/record")

    def shuttle(self, idx: int = 0, rate: float = 1.0):
        return self._post(f"transports/{idx}/shuttle", {"rate": rate})


def derive_state(tr: dict) -> str:
    for k in ["status", "state", "transport", "transportState", "transportMode", "mode", "playbackStatus"]:
        v = tr.get(k)
        if isinstance(v, str) and v.strip():
            return v
    truthy = lambda x: str(x).lower() in {"1", "true", "yes", "on"}
    if truthy(tr.get("isRecording")) or truthy(tr.get("recording")):
        return "Recording"
    if truthy(tr.get("isPlaying")) or truthy(tr.get("playing")):
        return "Playing"
    if truthy(tr.get("isStopped")) or truthy(tr.get("stopped")):
        return "Stopped"
    return "unknown"


def derive_timecode(tr: dict) -> str:
    for k in ["position", "timecode", "time", "tc", "currentTimecode"]:
        v = tr.get(k)
        if isinstance(v, str) and v.strip():
            return v
        if isinstance(v, (int, float)):
            s = int(v)
            h, rem = divmod(s, 3600)
            m, s = divmod(rem, 60)
            return f"{h:02d}:{m:02d}:{s:02d}:00"
    return "00:00:00:00"


def derive_active_clip_name(clip_info: dict | None) -> str:
    if not clip_info:
        return "—"
    for k in ["name", "clipName", "title", "filename"]:
        v = clip_info.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return "unnamed"


class HyperDeckGUI(ttk.Frame):
    def __init__(self, master, base_url: str, transport_idx: int = 0):
        super().__init__(master, padding=12)
        self.client = HyperDeckClient(base_url)
        self.transport_idx = transport_idx
        self._last_transport_json = {}
        self._last_custom_url = ""  # remember last custom entry

        self._build_ui(master)
        self.after(POLL_INTERVAL_MS, self.refresh_state)

    def _build_ui(self, master):
        master.title("HyperDeck Transport Control")
        master.minsize(680, 320)

        row0 = ttk.Frame(self)
        row0.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for i in range(9):
            row0.columnconfigure(i, weight=1)

        ttk.Label(row0, text="Deck:").grid(row=0, column=0, sticky="w")
        self.deck_var = tk.StringVar()
        deck_names = list(DECK_CHOICES.keys())
        default_deck = "DDR 28 (172.16.17.52)"
        if default_deck not in deck_names:
            default_deck = deck_names[0]
        self.deck_var.set(default_deck)

        self.deck_combo = ttk.Combobox(
            row0,
            textvariable=self.deck_var,
            values=deck_names,
            state="readonly",
            width=28,
        )
        self.deck_combo.grid(row=0, column=1, sticky="ew")
        self.deck_combo.bind("<<ComboboxSelected>>", self.on_deck_change)

        ttk.Label(row0, text="Base URL:").grid(row=0, column=2, padx=(10, 0), sticky="e")
        self.base_url_var = tk.StringVar(value=DECK_CHOICES[default_deck])
        self.base_url_entry = ttk.Entry(row0, textvariable=self.base_url_var, state="readonly")
        self.base_url_entry.grid(row=0, column=3, columnspan=3, sticky="ew")

        self.apply_btn = ttk.Button(row0, text="Apply URL", command=self.apply_custom_url, state="disabled")
        self.apply_btn.grid(row=0, column=6, padx=(8, 0), sticky="ew")

        ttk.Label(row0, text="Transport Index:").grid(row=0, column=7, padx=(10, 0), sticky="e")
        self.idx_var = tk.IntVar(value=self.transport_idx)
        ttk.Spinbox(row0, from_=0, to=7, textvariable=self.idx_var, width=5).grid(row=0, column=8, sticky="w")

        self.btn_show_json = ttk.Button(row0, text="Show transport JSON", command=self.show_transport_json)
        self.btn_show_json.grid(row=0, column=9, padx=(10, 0))

        row1 = ttk.LabelFrame(self, text="Status")
        row1.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        for i in range(6):
            row1.columnconfigure(i, weight=1)

        ttk.Label(row1, text="State:").grid(row=0, column=0, sticky="w", padx=(8, 4), pady=6)
        self.state_var = tk.StringVar(value="—")
        ttk.Label(row1, textvariable=self.state_var).grid(row=0, column=1, sticky="w", pady=6)

        ttk.Label(row1, text="Timecode:").grid(row=0, column=2, sticky="w", padx=(8, 4), pady=6)
        self.tc_var = tk.StringVar(value="—")
        ttk.Label(row1, textvariable=self.tc_var).grid(row=0, column=3, sticky="w", pady=6)

        ttk.Label(row1, text="Clip Name:").grid(row=0, column=4, sticky="w", padx=(8, 4), pady=6)
        self.clip_var = tk.StringVar(value="—")
        ttk.Label(row1, textvariable=self.clip_var, width=30).grid(row=0, column=5, sticky="w", pady=6)

        row2 = ttk.LabelFrame(self, text="Transport")
        row2.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        for i in range(6):
            row2.columnconfigure(i, weight=1)

        self.btn_play = ttk.Button(row2, text="Play", command=self.on_play)
        self.btn_stop = ttk.Button(row2, text="Stop", command=self.on_stop)
        self.btn_rec = ttk.Button(row2, text="Record", command=self.on_record)

        self.btn_rev = ttk.Button(row2, text="Shuttle -2x", command=lambda: self.on_shuttle(-2.0))
        self.btn_slw = ttk.Button(row2, text="Shuttle 0.5x", command=lambda: self.on_shuttle(0.5))
        self.btn_fwd = ttk.Button(row2, text="Shuttle 2x", command=lambda: self.on_shuttle(2.0))

        self.btn_play.grid(row=0, column=0, padx=6, pady=10, sticky="ew")
        self.btn_stop.grid(row=0, column=1, padx=6, pady=10, sticky="ew")
        self.btn_rec.grid(row=0, column=2, padx=6, pady=10, sticky="ew")
        self.btn_rev.grid(row=0, column=3, padx=6, pady=10, sticky="ew")
        self.btn_slw.grid(row=0, column=4, padx=6, pady=10, sticky="ew")
        self.btn_fwd.grid(row=0, column=5, padx=6, pady=10, sticky="ew")

        row3 = ttk.Frame(self)
        row3.grid(row=3, column=0, sticky="ew")
        row3.columnconfigure(0, weight=1)
        self.statusbar = ttk.Label(row3, text="Ready", anchor="w")
        self.statusbar.grid(row=0, column=0, sticky="ew")

        self.grid(sticky="nsew")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        self._apply_deck_selection()

    def on_deck_change(self, event=None):
        self._apply_deck_selection()

    def _apply_deck_selection(self):
        name = self.deck_var.get()
        url = DECK_CHOICES.get(name, "")
        if name == "Custom":
            # Enable editing and restore last custom url if present
            self.base_url_entry.configure(state="normal")
            if self._last_custom_url:
                self.base_url_var.set(self._last_custom_url)
            else:
                # Prefill with schema and control path hint
                self.base_url_var.set("http://172.16.17.xx/control/api/v1/")
            self.apply_btn.configure(state="normal")
            # Do not switch client until user hits Apply
            self.statusbar.config(text="Custom URL pending apply")
        else:
            # Read only for presets
            self.base_url_var.set(url)
            self.base_url_entry.configure(state="readonly")
            self.apply_btn.configure(state="disabled")
            self.client = HyperDeckClient(url)
            self.statusbar.config(text=f"Using preset {name}")

    def apply_custom_url(self):
        raw = self.base_url_var.get().strip()
        normalized = normalize_base_url(raw)
        if not normalized:
            messagebox.showerror("Invalid URL", "Please enter a host or full URL")
            return
        self._last_custom_url = normalized
        self.base_url_var.set(normalized)
        self.client = HyperDeckClient(normalized)
        self.statusbar.config(text=f"Custom URL applied")

    def _update_client_from_inputs(self):
        self.transport_idx = int(self.idx_var.get())

    def refresh_state(self):
        self._update_client_from_inputs()
        try:
            tr = self.client.get_transport(self.transport_idx)
            self._last_transport_json = tr

            state = derive_state(tr)
            position = derive_timecode(tr)

            clip_info = self.client.get_active_clip(self.transport_idx)
            clip_name = derive_active_clip_name(clip_info)

            self.state_var.set(state)
            self.tc_var.set(position)
            self.clip_var.set(clip_name)

            is_recording = state.lower() in {"record", "recording", "inputrecord"} or str(tr.get("isRecording")).lower() in {"true", "1"}
            self._set_record_button_style(is_recording)

            self.statusbar.config(text=f"OK on {self.deck_var.get()}")
        except requests.HTTPError as e:
            self.statusbar.config(text=f"HTTP error: {e.response.status_code}")
            self.state_var.set("error")
            self._set_record_button_style(False)
        except requests.RequestException as e:
            self.statusbar.config(text=f"Network error: {e.__class__.__name__}")
            self.state_var.set("offline")
            self._set_record_button_style(False)
        except Exception as e:
            self.statusbar.config(text=f"Error: {e.__class__.__name__}")
            self._set_record_button_style(False)

        self.after(POLL_INTERVAL_MS, self.refresh_state)

    def _set_record_button_style(self, active: bool):
        self.btn_rec.config(text="Record ●" if active else "Record")

    def show_transport_json(self):
        win = tk.Toplevel(self)
        win.title("Transport JSON")
        win.minsize(520, 360)
        txt = tk.Text(win, wrap="none")
        txt.pack(fill="both", expand=True)
        try:
            pretty = json.dumps(self._last_transport_json, indent=2)
        except Exception:
            pretty = str(self._last_transport_json)
        txt.insert("1.0", pretty)
        txt.configure(state="disabled")

    def on_play(self):
        self._update_client_from_inputs()
        try:
            self.client.play(self.transport_idx)
        except Exception as e:
            messagebox.showerror("Play failed", str(e))

    def on_stop(self):
        self._update_client_from_inputs()
        try:
            self.client.stop(self.transport_idx)
        except Exception as e:
            messagebox.showerror("Stop failed", str(e))

    def on_record(self):
        self._update_client_from_inputs()
        try:
            self.client.record(self.transport_idx)
        except Exception as e:
            messagebox.showerror("Record failed", str(e))

    def on_shuttle(self, rate: float):
        self._update_client_from_inputs()
        try:
            self.client.shuttle(self.transport_idx, rate=rate)
        except Exception as e:
            messagebox.showerror("Shuttle failed", str(e))


def main():
    default_base = DECK_CHOICES["DDR 28 (172.16.17.52)"]
    root = tk.Tk()

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    app = HyperDeckGUI(root, base_url=default_base, transport_idx=0)
    root.mainloop()


if __name__ == "__main__":
    main()
