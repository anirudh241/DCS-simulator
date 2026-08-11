from pid import PIDController

pid = PIDController(
    kp=0.5,
    ki=0.1,
    kd=0.05,
    setpoint=100,
)

pv = 40

for i in range(30):

    output = pid.update(pv, 0.1)

    pv += output * 0.08

    print(
        f"{i:02d}",
        f"PV={pv:6.2f}",
        f"OUT={output:6.2f}",
    )