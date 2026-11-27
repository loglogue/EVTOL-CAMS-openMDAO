
"""
CAMS Condenser Heat Exchanger Model
===================================

Purpose:
    Connect CAMS condenser geometry to OpenConcept HXGroup.
    Use OpenConcept OSF correlations for preliminary air-side analysis.

Important:
    - Cold side: air (OSF approximation)
    - Hot side: placeholder inputs only
    - Hot-side results and total HX heat transfer are NOT physically validated.
    - Air-side pressure drop is preliminary and requires experimental correlation
      / manufacturer data for final design.

Run:
    python cams_condenser_hx.py
"""

import math
import numpy as np
import openmdao.api as om

from openconcept.thermal.heat_exchanger import HXGroup
from cams_condenser_geometry import CondenserGeometry


# ============================================================
# 1. CAMS operating conditions
# ============================================================

AIR_VOLUME_FLOW = 3000.0 / 3600.0  # m^3/s

AIR_T_IN = 35.0 + 273.15           # K
AIR_RHO = 1.1335                   # kg/m^3
AIR_CP = 1005.0                    # J/(kg K)
AIR_K = 0.0267                     # W/(m K)
AIR_MU = 1.89e-5                   # Pa s

AIR_MDOT = AIR_VOLUME_FLOW * AIR_RHO


# ============================================================
# 2. Preliminary hot-side placeholder conditions
# ============================================================

# These values are only used to make HXGroup executable.
# They do NOT represent a validated R134a flat-tube model.

HOT_MDOT = 0.1                     # kg/s
HOT_T_IN = 373.15                  # K
HOT_RHO = 50.0                     # kg/m^3
HOT_CP = 1500.0                    # J/(kg K)
HOT_K = 0.05                       # W/(m K)
HOT_MU = 1.0e-5                    # Pa s


# ============================================================
# 3. Helper functions
# ============================================================

def scalar(value):
    """Convert OpenMDAO output to a Python float."""
    return float(np.asarray(value).reshape(-1)[0])


def get_io_name(prob, variable_name, io_type):
    """
    Find the absolute OpenMDAO variable name by promoted name.

    io_type:
        'input' or 'output'
    """

    if io_type == "input":
        io_list = prob.model.list_inputs(
            out_stream=None,
            prom_name=True
        )
    else:
        io_list = prob.model.list_outputs(
            out_stream=None,
            prom_name=True
        )

    # Exact promoted-name match
    for abs_name, metadata in io_list:
        prom_name = metadata.get("prom_name", "")

        if prom_name == variable_name:
            return abs_name

    # Fallback: match the end of the absolute variable name
    for abs_name, metadata in io_list:
        if abs_name.endswith("." + variable_name):
            return abs_name

    return None


def set_model_input(prob, name, value, required=True):
    """Set an HXGroup input using its promoted or absolute name."""

    abs_name = get_io_name(prob, name, "input")

    if abs_name is None:
        if required:
            raise KeyError(
                f"Cannot find required HXGroup input: {name}"
            )
        print(f"[WARNING] Input not found, skipped: {name}")
        return

    prob.set_val(abs_name, value)


def get_model_output(prob, name, required=True):
    """Read an HXGroup output using its promoted or absolute name."""

    abs_name = get_io_name(prob, name, "output")

    if abs_name is None:
        if required:
            raise KeyError(
                f"Cannot find required HXGroup output: {name}"
            )
        return None

    return scalar(prob.get_val(abs_name))


# ============================================================
# 4. Read CAMS condenser geometry
# ============================================================

geometry = CondenserGeometry()

# Basic dimensions
W_core = geometry.W_core
H_core = geometry.H_core
L_air = geometry.L_air

# OSF geometry
H_fin = geometry.H_fin
s_fin = geometry.s_fin
t_fin = geometry.t_fin
l_offset = geometry.l_offset

# Tube geometry
N_tube = geometry.N_tube
H_tube = geometry.H_tube

# Number of fin channels
N_fin = round(W_core / s_fin)
N_gap = N_tube - 1

# Clear air passage between adjacent tubes
s_clear = H_fin

# OpenConcept OSF geometry mapping
CHANNEL_WIDTH_COLD = s_clear
CHANNEL_HEIGHT_COLD = H_fin
FIN_LENGTH_COLD = l_offset
FIN_THICKNESS = t_fin

N_WIDE_COLD = N_fin
N_LONG_COLD = L_air / l_offset
N_TALL = N_gap

# Material properties: aluminum
MATERIAL_RHO = 2700.0              # kg/m^3
MATERIAL_K = 190.0                 # W/(m K)

