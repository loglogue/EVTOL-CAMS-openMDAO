
import csv
import numpy as np

from openmdao.api import (
    Problem,
    Group,
    IndepVarComp,
    ExecComp,
    ScipyOptimizeDriver,
)

from openconcept.thermal.heat_exchanger import HXGroup


# ============================================================
# 1. Global design settings
# ============================================================

NN = 1

# Fixed geometric parameters
N_WIDE_COLD = 25
N_LONG_COLD = 25
N_TALL = 8

CHANNEL_WIDTH_COLD = 1.35
CHANNEL_HEIGHT_HOT = 14.0
CHANNEL_WIDTH_HOT = 1.35

FIN_LENGTH_HOT = 6.0

# Initial design
H_COLD_INITIAL = 14.0       # mm
L_HX_INITIAL = 150.0        # mm
MDOT_COLD_INITIAL = 0.10    # kg/s

# Hot-side operating conditions
MDOT_HOT = 0.20             # kg/s

# Air properties
CP_AIR = 1005.0             # J/kg/K
K_COLD = 0.02596            # W/m/K
K_HOT = 0.026               # W/m/K

MU_COLD = 1.789e-5          # kg/m/s
MU_HOT = 1.80e-5            # kg/m/s

RHO_COLD = 1.12             # kg/m3
RHO_HOT = 1.10              # kg/m3

# Inlet temperatures
T_COLD_IN = 318.15          # K
T_HOT_IN = 363.15           # K

# Structural parameters
FIN_THICKNESS = 0.102       # mm
PLATE_THICKNESS = 0.2       # mm
CASE_THICKNESS = 2.0        # mm

MATERIAL_K = 190.0          # W/m/K
MATERIAL_RHO = 2700.0       # kg/m3


# ============================================================
# 2. Preliminary design constraints
# ============================================================

Q_MIN = 2000.0              # W
DP_COLD_MAX = 1000.0        # Pa
DP_HOT_MAX = 500.0          # Pa

# Stricter limits used by the optimizer (engineering design margins).
Q_DESIGN_MIN = 2200.0       # W
DP_COLD_DESIGN_MAX = 800.0  # Pa
DP_HOT_DESIGN_MAX = 400.0   # Pa

# V2 system-level estimation assumptions (editable placeholders)
FAN_EFFICIENCY_COLD = 0.62
MOTOR_EFFICIENCY_COLD = 0.90
# Additive air-path pressure losses, Pa. Replace with component/vendor data
# when available. These are preliminary placeholders, not validated requirements.
DP_COLD_FILTER_PA = 80.0
DP_COLD_DUCT_PA = 60.0
DP_COLD_GRILLE_PA = 30.0
DP_COLD_BENDS_PA = 40.0
DP_HOT_INLET_PA = 25.0
DP_HOT_DUCT_PA = 25.0
DP_HOT_OUTLET_PA = 25.0
HOT_SIDE_HAS_FAN = False  # hot side assumed ram/externally driven by default

# Preliminary installed-mass allowances relative to bare HX core mass
MASS_FACTOR_HEADERS = 0.12
MASS_FACTOR_CASING = 0.10
MASS_FACTOR_MOUNTS = 0.08
MASS_FACTOR_INSULATION_ACCESSORIES = 0.05

PARETO_Q_MIN = Q_DESIGN_MIN
PARETO_DP_COLD_MAX = DP_COLD_DESIGN_MAX
PARETO_DP_HOT_MAX = DP_HOT_DESIGN_MAX


# ============================================================
# 3. CAMS heat exchanger model
# ============================================================

