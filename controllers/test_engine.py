from controllers.simulation_engine import SimulationEngine

engine = SimulationEngine()

print("========== NORMAL OPERATION ==========\n")

for i in range(30):
    snap = engine.step()

    print(
        f"{i:02d} "
        f"Level={snap.level_mm:7.2f} "
        f"Valve={engine.valve.position_pct:6.2f}"
    )

print("\n========== LOAD INCREASE ==========\n")

engine.set_steam_demand(80)

for i in range(300):

    snap = engine.step()

    if i % 10 == 0:
        print(
            f"{i:03d} "
            f"Level={snap.level_mm:7.2f} "
            f"Valve={engine.valve.position_pct:6.2f} "
            f"Demand={snap.steam_demand_pct:6.2f} "
            f"Steam={snap.steam_flow:6.2f}"
        )