# Preliminary hot-side OSF placeholder geometry
CHANNEL_WIDTH_HOT = 0.0043214      # m, approximate port width
CHANNEL_HEIGHT_HOT = 0.0019        # m, approximate port height
FIN_LENGTH_HOT = 0.006             # m
N_WIDE_HOT = 70
N_LONG_HOT = 10.0

# Wall / case thickness
PLATE_THICKNESS = geometry.t_wall
CASE_THICKNESS = geometry.t_side


# ============================================================
# 5. Build OpenConcept model
# ============================================================

prob = om.Problem()

prob.model.add_subsystem(
    "hx",
    HXGroup(num_nodes=1)
)

prob.setup()


# ============================================================
# 6. Set geometry inputs
# ============================================================

geometry_inputs = {
    # Cold side: air
    "channel_width_cold": CHANNEL_WIDTH_COLD,
    "channel_height_cold": CHANNEL_HEIGHT_COLD,
    "fin_length_cold": FIN_LENGTH_COLD,
    "fin_thickness": FIN_THICKNESS,
    "n_wide_cold": N_WIDE_COLD,
    "n_long_cold": N_LONG_COLD,
    "n_tall": N_TALL,

    # Hot side: placeholder only
    "channel_width_hot": CHANNEL_WIDTH_HOT,
    "channel_height_hot": CHANNEL_HEIGHT_HOT,
    "fin_length_hot": FIN_LENGTH_HOT,
    "n_wide_hot": N_WIDE_HOT,
    "n_long_hot": N_LONG_HOT,

    # Shared geometry and material
    "plate_thickness": PLATE_THICKNESS,
    "case_thickness": CASE_THICKNESS,
    "material_rho": MATERIAL_RHO,
    "material_k": MATERIAL_K,
}

for name, value in geometry_inputs.items():
    set_model_input(prob, name, value, required=True)


# ============================================================
# 7. Set cold-side fluid inputs: air
# ============================================================

cold_fluid_inputs = {
    "mdot_cold": AIR_MDOT,
    "T_in_cold": AIR_T_IN,
    "rho_cold": AIR_RHO,
    "cp_cold": AIR_CP,
    "k_cold": AIR_K,
    "mu_cold": AIR_MU,
}

for name, value in cold_fluid_inputs.items():
    set_model_input(prob, name, value, required=True)


# ============================================================
# 8. Set hot-side fluid inputs: placeholder
# ============================================================

hot_fluid_inputs = {
    "mdot_hot": HOT_MDOT,
    "T_in_hot": HOT_T_IN,
    "rho_hot": HOT_RHO,
    "cp_hot": HOT_CP,
    "k_hot": HOT_K,
    "mu_hot": HOT_MU,
}

for name, value in hot_fluid_inputs.items():
    set_model_input(prob, name, value, required=True)


# ============================================================
# 9. Run model
# ============================================================

print("\nRunning OpenConcept HXGroup ...")

prob.run_model()

print("Model execution completed.")


# ============================================================
# 10. Extract air-side outputs
# ============================================================

output_names = [
    "xs_area_cold",
    "dh_cold",
    "heat_transfer_area_cold",
    "length_overall",
    "Re_dh_cold",
    "j_cold",
    "f_cold",
    "Nu_dh_cold",
    "h_conv_cold",
    "eta_overall_cold",
    "delta_p_cold",
]

results = {}

for name in output_names:
    value = get_model_output(prob, name, required=False)

    if value is not None:
        results[name] = value


# ============================================================
# 11. Print operating conditions
# ============================================================

print("\n")
print("=" * 72)
print("CAMS CONDENSER - AIR SIDE OPERATING CONDITIONS")
print("=" * 72)

print(f"Air volume flow       : {AIR_VOLUME_FLOW:.6f} m^3/s")
print(f"Air volume flow       : {AIR_VOLUME_FLOW * 3600:.2f} m^3/h")
print(f"Air mass flow         : {AIR_MDOT:.6f} kg/s")
print(f"Air inlet temperature : {AIR_T_IN - 273.15:.2f} degC")
print(f"Air density           : {AIR_RHO:.4f} kg/m^3")

A_frontal = W_core * H_core
V_frontal = AIR_VOLUME_FLOW / A_frontal

if "xs_area_cold" in results:
    V_free = AIR_VOLUME_FLOW / results["xs_area_cold"]
else:
    V_free = float("nan")

print(f"Frontal area          : {A_frontal:.6f} m^2")
print(f"Frontal velocity      : {V_frontal:.4f} m/s")

if math.isfinite(V_free):
    print(f"Free-flow velocity    : {V_free:.4f} m/s")