class CAMSHeatExchanger(Group):

    def initialize(self):

        self.options.declare(
            "num_nodes",
            default=1,
            types=int
        )

    def setup(self):

        nn = self.options["num_nodes"]

        iv = self.add_subsystem(
            "iv",
            IndepVarComp(),
            promotes_outputs=["*"]
        )

        # ----------------------------------------------------
        # Operating conditions
        # ----------------------------------------------------

        iv.add_output(
            "mdot_cold",
            val=np.ones(nn) * MDOT_COLD_INITIAL,
            units="kg/s"
        )

        iv.add_output(
            "mdot_hot",
            val=np.ones(nn) * MDOT_HOT,
            units="kg/s"
        )

        iv.add_output(
            "rho_cold",
            val=np.ones(nn) * RHO_COLD,
            units="kg/m**3"
        )

        iv.add_output(
            "rho_hot",
            val=np.ones(nn) * RHO_HOT,
            units="kg/m**3"
        )

        iv.add_output(
            "T_in_cold",
            val=np.ones(nn) * T_COLD_IN,
            units="K"
        )

        iv.add_output(
            "T_in_hot",
            val=np.ones(nn) * T_HOT_IN,
            units="K"
        )

        # ----------------------------------------------------
        # Fluid properties
        # ----------------------------------------------------

        iv.add_output("cp_cold", val=CP_AIR, units="J/kg/K")
        iv.add_output("cp_hot", val=CP_AIR, units="J/kg/K")

        iv.add_output("k_cold", val=K_COLD, units="W/m/K")
        iv.add_output("k_hot", val=K_HOT, units="W/m/K")

        iv.add_output("mu_cold", val=MU_COLD, units="kg/m/s")
        iv.add_output("mu_hot", val=MU_HOT, units="kg/m/s")

        # ----------------------------------------------------
        # Heat exchanger geometry
        # ----------------------------------------------------

        iv.add_output(
            "channel_width_cold",
            val=CHANNEL_WIDTH_COLD,
            units="mm"
        )

        iv.add_output(
            "channel_height_cold",
            val=H_COLD_INITIAL,
            units="mm"
        )

        iv.add_output(
            "fin_length_cold",
            val=L_HX_INITIAL / N_LONG_COLD,
            units="mm"
        )

        iv.add_output(
            "channel_width_hot",
            val=CHANNEL_WIDTH_HOT,
            units="mm"
        )

        iv.add_output(
            "channel_height_hot",
            val=CHANNEL_HEIGHT_HOT,
            units="mm"
        )

        iv.add_output(
            "fin_length_hot",
            val=FIN_LENGTH_HOT,
            units="mm"
        )

        iv.add_output(
            "fin_thickness",
            val=FIN_THICKNESS,
            units="mm"
        )

        iv.add_output(
            "plate_thickness",
            val=PLATE_THICKNESS,
            units="mm"
        )

        iv.add_output(
            "case_thickness",
            val=CASE_THICKNESS,
            units="mm"
        )

        iv.add_output(
            "material_k",
            val=MATERIAL_K,
            units="W/m/K"
        )

        iv.add_output(
            "material_rho",
            val=MATERIAL_RHO,
            units="kg/m**3"
        )

        # ----------------------------------------------------
        # Number of channels and stacks
        # ----------------------------------------------------

        iv.add_output(
            "ac|propulsion|thermal|hx|n_wide_cold",
            val=N_WIDE_COLD
        )

        iv.add_output(
            "ac|propulsion|thermal|hx|n_long_cold",
            val=N_LONG_COLD
        )

        iv.add_output(
            "ac|propulsion|thermal|hx|n_tall",
            val=N_TALL
        )

        # ----------------------------------------------------
        # OpenConcept HXGroup
        # ----------------------------------------------------

        self.add_subsystem(
            "hx",
            HXGroup(num_nodes=nn),
            promotes=["*"]
        )

        # System-level cold-side pressure loss and fan power are explicit
        # OpenMDAO outputs so fan power can be constrained during optimization.
        # delta_p_cold is negative in HXGroup; negate it to obtain a positive loss.
        self.add_subsystem(
            "fan_model",
            ExecComp(
                [
                    "system_dp_cold_Pa = -delta_p_cold + dp_extra",
                    # Use the expanded expression here instead of using another
                    # ExecComp output as an internal input. This avoids an
                    # OpenMDAO partial-derivative pattern error in some versions.
                    "fan_power_cold_W = (mdot_cold / rho_cold) * (-delta_p_cold + dp_extra) / (eta_fan * eta_motor)",
                ],
                mdot_cold={"units": "kg/s"},
                delta_p_cold={"units": "Pa"},
                dp_extra={"val": DP_COLD_FILTER_PA + DP_COLD_DUCT_PA + DP_COLD_GRILLE_PA + DP_COLD_BENDS_PA, "units": "Pa"},
                rho_cold={"val": RHO_COLD, "units": "kg/m**3"},
                eta_fan={"val": FAN_EFFICIENCY_COLD},
                eta_motor={"val": MOTOR_EFFICIENCY_COLD},
                system_dp_cold_Pa={"units": "Pa"},
                fan_power_cold_W={"units": "W"},
            ),
            promotes_inputs=["mdot_cold", "delta_p_cold"],
            promotes_outputs=["system_dp_cold_Pa", "fan_power_cold_W"],
        )


