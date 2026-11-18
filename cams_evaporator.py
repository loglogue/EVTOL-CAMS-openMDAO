
# cams_evaporator.py
"""
CAMS 蒸发器空气侧性能计算

模型：
    ADP（装置露点温度）+ BF（旁通因子）

输入：
    混合空气入口状态
    蒸发器目标制冷量
    蒸发器 ADP

输出：
    空气出口温度、相对湿度、含湿量、焓值
    旁通因子
    显热负荷、潜热负荷
    冷凝水流量

单位：
    温度：degC
    压力：Pa
    焓值：kJ/kg干空气
    质量流量：kg/s
    热量：W
"""

from cams_inputs import (
    Q_EVAPORATOR_DESIGN,
    P_AMBIENT,
)

from cams_psychrometrics import (
    humidity_ratio,
    moist_air_enthalpy,
    relative_humidity,
)


# ============================================================
# 1. 蒸发器入口空气参数
# ============================================================

# 来自 cams_psychrometrics.py 的混合空气计算结果
# 如果以后修改新风、回风条件，应同步更新这些参数
T_IN = 26.14
RH_IN = 0.5158
M_DA = 0.1739

# 蒸发器空气侧装置露点温度（暂定）
T_ADP = 3.0


# ============================================================
# 2. 蒸发器计算
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
    计算蒸发器空气侧性能。

    参数
    ----
    T_in : float
        入口空气温度，degC

    RH_in : float
        入口相对湿度，0~1

    m_da : float
        干空气质量流量，kg/s

    Q_total : float
        蒸发器总制冷量，W

    T_adp : float
        装置露点温度，degC

    pressure : float
        空气压力，Pa
    """

    # --------------------------------------------------------
    # Step 1：入口空气状态
    # --------------------------------------------------------

    W_in = humidity_ratio(T_in, RH_in, pressure)

    h_in = moist_air_enthalpy(T_in, W_in)

    # --------------------------------------------------------
    # Step 2：ADP 状态
    # --------------------------------------------------------

    # ADP 点假设为饱和空气
    W_adp = humidity_ratio(T_adp, 1.0, pressure)

    h_adp = moist_air_enthalpy(T_adp, W_adp)

    # --------------------------------------------------------
    # Step 3：根据目标制冷量计算出口焓值
    # --------------------------------------------------------

    # 注意：焓值单位为 kJ/kg，制冷量单位为 W
    delta_h = Q_total / (m_da * 1000.0)

    h_out = h_in - delta_h

    # --------------------------------------------------------
    # Step 4：计算旁通因子 BF
    # --------------------------------------------------------

    BF = (h_out - h_adp) / (h_in - h_adp)

    if not 0.0 <= BF <= 1.0:
        raise ValueError(
            f"计算得到 BF={BF:.4f}，超出 0~1 范围。"
            "请检查目标冷量、空气流量和 ADP 假设。"
        )

    # --------------------------------------------------------
    # Step 5：计算出口含湿量
    # --------------------------------------------------------

    W_out = W_adp + BF * (W_in - W_adp)

    # --------------------------------------------------------
    # Step 6：根据出口焓值和含湿量反算出口温度
    # --------------------------------------------------------

    # 湿空气焓值公式：
    # h = 1.006*T + W*(2501 + 1.86*T)
    #
    # 反算：
    # T = (h - 2501*W) / (1.006 + 1.86*W)

    T_out = (
        h_out - 2501.0 * W_out
    ) / (
        1.006 + 1.86 * W_out
    )

    # --------------------------------------------------------
    # Step 7：计算出口相对湿度
    # --------------------------------------------------------

    RH_out = relative_humidity(
        T_out,
        W_out,
        pressure,
    )

    # --------------------------------------------------------
    # Step 8：计算显热和潜热负荷
    # --------------------------------------------------------

    # 采用入口含湿量下的湿空气定压比热近似计算显热
    cp_air = 1.006 + 1.86 * W_in

    Q_sensible = (
        m_da
        * cp_air
        * (T_in - T_out)
        * 1000.0
    )

    # 总冷量 = 显热 + 潜热
    Q_latent = Q_total - Q_sensible

    sensible_heat_ratio = Q_sensible / Q_total

    # --------------------------------------------------------
    # Step 9：计算冷凝水流量
    # --------------------------------------------------------

    # kg/s
    m_condensate = m_da * (W_in - W_out)

    # kg/h
    m_condensate_hour = m_condensate * 3600.0

    # --------------------------------------------------------
    # Step 10：结果汇总
    # --------------------------------------------------------

    return {
        "T_in": T_in,
        "RH_in": RH_in,
        "W_in": W_in,
        "h_in": h_in,

        "T_adp": T_adp,
        "W_adp": W_adp,
        "h_adp": h_adp,

        "BF": BF,

        "T_out": T_out,
        "RH_out": RH_out,
        "W_out": W_out,
        "h_out": h_out,

        "Q_total": Q_total,
        "Q_sensible": Q_sensible,
        "Q_latent": Q_latent,
        "SHR": sensible_heat_ratio,

        "m_da": m_da,
        "m_condensate": m_condensate,
        "m_condensate_hour": m_condensate_hour,
    }


# ============================================================
# 3. 主程序
# ============================================================

if __name__ == "__main__":

    result = calculate_evaporator(
        T_in=T_IN,
        RH_in=RH_IN,
        m_da=M_DA,
        Q_total=Q_EVAPORATOR_DESIGN,
        T_adp=T_ADP,
        pressure=P_AMBIENT,
    )

    print("\n========== CAMS Evaporator Analysis ==========")

    print("\n--- Design Inputs ---")
    print(f"Total Cooling Capacity : {result['Q_total']:.2f} W")
    print(f"Dry Air Mass Flow      : {result['m_da']:.4f} kg/s")
    print(f"ADP Temperature        : {result['T_adp']:.2f} degC")

    print("\n--- Inlet Air ---")
    print(f"Temperature            : {result['T_in']:.2f} degC")
    print(f"Relative Humidity      : {result['RH_in']*100:.2f} %")
    print(f"Humidity Ratio         : {result['W_in']:.6f} kg/kg")
    print(f"Enthalpy               : {result['h_in']:.3f} kJ/kg")

    print("\n--- ADP State ---")
    print(f"ADP Humidity Ratio     : {result['W_adp']:.6f} kg/kg")
    print(f"ADP Enthalpy           : {result['h_adp']:.3f} kJ/kg")

    print("\n--- Evaporator Performance ---")
    print(f"Bypass Factor          : {result['BF']:.4f}")
    print(f"Outlet Temperature     : {result['T_out']:.2f} degC")
    print(f"Outlet Relative Humidity: {result['RH_out']*100:.2f} %")
    print(f"Outlet Humidity Ratio  : {result['W_out']:.6f} kg/kg")
    print(f"Outlet Enthalpy        : {result['h_out']:.3f} kJ/kg")

    print("\n--- Cooling Load ---")
    print(f"Total Cooling          : {result['Q_total']:.2f} W")
    print(f"Sensible Cooling       : {result['Q_sensible']:.2f} W")
    print(f"Latent Cooling         : {result['Q_latent']:.2f} W")
    print(f"Sensible Heat Ratio    : {result['SHR']:.4f}")

    print("\n--- Condensate ---")
    print(
        f"Condensate Flow       : "
        f"{result['m_condensate_hour']:.3f} kg/h"
    )

    print("\n==============================================")
