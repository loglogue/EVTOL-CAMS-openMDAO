# cams_condenser_weight.py
# CAMS Condenser Geometry & Tube-Fin Core Mass Model V1.0
#
# Scope:
#   1. Installation-envelope calculation
#   2. Tube-fin core preliminary mass estimation
#   3. Installation-angle sweep and CSV export
#
# Important:
#   This version does NOT calculate heat-transfer capability.
#   A geometrically feasible core is NOT necessarily a 12 kW feasible core.
#   All tube/fin dimensions below are provisional placeholders.

from dataclasses import dataclass
from math import sin, cos, radians, floor, pi
import csv


# ============================================================
# 1. DESIGN INPUTS
# ============================================================

@dataclass
class DesignInputs:

    # Thermal design target
    q_cond_w: float = 12000.0
    t_air_in_c: float = 40.0
    delta_t_air_k: float = 13.0
    air_mass_flow_kg_s: float = 0.918

    # Installation envelope
    max_vertical_m: float = 0.250
    max_longitudinal_m: float = 0.500
    max_width_m: float = 0.400

    # Fan axial occupied length
    fan_axial_m: float = 0.080

    # Angle range
    angle_start_deg: float = 30.0
    angle_end_deg: float = 90.0
    angle_step_deg: float = 5.0

    # Preliminary core dimensions
    # These are design variables, not confirmed dimensions.
    core_width_m: float = 0.350
    core_depth_m: float = 0.060

    # Tube geometry: rectangular extruded tube approximation
    tube_width_m: float = 0.010
    tube_height_m: float = 0.002
    tube_wall_m: float = 0.00030
    tube_pitch_m: float = 0.008

    # Fin geometry
    fin_thickness_m: float = 0.00010

    # Developed fin area / frontal core area.
    # Placeholder pending actual corrugated-fin geometry.
    fin_area_ratio: float = 18.0

    # Header geometry: hollow rectangular approximation
    header_width_m: float = 0.020
    header_height_m: float = 0.020
    header_wall_m: float = 0.0010

    # Side plate geometry
    side_plate_thickness_m: float = 0.0010

    # Material density
    aluminum_density_kg_m3: float = 2700.0

    # Explicit braze allowance per tube.
    # This is a provisional input, not a percentage of core mass.
    braze_mass_per_tube_kg: float = 0.001


# ============================================================
# 2. GEOMETRY CALCULATION
# ============================================================

def calculate_max_core_height(
    angle_deg: float,
    core_depth_m: float,
    fan_axial_m: float,
    max_vertical_m: float,
    max_longitudinal_m: float,
):
    """
    Simplified geometry:
      Fan axis is assumed normal to the core plane.
      Core + fan axial length = core depth + fan axial length.

    Returns maximum allowable core height.
    """

    theta = radians(angle_deg)
    axial_length = core_depth_m + fan_axial_m

    s = sin(theta)
    c = cos(theta)

    # Vertical envelope constraint
    h_from_vertical = (
        max_vertical_m - axial_length * c
    ) / s if s > 1e-12 else float("-inf")

    # Longitudinal envelope constraint
    if c > 1e-12:
        h_from_longitudinal = (
            max_longitudinal_m - axial_length * s
        ) / c
    else:
        h_from_longitudinal = float("inf")

    h_max = min(
        h_from_vertical,
        h_from_longitudinal
    )

    return max(0.0, h_max)


def calculate_envelope(
    angle_deg: float,
    core_height_m: float,
    core_depth_m: float,
    fan_axial_m: float,
):
    theta = radians(angle_deg)

    axial_length = core_depth_m + fan_axial_m

    vertical = (
        core_height_m * sin(theta)
        + axial_length * cos(theta)
    )

    longitudinal = (
        core_height_m * cos(theta)
        + axial_length * sin(theta)
    )

    return vertical, longitudinal


# ============================================================
# 3. TUBE-FIN CORE MASS MODEL
# ============================================================

def calculate_core_mass(
    width_m: float,
    height_m: float,
    depth_m: float,
    p: DesignInputs,
):
    """
    Preliminary tube-fin mass breakdown.

    Assumptions:
      - Tubes span the core width.
      - Tubes are stacked along core height.
      - Two headers extend along core height.
      - Two side plates cover the core frontal side edges.
      - Fin developed area is represented by an explicit multiplier.

    Actual tube cross-section, fin geometry and header design
    must replace these approximations in a later revision.
    """

    rho = p.aluminum_density_kg_m3

    # Number of tubes
    n_tubes = max(
        0,
        floor(height_m / p.tube_pitch_m)
    )

    # Rectangular tube metal cross-sectional area
    tube_outer_area = (
        p.tube_width_m * p.tube_height_m
    )

    tube_inner_width = (
        p.tube_width_m - 2.0 * p.tube_wall_m
    )

    tube_inner_height = (
        p.tube_height_m - 2.0 * p.tube_wall_m
    )

    if tube_inner_width <= 0 or tube_inner_height <= 0:
        raise ValueError("Tube wall thickness is too large.")

    tube_inner_area = (
        tube_inner_width * tube_inner_height
    )

    tube_metal_area = (
        tube_outer_area - tube_inner_area
    )

    # Tube mass
    tube_total_length = n_tubes * width_m

    m_tube = (
        rho * tube_metal_area * tube_total_length
    )

    # Fin mass
    frontal_area = width_m * height_m

    fin_developed_area = (
        frontal_area * p.fin_area_ratio
    )

    m_fin = (
        rho
        * p.fin_thickness_m
        * fin_developed_area
    )

    # Two hollow rectangular headers
    header_outer_area = (
        p.header_width_m * p.header_height_m
    )

    header_inner_width = (
        p.header_width_m - 2.0 * p.header_wall_m
    )

    header_inner_height = (
        p.header_height_m - 2.0 * p.header_wall_m
    )

    if header_inner_width <= 0 or header_inner_height <= 0:
        raise ValueError("Header wall thickness is too large.")

    header_inner_area = (
        header_inner_width * header_inner_height
    )

    header_metal_area = (
        header_outer_area - header_inner_area
    )

    m_header = (
        2.0
        * rho
        * header_metal_area
        * height_m
    )

    # Two side plates
    m_side = (
        2.0
        * rho
        * p.side_plate_thickness_m
        * height_m
        * depth_m
    )

    # Explicit braze allowance
    m_joint = (
        n_tubes * p.braze_mass_per_tube_kg
    )

    m_total = (
        m_tube
        + m_fin
        + m_header
        + m_side
        + m_joint
    )

    return {
        "tube_count": n_tubes,
        "tube_mass_kg": m_tube,
        "fin_mass_kg": m_fin,
        "header_mass_kg": m_header,
        "side_plate_mass_kg": m_side,
        "joint_mass_kg": m_joint,
        "core_mass_kg": m_total,
        "frontal_area_m2": frontal_area,
    }