# ============================================================
# 4. Utility functions
# ============================================================

def get_scalar(prob, name, units=None):

    value = prob.get_val(name, units=units)

    return float(np.asarray(value).reshape(-1)[0])


def set_design_point(prob, height_mm, length_mm, mdot_cold):

    # HXGroup calculates:
    # length_overall = fin_length_cold * n_long_cold

    fin_length = length_mm / N_LONG_COLD

    prob.set_val(
        "channel_height_cold",
        height_mm,
        units="mm"
    )

    prob.set_val(
        "fin_length_cold",
        fin_length,
        units="mm"
    )

    prob.set_val(
        "mdot_cold",
        np.ones(NN) * mdot_cold,
        units="kg/s"
    )


def add_system_estimates(result):
    """Preliminary fan-power and installed-mass estimates.

    System pressure loss = HX core loss + itemized component losses.
    Replace placeholder component losses with measured/vendor/design data.
    """
    vdot_c = float(result["mdot_cold"]) / RHO_COLD
    vdot_h = float(MDOT_HOT) / RHO_HOT

    dp_c_system = (
        float(result["dp_cold_Pa"]) + DP_COLD_FILTER_PA + DP_COLD_DUCT_PA
        + DP_COLD_GRILLE_PA + DP_COLD_BENDS_PA
    )
    dp_h_system = (
        float(result["dp_hot_Pa"]) + DP_HOT_INLET_PA + DP_HOT_DUCT_PA
        + DP_HOT_OUTLET_PA
    )

    p_c = vdot_c * dp_c_system / (FAN_EFFICIENCY_COLD * MOTOR_EFFICIENCY_COLD)
    p_h = (vdot_h * dp_h_system / (FAN_EFFICIENCY_HOT * MOTOR_EFFICIENCY_HOT)
           if HOT_SIDE_HAS_FAN else 0.0)

    core = float(result["mass_kg"])
    m_headers = core * MASS_FACTOR_HEADERS
    m_casing = core * MASS_FACTOR_CASING
    m_mounts = core * MASS_FACTOR_MOUNTS
    m_accessories = core * MASS_FACTOR_INSULATION_ACCESSORIES
    result.update({
        "volume_flow_cold_m3_s": vdot_c,
        "volume_flow_hot_m3_s": vdot_h,
        "dp_cold_filter_Pa": DP_COLD_FILTER_PA,
        "dp_cold_duct_Pa": DP_COLD_DUCT_PA,
        "dp_cold_grille_Pa": DP_COLD_GRILLE_PA,
        "dp_cold_bends_Pa": DP_COLD_BENDS_PA,
        "dp_hot_inlet_Pa": DP_HOT_INLET_PA,
        "dp_hot_duct_Pa": DP_HOT_DUCT_PA,
        "dp_hot_outlet_Pa": DP_HOT_OUTLET_PA,
        "system_dp_cold_Pa": dp_c_system,
        "system_dp_hot_Pa": dp_h_system,
        "fan_power_cold_W": p_c,
        "fan_power_hot_W": p_h,
        "fan_power_total_W": p_c + p_h,
        "core_mass_kg": core,
        "headers_mass_kg": m_headers,
        "casing_mass_kg": m_casing,
        "mounts_mass_kg": m_mounts,
        "accessories_mass_kg": m_accessories,
        "installed_mass_kg": core + m_headers + m_casing + m_mounts + m_accessories,
    })
    return result


