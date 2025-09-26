#!/usr/bin/env python3
"""
Blackmagic HyperDeck Transport Control v2
Enhanced version with better error handling, UI/UX, and code organization.
"""

import json
import logging
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import certifi
import requests
import tkinter as tk
from tkinter import ttk, messagebox

# Set SSL certificate path
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hyperdeck.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration constants and settings."""
    POLL_INTERVAL_MS = 1000
    POLL_INTERVAL_MS_DISCONNECTED = 5000
    TIMEOUT = 2.5
    MAX_RETRIES = 3
    DEFAULT_TRANSPORT_IDX = 0
    WINDOW_MIN_WIDTH = 680
    WINDOW_MIN_HEIGHT = 320
    SETTINGS_FILE = Path.home() / '.hyperdeck_settings.json'
    
    # Deck presets
    DECK_CHOICES = {
        "DDR 27 (172.16.17.51)": "http://172.16.17.51/control/api/v1/",
        "DDR 28 (172.16.17.52)": "http://172.16.17.52/control/api/v1/",
        "Custom": "",  # enabled via text field
    }


class SettingsManager:
    """Manages application settings persistence."""
    
    def __init__(self, settings_file: Path = Config.SETTINGS_FILE):
        self.settings_file = settings_file
        self._settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load settings: {e}")
        return self._get_default_settings()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings."""
        return {
            "last_deck": "DDR 28 (172.16.17.52)",
            "last_custom_url": "",
            "transport_idx": Config.DEFAULT_TRANSPORT_IDX,
            "window_geometry": None,
        }
    
    def save_settings(self) -> None:
        """Save current settings to file."""
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        self._settings[key] = value
        self.save_settings()


class ConnectionManager:
    """Manages connection state and validation."""
    
    def __init__(self, client: 'HyperDeckClient'):
        self.client = client
        self.is_connected = False
        self.last_connection_check = 0
        self.connection_check_interval = 5.0  # seconds
    
    def check_connection(self) -> bool:
        """Check if connection is valid, with caching."""
        current_time = time.time()
        if current_time - self.last_connection_check < self.connection_check_interval:
            return self.is_connected
        
        self.is_connected = self.client.health_check()
        self.last_connection_check = current_time
        return self.is_connected
    
    def get_connection_status(self) -> Tuple[bool, str]:
        """Get connection status with descriptive message."""
        if self.check_connection():
            return True, "Connected"
        else:
            return False, "Disconnected"


def normalize_base_url(s: str) -> str:
    """
    Normalize a base URL for HyperDeck API.
    
    Args:
        s: Input URL string (IP, hostname, or full URL)
        
    Returns:
        Normalized URL ending with /control/api/v1/
    """
    s = (s or "").strip()
    if not s:
        return ""
    
    # Add http:// if no scheme provided
    if not re.match(r"^https?://", s, re.I):
        s = "http://" + s
    
    s = s.strip()
    
    # If they already included /control/api/v1 or /control/api/v1/, normalize trailing slash
    if re.search(r"/control/api/v1/?$", s, re.I):
        return re.sub(r"/?$", "/", s)
    
    # Remove trailing slash before appending
    s = re.sub(r"/+$", "", s)
    return s + "/control/api/v1/"


