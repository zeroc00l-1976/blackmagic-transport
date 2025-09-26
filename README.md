# Blackmagic HyperDeck Remote Transport

A simple Python/Tkinter app for controlling Blackmagic HyperDeck 4K devices over the network.  
This tool provides a GUI with familiar transport controls (play, stop, record, etc.) and polls the HyperDeck API to display current status in real time.

## Features
- Connect to HyperDeck units via IP over your local network  
- Remote control playback, stop, record, and other transport functions  
- Live status updates pulled from the HyperDeck REST API  
- Lightweight GUI built with Tkinter, no special hardware required  

## Prerequisites
- Python 3.11 (or newer)  
- [uv](https://github.com/astral-sh/uv) (fast Python package/dependency manager)  

# 1) Install uv if you do not have it yet
pip install uv    # or: curl -LsSf https://astral.sh/uv/install.sh | sh

# 2) Clone and enter the repo
git clone https://github.com/<your-username>/blackmagic-transport.git
cd blackmagic-transport

# 3) Create the venv and install deps from pyproject.toml and uv.lock
uv sync

# 4) Run the app
uv run blackmagic-transport.py

## Notes
- HyperDeck devices must have their API enabled and be reachable on your network.  
- Designed for HyperDeck Studio 4K models, but may work with other recent HyperDeck units that expose the REST API.  

## License
MIT License – feel free to modify and use.

