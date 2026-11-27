
"""
CAMS Condenser Inlet Model V1.0

Purpose:
    Estimate condenser inlet capture-flow capacity and inlet
    local pressure loss at different flight speeds and inlet areas.

Model boundary:
    - Calculates theoretical captured airflow capacity.
    - Calculates inlet local pressure loss.
    - Does NOT solve actual condenser system operating flow.
    - Does NOT include condenser core, ducts, outlet or fan.

Units:
    Flight speed       : m/s
    Air density        : kg/m^3
    Inlet area         : m^2
    Volume flow        : m^3/s
    Mass flow          : kg/s
    Pressure           : Pa
"""

from dataclasses import dataclass
from typing import Iterable


# ============================================================
# 1. Default design inputs
# ============================================================

RHO_AIR = 0.9096              # kg/m^3
C_CAPTURE = 0.70              # Inlet capture efficiency
C_RECOVERY = 0.70             # Ram pressure recovery coefficient
K_INLET = 1.0                 # Provisional inlet loss coefficient

FLIGHT_SPEEDS = [32.0, 48.0, 60.0, 72.0]  # m/s

INLET_AREAS = [
    0.0200,
    0.0250,
    0.0300,
    0.0372,
    0.0400,
]  # m^2

TARGET_FLOW = 3000.0 / 3600.0  # m^3/s


# ============================================================
# 2. Input data structure
# ============================================================

@dataclass
class InletResult:
    flight_speed: float
    inlet_area: float
    capture_efficiency: float

    dynamic_pressure: float
    ram_pressure_available: float

    volume_flow_capture: float
    mass_flow_capture: float
    inlet_velocity: float

    inlet_dynamic_pressure: float
    dp_inlet: float
    dp_after_inlet: float

    target_flow: float
    flow_ratio: float


# ============================================================
# 3. Main calculation function
# ============================================================

def calculate_inlet(
    flight_speed: float,
    inlet_area: float,
    rho_air: float = RHO_AIR,
    c_capture: float = C_CAPTURE,
    c_recovery: float = C_RECOVERY,
    k_inlet: float = K_INLET,
    target_flow: float = TARGET_FLOW,
) -> InletResult:
    """
    Calculate inlet capture capacity and local pressure loss.
    """

    # ----- Input validation -----

    if flight_speed <= 0:
        raise ValueError("flight_speed must be positive.")

    if inlet_area <= 0:
        raise ValueError("inlet_area must be positive.")

    if rho_air <= 0:
        raise ValueError("rho_air must be positive.")

    if not 0.0 < c_capture <= 1.0:
        raise ValueError("c_capture must be in (0, 1].")

    if not 0.0 <= c_recovery <= 1.0:
        raise ValueError("c_recovery must be in [0, 1].")

    if k_inlet < 0:
        raise ValueError("k_inlet cannot be negative.")

    if target_flow <= 0:
        raise ValueError("target_flow must be positive.")

    # ----- 1. Free-stream dynamic pressure -----

    dynamic_pressure = (
        0.5 * rho_air * flight_speed**2
    )

    # ----- 2. Available ram pressure -----

    ram_pressure_available = (
        c_recovery * dynamic_pressure
    )

    # ----- 3. Inlet capture volume flow -----

    volume_flow_capture = (
        c_capture * inlet_area * flight_speed
    )

    # ----- 4. Captured air mass flow -----

    mass_flow_capture = (
        rho_air * volume_flow_capture
    )

    # ----- 5. Average inlet velocity -----

    inlet_velocity = (
        volume_flow_capture / inlet_area
    )

    # ----- 6. Inlet dynamic pressure -----

    inlet_dynamic_pressure = (
        0.5 * rho_air * inlet_velocity**2
    )

    # ----- 7. Inlet local pressure loss -----

    dp_inlet = (
        k_inlet * inlet_dynamic_pressure
    )

    # ----- 8. Remaining pressure after inlet -----

    dp_after_inlet = (
        ram_pressure_available - dp_inlet
    )

    # ----- 9. Flow capacity ratio -----

    flow_ratio = (
        volume_flow_capture / target_flow
    )

    return InletResult(
        flight_speed=flight_speed,
        inlet_area=inlet_area,
        capture_efficiency=c_capture,

        dynamic_pressure=dynamic_pressure,
        ram_pressure_available=ram_pressure_available,

        volume_flow_capture=volume_flow_capture,
        mass_flow_capture=mass_flow_capture,
        inlet_velocity=inlet_velocity,

        inlet_dynamic_pressure=inlet_dynamic_pressure,
        dp_inlet=dp_inlet,
        dp_after_inlet=dp_after_inlet,

        target_flow=target_flow,
        flow_ratio=flow_ratio,
    )