# ============================================================
# 4. ANGLE SWEEP
# ============================================================

def run_angle_sweep(p: DesignInputs):

    results = []

    angle = p.angle_start_deg

    while angle <= p.angle_end_deg + 1e-9:

        h_max = calculate_max_core_height(
            angle,
            p.core_depth_m,
            p.fan_axial_m,
            p.max_vertical_m,
            p.max_longitudinal_m,
        )

        width = p.core_width_m

        width_ok = width <= p.max_width_m
        height_ok = h_max > 0.0

        if width_ok and height_ok:

            vertical, longitudinal = calculate_envelope(
                angle,
                h_max,
                p.core_depth_m,
                p.fan_axial_m,
            )

            mass = calculate_core_mass(
                width,
                h_max,
                p.core_depth_m,
                p,
            )

            results.append({
                "angle_deg": angle,
                "core_width_mm": width * 1000.0,
                "max_core_height_mm": h_max * 1000.0,
                "core_depth_mm": p.core_depth_m * 1000.0,
                "vertical_envelope_mm": vertical * 1000.0,
                "longitudinal_envelope_mm": longitudinal * 1000.0,
                "width_ok": width_ok,
                "geometry_ok": True,
                "tube_count": mass["tube_count"],
                "tube_mass_kg": mass["tube_mass_kg"],
                "fin_mass_kg": mass["fin_mass_kg"],
                "header_mass_kg": mass["header_mass_kg"],
                "side_plate_mass_kg": mass["side_plate_mass_kg"],
                "joint_mass_kg": mass["joint_mass_kg"],
                "core_mass_kg": mass["core_mass_kg"],
                "thermal_feasibility": "NOT_EVALUATED",
            })

        else:
            results.append({
                "angle_deg": angle,
                "core_width_mm": width * 1000.0,
                "max_core_height_mm": h_max * 1000.0,
                "core_depth_mm": p.core_depth_m * 1000.0,
                "vertical_envelope_mm": None,
                "longitudinal_envelope_mm": None,
                "width_ok": width_ok,
                "geometry_ok": False,
                "tube_count": 0,
                "tube_mass_kg": None,
                "fin_mass_kg": None,
                "header_mass_kg": None,
                "side_plate_mass_kg": None,
                "joint_mass_kg": None,
                "core_mass_kg": None,
                "thermal_feasibility": "NOT_EVALUATED",
            })

        angle += p.angle_step_deg

    return results


# ============================================================
# 5. CSV EXPORT
# ============================================================

def export_csv(results, filename="cams_condenser_weight_results.csv"):

    if not results:
        return

    fieldnames = list(results[0].keys())

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)


# ============================================================
# 6. MAIN
# ============================================================

def main():

    p = DesignInputs()

    results = run_angle_sweep(p)

    print("=" * 72)
    print("CAMS CONDENSER WEIGHT MODEL V1.0")
    print("=" * 72)

    print(f"Condenser heat target : {p.q_cond_w / 1000:.2f} kW")
    print(f"Air inlet temperature: {p.t_air_in_c:.1f} degC")
    print(f"Air outlet temperature: {p.t_air_in_c + p.delta_t_air_k:.1f} degC")
    print(f"Air mass flow         : {p.air_mass_flow_kg_s:.3f} kg/s")
    print(f"Core width            : {p.core_width_m * 1000:.1f} mm")
    print(f"Core depth            : {p.core_depth_m * 1000:.1f} mm")
    print()

    print(
        f"{'Angle':>7} "
        f"{'Height':>10} "
        f"{'Mass':>10} "
        f"{'Geometry':>12} "
        f"{'Thermal':>18}"
    )

    print("-" * 65)

    for r in results:

        height = r["max_core_height_mm"]
        mass = r["core_mass_kg"]

        height_text = (
            f"{height:.1f}"
            if height is not None else "N/A"
        )

        mass_text = (
            f"{mass:.3f}"
            if mass is not None else "N/A"
        )

        print(
            f"{r['angle_deg']:7.1f} "
            f"{height_text:>10} "
            f"{mass_text:>10} "
            f"{str(r['geometry_ok']):>12} "
            f"{r['thermal_feasibility']:>18}"
        )

    export_csv(results)

    print()
    print("CSV exported: cams_condenser_weight_results.csv")
    print()
    print("WARNING:")
    print("Mass results are preliminary geometry-based estimates.")
    print("No 12 kW heat-transfer feasibility has been established.")


if __name__ == "__main__":
    main()