class HyperDeckClient:
    """Enhanced HyperDeck API client with better error handling and features."""
    
    def __init__(self, base_url: str, timeout: float = Config.TIMEOUT):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HyperDeck-Transport/2.0',
            'Accept': 'application/json'
        })
        logger.info(f"Initialized HyperDeck client for {self.base_url}")
    
    def _request_with_retry(self, method: str, path: str, payload: Optional[Dict] = None) -> requests.Response:
        """Make HTTP request with retry logic."""
        url = urljoin(self.base_url, path.lstrip("/"))
        
        for attempt in range(Config.MAX_RETRIES):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, timeout=self.timeout)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=payload or {}, timeout=self.timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                if attempt == Config.MAX_RETRIES - 1:
                    logger.error(f"Request failed after {Config.MAX_RETRIES} attempts: {e}")
                    raise
                logger.warning(f"Request attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(0.5 * (2 ** attempt))  # Exponential backoff
    
    def health_check(self) -> bool:
        """Check if the HyperDeck is reachable."""
        try:
            response = self._request_with_retry('GET', 'status')
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False
    
    @lru_cache(maxsize=128)
    def get_transport(self, idx: int = 0) -> Dict[str, Any]:
        """Get transport information with caching."""
        try:
            response = self._request_with_retry('GET', f"transports/{idx}")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get transport {idx}: {e}")
            raise
    
    def get_active_clip(self, idx: int = 0) -> Optional[Dict[str, Any]]:
        """Get active clip information."""
        try:
            # Try direct active clip endpoint first
            response = self._request_with_retry('GET', "clips/active")
            return response.json()
        except Exception:
            try:
                # Fallback to clips list
                response = self._request_with_retry('GET', "clips")
                clips = response.json()
                items = clips.get("items") if isinstance(clips, dict) else clips
                
                if isinstance(items, list):
                    for clip in items:
                        if clip.get("active") is True:
                            return clip
            except Exception as e:
                logger.warning(f"Failed to get active clip: {e}")
        return None
    
    def play(self, idx: int = 0) -> Dict[str, Any]:
        """Start playback."""
        try:
            response = self._request_with_retry('POST', f"transports/{idx}/play")
            self.get_transport.cache_clear()  # Clear cache after state change
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Play command failed: {e}")
            raise
    
    def stop(self, idx: int = 0) -> Dict[str, Any]:
        """Stop playback/recording."""
        try:
            response = self._request_with_retry('POST', f"transports/{idx}/stop")
            self.get_transport.cache_clear()  # Clear cache after state change
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Stop command failed: {e}")
            raise
    
    def record(self, idx: int = 0) -> Dict[str, Any]:
        """Start recording."""
        try:
            response = self._request_with_retry('POST', f"transports/{idx}/record")
            self.get_transport.cache_clear()  # Clear cache after state change
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Record command failed: {e}")
            raise
    
    def shuttle(self, idx: int = 0, rate: float = 1.0) -> Dict[str, Any]:
        """Set shuttle speed."""
        try:
            response = self._request_with_retry('POST', f"transports/{idx}/shuttle", {"rate": rate})
            self.get_transport.cache_clear()  # Clear cache after state change
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Shuttle command failed: {e}")
            raise
    
    def _parse_response(self, response: requests.Response) -> Dict[str, Any]:
        """Parse HTTP response."""
        if response.status_code == 204 or not response.content:
            return {}
        
        try:
            return response.json()
        except ValueError:
            return {"ok": True, "raw": response.text}


def derive_state(transport_data: Dict[str, Any]) -> str:
    """Derive transport state from API response."""
    # Check common state fields
    for key in ["status", "state", "transport", "transportState", "transportMode", "mode", "playbackStatus"]:
        value = transport_data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    
    # Check boolean flags
    truthy = lambda x: str(x).lower() in {"1", "true", "yes", "on"}
    
    if truthy(transport_data.get("isRecording")) or truthy(transport_data.get("recording")):
        return "Recording"
    if truthy(transport_data.get("isPlaying")) or truthy(transport_data.get("playing")):
        return "Playing"
    if truthy(transport_data.get("isStopped")) or truthy(transport_data.get("stopped")):
        return "Stopped"
    
    return "Unknown"


def derive_timecode(transport_data: Dict[str, Any]) -> str:
    """Derive timecode from API response."""
    # Check common timecode fields
    for key in ["position", "timecode", "time", "tc", "currentTimecode"]:
        value = transport_data.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, (int, float)):
            seconds = int(value)
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}:00"
    
    return "00:00:00:00"


def derive_active_clip_name(clip_info: Optional[Dict[str, Any]]) -> str:
    """Derive clip name from clip information."""
    if not clip_info:
        return "—"
    
    for key in ["name", "clipName", "title", "filename"]:
        value = clip_info.get(key)
        if isinstance(value, str) and value.strip():
            return value
    
    return "Unnamed"