def is_pareto_efficient(points):
    """Return the non-dominated mask for objectives that are all minimized."""
    points = np.asarray(points, dtype=float)
    keep = np.ones(points.shape[0], dtype=bool)
    for i, point in enumerate(points):
        dominates = np.all(points <= point, axis=1) & np.any(points < point, axis=1)
        dominates[i] = False
        if np.any(dominates):
            keep[i] = False
    return keep


def pareto_analysis_v4(epsilon_results):
    """Filter feasible epsilon-constraint runs and retain non-dominated points."""
    feasible = [r for r in epsilon_results if r.get("feasible", False) and r.get("driver_success", False)]
    print("\n--- V4 Multi-objective Pareto Analysis ---")
    print(f"Feasible epsilon-constraint solutions: {len(feasible)} / {len(epsilon_results)}")
    if not feasible:
        print("No feasible optimizer point was found. Review bounds and constraints.")
        return []

    objectives = np.array([
        [r["installed_mass_kg"], r["fan_power_total_W"], -r["heat_transfer_W"]]
        for r in feasible
    ])
    pareto = [r for r, flag in zip(feasible, is_pareto_efficient(objectives)) if flag]
    pareto.sort(key=lambda r: (r["installed_mass_kg"], r["fan_power_total_W"]))

    print(f"Non-dominated solutions: {len(pareto)}")
    print("Installed kg | Fan W | Q W | Core DPc Pa | System DPc Pa | H mm | L mm | mdot kg/s")
    for r in pareto:
        print(
            f"{r['installed_mass_kg']:.3f} | {r['fan_power_total_W']:.1f} | "
            f"{r['heat_transfer_W']:.1f} | {r['dp_cold_Pa']:.1f} | "
            f"{r['system_dp_cold_Pa']:.1f} | {r['channel_height_cold_mm']:.1f} | "
            f"{r['length_mm']:.1f} | {r['mdot_cold']:.4f}"
        )

    def export_csv(filename, rows):
        if not rows:
            return
        keys = list(dict.fromkeys(k for row in rows for k in row.keys()))
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys, restval="")
            writer.writeheader()
            writer.writerows(rows)

    export_csv("cams_hx_epsilon_runs_v4.csv", epsilon_results)
    export_csv("cams_hx_pareto_v4.csv", pareto)
    print("CSV exported: cams_hx_epsilon_runs_v4.csv, cams_hx_pareto_v4.csv")
    return pareto


def read_results(prob):

    # Operating flow characteristics

    area_cold = get_scalar(prob, "xs_area_cold", "m**2")
    area_hot = get_scalar(prob, "xs_area_hot", "m**2")

    velocity_cold = (
        get_scalar(prob, "mdot_cold", "kg/s")
        / (RHO_COLD * area_cold)
    )

    velocity_hot = MDOT_HOT / (RHO_HOT * area_hot)

    # Actual model outputs

    result = {

        "channel_height_cold_mm":
            get_scalar(prob, "channel_height_cold", "mm"),

        "length_mm":
            get_scalar(prob, "length_overall", "m") * 1000.0,

        "width_mm":
            get_scalar(prob, "width_overall", "m") * 1000.0,

        "height_mm":
            get_scalar(prob, "height_overall", "m") * 1000.0,

        "frontal_area_m2":
            get_scalar(prob, "frontal_area", "m**2"),

        "mdot_cold":
            get_scalar(prob, "mdot_cold", "kg/s"),

        "heat_transfer_W":
            get_scalar(prob, "heat_transfer", "W"),

        "UA_W_K":
            get_scalar(prob, "UA_overall", "W/K"),

        "NTU":
            get_scalar(prob, "NTU"),

        "effectiveness":
            get_scalar(prob, "effectiveness"),

        "dp_cold_Pa":
            abs(get_scalar(prob, "delta_p_cold", "Pa")),

        "dp_hot_Pa":
            abs(get_scalar(prob, "delta_p_hot", "Pa")),

        "mass_kg":
            get_scalar(prob, "component_weight", "kg"),

        "velocity_cold_m_s":
            velocity_cold,

        "velocity_hot_m_s":
            velocity_hot,

        "Re_cold":
            get_scalar(prob, "Re_dh_cold"),

        "Re_hot":
            get_scalar(prob, "Re_dh_hot"),

        "h_cold_W_m2K":
            get_scalar(prob, "h_conv_cold", "W/m**2/K"),

        "h_hot_W_m2K":
            get_scalar(prob, "h_conv_hot", "W/m**2/K"),

        "area_cold_m2":
            area_cold,

        "area_hot_m2":
            area_hot,

    }

    return add_system_estimates(result)


