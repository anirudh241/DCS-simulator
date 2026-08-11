# DCS Simulator — Boiler Drum Module

A software-based industrial control simulator, inspired by NSPCL Bhilai
vocational training. Phase 1 focuses on a single closed control loop:
boiler drum level control (feedwater valve responding to a level
transmitter reading, with steam-demand feedforward), presented on a
control-room-style mimic screen.

## Status

Steps 1–4 done, step 6 partially done. Live simulation is running:
the mimic canvas shows the boiler drum, piping, and a wider plant
context (turbine, condenser), with tag boxes wired to real values
from a closed-loop PID + feedforward controller. An "Operator
Controls" dock panel lets you adjust the level setpoint and steam
load live and watch the loop respond. Trend graph and alarm logic
are not built yet.

## Setup

You already have a venv at `.venv` with the dependencies installed.
From the project root, with the venv active:

```
python main.py
```

## Structure

```
main.py                          entry point
ui/
  main_window.py                 window shell, toolbar, Operator Controls dock
  mimic_scene.py                 the mimic diagram (drum, piping, tag boxes)
models/
  drum.py                        boiler drum process model (level, pressure, temp)
  valve.py                       control valve model (position -> flow)
controllers/
  pid.py                         generic PID controller
  level_controller.py            drum level loop (feedforward + PID trim)
  simulation_engine.py           ties model + controller together, runs the tick loop
data/                            logged/exported simulation data (not used yet)
assets/                          icons, images for the mimic diagram (not used yet)
requirements.txt                 Python dependencies
```

Each module under `models/` and `controllers/` has a matching
`test_*.py` you can run standalone (no Qt event loop needed) to sanity
check the physics/control logic in isolation.

## Build plan

1. Minimal PySide6 window — done
2. Boiler drum dashboard layout (mimic diagram + tag boxes), zoned like a real DCS overview — done
3. Simulation engine — drum model + PID level controller with steam-demand feedforward — done
4. Live tag boxes wired to the running simulation — done
5. Trend graph (pyqtgraph) — next up
6. Manual/auto controls — partially done (live setpoint/load entry via Operator Controls dock; no manual valve override or auto/manual mode switch yet)
7. Alarm logic (visual state change on tag boxes at high/low thresholds)
8. Clickable mimic objects
9. Styling polish (+ QML upgrade if time allows)