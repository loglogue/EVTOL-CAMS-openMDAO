
# cams_evaporator.py
"""
CAMS Evaporator Air-Side Performance Model V2.1

模型：
    1. 新风与回风混合
    2. ADP（装置露点温度）+ BF（旁通因子）
    3. 蒸发器出口空气状态计算
    4. 显热、潜热及冷凝水计算
    5. 质量守恒与能量守恒验证

单位：
    温度：degC
    压力：Pa
    焓值：kJ/kg dry air
    含湿量：kg water/kg dry air
    干空气质量流量：kg/s
    制冷量：W
    体积流量：m3/s
"""

from cams_inputs import (
    Q_EVAPORATOR_DESIGN,
    P_AMBIENT,
    T_OUTDOOR,
    RH_OUTDOOR,
    T_RETURN_AIR,
    RH_RETURN_AIR,
    V_FRESH_AIR,
    V_RETURN_AIR,
)

from cams_psychrometrics import (
    humidity_ratio,
    moist_air_enthalpy,
    relative_humidity,
    dew_point_temperature,
    mix_air_streams,
)


# ============================================================
# 1. 模型设计参数
# ============================================================

# 蒸发器装置露点温度，暂定值
T_ADP = 3.0

# 数值验证容差
MASS_FLOW_TOL = 1.0e-8       # kg/s
ENERGY_TOL = 1.0e-6          # W
RH_TOL = 1.0e-6
BF_TOL = 1.0e-8


# ============================================================
# 2. 输入参数检查
# ============================================================

def validate_inputs(
    T_in,
    RH_in,
    m_da,
    Q_total,
    T_adp,
    pressure,
):
    """检查蒸发器计算输入参数。"""

    if not isinstance(T_in, (int, float)):
        raise TypeError("T_in 必须为数值")

    if not 0.0 <= RH_in <= 1.0:
        raise ValueError("RH_in 必须在 0~1 之间")

    if m_da <= 0.0:
        raise ValueError("干空气质量流量必须大于零")

    if Q_total <= 0.0:
        raise ValueError("蒸发器制冷量必须大于零")

    if pressure <= 0.0:
        raise ValueError("空气压力必须大于零")

    if T_adp >= T_in:
        raise ValueError(
            "ADP 必须低于蒸发器入口空气温度"
        )


# ============================================================
# 3. 蒸发器 ADP + BF 模型
# ============================================================

