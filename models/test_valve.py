from valve import ControlValve

valve = ControlValve()

for opening in (0, 25, 50, 75, 100):

    valve.set_position(opening)

    print(
        f"Valve {opening:3d}%  -> "
        f"Flow {valve.flow:6.1f}"
    )