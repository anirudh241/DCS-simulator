"""Generate repeatable CSV data from the boiler drum simulation."""

import argparse
import csv
from pathlib import Path

from controllers.simulation_engine import SimulationEngine
from models.alarm import AlarmManager


SETPOINTS_MM = (400.0, 500.0, 600.0)
STEAM_DEMANDS_PCT = (25.0, 50.0, 75.0, 100.0)
INITIAL_SETPOINT_MM = 500.0
INITIAL_DEMAND_PCT = 60.0

FIELDS = (
    "episode_id", "time_s", "phase", "setpoint_mm", "steam_demand_pct",
    "drum_level_mm", "level_error_mm", "pressure_bar", "temperature_c",
    "steam_flow", "feedwater_flow", "valve_position_pct", "pid_p", "pid_i",
    "pid_d", "feedforward_pct", "valve_command_pct", "active_alarm_tags",
)


def generate_dataset(output_path, seconds_per_episode=60):
    """Run each demand/setpoint combination and save its response to CSV."""
    rows_per_episode = round(seconds_per_episode / SimulationEngine().dt)
    transition_step = rows_per_episode // 2
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    row_count = 0

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
        writer.writeheader()

        for setpoint in SETPOINTS_MM:
            for demand in STEAM_DEMANDS_PCT:
                engine = SimulationEngine()
                alarms = AlarmManager()
                engine.set_level_setpoint(INITIAL_SETPOINT_MM)
                engine.set_steam_demand(INITIAL_DEMAND_PCT)
                episode_id = f"sp{int(setpoint)}_load{int(demand):03d}"

                for step in range(rows_per_episode):
                    phase = "baseline" if step < transition_step else "response"
                    if phase == "response":
                        engine.set_level_setpoint(setpoint)
                        engine.set_steam_demand(demand)

                    state = engine.step()
                    sample = engine.last_control_sample
                    control = sample.control
                    elapsed = (step + 1) * engine.dt
                    alarms.update_drum_level(state.level_mm, elapsed)

                    writer.writerow({
                        "episode_id": episode_id,
                        "time_s": round(elapsed, 2),
                        "phase": phase,
                        "setpoint_mm": round(engine.controller.setpoint_mm, 2),
                        "steam_demand_pct": round(state.steam_demand_pct, 2),
                        "drum_level_mm": round(state.level_mm, 4),
                        "level_error_mm": round(control.pid.error, 4),
                        "pressure_bar": round(state.pressure_bar, 4),
                        "temperature_c": round(state.temperature_c, 4),
                        "steam_flow": round(state.steam_flow, 4),
                        "feedwater_flow": round(state.feedwater_flow, 4),
                        "valve_position_pct": round(sample.valve_position_pct, 4),
                        "pid_p": round(control.pid.proportional, 4),
                        "pid_i": round(control.pid.integral, 4),
                        "pid_d": round(control.pid.derivative, 4),
                        "feedforward_pct": round(control.feedforward_pct, 4),
                        "valve_command_pct": round(control.valve_command_pct, 4),
                        "active_alarm_tags": "|".join(
                            alarm.definition.tag for alarm in alarms.active_alarms
                        ),
                    })
                    row_count += 1

    return row_count


def main():
    default_output = Path(__file__).with_name("boiler_drum_dataset.csv")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--seconds-per-episode", type=int, default=60)
    args = parser.parse_args()
    if args.seconds_per_episode < 2:
        parser.error("--seconds-per-episode must be at least 2")

    rows = generate_dataset(args.output, args.seconds_per_episode)
    print(f"Generated {rows:,} rows across 12 episodes: {args.output.resolve()}")


if __name__ == "__main__":
    main()