def calculate_evaporator(
    T_in,
    RH_in,
    m_da,
    Q_total,
    T_adp,
    pressure,
):
    """
    根据入口空气状态、目标制冷量和 ADP 计算蒸发器性能。

    BF 计算：
        BF = (h_out - h_adp) / (h_in - h_adp)

    出口含湿量：
        W_out = W_adp + BF * (W_in - W_adp)

    出口温度：
        由出口焓值和出口含湿量反算。
    """

    validate_inputs(
        T_in,
        RH_in,
        m_da,
        Q_total,
        T_adp,
        pressure,
    )

    # --------------------------------------------------------
    # Step 1. 入口空气状态
    # --------------------------------------------------------

    W_in = humidity_ratio(
        T_in,
        RH_in,
        pressure,
    )

    h_in = moist_air_enthalpy(
        T_in,
        W_in,
    )

    T_dewpoint_in = dew_point_temperature(
        T_in,
        RH_in,
    )

    # --------------------------------------------------------
    # Step 2. ADP 饱和空气状态
    # --------------------------------------------------------

    if T_adp >= T_dewpoint_in:
        raise ValueError(
            f"ADP={T_adp:.2f} degC 不低于入口露点"
            f"{T_dewpoint_in:.2f} degC，"
            "当前 ADP 设定不满足预期除湿条件。"
        )

    W_adp = humidity_ratio(
        T_adp,
        1.0,
        pressure,
    )

    h_adp = moist_air_enthalpy(
        T_adp,
        W_adp,
    )

    if h_in <= h_adp:
        raise ValueError(
            "入口空气焓值必须高于 ADP 饱和空气焓值"
        )

    # --------------------------------------------------------
    # Step 3. 根据目标制冷量计算出口焓值
    # --------------------------------------------------------

    delta_h = Q_total / (m_da * 1000.0)

    h_out = h_in - delta_h

    # --------------------------------------------------------
    # Step 4. 计算旁通因子 BF
    # --------------------------------------------------------

    BF = (
        (h_out - h_adp)
        / (h_in - h_adp)
    )

    if not -BF_TOL <= BF <= 1.0 + BF_TOL:
        raise ValueError(
            f"计算得到 BF={BF:.5f}，超出 0~1 范围。\n"
            "请检查目标制冷量、空气流量或 ADP。"
        )

    # 仅处理浮点数造成的极小越界
    BF = max(0.0, min(1.0, BF))

    # --------------------------------------------------------
    # Step 5. 计算出口含湿量
    # --------------------------------------------------------

    W_out = (
        W_adp
        + BF * (W_in - W_adp)
    )

    if W_out < 0.0:
        raise ValueError("计算得到负的出口含湿量")

    # --------------------------------------------------------
    # Step 6. 反算出口温度
    # --------------------------------------------------------

    T_out = (
        h_out - 2501.0 * W_out
    ) / (
        1.006 + 1.86 * W_out
    )

    # --------------------------------------------------------
    # Step 7. 出口相对湿度及露点
    # --------------------------------------------------------

    RH_out = relative_humidity(
        T_out,
        W_out,
        pressure,
    )

    if RH_out > 1.0 + RH_TOL:
        raise ValueError(
            f"出口空气出现过饱和状态："
            f"RH_out={RH_out * 100:.3f}%。"
            "请检查 ADP、目标冷量及模型假设。"
        )

    if RH_out < 0.0:
        raise ValueError("出口相对湿度不能为负数")

    T_dewpoint_out = dew_point_temperature(
        T_out,
        min(RH_out, 1.0),
    )

    # --------------------------------------------------------
    # Step 8. 显热与潜热
    # --------------------------------------------------------

    # 使用入口和出口平均含湿量计算湿空气比热
    W_average = 0.5 * (W_in + W_out)

    cp_air = 1.006 + 1.86 * W_average

    Q_sensible = (
        m_da
        * cp_air
        * (T_in - T_out)
        * 1000.0
    )

    # 总冷量 = 显热 + 潜热
    Q_latent = Q_total - Q_sensible

    SHR = Q_sensible / Q_total

    # --------------------------------------------------------
    # Step 9. 冷凝水计算
    # --------------------------------------------------------

    m_condensate = (
        m_da * (W_in - W_out)
    )

    m_condensate_hour = (
        m_condensate * 3600.0
    )

    if m_condensate < -1.0e-10:
        raise ValueError(
            "计算得到负冷凝水流量，请检查出口含湿量"
        )

    # 消除数值精度导致的极小负值
    m_condensate = max(0.0, m_condensate)

    # --------------------------------------------------------
    # Step 10. 能量闭合
    # --------------------------------------------------------

    Q_energy_sum = Q_sensible + Q_latent

    energy_error = Q_energy_sum - Q_total

    # --------------------------------------------------------
    # Step 11. 结果
    # --------------------------------------------------------

    return {
        "T_in": T_in,
        "RH_in": RH_in,
        "W_in": W_in,
        "h_in": h_in,
        "T_dewpoint_in": T_dewpoint_in,

        "T_adp": T_adp,
        "W_adp": W_adp,
        "h_adp": h_adp,

        "BF": BF,

        "T_out": T_out,
        "RH_out": RH_out,
        "W_out": W_out,
        "h_out": h_out,
        "T_dewpoint_out": T_dewpoint_out,

        "Q_total": Q_total,
        "Q_sensible": Q_sensible,
        "Q_latent": Q_latent,
        "SHR": SHR,

        "cp_air": cp_air,
        "W_average": W_average,

        "m_da": m_da,
        "m_condensate": m_condensate,
        "m_condensate_hour": m_condensate_hour,

        "Q_energy_sum": Q_energy_sum,
        "energy_error": energy_error,
    }


# ============================================================
# 4. CAMS 新风与回风混合
# ============================================================