# ============================================================
# 12. Print CAMS geometry
# ============================================================

print("\n")
print("=" * 72)
print("CAMS CONDENSER GEOMETRY")
print("=" * 72)

print(f"Core width            : {W_core * 1000:.3f} mm")
print(f"Core height           : {H_core * 1000:.3f} mm")
print(f"Air flow depth        : {L_air * 1000:.3f} mm")

print(f"Tube count            : {N_tube}")
print(f"Tube height           : {H_tube * 1000:.3f} mm")

print(f"Fin height            : {H_fin * 1000:.3f} mm")
print(f"Fin pitch             : {s_fin * 1000:.3f} mm")
print(f"Fin thickness         : {t_fin * 1000:.3f} mm")
print(f"OSF segment length    : {l_offset * 1000:.3f} mm")

print(f"n_wide_cold           : {N_WIDE_COLD}")
print(f"n_long_cold           : {N_LONG_COLD:.6f}")
print(f"n_tall                : {N_TALL}")


# ============================================================
# 13. Geometry consistency check
# ============================================================

print("\n")
print("=" * 72)
print("GEOMETRY CONSISTENCY CHECK")
print("=" * 72)

A_air_free_cams = geometry.A_air_free

print(f"CAMS A_air_free       : {A_air_free_cams:.9f} m^2")

if "xs_area_cold" in results:

    xs_area_cold = results["xs_area_cold"]

    abs_diff = abs(xs_area_cold - A_air_free_cams)

    if A_air_free_cams > 0:
        rel_diff = abs_diff / A_air_free_cams * 100.0
    else:
        rel_diff = float("nan")

    print(f"OpenConcept xs_area   : {xs_area_cold:.9f} m^2")
    print(f"Absolute difference  : {abs_diff:.9e} m^2")
    print(f"Relative difference  : {rel_diff:.6f} %")

    if math.isclose(
        xs_area_cold,
        A_air_free_cams,
        rel_tol=1e-6,
        abs_tol=1e-9
    ):
        print("[PASS] Air-side free-flow area matches.")
    else:
        print("[WARNING] Air-side free-flow area does not match.")
        print("Please check the OSF geometry mapping.")

else:
    print("[WARNING] OpenConcept xs_area_cold output was not found.")


# Check overall air flow depth
if "length_overall" in results:

    length_overall = results["length_overall"]

    print(f"\nCAMS L_air            : {L_air:.9f} m")
    print(f"OpenConcept length    : {length_overall:.9f} m")

    if math.isclose(
        length_overall,
        L_air,
        rel_tol=1e-6,
        abs_tol=1e-9
    ):
        print("[PASS] Overall air flow depth matches.")
    else:
        print("[WARNING] Overall air flow depth does not match.")

else:
    print("[WARNING] OpenConcept length_overall output was not found.")


# ============================================================
# 14. Print OpenConcept air-side thermal / hydraulic results
# ============================================================

print("\n")
print("=" * 72)
print("OPENCONCEPT AIR-SIDE RESULTS")
print("=" * 72)

display_units = {
    "xs_area_cold": ("m^2", 1.0),
    "dh_cold": ("mm", 1000.0),
    "heat_transfer_area_cold": ("m^2", 1.0),
    "length_overall": ("mm", 1000.0),
    "Re_dh_cold": ("-", 1.0),
    "j_cold": ("-", 1.0),
    "f_cold": ("-", 1.0),
    "Nu_dh_cold": ("-", 1.0),
    "h_conv_cold": ("W/(m^2 K)", 1.0),
    "eta_overall_cold": ("-", 1.0),
    "delta_p_cold": ("Pa, OpenConcept sign", 1.0),
}

for name, value in results.items():

    unit, factor = display_units.get(name, ("-", 1.0))

    print(
        f"{name:28s}: "
        f"{value * factor:14.6f} {unit}"
    )

if "delta_p_cold" in results:
    dp_positive = -results["delta_p_cold"]

    print("\nEstimated positive air-side pressure drop:")
    print(f"Air-side pressure drop : {dp_positive:.3f} Pa")


# ============================================================
# 15. Final notes
# ============================================================

print("\n")
print("=" * 72)
print("MODEL LIMITATIONS")
print("=" * 72)

print("1. Cold-side results use OpenConcept OSF correlations.")
print("2. Hot-side inputs are placeholders, not a real R134a model.")
print("3. Total heat transfer and hot-side pressure drop are not validated.")
print("4. Air-side pressure drop requires verification against actual OSF geometry.")
print("5. The model uses 3000 m^3/h as the current air-flow operating point.")

print("\nCAMS condenser HX model finished.")