# ============================================================
# 4. Parametric sweep
# ============================================================

def run_sweep(
    flight_speeds: Iterable[float] = FLIGHT_SPEEDS,
    inlet_areas: Iterable[float] = INLET_AREAS,
):
    """
    Calculate all combinations of flight speeds and inlet areas.
    """

    results = []

    for area in inlet_areas:
        for speed in flight_speeds:
            result = calculate_inlet(
                flight_speed=speed,
                inlet_area=area,
            )
            results.append(result)

    return results


# ============================================================
# 5. Print results
# ============================================================

def print_results(results):
    print("\nCAMS Condenser Inlet Model V1.0")
    print("=" * 112)

    print(
        f"Air density       : {RHO_AIR:.4f} kg/m^3"
    )
    print(
        f"Capture efficiency: {C_CAPTURE:.3f}"
    )
    print(
        f"Pressure recovery : {C_RECOVERY:.3f}"
    )
    print(
        f"Inlet loss K      : {K_INLET:.3f} (provisional)"
    )
    print(
        f"Target flow       : {TARGET_FLOW * 3600:.1f} m^3/h"
    )

    print("-" * 112)

    header = (
        f"{'Area(m2)':>9}"
        f"{'Speed(m/s)':>12}"
        f"{'Capture(m3/h)':>15}"
        f"{'Mass(kg/s)':>13}"
        f"{'V_in(m/s)':>12}"
        f"{'Ram(Pa)':>12}"
        f"{'Inlet DP(Pa)':>14}"
        f"{'After inlet(Pa)':>17}"
        f"{'Flow ratio':>12}"
    )

    print(header)
    print("-" * 112)

    for r in results:
        print(
            f"{r.inlet_area:9.4f}"
            f"{r.flight_speed:12.1f}"
            f"{r.volume_flow_capture * 3600:15.1f}"
            f"{r.mass_flow_capture:13.4f}"
            f"{r.inlet_velocity:12.2f}"
            f"{r.ram_pressure_available:12.1f}"
            f"{r.dp_inlet:14.1f}"
            f"{r.dp_after_inlet:17.1f}"
            f"{r.flow_ratio:12.3f}"
        )

    print("=" * 112)


# ============================================================
# 6. Self-test
# ============================================================

def self_test():
    result = calculate_inlet(
        flight_speed=32.0,
        inlet_area=0.0372,
    )

    assert result.volume_flow_capture > 0
    assert result.mass_flow_capture > 0
    assert result.dp_inlet >= 0

    expected_flow = (
        C_CAPTURE * 0.0372 * 32.0
    )

    assert abs(
        result.volume_flow_capture - expected_flow
    ) < 1e-10

    assert result.dp_after_inlet < result.ram_pressure_available

    # Larger inlet area should provide greater capture capacity
    result_small = calculate_inlet(32.0, 0.020)
    result_large = calculate_inlet(32.0, 0.040)

    assert (
        result_large.volume_flow_capture
        > result_small.volume_flow_capture
    )

    print("Self-test passed.")


# ============================================================
# 7. Main
# ============================================================

if __name__ == "__main__":

    self_test()

    results = run_sweep()

    print_results(results)
