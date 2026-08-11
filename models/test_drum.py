from drum import Drum

drum = Drum()

print("Initial State")
print(drum.snapshot())
print()

for i in range(20):

    drum.update(
        feedwater_flow=60,
        dt=0.1,
    )

print("Steady State")
print(drum.snapshot())
print()

print("Increasing Steam Demand...\n")

drum.set_steam_demand(80)

for i in range(30):

    drum.update(
        valve_position_pct=60,
        dt=0.1,
    )

    snap = drum.snapshot()

    print(
        f"{i:02d}",
        f"Level={snap.level_mm:7.2f}",
        f"Pressure={snap.pressure_bar:7.2f}",
        f"Temp={snap.temperature_c:7.2f}",
    )