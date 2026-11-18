# cams_psychrometrics.py
"""
CAMS 湿空气计算模块

提供：
1. 饱和水蒸气压力
2. 含湿量
3. 湿空气焓值
4. 相对湿度
5. 露点温度
6. 湿空气密度
7. 新风与回风混合计算

焓值单位：kJ/kg干空气
含湿量单位：kg水/kg干空气
压力单位：Pa
温度单位：degC
"""

import math


# =========================
# 常数
# =========================

R_DA = 287.055       # 干空气气体常数，J/(kg·K)
R_V = 461.52         # 水蒸气气体常数，J/(kg·K)
EPSILON = 0.621945


# =========================
# 1. 饱和水蒸气压力
# =========================

def saturation_pressure(T):
    """
    根据干球温度计算饱和水蒸气压力。

    参数
    ----
    T : float
        温度，degC

    返回
    ----
    float
        饱和水蒸气压力，Pa

    说明
    ----
    使用 Buck 公式。
    本模型主要用于常见空调空气温度范围。
    """

    # 水面上的饱和水蒸气压力，单位 kPa
    p_ws = 0.61121 * math.exp(
        (18.678 - T / 234.5) * (T / (257.14 + T))
    )

    return p_ws * 1000.0


# =========================
# 2. 含湿量
# =========================

def humidity_ratio(T, RH, P=101325.0):
    """
    根据温度、相对湿度和总压力计算含湿量。

    参数
    ----
    T : float
        干球温度，degC

    RH : float
        相对湿度，0~1

    P : float
        总压力，Pa

    返回
    ----
    float
        含湿量，kg水/kg干空气
    """

    if not 0.0 <= RH <= 1.0:
        raise ValueError("RH 必须在 0~1 之间")

    p_ws = saturation_pressure(T)
    p_v = RH * p_ws

    if p_v >= P:
        raise ValueError("水蒸气分压力必须小于总压力")

    W = EPSILON * p_v / (P - p_v)

    return W


# =========================
# 3. 湿空气焓值
# =========================

def moist_air_enthalpy(T, W):
    """
    计算湿空气焓值。

    参数
    ----
    T : float
        干球温度，degC

    W : float
        含湿量，kg水/kg干空气

    返回
    ----
    float
        焓值，kJ/kg干空气
    """

    h = 1.006 * T + W * (2501.0 + 1.86 * T)

    return h


# =========================
# 4. 相对湿度
# =========================

def relative_humidity(T, W, P=101325.0):
    """
    根据温度、含湿量和总压力计算相对湿度。
    """

    p_ws = saturation_pressure(T)

    p_v = P * W / (EPSILON + W)

    RH = p_v / p_ws

    return RH


# =========================
# 5. 露点温度
# =========================

def dew_point_temperature(T, RH):
    """
    根据干球温度和相对湿度计算露点温度。

    使用二分法反求饱和水蒸气压力对应的温度。
    """

    if RH <= 0.0 or RH > 1.0:
        raise ValueError("露点计算要求 RH 在 (0, 1] 之间")

    p_v = RH * saturation_pressure(T)

    T_low = -80.0
    T_high = T

    for _ in range(100):

        T_mid = 0.5 * (T_low + T_high)

        p_mid = saturation_pressure(T_mid)

        if p_mid > p_v:
            T_high = T_mid
        else:
            T_low = T_mid

    return 0.5 * (T_low + T_high)


# =========================
# 6. 湿空气密度
# =========================

def moist_air_density(T, W, P=101325.0):
    """
    计算湿空气总密度。

    参数
    ----
    T : float
        干球温度，degC

    W : float
        含湿量，kg水/kg干空气

    P : float
        总压力，Pa

    返回
    ----
    float
        湿空气密度，kg/m^3
    """

    T_K = T + 273.15

    # 水蒸气分压力
    p_v = P * W / (EPSILON + W)

    # 干空气分压力
    p_da = P - p_v

    # 干空气密度 + 水蒸气密度
    rho_da = p_da / (R_DA * T_K)
    rho_v = p_v / (R_V * T_K)

    return rho_da + rho_v


# =========================
# 7. 空气状态计算
# =========================

def air_state(T, RH, P=101325.0):
    """
    根据温度和相对湿度，计算完整湿空气状态。

    返回字典：
        T
        RH
        W
        h
        dew_point
        density
    """

    W = humidity_ratio(T, RH, P)

    h = moist_air_enthalpy(T, W)

    T_dp = dew_point_temperature(T, RH)

    rho = moist_air_density(T, W, P)

    return {
        "T": T,
        "RH": RH,
        "W": W,
        "h": h,
        "dew_point": T_dp,
        "density": rho,
    }


