
"""
CAMS Condenser Heat Exchanger Model V2.0
=========================================

Purpose:
    Connect CAMS condenser geometry to OpenConcept HXGroup.
    Use OpenConcept OSF correlations for preliminary air-side analysis.

Important:
    - Cold side: air (OSF approximation)
    - Hot side: placeholder inputs only
    - Hot-side results and total HX heat transfer are NOT validated.
    - Air-side pressure drop is preliminary.

Updates V2.0:
    1. Correct air density to 0.9096 kg/m^3.
    2. Remove non-existent n_wide_hot and n_long_hot inputs.
    3. Use direct promoted-variable access.
    4. Remove list_inputs calls before final_setup.
    5. Fix xs_area_cold undefined-variable issue.
    6. Add robust input/output checks.
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

# Corrected air density
AIR_RHO = 0.9096                   # kg/m^3

AIR_CP = 1005.0                    # J/(kg K)
AIR_K = 0.0267                     # W/(m K)
AIR_MU = 1.89e-5                   # Pa s

AIR_MDOT = AIR_VOLUME_FLOW * AIR_RHO


# ============================================================
# 2. Preliminary hot-side placeholder conditions
# ============================================================

# Placeholder only.
# These parameters do NOT represent a validated R134a model.

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


def set_model_input(prob, name, value, required=True):
    """
    Set HXGroup input through its promoted variable name.

    HXGroup promotes its subsystem inputs using '*',
    so direct promoted-name access is sufficient.
    """

    try:
        prob.set_val(name, value)

    except (KeyError, ValueError) as exc:

        if required:
            raise KeyError(
                f"Cannot set required HXGroup input: {name}\n"
                f"Original error: {exc}"
            ) from exc

        print(f"[WARNING] Input not found, skipped: {name}")


def get_model_output(prob, name, required=True):
    """Read HXGroup output through its promoted variable name."""

    try:
        return scalar(prob.get_val(name))

    except (KeyError, ValueError) as exc:

        if required:
            raise KeyError(
                f"Cannot find required HXGroup output: {name}\n"
                f"Original error: {exc}"
            ) from exc

        return None


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

# Number of tube gaps
N_gap = N_tube - 1

# Clear air passage
s_clear = H_fin

# OpenConcept OSF geometry mapping
CHANNEL_WIDTH_COLD = s_clear
CHANNEL_HEIGHT_COLD = H_fin
FIN_LENGTH_COLD = l_offset
FIN_THICKNESS = t_fin

N_WIDE_COLD = N_fin
N_LONG_COLD = L_air / l_offset
N_TALL = N_gap


# ============================================================
# 5. Material and hot-side placeholder geometry
# ============================================================

# Aluminum
MATERIAL_RHO = 2700.0              # kg/m^3
MATERIAL_K = 190.0                 # W/(m K)

# Hot-side placeholder geometry
CHANNEL_WIDTH_HOT = 0.0043214      # m
CHANNEL_HEIGHT_HOT = 0.0019        # m
FIN_LENGTH_HOT = 0.006             # m

# IMPORTANT:
# n_wide_hot and n_long_hot are NOT HXGroup inputs.
# OpenConcept calculates them internally.

# Wall / case thickness
PLATE_THICKNESS = geometry.t_wall
CASE_THICKNESS = geometry.t_side


# ============================================================
# 6. Build OpenConcept model
# ============================================================

prob = om.Problem()

prob.model.add_subsystem(
    "hx",
    HXGroup(num_nodes=1)
)

prob.setup()


# ============================================================
# 7. Set geometry inputs
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

    # Shared geometry and material
    "plate_thickness": PLATE_THICKNESS,
    "case_thickness": CASE_THICKNESS,

    "material_rho": MATERIAL_RHO,
    "material_k": MATERIAL_K,
}

for name, value in geometry_inputs.items():

    set_model_input(
        prob,
        name,
        value,
        required=True
    )


# ============================================================
# 8. Set cold-side fluid inputs: air
# ============================================================

cold_fluid_inputs = {

    "mdot_cold": np.array([AIR_MDOT]),
    "T_in_cold": np.array([AIR_T_IN]),
    "rho_cold": np.array([AIR_RHO]),

    "cp_cold": AIR_CP,
    "k_cold": AIR_K,
    "mu_cold": AIR_MU,
}

for name, value in cold_fluid_inputs.items():

    set_model_input(
        prob,
        name,
        value,
        required=True
    )


# ============================================================
# 9. Set hot-side fluid inputs: placeholder
# ============================================================

hot_fluid_inputs = {

    "mdot_hot": np.array([HOT_MDOT]),
    "T_in_hot": np.array([HOT_T_IN]),
    "rho_hot": np.array([HOT_RHO]),

    "cp_hot": HOT_CP,
    "k_hot": HOT_K,
    "mu_hot": HOT_MU,
}

for name, value in hot_fluid_inputs.items():

    set_model_input(
        prob,
        name,
        value,
        required=True
    )


# ============================================================
# 10. Run model
# ============================================================

print("\nRunning OpenConcept HXGroup ...")

prob.run_model()

print("Model execution completed.")


# ============================================================
# 11. Extract OpenConcept outputs
# ============================================================

output_names = [

    "xs_area_cold",
    "dh_cold",
    "heat_transfer_area_cold",

    "length_overall",
    "height_overall",
    "width_overall",
    "frontal_area",

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

    value = get_model_output(
        prob,
        name,
        required=False
    )

    if value is not None:
        results[name] = value


# ============================================================
# 12. Print operating conditions
# ============================================================

print("\n")
print("=" * 76)
print("CAMS CONDENSER - AIR SIDE OPERATING CONDITIONS")
print("=" * 76)

print(f"Air volume flow       : {AIR_VOLUME_FLOW:.6f} m^3/s")
print(f"Air volume flow       : {AIR_VOLUME_FLOW * 3600:.2f} m^3/h")

print(f"Air mass flow         : {AIR_MDOT:.6f} kg/s")

print(f"Air inlet temperature : {AIR_T_IN - 273.15:.2f} degC")
print(f"Air density           : {AIR_RHO:.4f} kg/m^3")

A_frontal = W_core * H_core

V_frontal = AIR_VOLUME_FLOW / A_frontal

print(f"Frontal area          : {A_frontal:.6f} m^2")
print(f"Frontal velocity      : {V_frontal:.4f} m/s")

if "xs_area_cold" in results:

    xs_area_cold = results["xs_area_cold"]

    V_free = AIR_VOLUME_FLOW / xs_area_cold

    print(f"Free-flow area        : {xs_area_cold:.9f} m^2")
    print(f"Free-flow velocity    : {V_free:.4f} m/s")

else:

    print("[WARNING] xs_area_cold output unavailable.")


# ============================================================
# 13. Print CAMS geometry
# ============================================================

print("\n")
print("=" * 76)
print("CAMS CONDENSER GEOMETRY")
print("=" * 76)

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
# 14. Geometry consistency check
# ============================================================

print("\n")
print("=" * 76)
print("GEOMETRY CONSISTENCY CHECK")
print("=" * 76)

A_air_free_cams = geometry.A_air_free

print(f"CAMS A_air_free       : {A_air_free_cams:.9f} m^2")

if "xs_area_cold" in results:

    xs_area_cold = results["xs_area_cold"]

    abs_diff = abs(
        xs_area_cold - A_air_free_cams
    )

    if A_air_free_cams > 0:

        rel_diff = (
            abs_diff / A_air_free_cams * 100.0
        )

    else:

        rel_diff = float("nan")

    print(
        f"OpenConcept xs_area   : "
        f"{xs_area_cold:.9f} m^2"
    )

    print(
        f"Absolute difference  : "
        f"{abs_diff:.9e} m^2"
    )

    print(
        f"Relative difference  : "
        f"{rel_diff:.6f} %"
    )

    if math.isclose(
        xs_area_cold,
        A_air_free_cams,
        rel_tol=1e-6,
        abs_tol=1e-9
    ):

        print("[PASS] Air-side free-flow area matches.")

    else:

        print(
            "[WARNING] Air-side free-flow area does not match."
        )

        print(
            "Please check the OSF geometry mapping."
        )

else:

    print(
        "[WARNING] OpenConcept xs_area_cold output was not found."
    )


# Check overall air flow depth
if "length_overall" in results:

    length_overall = results["length_overall"]

    print(f"\nCAMS L_air            : {L_air:.9f} m")

    print(
        f"OpenConcept length    : "
        f"{length_overall:.9f} m"
    )

    if math.isclose(
        length_overall,
        L_air,
        rel_tol=1e-6,
        abs_tol=1e-9
    ):

        print("[PASS] Overall air flow depth matches.")

    else:

        print(
            "[WARNING] Overall air flow depth does not match."
        )

else:

    print(
        "[WARNING] OpenConcept length_overall output was not found."
    )


# ============================================================
# 15. Print OpenConcept air-side results
# ============================================================

print("\n")
print("=" * 76)
print("OPENCONCEPT AIR-SIDE THERMAL / HYDRAULIC RESULTS")
print("=" * 76)

display_units = {

    "xs_area_cold": ("m^2", 1.0),

    "dh_cold": ("mm", 1000.0),

    "heat_transfer_area_cold": ("m^2", 1.0),

    "length_overall": ("mm", 1000.0),

    "height_overall": ("mm", 1000.0),

    "width_overall": ("mm", 1000.0),

    "frontal_area": ("m^2", 1.0),

    "Re_dh_cold": ("-", 1.0),

    "j_cold": ("-", 1.0),

    "f_cold": ("-", 1.0),

    "Nu_dh_cold": ("-", 1.0),

    "h_conv_cold": ("W/(m^2 K)", 1.0),

    "eta_overall_cold": ("-", 1.0),

    "delta_p_cold": ("Pa, OpenConcept sign", 1.0),
}

for name, value in results.items():

    unit, factor = display_units.get(
        name,
        ("-", 1.0)
    )

    print(
        f"{name:28s}: "
        f"{value * factor:14.6f} {unit}"
    )


# Convert OpenConcept negative pressure-drop convention
if "delta_p_cold" in results:

    dp_positive = -results["delta_p_cold"]

    print("\nEstimated positive air-side pressure drop:")

    print(
        f"Air-side pressure drop : "
        f"{dp_positive:.3f} Pa"
    )


# ============================================================
# 16. Final notes
# ============================================================

print("\n")
print("=" * 76)
print("MODEL LIMITATIONS")
print("=" * 76)

print("1. Cold-side results use OpenConcept OSF correlations.")

print("2. Hot-side inputs are placeholders, not a real R134a model.")

print("3. Total heat transfer and hot-side pressure drop are not validated.")

print("4. Air-side pressure drop requires verification against actual OSF geometry.")

print("5. Air density is set to 0.9096 kg/m^3.")

print("6. Air volume flow is set to 3000 m^3/h.")

print("7. Hot-side channel counts are calculated internally by OpenConcept.")

print("\nCAMS condenser HX model V2.0 finished.")