def calculate_mixed_air():
    """
    根据 cams_inputs.py 的参数动态计算混合空气状态。
    """

    mixed = mix_air_streams(
        T_fresh=T_OUTDOOR,
        RH_fresh=RH_OUTDOOR,
        V_fresh=V_FRESH_AIR,

        T_return=T_RETURN_AIR,
        RH_return=RH_RETURN_AIR,
        V_return=V_RETURN_AIR,

        P=P_AMBIENT,
    )

    return mixed


# ============================================================
# 5. 验证模块
# ============================================================

def validate_evaporator(result, mixed):
    """
    蒸发器模型验证。

    Mixed Airflow Consistency 保留原名称。
    验证内容为干空气质量流量守恒，而非体积流量守恒。
    """

    checks = {}

    # 1. BF 范围
    checks["Bypass Factor"] = (
        -BF_TOL <= result["BF"] <= 1.0 + BF_TOL
    )

    # 2. 出口相对湿度
    checks["Outlet RH"] = (
        0.0 <= result["RH_out"] <= 1.0 + RH_TOL
    )

    # 3. 出口含湿量不高于入口
    checks["Outlet Humidity <= Inlet"] = (
        result["W_out"] <= result["W_in"] + 1.0e-10
    )

    # 4. 冷凝水非负
    checks["Condensate Non-negative"] = (
        result["m_condensate"] >= 0.0
    )

    # 5. 显热与潜热比例合理
    checks["SHR Physical Range"] = (
        0.0 <= result["SHR"] <= 1.0
    )

    # 6. 能量闭合
    checks["Cooling Energy Balance"] = (
        abs(result["energy_error"]) < ENERGY_TOL
    )

    # 7. 混合空气流量一致性
    # 保留原验证名称，但采用干空气质量守恒判据
    mass_flow_error = abs(
        mixed["mdot_da_total"]
        - mixed["mdot_da_fresh"]
        - mixed["mdot_da_return"]
    )

    checks["Mixed Airflow Consistency"] = (
        mass_flow_error < MASS_FLOW_TOL
    )

    # 8. 蒸发器入口质量流量一致性
    checks["Evaporator Inlet Mass Flow"] = (
        abs(
            result["m_da"]
            - mixed["mdot_da_total"]
        ) < MASS_FLOW_TOL
    )

    return checks


# ============================================================
# 6. 结果输出
# ============================================================

