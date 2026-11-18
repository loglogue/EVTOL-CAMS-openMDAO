
# cams_condenser_pressure.py
"""
CAMS 冷凝器冲压空气压力平衡分析

分析内容：
1. 计算冷凝器所需空气体积流量
2. 计算飞行自由来流动压
3. 估算冲压空气可用压差
4. 计算进气口、风道、冷凝器芯体和出口压力损失
5. 根据压力平衡估算系统实际空气流量
6. 判断冲压空气是否满足冷凝器需求

注意：
各部件参考压降为暂定示例值，不是实测数据。
正式设计时应替换为供应商数据、CFD结果或试验数据。
"""

import math

from cams_inputs import (
    Q_CONDENSER,
    T_OUTDOOR,
    RH_OUTDOOR,
    P_AMBIENT,
    V_FLIGHT,
    DELTA_T_CONDENSER_AIR,
)

from cams_psychrometrics import (
    humidity_ratio,
    moist_air_density,
)


# ============================================================
# 1. 暂定压力系统参数
# ============================================================

# 压力恢复系数：暂定示例值，不能直接等同空气捕获效率
RAM_PRESSURE_RECOVERY = 0.70

# 以下压力损失均定义在设计参考流量下
# 暂定示例值，正式设计需替换
DELTA_P_INLET_REF = 20.0       # 进气口压损，Pa
DELTA_P_DUCT_REF = 30.0        # 风道压损，Pa
DELTA_P_CORE_REF = 100.0       # 冷凝器芯体压降，Pa
DELTA_P_OUTLET_REF = 20.0      # 出口压损，Pa


# ============================================================
# 2. 计算冷凝器设计空气流量
# ============================================================

def calculate_required_airflow():

    w = humidity_ratio(
        T_OUTDOOR,
        RH_OUTDOOR,
        P_AMBIENT
    )

    rho = moist_air_density(
        T_OUTDOOR,
        w,
        P_AMBIENT
    )

    # 湿空气定压比热近似，单位：kJ/(kg*K)
    cp = 1.006 + 1.86 * w

    # 根据冷凝器热负荷反算干空气质量流量
    m_dry = Q_CONDENSER / (
        cp * 1000.0 * DELTA_T_CONDENSER_AIR
    )

    # 湿空气总质量流量
    m_moist = m_dry * (1.0 + w)

    # 湿空气体积流量
    v_air = m_moist / rho

    return {
        "humidity_ratio": w,
        "density": rho,
        "cp": cp,
        "dry_mass_flow": m_dry,
        "moist_mass_flow": m_moist,
        "volume_flow": v_air,
    }


# ============================================================
# 3. 计算冲压空气可用压差
# ============================================================

def calculate_available_pressure():

    rho = moist_air_density(
        T_OUTDOOR,
        humidity_ratio(
            T_OUTDOOR,
            RH_OUTDOOR,
            P_AMBIENT
        ),
        P_AMBIENT
    )

    # 自由来流动压
    q_dynamic = 0.5 * rho * V_FLIGHT ** 2

    # 进气系统可利用的压力恢复
    delta_p_available = (
        RAM_PRESSURE_RECOVERY * q_dynamic
    )

    return q_dynamic, delta_p_available


# ============================================================
# 4. 计算各部件压降
# ============================================================

def calculate_pressure_losses(
    actual_flow,
    reference_flow
):

    # 假设各部件压降与流量平方成正比
    flow_ratio_squared = (
        actual_flow / reference_flow
    ) ** 2

    dp_inlet = (
        DELTA_P_INLET_REF * flow_ratio_squared
    )

    dp_duct = (
        DELTA_P_DUCT_REF * flow_ratio_squared
    )

    dp_core = (
        DELTA_P_CORE_REF * flow_ratio_squared
    )

    dp_outlet = (
        DELTA_P_OUTLET_REF * flow_ratio_squared
    )

    dp_total = (
        dp_inlet
        + dp_duct
        + dp_core
        + dp_outlet
    )

    return {
        "inlet": dp_inlet,
        "duct": dp_duct,
        "core": dp_core,
        "outlet": dp_outlet,
        "total": dp_total,
    }


# ============================================================
# 5. 根据压力平衡估算实际流量
# ============================================================

