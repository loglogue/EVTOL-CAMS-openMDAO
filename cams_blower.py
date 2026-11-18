
"""
CAMS Blower Model V4
========================================================
eVTOL Cabin Air Management System

Airflow architecture:
    Fresh air + Recirculated air
              |
         Mixing section
              |
          Air filter
              |
        Blower (24 VDC)
              |
          Evaporator
              |
          APTC heater
              |
       Common supply duct
              |
       Parallel distribution
          /     |     \
       Row 1  Row 2  Row 3
        duct   duct   duct
          |     |     |
       Outlets Outlets Outlets

Features:
1. Common airflow path pressure loss
2. Three independent parallel cabin duct branches
3. Automatic airflow distribution
4. Blower electrical power and DC current
5. Efficiency sensitivity analysis
6. Power-to-pressure reverse calculation

All pressure losses are preliminary assumptions.
Replace them with actual component data and test results.
"""

import math


# ============================================================
# 1. GENERAL CAMS PARAMETERS
# ============================================================

OCCUPANT_NUMBER = 6

TOTAL_AIRFLOW_LS = 150.0
FRESH_AIR_RATIO = 0.20
RECIRCULATION_RATIO = 0.80

AIR_DENSITY = 1.1335       # kg/m3
AIR_SPECIFIC_HEAT = 1005.0 # J/(kg.K)

BLOWER_VOLTAGE = 24.0      # VDC
BLOWER_EFFICIENCY = 0.55   # Assumed overall efficiency

TOTAL_AIRFLOW = TOTAL_AIRFLOW_LS / 1000.0


# ============================================================
# 2. COMMON AIRFLOW PATH
# ============================================================
# All components in this section carry the total airflow.
#
# Pressure loss model:
# dp = dp_ref * (Q / Q_ref)^2
#
# q_ref: m3/s
# dp_ref: Pa

COMMON_COMPONENTS = [

    {
        "name": "Mixing section and inlet",
        "q_ref": 0.150,
        "dp_ref": 30.0,
    },

    {
        "name": "Air filter",
        "q_ref": 0.150,
        "dp_ref": 80.0,
    },

    {
        "name": "Evaporator core",
        "q_ref": 0.150,
        "dp_ref": 150.0,
    },

    {
        "name": "APTC heater",
        "q_ref": 0.150,
        "dp_ref": 150.0,
    },

    {
        "name": "Common supply duct",
        "q_ref": 0.150,
        "dp_ref": 250.0,
    },
]


# ============================================================
# 3. THREE INDEPENDENT CABIN DUCT BRANCHES
# ============================================================
#
# Each row is an independent parallel branch.
#
# Initial design airflow:
# Row 1 = 50 L/s
# Row 2 = 50 L/s
# Row 3 = 50 L/s
#
# Each branch has:
# 1. Duct pressure loss
# 2. Elbow and local pressure loss
# 3. Cabin outlet pressure loss
#
# Change the values independently when actual data is available.

CABIN_BRANCHES = {

    "Row_1": {

        "components": [

            {
                "name": "Row 1 duct",
                "q_ref": 0.050,
                "dp_ref": 150.0,
            },

            {
                "name": "Row 1 elbows and local losses",
                "q_ref": 0.050,
                "dp_ref": 100.0,
            },

            {
                "name": "Row 1 cabin outlets",
                "q_ref": 0.050,
                "dp_ref": 100.0,
            },
        ],
    },

    "Row_2": {

        "components": [

            {
                "name": "Row 2 duct",
                "q_ref": 0.050,
                "dp_ref": 150.0,
            },

            {
                "name": "Row 2 elbows and local losses",
                "q_ref": 0.050,
                "dp_ref": 100.0,
            },

            {
                "name": "Row 2 cabin outlets",
                "q_ref": 0.050,
                "dp_ref": 100.0,
            },
        ],
    },

    "Row_3": {

        "components": [

            {
                "name": "Row 3 duct",
                "q_ref": 0.050,
                "dp_ref": 150.0,
            },

            {
                "name": "Row 3 elbows and local losses",
                "q_ref": 0.050,
                "dp_ref": 100.0,
            },

            {
                "name": "Row 3 cabin outlets",
                "q_ref": 0.050,
                "dp_ref": 100.0,
            },
        ],
    },
}


