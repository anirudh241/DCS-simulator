# DCS Simulator — Boiler Drum Module

A software-based industrial control simulator, inspired by NSPCL Bhilai
vocational training. Phase 1 focuses on a single closed control loop:
boiler drum level control (feedwater valve/pump responding to level
transmitter readings), presented on a control-room-style mimic screen.

## Status

Step 1 of the build plan: minimal runnable window with the dark
industrial theme and an empty mimic canvas (`QGraphicsScene`). No
simulation logic yet.

## Setup

You already have a venv at `.venv` with PySide6 and pyqtgraph
installed. From the project root, with the venv active:

```
python main.py
```

## Structure

```
main.py            entry point
ui/                 windows, widgets, the mimic scene/view
models/             process models (drum, valve, pump, etc.)
controllers/        control logic (PID, alarm logic)
data/               logged/exported simulation data
assets/             icons, images for the mimic diagram
requirements.txt    Python dependencies
```

## Build plan

1. Minimal PySide6 window — done
2. Boiler drum dashboard layout (mimic diagram + tag boxes)
3. Simulation engine for process values
4. Live labels / indicators wired to the simulation
5. Trend graph (pyqtgraph)
6. Manual/auto controls
7. Alarm logic
8. Clickable mimic objects / wider plant context
9. Styling polish (+ QML upgrade if time allows)