def print_result(
    title,
    result,
    q_min=Q_MIN,
    dp_cold_max=DP_COLD_MAX,
    dp_hot_max=DP_HOT_MAX,
):

    print("\n" + "=" * 65)
    print(title)
    print("=" * 65)

    print("\n--- Design Variables ---")

    print(
        f"Cold channel height : "
        f"{result['channel_height_cold_mm']:.3f} mm"
    )

    print(
        f"Heat exchanger length : "
        f"{result['length_mm']:.3f} mm"
    )

    print(
        f"Cold mass flow : "
        f"{result['mdot_cold']:.4f} kg/s"
    )

    print("\n--- Thermal Performance ---")

    print(
        f"Heat transfer : "
        f"{result['heat_transfer_W']:.2f} W"
    )

    print(
        f"UA : "
        f"{result['UA_W_K']:.3f} W/K"
    )

    print(
        f"NTU : "
        f"{result['NTU']:.4f}"
    )

    print(
        f"Effectiveness : "
        f"{result['effectiveness'] * 100:.2f} %"
    )

    print("\n--- Pressure Drop ---")

    print(
        f"Cold side : "
        f"{result['dp_cold_Pa']:.2f} Pa"
    )

    print(
        f"Hot side : "
        f"{result['dp_hot_Pa']:.2f} Pa"
    )

    print("\n--- Flow Characteristics ---")

    print(
        f"Cold velocity : "
        f"{result['velocity_cold_m_s']:.3f} m/s"
    )

    print(
        f"Hot velocity : "
        f"{result['velocity_hot_m_s']:.3f} m/s"
    )

    print(
        f"Cold Reynolds number : "
        f"{result['Re_cold']:.1f}"
    )

    print(
        f"Hot Reynolds number : "
        f"{result['Re_hot']:.1f}"
    )

    print("\n--- Geometry and Weight ---")

    print(
        f"Length : {result['length_mm']:.2f} mm"
    )

    print(
        f"Width : {result['width_mm']:.2f} mm"
    )

    print(
        f"Height : {result['height_mm']:.2f} mm"
    )

    print(
        f"Frontal area : "
        f"{result['frontal_area_m2']:.6f} m2"
    )

    print(
        f"Core weight : "
        f"{result['mass_kg']:.4f} kg"
    )

    print(f"Installed mass estimate : {result['installed_mass_kg']:.4f} kg")
    print(f"Cold-side system pressure drop : {result['system_dp_cold_Pa']:.2f} Pa")
    print(f"Hot-side system pressure drop : {result['system_dp_hot_Pa']:.2f} Pa")
    print(f"Cabin/common fan power : {result['fan_power_cold_W']:.2f} W")
    print(f"Total modeled fan power : {result['fan_power_total_W']:.2f} W")

    print("\n--- Design Constraint Check ---")

    q_ok = result["heat_transfer_W"] >= q_min - 1e-6

    cold_ok = result["dp_cold_Pa"] <= dp_cold_max

    hot_ok = result["dp_hot_Pa"] <= dp_hot_max

    print(
        f"Heat transfer >= {q_min:.0f} W : "
        f"{'PASS' if q_ok else 'FAIL'}"
    )

    print(
        f"Cold pressure drop <= {dp_cold_max:.0f} Pa : "
        f"{'PASS' if cold_ok else 'FAIL'}"
    )

    print(
        f"Hot pressure drop <= {dp_hot_max:.0f} Pa : "
        f"{'PASS' if hot_ok else 'FAIL'}"
    )

    # Relative reserve against selected limits; not a certification margin.
    q_reserve = (result["heat_transfer_W"] - q_min) / q_min * 100.0
    cold_reserve = (dp_cold_max - result["dp_cold_Pa"]) / dp_cold_max * 100.0
    hot_reserve = (dp_hot_max - result["dp_hot_Pa"]) / dp_hot_max * 100.0
    print("\n--- Constraint Reserve (relative to selected limits) ---")
    print(f"Heat-duty reserve : {q_reserve:+.2f} %")
    print(f"Cold-side DP reserve : {cold_reserve:+.2f} %")
    print(f"Hot-side DP reserve : {hot_reserve:+.2f} %")