# ============================================================
# 4. PRESSURE LOSS CALCULATION
# ============================================================

def calculate_component_dp(component, airflow):
    """
    Calculate pressure loss of one component.

    Quadratic resistance model:
        dp = dp_ref * (Q / Q_ref)^2

    Parameters
    ----------
    component : dict
    airflow : float
        Actual airflow, m3/s

    Returns
    -------
    float
        Pressure loss, Pa
    """

    q_ref = component["q_ref"]
    dp_ref = component["dp_ref"]

    if q_ref <= 0.0:
        raise ValueError(
            "Reference airflow must be greater than zero."
        )

    if airflow < 0.0:
        raise ValueError(
            "Airflow cannot be negative."
        )

    return dp_ref * (airflow / q_ref) ** 2


def calculate_component_group(components, airflow):
    """
    Calculate pressure losses of series components.
    """

    results = []

    for component in components:

        dp = calculate_component_dp(
            component,
            airflow
        )

        results.append({
            "name": component["name"],
            "dp": dp,
        })

    total_dp = sum(
        item["dp"] for item in results
    )

    return total_dp, results


def calculate_common_path(airflow):
    """
    Calculate common path pressure loss.

    All common components carry the total airflow.
    """

    return calculate_component_group(
        COMMON_COMPONENTS,
        airflow
    )


# ============================================================
# 5. PARALLEL BRANCH RESISTANCE
# ============================================================

def calculate_branch_k(components):
    """
    Calculate equivalent resistance coefficient.

    For each component:

        dp = K * Q^2

    For series components:

        K_total = sum(K_i)

    Therefore:

        K_i = dp_ref / q_ref^2
    """

    total_k = 0.0

    for component in components:

        q_ref = component["q_ref"]
        dp_ref = component["dp_ref"]

        if q_ref <= 0.0:
            raise ValueError(
                "Branch reference airflow must be positive."
            )

        if dp_ref < 0.0:
            raise ValueError(
                "Pressure loss cannot be negative."
            )

        total_k += dp_ref / (q_ref ** 2)

    if total_k <= 0.0:
        raise ValueError(
            "Branch resistance must be positive."
        )

    return total_k


# ============================================================
# 6. SOLVE THREE PARALLEL BRANCHES
# ============================================================

def calculate_parallel_branches(total_airflow):
    """
    Solve airflow distribution among parallel branches.

    Conditions:

        Q_total = Q1 + Q2 + Q3

        dp1 = dp2 = dp3

    Each branch:

        dp = K_i * Q_i^2

    Therefore:

        Q_i = sqrt(dp / K_i)

    A bisection method is used to solve the common
    branch pressure difference.
    """

    if not CABIN_BRANCHES:
        raise ValueError(
            "At least one cabin branch is required."
        )

    branch_data = []

    for name, branch in CABIN_BRANCHES.items():

        k = calculate_branch_k(
            branch["components"]
        )

        branch_data.append({
            "name": name,
            "k": k,
            "components": branch["components"],
        })

    def calculate_total_flow(dp):

        flow_sum = 0.0

        for branch in branch_data:

            flow = math.sqrt(
                dp / branch["k"]
            )

            flow_sum += flow

        return flow_sum

    # Establish upper pressure bound
    low = 0.0
    high = 1.0

    while calculate_total_flow(high) < total_airflow:
        high *= 2.0

    # Bisection
    for _ in range(150):

        mid = 0.5 * (low + high)

        flow = calculate_total_flow(mid)

        if flow < total_airflow:
            low = mid
        else:
            high = mid

    branch_pressure = 0.5 * (low + high)

    results = []

    for branch in branch_data:

        branch_flow = math.sqrt(
            branch_pressure / branch["k"]
        )

        component_dp, component_results = (
            calculate_component_group(
                branch["components"],
                branch_flow
            )
        )

        results.append({

            "name": branch["name"],

            "airflow": branch_flow,

            "airflow_ls": branch_flow * 1000.0,

            "pressure_loss": component_dp,

            "components": component_results,
        })

    return branch_pressure, results