# =========================
# 8. 新风与回风混合
# =========================

def mix_air_streams(
    T_fresh,
    RH_fresh,
    V_fresh,
    T_return,
    RH_return,
    V_return,
    P=101325.0,
):
    """
    根据新风和回风状态计算混合空气状态。

    注意：
    V_fresh 和 V_return 分别是各自入口状态下的体积流量。
    先换算为干空气质量流量，再进行质量加权混合。

    返回：
        混合空气温度
        混合空气含湿量
        混合空气焓值
        混合空气相对湿度
        混合空气露点
        混合空气密度
        新风干空气质量流量
        回风干空气质量流量
    """

    if V_fresh < 0.0 or V_return < 0.0:
        raise ValueError("体积流量不能为负数")

    fresh = air_state(T_fresh, RH_fresh, P)
    ret = air_state(T_return, RH_return, P)

    # 各股空气的干空气质量流量
    mdot_da_fresh = (
        fresh["density"] * V_fresh / (1.0 + fresh["W"])
    )

    mdot_da_return = (
        ret["density"] * V_return / (1.0 + ret["W"])
    )

    mdot_da_total = mdot_da_fresh + mdot_da_return

    if mdot_da_total <= 0.0:
        raise ValueError("混合空气总干空气质量流量必须大于零")

    # 按干空气质量流量加权
    W_mix = (
        mdot_da_fresh * fresh["W"]
        + mdot_da_return * ret["W"]
    ) / mdot_da_total

    h_mix = (
        mdot_da_fresh * fresh["h"]
        + mdot_da_return * ret["h"]
    ) / mdot_da_total

    # 根据混合焓值和含湿量反算温度
    T_mix = (
        h_mix - 2501.0 * W_mix
    ) / (1.006 + 1.86 * W_mix)

    RH_mix = relative_humidity(T_mix, W_mix, P)

    T_dp_mix = dew_point_temperature(T_mix, RH_mix)

    rho_mix = moist_air_density(T_mix, W_mix, P)

    # 混合状态下的体积流量
    V_mix = mdot_da_total * (1.0 + W_mix) / rho_mix

    return {
        "T": T_mix,
        "RH": RH_mix,
        "W": W_mix,
        "h": h_mix,
        "dew_point": T_dp_mix,
        "density": rho_mix,
        "mdot_da_fresh": mdot_da_fresh,
        "mdot_da_return": mdot_da_return,
        "mdot_da_total": mdot_da_total,
        "V_total": V_mix,
    }
# =========================
# 9. 独立运行测试
# =========================

if __name__ == "__main__":

    from cams_inputs import (
        P_AMBIENT,
        T_OUTDOOR,
        RH_OUTDOOR,
        T_RETURN_AIR,
        RH_RETURN_AIR,
        V_FRESH_AIR,
        V_RETURN_AIR,
    )

    print("\n========== CAMS Psychrometric Analysis ==========")

    # 新风状态
    fresh = air_state(
        T_OUTDOOR,
        RH_OUTDOOR,
        P_AMBIENT,
    )

    # 回风状态
    return_air = air_state(
        T_RETURN_AIR,
        RH_RETURN_AIR,
        P_AMBIENT,
    )

    # 新风与回风混合
    mixed = mix_air_streams(
        T_fresh=T_OUTDOOR,
        RH_fresh=RH_OUTDOOR,
        V_fresh=V_FRESH_AIR,
        T_return=T_RETURN_AIR,
        RH_return=RH_RETURN_AIR,
        V_return=V_RETURN_AIR,
        P=P_AMBIENT,
    )

    def print_air_state(name, state):
        print(f"\n--- {name} ---")
        print(f"Temperature : {state['T']:.2f} degC")
        print(f"Relative Humidity : {state['RH'] * 100:.2f} %")
        print(f"Humidity Ratio : {state['W']:.6f} kg/kg")
        print(f"Enthalpy : {state['h']:.3f} kJ/kg")
        print(f"Dew Point : {state['dew_point']:.2f} degC")
        print(f"Density : {state['density']:.4f} kg/m3")

    print_air_state("Fresh Air", fresh)
    print_air_state("Return Air", return_air)
    print_air_state("Mixed Air", mixed)

    print("\n--- Air Flow ---")
    print(
        f"Fresh Air Flow : {V_FRESH_AIR * 1000:.2f} L/s"
    )
    print(
        f"Return Air Flow : {V_RETURN_AIR * 1000:.2f} L/s"
    )
    print(
        f"Mixed Air Flow : {mixed['V_total'] * 1000:.2f} L/s"
    )
    print(
        f"Dry Air Mass Flow : {mixed['mdot_da_total']:.4f} kg/s"
    )

    print("\n=================================================")