def calculate_actual_airflow(
    available_pressure,
    reference_flow
):

    # 设计参考流量下的总压降
    dp_reference = (
        DELTA_P_INLET_REF
        + DELTA_P_DUCT_REF
        + DELTA_P_CORE_REF
        + DELTA_P_OUTLET_REF
    )

    if available_pressure <= 0.0:
        return 0.0

    if dp_reference <= 0.0:
        raise ValueError("参考总压降必须大于0")

    # 压力平衡：
    # available_pressure = dp_reference * (V/Vref)^2
    actual_flow = reference_flow * math.sqrt(
        available_pressure / dp_reference
    )

    return actual_flow


# ============================================================
# 6. 主程序
# ============================================================

def main():

    print("\n========== CAMS Condenser Pressure Analysis ==========")

    # 设计所需空气流量
    airflow = calculate_required_airflow()

    v_required = airflow["volume_flow"]

    print("\n--- Required Condenser Airflow ---")

    print(
        f"Condenser Heat Load  : {Q_CONDENSER:.2f} W"
    )

    print(
        f"Air Temperature Rise: {DELTA_T_CONDENSER_AIR:.2f} K"
    )

    print(
        f"Air Density         : {airflow['density']:.4f} kg/m3"
    )

    print(
        f"Dry Air Mass Flow   : {airflow['dry_mass_flow']:.4f} kg/s"
    )

    print(
        f"Moist Air Mass Flow : {airflow['moist_mass_flow']:.4f} kg/s"
    )

    print(
        f"Required Airflow    : {v_required:.4f} m3/s"
    )

    print(
        f"Required Airflow    : {v_required * 3600:.2f} m3/h"
    )

    # 冲压空气可用压差
    q_dynamic, dp_available = calculate_available_pressure()

    print("\n--- Ram Air Pressure ---")

    print(
        f"Flight Speed          : {V_FLIGHT:.2f} m/s"
    )

    print(
        f"Free Stream Dynamic P : {q_dynamic:.2f} Pa"
    )

    print(
        f"Pressure Recovery     : {RAM_PRESSURE_RECOVERY:.2f}"
    )

    print(
        f"Available Pressure    : {dp_available:.2f} Pa"
    )

    # 设计流量下的系统压力损失
    losses = calculate_pressure_losses(
        v_required,
        v_required
    )

    print("\n--- Pressure Loss at Required Airflow ---")

    print(
        f"Inlet Pressure Loss  : {losses['inlet']:.2f} Pa"
    )

    print(
        f"Duct Pressure Loss   : {losses['duct']:.2f} Pa"
    )

    print(
        f"Core Pressure Loss   : {losses['core']:.2f} Pa"
    )

    print(
        f"Outlet Pressure Loss : {losses['outlet']:.2f} Pa"
    )

    print(
        f"Total Pressure Loss  : {losses['total']:.2f} Pa"
    )

    # 压差裕度
    pressure_margin = dp_available - losses["total"]

    print("\n--- Pressure Balance ---")

    print(
        f"Available Pressure : {dp_available:.2f} Pa"
    )

    print(
        f"Required Pressure  : {losses['total']:.2f} Pa"
    )

    print(
        f"Pressure Margin    : {pressure_margin:.2f} Pa"
    )

    # 实际流量估算
    v_actual = calculate_actual_airflow(
        dp_available,
        v_required
    )

    actual_losses = calculate_pressure_losses(
        v_actual,
        v_required
    )

    print("\n--- Estimated Actual Airflow ---")

    print(
        f"Estimated Airflow : {v_actual:.4f} m3/s"
    )

    print(
        f"Estimated Airflow : {v_actual * 3600:.2f} m3/h"
    )

    print(
        f"Required Airflow  : {v_required * 3600:.2f} m3/h"
    )

    print(
        f"Flow Ratio        : {v_actual / v_required * 100:.2f} %"
    )

    print(
        f"Pressure Loss     : {actual_losses['total']:.2f} Pa"
    )

    # 结果判断
    print("\n--- Preliminary Assessment ---")

    if pressure_margin >= 0:
        print("Pressure Check : PASS")
    else:
        print("Pressure Check : FAIL")

    if v_actual >= v_required:
        print("Airflow Check   : PASS")
        print("Conclusion      : Ram air may satisfy the airflow requirement.")
    else:
        print("Airflow Check   : FAIL")
        print("Conclusion      : Ram air cannot satisfy the airflow requirement.")

    print("\n=======================================================")


if __name__ == "__main__":
    main()