# ============================================================
# 7. BLOWER POWER
# ============================================================

def calculate_blower_power(
    airflow,
    pressure_loss,
    efficiency,
    voltage
):
    """
    Calculate blower power.

    Air power:
        P_air = Q * dp

    Electrical power:
        P_electric = P_air / efficiency

    DC current:
        I = P_electric / voltage

    Assumption:
        efficiency is the overall efficiency from
        electrical input to useful air power.
    """

    if not (0.0 < efficiency <= 1.0):
        raise ValueError(
            "Efficiency must be between 0 and 1."
        )

    if voltage <= 0.0:
        raise ValueError(
            "Voltage must be positive."
        )

    air_power = airflow * pressure_loss

    electrical_power = air_power / efficiency

    current = electrical_power / voltage

    return air_power, electrical_power, current


# ============================================================
# 8. REVERSE PRESSURE CALCULATION
# ============================================================

def calculate_required_pressure(
    airflow,
    electrical_power,
    efficiency
):
    """
    Calculate pressure corresponding to a given
    electrical power at a specified airflow.

    dp = P_electric * efficiency / Q
    """

    if airflow <= 0.0:
        raise ValueError("Airflow must be positive.")

    if electrical_power < 0.0:
        raise ValueError("Power cannot be negative.")

    if not (0.0 < efficiency <= 1.0):
        raise ValueError("Invalid efficiency.")

    return electrical_power * efficiency / airflow


# ============================================================
# 9. MAIN ANALYSIS
# ============================================================

