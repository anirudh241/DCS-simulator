# DCS Simulator - Boiler Drum Module

A software-based Distributed Control System (DCS) simulator for boiler-drum
level control. The project includes a live process mimic, PID control with
steam-demand feedforward, operator controls, and real-time trend graphs.

## Requirements

- Windows 10/11
- Python 3.10 or newer (64-bit recommended)
- Git

Python packages are listed in `requirements.txt`:

- PySide6
- pyqtgraph
- NumPy

## Setup

Open Git Bash and run:

```bash
git clone https://github.com/anirudh241/DCS-simulator.git
cd DCS-simulator

python -m venv .venv
source .venv/Scripts/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The terminal prompt should now begin with `(.venv)`.

## Run

With the virtual environment active:

```bash
python main.py
```

Use **START** and **STOP** to control the simulation. Change the level
setpoint or steam-load demand from the controller panel, and open **TRENDS**
to view the response.

When finished:

```bash
deactivate
```

## PowerShell alternative

Activate the same environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, the project can still be installed and run
directly through the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Updating an existing clone

```bash
git pull
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python main.py
```