# ============================================================
# 5. Build a normal analysis problem
# ============================================================

def build_analysis_problem():

    prob = Problem(
        model=CAMSHeatExchanger(num_nodes=NN)
    )

    prob.setup()

    return prob


# ============================================================
# 6. Baseline analysis
# ============================================================

def baseline_analysis():

    print("\n\n")
    print("#" * 70)
    print("1. BASELINE CAMS HEAT EXCHANGER ANALYSIS")
    print("#" * 70)

    prob = build_analysis_problem()

    set_design_point(
        prob,
        H_COLD_INITIAL,
        L_HX_INITIAL,
        MDOT_COLD_INITIAL
    )

    prob.run_model()

    result = read_results(prob)

    print_result(
        "BASELINE DESIGN",
        result
    )

    return result


# ============================================================
# 7. Parametric sweep
# ============================================================

def parametric_sweep():

    print("\n\n")
    print("#" * 70)
    print("2. PARAMETRIC DESIGN SWEEP")
    print("#" * 70)

    # Parameter ranges

    height_list = [
        10, 12, 14, 16, 18,
        20, 22, 24, 26, 28
    ]

    length_list = [
        100, 125, 150, 175, 200
    ]

    mdot_list = [
        0.06, 0.08, 0.10, 0.12, 0.14
    ]

    prob = build_analysis_problem()

    results = []

    total = (
        len(height_list)
        * len(length_list)
        * len(mdot_list)
    )

    count = 0

    for height in height_list:

        for length in length_list:

            for mdot in mdot_list:

                count += 1

                set_design_point(
                    prob,
                    height,
                    length,
                    mdot
                )

                prob.run_model()

                result = read_results(prob)

                result["feasible"] = (
                    result["heat_transfer_W"] >= Q_MIN
                    and result["dp_cold_Pa"] <= DP_COLD_MAX
                    and result["dp_hot_Pa"] <= DP_HOT_MAX
                )

                results.append(result)

                if count % 25 == 0:

                    print(
                        f"Completed {count}/{total} "
                        f"design points"
                    )

    # --------------------------------------------------------
    # Save CSV
    # --------------------------------------------------------

    csv_file = "cams_hx_sweep.csv"

    fieldnames = list(results[0].keys())

    with open(
        csv_file,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(results)

    print(f"\nCSV exported: {csv_file}")

    # --------------------------------------------------------
    # Find feasible designs
    # --------------------------------------------------------

    feasible = [
        r for r in results
        if r["feasible"]
    ]

    print("\n--- Sweep Summary ---")

    print(f"Total design points : {total}")

    print(f"Feasible designs : {len(feasible)}")

    if len(feasible) > 0:

        feasible.sort(
            key=lambda x: x["mass_kg"]
        )

        print("\n--- Ten Lightest Feasible Designs ---")

        print(
            f"{'Height':>8s}"
            f"{'Length':>9s}"
            f"{'Flow':>9s}"
            f"{'Q(W)':>11s}"
            f"{'DPc(Pa)':>11s}"
            f"{'DPh(Pa)':>11s}"
            f"{'Mass(kg)':>11s}"
        )

        for r in feasible[:10]:

            print(
                f"{r['channel_height_cold_mm']:8.1f}"
                f"{r['length_mm']:9.1f}"
                f"{r['mdot_cold']:9.3f}"
                f"{r['heat_transfer_W']:11.1f}"
                f"{r['dp_cold_Pa']:11.1f}"
                f"{r['dp_hot_Pa']:11.1f}"
                f"{r['mass_kg']:11.4f}"
            )

        best = feasible[0]

        print_result(
            "BEST FEASIBLE SWEEP DESIGN",
            best
        )

    else:

        best = None

        print(
            "\n[WARNING] No design satisfies all "
            "current constraints."
        )

        # Rank by normalized constraint violation
        def violation(r):

            return (
                max(0.0, Q_MIN - r["heat_transfer_W"]) / Q_MIN
                + max(0.0, r["dp_cold_Pa"] - DP_COLD_MAX)
                / DP_COLD_MAX
                + max(0.0, r["dp_hot_Pa"] - DP_HOT_MAX)
                / DP_HOT_MAX
            )

        results.sort(key=violation)

        print("\nTen designs with smallest constraint violations:")

        for r in results[:10]:

            print(
                f"H={r['channel_height_cold_mm']:.1f} mm, "
                f"L={r['length_mm']:.1f} mm, "
                f"mdot={r['mdot_cold']:.3f} kg/s, "
                f"Q={r['heat_transfer_W']:.1f} W, "
                f"DPc={r['dp_cold_Pa']:.1f} Pa, "
                f"DPh={r['dp_hot_Pa']:.1f} Pa, "
                f"mass={r['mass_kg']:.4f} kg"
            )

    return results, best


# ============================================================
# 8. OpenMDAO optimization
# ============================================================

def run_epsilon_optimization(q_target_W, fan_cap_W, initial_design=None):
    """One epsilon-constraint solve: minimize core mass at Q and fan-power limits."""
    prob = Problem(model=CAMSHeatExchanger(num_nodes=NN))
    prob.driver = ScipyOptimizeDriver()
    prob.driver.options["optimizer"] = "SLSQP"
    prob.driver.options["maxiter"] = 250
    prob.driver.options["tol"] = 1e-6
    prob.driver.options["disp"] = False

    prob.model.add_design_var("channel_height_cold", lower=14.0, upper=28.0, units="mm")
    prob.model.add_design_var("fin_length_cold", lower=4.0, upper=8.0, units="mm")
    prob.model.add_design_var("mdot_cold", lower=0.06, upper=0.14, units="kg/s")

    # Objective: minimize core mass. The current installed-mass model is a
    # constant multiplier of core mass; improve it when component-level masses exist.
    prob.model.add_objective("component_weight")

    prob.model.add_constraint("heat_transfer", lower=float(q_target_W))
    prob.model.add_constraint("delta_p_cold", lower=-DP_COLD_DESIGN_MAX)
    prob.model.add_constraint("delta_p_hot", lower=-DP_HOT_DESIGN_MAX)
    prob.model.add_constraint("fan_power_cold_W", upper=float(fan_cap_W))

    prob.setup()
    if initial_design is None:
        initial_design = (H_COLD_INITIAL, L_HX_INITIAL, MDOT_COLD_INITIAL)
    set_design_point(prob, *initial_design)

    driver_success = False
    error_message = ""
    try:
        prob.run_model()
        driver_result = prob.run_driver()
        driver_success = bool(driver_result.success)
    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        # Retain the current model point for diagnosis; it will not be treated
        # as a feasible optimizer result unless all constraints are satisfied.
        try:
            prob.run_model()
        except Exception:
            pass

    result = read_results(prob)
    q_ok = result["heat_transfer_W"] >= q_target_W - 1e-3
    cold_ok = result["dp_cold_Pa"] <= DP_COLD_DESIGN_MAX + 1e-3
    hot_ok = result["dp_hot_Pa"] <= DP_HOT_DESIGN_MAX + 1e-3
    fan_ok = result["fan_power_total_W"] <= fan_cap_W + 1e-3
    result.update({
        "epsilon_q_target_W": float(q_target_W),
        "epsilon_fan_cap_W": float(fan_cap_W),
        "driver_success": driver_success,
        "feasible": bool(q_ok and cold_ok and hot_ok and fan_ok),
        "q_constraint_pass": bool(q_ok),
        "cold_core_dp_pass": bool(cold_ok),
        "hot_core_dp_pass": bool(hot_ok),
        "fan_power_pass": bool(fan_ok),
        "optimizer_message": error_message,
    })
    return result


def optimization_analysis_v4():
    print("\n\n" + "#" * 70)
    print("4. V4 MULTI-OBJECTIVE OPTIMIZATION (EPSILON-CONSTRAINT METHOD)")
    print("#" * 70)
    print("Objective: minimize HX core mass")
    print("Constraints: Q >= epsilon target; cold/hot core DP limits; fan power <= epsilon cap")

    # Epsilon grid. Increase/decrease these lists to refine the Pareto front.
    q_targets = [2000.0, 2100.0, 2200.0, 2300.0]
    fan_caps = [140.0, 160.0, 180.0, 200.0, 220.0, 240.0]

    all_results = []
    total = len(q_targets) * len(fan_caps)
    count = 0
    warm_start = (H_COLD_INITIAL, L_HX_INITIAL, MDOT_COLD_INITIAL)

    for q_target in q_targets:
        for fan_cap in fan_caps:
            count += 1
            print(
                f"[{count:02d}/{total}] Optimize: Q >= {q_target:.0f} W, "
                f"fan <= {fan_cap:.0f} W ...",
                end=" "
            )
            try:
                row = run_epsilon_optimization(q_target, fan_cap, warm_start)
                all_results.append(row)
                if row["feasible"]:
                    warm_start = (
                        row["channel_height_cold_mm"],
                        row["length_mm"],
                        row["mdot_cold"],
                    )
                    print(
                        f"FEASIBLE | m_inst={row['installed_mass_kg']:.3f} kg | "
                        f"Pfan={row['fan_power_total_W']:.1f} W | "
                        f"Q={row['heat_transfer_W']:.1f} W | "
                        f"driver_success={row['driver_success']}"
                    )
                else:
                    print(
                        f"INFEASIBLE | Q={row['heat_transfer_W']:.1f} W | "
                        f"Pfan={row['fan_power_total_W']:.1f} W | "
                        f"DPc={row['dp_cold_Pa']:.1f} Pa | "
                        f"DPh={row['dp_hot_Pa']:.1f} Pa"
                    )
            except Exception as exc:
                print(f"FAILED | {type(exc).__name__}: {exc}")

    pareto = pareto_analysis_v4(all_results)
    if pareto:
        print_result(
            "V4 LOWEST-MASS PARETO SOLUTION",
            min(pareto, key=lambda r: r["installed_mass_kg"]),
            q_min=Q_MIN,
            dp_cold_max=DP_COLD_DESIGN_MAX,
            dp_hot_max=DP_HOT_DESIGN_MAX,
        )
        print_result(
            "V4 LOWEST-FAN-POWER PARETO SOLUTION",
            min(pareto, key=lambda r: r["fan_power_total_W"]),
            q_min=Q_MIN,
            dp_cold_max=DP_COLD_DESIGN_MAX,
            dp_hot_max=DP_HOT_DESIGN_MAX,
        )
    return all_results, pareto


# ============================================================
# 9. Main program
# ============================================================

def main():
    print("\n" + "=" * 70)
    print(" CAMS HEAT EXCHANGER PARAMETRIC DESIGN AND MULTI-OBJECTIVE OPTIMIZATION V4")
    print("=" * 70)
    print("\nV4 method: epsilon-constraint multi-objective optimization")
    print(f"Cold-side fan: eta_fan={FAN_EFFICIENCY_COLD:.2f}, eta_motor={MOTOR_EFFICIENCY_COLD:.2f}")
    print("Note: itemized duct/filter/grille/bend losses and installed-mass factors are preliminary assumptions.")

    baseline_analysis()
    parametric_sweep()
    optimization_analysis_v4()

    print("\n" + "=" * 70)
    print("V4 ANALYSIS COMPLETED")
    print("=" * 70)
    print("Generated files:")
    print("  1. cams_hx_sweep.csv")
    print("  2. cams_hx_epsilon_runs_v4.csv")
    print("  3. cams_hx_pareto_v4.csv")


if __name__ == "__main__":
    main()