def main():

    # --------------------------------------------------------
    # Airflow distribution
    # --------------------------------------------------------

    fresh_airflow = (
        TOTAL_AIRFLOW * FRESH_AIR_RATIO
    )

    recirculation_airflow = (
        TOTAL_AIRFLOW * RECIRCULATION_RATIO
    )

    mass_flow = AIR_DENSITY * TOTAL_AIRFLOW

    # --------------------------------------------------------
    # Common path
    # --------------------------------------------------------

    common_dp, common_results = calculate_common_path(
        TOTAL_AIRFLOW
    )

    # --------------------------------------------------------
    # Parallel branches
    # --------------------------------------------------------

    branch_dp, branch_results = calculate_parallel_branches(
        TOTAL_AIRFLOW
    )

    # --------------------------------------------------------
    # Total system pressure
    # --------------------------------------------------------
    #
    # Common pressure loss + common branch pressure loss
    #
    # Do NOT sum parallel branch pressure losses.
    # --------------------------------------------------------

    total_system_dp = common_dp + branch_dp

    # --------------------------------------------------------
    # Blower power
    # --------------------------------------------------------

    air_power, electrical_power, current = (
        calculate_blower_power(
            TOTAL_AIRFLOW,
            total_system_dp,
            BLOWER_EFFICIENCY,
            BLOWER_VOLTAGE
        )
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print("\n")
    print("=" * 66)
    print("                CAMS BLOWER ANALYSIS V4")
    print("=" * 66)

    print("\n--- 1. General Parameters ---")

    print(
        f"Occupant Number       : "
        f"{OCCUPANT_NUMBER} persons"
    )

    print(
        f"Total Airflow         : "
        f"{TOTAL_AIRFLOW * 1000:.2f} L/s"
    )

    print(
        f"Fresh Airflow         : "
        f"{fresh_airflow * 1000:.2f} L/s"
    )

    print(
        f"Recirculation Airflow : "
        f"{recirculation_airflow * 1000:.2f} L/s"
    )

    print(
        f"Air Mass Flow         : "
        f"{mass_flow:.4f} kg/s"
    )

    print("\n--- 2. Common Path Pressure Loss ---")

    for item in common_results:

        print(
            f"{item['name']:<36}: "
            f"{item['dp']:8.2f} Pa"
        )

    print("-" * 52)

    print(
        f"{'Common Path Total':<36}: "
        f"{common_dp:8.2f} Pa"
    )

    print("\n--- 3. Three Parallel Cabin Branches ---")

    for branch in branch_results:

        print(f"\n{branch['name']}")

        print(
            f"  Airflow             : "
            f"{branch['airflow_ls']:.2f} L/s"
        )

        for item in branch["components"]:

            print(
                f"  {item['name']:<34}: "
                f"{item['dp']:8.2f} Pa"
            )

        print(
            f"  Branch Total        : "
            f"{branch['pressure_loss']:.2f} Pa"
        )

    total_branch_flow = sum(
        branch["airflow"]
        for branch in branch_results
    )

    print("\n--- 4. System Pressure Loss ---")

    print(
        f"Common Path           : "
        f"{common_dp:.2f} Pa"
    )

    print(
        f"Parallel Branch       : "
        f"{branch_dp:.2f} Pa"
    )

    print("-" * 52)

    print(
        f"Total System Pressure : "
        f"{total_system_dp:.2f} Pa"
    )

    print(
        f"Total Branch Flow     : "
        f"{total_branch_flow * 1000:.2f} L/s"
    )

    print("\n--- 5. Blower Power ---")

    print(
        f"Supply Voltage        : "
        f"{BLOWER_VOLTAGE:.2f} VDC"
    )

    print(
        f"Blower Efficiency     : "
        f"{BLOWER_EFFICIENCY * 100:.1f} %"
    )

    print(
        f"Air Power             : "
        f"{air_power:.2f} W"
    )

    print(
        f"Electrical Power      : "
        f"{electrical_power:.2f} W"
    )

    print(
        f"DC Current            : "
        f"{current:.2f} A"
    )

    # --------------------------------------------------------
    # Efficiency sensitivity
    # --------------------------------------------------------

    print("\n--- 6. Efficiency Sensitivity ---")

    for efficiency in [
        0.40,
        0.45,
        0.50,
        0.55,
        0.60
    ]:

        _, power, amps = calculate_blower_power(
            TOTAL_AIRFLOW,
            total_system_dp,
            efficiency,
            BLOWER_VOLTAGE
        )

        print(
            f"Efficiency {efficiency * 100:5.1f}%"
            f" | Power {power:8.2f} W"
            f" | Current {amps:6.2f} A"
        )

    # --------------------------------------------------------
    # Reverse pressure calculation
    # --------------------------------------------------------

    print("\n--- 7. Power Range Reverse Calculation ---")

    for target_power in [
        300.0,
        350.0,
        400.0
    ]:

        required_dp = calculate_required_pressure(
            TOTAL_AIRFLOW,
            target_power,
            BLOWER_EFFICIENCY
        )

        print(
            f"Power {target_power:6.1f} W"
            f" | Required Pressure {required_dp:8.2f} Pa"
        )

    # --------------------------------------------------------
    # Engineering notes
    # --------------------------------------------------------

    print("\n--- 8. Engineering Notes ---")

    print("1. Three cabin rows are modeled as parallel branches.")

    print("2. Branch pressure losses are not added together.")

    print("3. Branch airflow is calculated automatically.")

    print("4. Evaporator and APTC pressure losses are included.")

    print("5. Filter pressure loss is included.")

    print("6. Pressure losses are preliminary assumptions.")

    print("7. Actual blower selection requires a fan performance curve.")

    print("8. Overall efficiency must match the selected fan data.")

    print("\n" + "=" * 66)
    print("                  ANALYSIS COMPLETE")
    print("=" * 66)


if __name__ == "__main__":
    main()
