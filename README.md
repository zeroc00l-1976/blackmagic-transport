# Blackmagic HyperDeck Remote Transport

A simple Python/Tkinter app for controlling Blackmagic HyperDeck 4K devices over the network.  
This tool provides a GUI with familiar transport controls (play, stop, record, etc.) and polls the HyperDeck API to display current status in real time.

## Features
- Connect to HyperDeck units via IP over your local network  
- Remote control playback, stop, record, and other transport functions  
- Live status updates pulled from the HyperDeck REST API  
- Lightweight GUI built with Tkinter, no special hardware required  

## Prerequisites
- Python 3.11 or newer (project tested with Python 3.13)  
- [uv](https://github.com/astral-sh/uv) (fast Python package/dependency manager)  

### macOS Tk note
On macOS, Homebrew’s `python@3.x` may not include Tkinter by default. If you see  
`ModuleNotFoundError: No module named '_tkinter'`, do one of the following:

1. **Install Python from [python.org](https://www.python.org/downloads/macos/)** – these builds include Tk by default.  
2. Or install Python via **pyenv** and compile with Homebrew’s `tcl-tk`:  
   ```bash
   brew install pyenv tcl-tk
   pyenv install 3.13.7
   uv python pin /Users/<you>/.pyenv/versions/3.13.7/bin/python3.13
   uv sync
   ```
3. Then re-run your project with uv.

### Windows Tk note
On Windows, the official Python.org installer includes Tkinter by default.  
If you encounter a `_tkinter` error, make sure you installed Python with the **"tcl/tk and IDLE"** option enabled (this is selected by default).  
If using a custom distribution (e.g., Miniconda), you may need to install Tk manually:
```bash
conda install tk
```

---

## Quick Start

```bash
# 1) Install uv if you do not have it yet
pip install uv    # or: curl -LsSf https://astral.sh/uv/install.sh | sh

# 2) Clone and enter the repo
git clone https://github.com/<your-username>/blackmagic-transport.git
cd blackmagic-transport

# 3) Create the venv and install deps from pyproject.toml and uv.lock
uv sync

# 4) Run the app
uv run blackmagic-transport.py
```

## Notes
- HyperDeck devices must have their API enabled and be reachable on your network.  
- Designed for HyperDeck Studio 4K models, but may work with other recent HyperDeck units that expose the REST API.  

## License
MIT License – feel free to modify and use.