class HyperDeckGUI(ttk.Frame):
    """Enhanced HyperDeck GUI with better organization and features."""
    
    def __init__(self, master: tk.Tk, base_url: str, transport_idx: int = 0):
        super().__init__(master, padding=12)
        
        # Initialize managers
        self.settings = SettingsManager()
        self.client = HyperDeckClient(base_url)
        self.connection_manager = ConnectionManager(self.client)
        
        # State variables
        self.transport_idx = transport_idx
        self.last_transport_json = {}
        self.last_custom_url = self.settings.get("last_custom_url", "")
        
        # UI variables
        self.state_var = tk.StringVar(value="—")
        self.tc_var = tk.StringVar(value="—")
        self.clip_var = tk.StringVar(value="—")
        self.connection_var = tk.StringVar(value="Checking...")
        
        self._build_ui(master)
        self._setup_keyboard_shortcuts()
        self._load_settings()
        
        # Start polling
        self.after(Config.POLL_INTERVAL_MS, self.refresh_state)
        
        logger.info("HyperDeck GUI initialized")
    
    def _build_ui(self, master: tk.Tk) -> None:
        """Build the user interface."""
        master.title("HyperDeck Transport Control v2")
        master.minsize(Config.WINDOW_MIN_WIDTH, Config.WINDOW_MIN_HEIGHT)
        
        # Configure grid weights
        self.grid(sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        
        # Build UI sections
        self._build_connection_section()
        self._build_status_section()
        self._build_controls_section()
        self._build_statusbar()
    
    def _build_connection_section(self) -> None:
        """Build connection configuration section."""
        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for i in range(9):
            frame.columnconfigure(i, weight=1)
        
        # Deck selection
        ttk.Label(frame, text="Deck:").grid(row=0, column=0, sticky="w")
        self.deck_var = tk.StringVar()
        deck_names = list(Config.DECK_CHOICES.keys())
        self.deck_var.set(self.settings.get("last_deck", "DDR 28 (172.16.17.52)"))
        
        self.deck_combo = ttk.Combobox(
            frame,
            textvariable=self.deck_var,
            values=deck_names,
            state="readonly",
            width=28,
        )
        self.deck_combo.grid(row=0, column=1, sticky="ew")
        self.deck_combo.bind("<<ComboboxSelected>>", self._on_deck_change)
        
        # Base URL
        ttk.Label(frame, text="Base URL:").grid(row=0, column=2, padx=(10, 0), sticky="e")
        self.base_url_var = tk.StringVar()
        self.base_url_entry = ttk.Entry(frame, textvariable=self.base_url_var, state="readonly")
        self.base_url_entry.grid(row=0, column=3, columnspan=3, sticky="ew")
        
        # Apply button
        self.apply_btn = ttk.Button(frame, text="Apply URL", command=self._apply_custom_url, state="disabled")
        self.apply_btn.grid(row=0, column=6, padx=(8, 0), sticky="ew")
        
        # Transport index
        ttk.Label(frame, text="Transport Index:").grid(row=0, column=7, padx=(10, 0), sticky="e")
        self.idx_var = tk.IntVar(value=self.transport_idx)
        ttk.Spinbox(frame, from_=0, to=7, textvariable=self.idx_var, width=5).grid(row=0, column=8, sticky="w")
        
        # Connection status
        ttk.Label(frame, text="Status:").grid(row=0, column=9, padx=(10, 0), sticky="e")
        self.connection_label = ttk.Label(frame, textvariable=self.connection_var, foreground="orange")
        self.connection_label.grid(row=0, column=10, sticky="w")
        
        # JSON viewer button
        self.btn_show_json = ttk.Button(frame, text="Show JSON", command=self._show_transport_json)
        self.btn_show_json.grid(row=0, column=11, padx=(10, 0))
    
    def _build_status_section(self) -> None:
        """Build status display section."""
        frame = ttk.LabelFrame(self, text="Status")
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        for i in range(6):
            frame.columnconfigure(i, weight=1)
        
        # State
        ttk.Label(frame, text="State:").grid(row=0, column=0, sticky="w", padx=(8, 4), pady=6)
        ttk.Label(frame, textvariable=self.state_var).grid(row=0, column=1, sticky="w", pady=6)
        
        # Timecode
        ttk.Label(frame, text="Timecode:").grid(row=0, column=2, sticky="w", padx=(8, 4), pady=6)
        ttk.Label(frame, textvariable=self.tc_var).grid(row=0, column=3, sticky="w", pady=6)
        
        # Clip name
        ttk.Label(frame, text="Clip Name:").grid(row=0, column=4, sticky="w", padx=(8, 4), pady=6)
        ttk.Label(frame, textvariable=self.clip_var, width=30).grid(row=0, column=5, sticky="w", pady=6)
    
    def _build_controls_section(self) -> None:
        """Build transport controls section."""
        frame = ttk.LabelFrame(self, text="Transport Controls")
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        for i in range(6):
            frame.columnconfigure(i, weight=1)
        
        # Control buttons
        self.btn_play = ttk.Button(frame, text="Play (Space)", command=self._on_play)
        self.btn_stop = ttk.Button(frame, text="Stop (S)", command=self._on_stop)
        self.btn_rec = ttk.Button(frame, text="Record (R)", command=self._on_record)
        
        self.btn_rev = ttk.Button(frame, text="Shuttle -2x", command=lambda: self._on_shuttle(-2.0))
        self.btn_slw = ttk.Button(frame, text="Shuttle 0.5x", command=lambda: self._on_shuttle(0.5))
        self.btn_fwd = ttk.Button(frame, text="Shuttle 2x", command=lambda: self._on_shuttle(2.0))
        
        # Grid buttons
        buttons = [self.btn_play, self.btn_stop, self.btn_rec, self.btn_rev, self.btn_slw, self.btn_fwd]
        for i, btn in enumerate(buttons):
            btn.grid(row=0, column=i, padx=6, pady=10, sticky="ew")
    
    def _build_statusbar(self) -> None:
        """Build status bar."""
        frame = ttk.Frame(self)
        frame.grid(row=3, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)
        
        self.statusbar = ttk.Label(frame, text="Ready", anchor="w")
        self.statusbar.grid(row=0, column=0, sticky="ew")
    
    def _setup_keyboard_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        self.master.bind('<KeyPress-space>', lambda e: self._on_play())
        self.master.bind('<KeyPress-s>', lambda e: self._on_stop())
        self.master.bind('<KeyPress-r>', lambda e: self._on_record())
        self.master.focus_set()  # Enable keyboard focus
    
    def _load_settings(self) -> None:
        """Load saved settings."""
        self.transport_idx = self.settings.get("transport_idx", Config.DEFAULT_TRANSPORT_IDX)
        self.idx_var.set(self.transport_idx)
        self._apply_deck_selection()
    
    def _on_deck_change(self, event=None) -> None:
        """Handle deck selection change."""
        self._apply_deck_selection()
    
    def _apply_deck_selection(self) -> None:
        """Apply deck selection and update UI."""
        name = self.deck_var.get()
        url = Config.DECK_CHOICES.get(name, "")
        
        if name == "Custom":
            # Enable editing for custom URL
            self.base_url_entry.configure(state="normal")
            if self.last_custom_url:
                self.base_url_var.set(self.last_custom_url)
            else:
                self.base_url_var.set("http://172.16.17.xx/control/api/v1/")
            self.apply_btn.configure(state="normal")
            self.statusbar.config(text="Custom URL pending apply")
        else:
            # Use preset URL
            self.base_url_var.set(url)
            self.base_url_entry.configure(state="readonly")
            self.apply_btn.configure(state="disabled")
            self._update_client(url)
            self.settings.set("last_deck", name)
            self.statusbar.config(text=f"Using preset {name}")
    
    def _apply_custom_url(self) -> None:
        """Apply custom URL."""
        raw = self.base_url_var.get().strip()
        normalized = normalize_base_url(raw)
        
        if not normalized:
            messagebox.showerror("Invalid URL", "Please enter a valid host or full URL")
            return
        
        self.last_custom_url = normalized
        self.base_url_var.set(normalized)
        self._update_client(normalized)
        self.settings.set("last_custom_url", normalized)
        self.statusbar.config(text="Custom URL applied")
    
    def _update_client(self, base_url: str) -> None:
        """Update the API client with new base URL."""
        self.client = HyperDeckClient(base_url)
        self.connection_manager = ConnectionManager(self.client)
        logger.info(f"Updated client to use {base_url}")
    
    def _update_client_from_inputs(self) -> None:
        """Update client settings from UI inputs."""
        self.transport_idx = int(self.idx_var.get())
        self.settings.set("transport_idx", self.transport_idx)
    
    def refresh_state(self) -> None:
        """Refresh transport state with enhanced error handling."""
        self._update_client_from_inputs()
        
        # Check connection status
        is_connected, status_msg = self.connection_manager.get_connection_status()
        self.connection_var.set(status_msg)
        
        if is_connected:
            self.connection_label.configure(foreground="green")
        else:
            self.connection_label.configure(foreground="red")
        
        if not is_connected:
            self.state_var.set("Offline")
            self.tc_var.set("—")
            self.clip_var.set("—")
            self._set_record_button_style(False)
            self.statusbar.config(text=f"Disconnected from {self.deck_var.get()}")
            # Use slower polling when disconnected
            self.after(Config.POLL_INTERVAL_MS_DISCONNECTED, self.refresh_state)
            return
        
        try:
            # Get transport data
            transport_data = self.client.get_transport(self.transport_idx)
            self.last_transport_json = transport_data
            
            # Update UI
            state = derive_state(transport_data)
            timecode = derive_timecode(transport_data)
            
            clip_info = self.client.get_active_clip(self.transport_idx)
            clip_name = derive_active_clip_name(clip_info)
            
            self.state_var.set(state)
            self.tc_var.set(timecode)
            self.clip_var.set(clip_name)
            
            # Update record button style
            is_recording = state.lower() in {"record", "recording", "inputrecord"}
            self._set_record_button_style(is_recording)
            
            self.statusbar.config(text=f"Connected to {self.deck_var.get()}")
            
        except requests.HTTPError as e:
            self.statusbar.config(text=f"HTTP error: {e.response.status_code}")
            self.state_var.set("Error")
            self._set_record_button_style(False)
            logger.error(f"HTTP error: {e}")
            
        except requests.RequestException as e:
            self.statusbar.config(text=f"Network error: {e.__class__.__name__}")
            self.state_var.set("Network Error")
            self._set_record_button_style(False)
            logger.error(f"Network error: {e}")
            
        except Exception as e:
            self.statusbar.config(text=f"Error: {e.__class__.__name__}")
            self._set_record_button_style(False)
            logger.error(f"Unexpected error: {e}")
        
        # Schedule next refresh
        self.after(Config.POLL_INTERVAL_MS, self.refresh_state)
    
    def _set_record_button_style(self, active: bool) -> None:
        """Update record button appearance."""
        self.btn_rec.config(text="Record ●" if active else "Record")
    
    def _show_transport_json(self) -> None:
        """Show transport JSON in a new window."""
        window = tk.Toplevel(self)
        window.title("Transport JSON")
        window.minsize(520, 360)
        
        text_widget = tk.Text(window, wrap="none", font=("Courier", 10))
        text_widget.pack(fill="both", expand=True)
        
        try:
            pretty_json = json.dumps(self.last_transport_json, indent=2)
        except Exception:
            pretty_json = str(self.last_transport_json)
        
        text_widget.insert("1.0", pretty_json)
        text_widget.configure(state="disabled")
    
    def _on_play(self) -> None:
        """Handle play button click."""
        self._update_client_from_inputs()
        try:
            self.client.play(self.transport_idx)
            self.statusbar.config(text="Play command sent")
            logger.info("Play command executed")
        except Exception as e:
            messagebox.showerror("Play failed", str(e))
            logger.error(f"Play command failed: {e}")
    
    def _on_stop(self) -> None:
        """Handle stop button click."""
        self._update_client_from_inputs()
        try:
            self.client.stop(self.transport_idx)
            self.statusbar.config(text="Stop command sent")
            logger.info("Stop command executed")
        except Exception as e:
            messagebox.showerror("Stop failed", str(e))
            logger.error(f"Stop command failed: {e}")
    
    def _on_record(self) -> None:
        """Handle record button click."""
        self._update_client_from_inputs()
        try:
            self.client.record(self.transport_idx)
            self.statusbar.config(text="Record command sent")
            logger.info("Record command executed")
        except Exception as e:
            messagebox.showerror("Record failed", str(e))
            logger.error(f"Record command failed: {e}")
    
    def _on_shuttle(self, rate: float) -> None:
        """Handle shuttle button click."""
        self._update_client_from_inputs()
        try:
            self.client.shuttle(self.transport_idx, rate=rate)
            self.statusbar.config(text=f"Shuttle {rate}x command sent")
            logger.info(f"Shuttle command executed: {rate}x")
        except Exception as e:
            messagebox.showerror("Shuttle failed", str(e))
            logger.error(f"Shuttle command failed: {e}")


def main() -> None:
    """Main application entry point."""
    # Set up root window
    root = tk.Tk()
    
    # Configure style
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    
    # Create and run application
    default_base = Config.DECK_CHOICES["DDR 28 (172.16.17.52)"]
    app = HyperDeckGUI(root, base_url=default_base, transport_idx=Config.DEFAULT_TRANSPORT_IDX)
    
    # Handle window closing
    def on_closing():
        logger.info("Application closing")
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Start main loop
    logger.info("Starting HyperDeck Transport Control v2")
    root.mainloop()


if __name__ == "__main__":
    main()