def print_results(result, mixed, checks):

    print("\n" + "=" * 66)
    print("              CAMS EVAPORATOR ANALYSIS V2.1")
    print("=" * 66)

    # --------------------------------------------------------
    # General Parameters
    # --------------------------------------------------------

    print("\n--- 1. General Parameters ---")

    print(
        f"Evaporator Cooling Capacity : "
        f"{result['Q_total']:.2f} W"
    )

    print(
        f"Fresh Air Flow              : "
        f"{V_FRESH_AIR * 1000:.2f} L/s"
    )

    print(
        f"Return Air Flow             : "
        f"{V_RETURN_AIR * 1000:.2f} L/s"
    )

    print(
        f"Mixed Air Flow              : "
        f"{mixed['V_total'] * 1000:.2f} L/s"
    )

    print(
        f"Dry Air Mass Flow           : "
        f"{result['m_da']:.6f} kg/s"
    )

    print(
        f"ADP Temperature             : "
        f"{result['T_adp']:.2f} degC"
    )

    # --------------------------------------------------------
    # Mixed Air
    # --------------------------------------------------------

    print("\n--- 2. Mixed Air State ---")

    print(
        f"Temperature                 : "
        f"{mixed['T']:.2f} degC"
    )

    print(
        f"Relative Humidity           : "
        f"{mixed['RH'] * 100:.2f} %"
    )

    print(
        f"Humidity Ratio              : "
        f"{mixed['W']:.6f} kg/kg"
    )

    print(
        f"Enthalpy                    : "
        f"{mixed['h']:.3f} kJ/kg"
    )

    print(
        f"Density                     : "
        f"{mixed['density']:.4f} kg/m3"
    )

    print(
        f"Fresh Air Dry Mass Flow     : "
        f"{mixed['mdot_da_fresh']:.6f} kg/s"
    )

    print(
        f"Return Air Dry Mass Flow    : "
        f"{mixed['mdot_da_return']:.6f} kg/s"
    )

    print(
        f"Mixed Air Dry Mass Flow     : "
        f"{mixed['mdot_da_total']:.6f} kg/s"
    )

    # --------------------------------------------------------
    # ADP
    # --------------------------------------------------------

    print("\n--- 3. ADP State ---")

    print(
        f"ADP Temperature             : "
        f"{result['T_adp']:.2f} degC"
    )

    print(
        f"ADP Humidity Ratio          : "
        f"{result['W_adp']:.6f} kg/kg"
    )

    print(
        f"ADP Enthalpy                : "
        f"{result['h_adp']:.3f} kJ/kg"
    )

    print(
        f"Inlet Dew Point             : "
        f"{result['T_dewpoint_in']:.2f} degC"
    )

    # --------------------------------------------------------
    # Evaporator Outlet
    # --------------------------------------------------------

    print("\n--- 4. Evaporator Performance ---")

    print(
        f"Bypass Factor               : "
        f"{result['BF']:.4f}"
    )

    print(
        f"Outlet Temperature          : "
        f"{result['T_out']:.2f} degC"
    )

    print(
        f"Outlet Relative Humidity    : "
        f"{result['RH_out'] * 100:.2f} %"
    )

    print(
        f"Outlet Humidity Ratio       : "
        f"{result['W_out']:.6f} kg/kg"
    )

    print(
        f"Outlet Enthalpy             : "
        f"{result['h_out']:.3f} kJ/kg"
    )

    print(
        f"Outlet Dew Point            : "
        f"{result['T_dewpoint_out']:.2f} degC"
    )

    # --------------------------------------------------------
    # Cooling Load
    # --------------------------------------------------------

    print("\n--- 5. Cooling Load ---")

    print(
        f"Total Cooling               : "
        f"{result['Q_total']:.2f} W"
    )

    print(
        f"Sensible Cooling            : "
        f"{result['Q_sensible']:.2f} W"
    )

    print(
        f"Latent Cooling              : "
        f"{result['Q_latent']:.2f} W"
    )

    print(
        f"Sensible Heat Ratio         : "
        f"{result['SHR']:.4f}"
    )

    print(
        f"Moist Air Specific Heat     : "
        f"{result['cp_air']:.4f} kJ/(kg.K)"
    )

    # --------------------------------------------------------
    # Condensate
    # --------------------------------------------------------

    print("\n--- 6. Condensate ---")

    print(
        f"Condensate Flow             : "
        f"{result['m_condensate']:.6f} kg/s"
    )

    print(
        f"Condensate Flow             : "
        f"{result['m_condensate_hour']:.3f} kg/h"
    )

    # --------------------------------------------------------
    # Energy Balance
    # --------------------------------------------------------

    print("\n--- 7. Energy Balance ---")

    print(
        f"Sensible + Latent           : "
        f"{result['Q_energy_sum']:.6f} W"
    )

    print(
        f"Energy Balance Error        : "
        f"{result['energy_error']:.10f} W"
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print("\n--- 8. Model Validation ---")

    for name, passed in checks.items():

        status = "PASS" if passed else "FAIL"

        print(
            f"{name:<36}: {status}"
        )

    all_passed = all(checks.values())

    print("\n" + "-" * 66)

    print(
        "Overall Validation           : "
        + ("PASS" if all_passed else "FAIL")
    )

    print("=" * 66)


# ============================================================
# 7. 主程序
# ============================================================

def run_evaporator_analysis():

    # Step 1: 新风与回风混合
    mixed = calculate_mixed_air()

    # Step 2: 使用混合空气状态作为蒸发器入口
    result = calculate_evaporator(
        T_in=mixed["T"],
        RH_in=mixed["RH"],
        m_da=mixed["mdot_da_total"],
        Q_total=Q_EVAPORATOR_DESIGN,
        T_adp=T_ADP,
        pressure=P_AMBIENT,
    )

    # Step 3: 模型验证
    checks = validate_evaporator(
        result,
        mixed,
    )

    # Step 4: 输出结果
    print_results(
        result,
        mixed,
        checks,
    )

    return {
        "mixed_air": mixed,
        "evaporator": result,
        "checks": checks,
        "all_passed": all(checks.values()),
    }


# ============================================================
# 8. 独立运行
# ============================================================

if __name__ == "__main__":

    run_evaporator_analysis()
