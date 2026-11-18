
# cams_condenser.py
"""
CAMS 冷凝器空气侧初步性能计算模型

计算内容：
1. 冷凝器总散热量
2. 压缩机轴功率
3. 冷凝器入口空气状态
4. 冷凝器所需空气质量流量
5. 冷凝器空气体积流量
6. 冷凝器空气出口温度
7. 冷凝器迎风面积
8. 冲压空气捕获面积
9. 飞行状态下自由来流动压

注意：
本模型属于系统级初步估算模型，
不代替制冷剂两相流换热器详细设计。

单位：
    温度：degC
    压力：Pa
    功率：W
    质量流量：kg/s
    体积流量：m^3/s
    面积：m^2
"""


# ============================================================
# 1. 导入统一设计参数
# ============================================================

from cams_inputs import (
    Q_EVAPORATOR_DESIGN,
    COP_COOLING,
    P_COMPRESSOR_SHAFT,
    Q_CONDENSER,

    T_OUTDOOR,
    RH_OUTDOOR,
    P_AMBIENT,

    V_FLIGHT,

    DELTA_T_CONDENSER_AIR,
    V_CONDENSER_FACE,
    RAM_AIR_CAPTURE_EFFICIENCY,
)

from cams_psychrometrics import (
    humidity_ratio,
    moist_air_density,
)


# ============================================================
# 2. 冷凝器计算函数
# ============================================================

def calculate_condenser(
    Q_evaporator,
    COP,
    P_compressor_shaft,
    Q_condenser,
    T_air_in,
    RH_air_in,
    pressure,
    delta_T_air,
    v_flight,
    v_face,
    capture_efficiency,
):
    """
    计算冷凝器空气侧初步设计参数。

    参数
    ----
    Q_evaporator : float
        蒸发器制冷量，W

    COP : float
        制冷系统 COP

    P_compressor_shaft : float
        压缩机轴功率，W

    Q_condenser : float
        冷凝器散热量，W

    T_air_in : float
        冷凝器入口空气温度，degC

    RH_air_in : float
        冷凝器入口空气相对湿度，0~1

    pressure : float
        环境压力，Pa

    delta_T_air : float
        冷凝器空气侧温升，K

    v_flight : float
        飞行速度，m/s

    v_face : float
        冷凝器迎面风速，m/s

    capture_efficiency : float
        冲压空气捕获效率，0~1

    返回
    ----
    result : dict
        冷凝器计算结果
    """

    # --------------------------------------------------------
    # Step 1：输入参数检查
    # --------------------------------------------------------

    if Q_evaporator <= 0:
        raise ValueError("蒸发器制冷量必须大于0。")

    if COP <= 0:
        raise ValueError("制冷 COP 必须大于0。")

    if P_compressor_shaft < 0:
        raise ValueError("压缩机轴功率不能小于0。")

    if Q_condenser <= 0:
        raise ValueError("冷凝器散热量必须大于0。")

    if not 0 <= RH_air_in <= 1:
        raise ValueError("空气相对湿度必须在0~1之间。")

    if pressure <= 0:
        raise ValueError("环境压力必须大于0。")

    if delta_T_air <= 0:
        raise ValueError("冷凝器空气温升必须大于0。")

    if v_flight <= 0 or v_face <= 0:
        raise ValueError("飞行速度和迎面风速必须大于0。")

    if not 0 < capture_efficiency <= 1:
        raise ValueError("冲压空气捕获效率必须在0~1之间。")

    # --------------------------------------------------------
    # Step 2：制冷循环能量平衡校核
    # --------------------------------------------------------

    # 根据 COP 计算压缩机轴功率
    P_comp_calculated = Q_evaporator / COP

    # 根据能量守恒计算冷凝器散热量
    Q_cond_calculated = (
        Q_evaporator + P_comp_calculated
    )

    # 校核统一输入参数
    if abs(P_compressor_shaft - P_comp_calculated) > 1.0:
        raise ValueError(
            "压缩机轴功率与 COP 计算结果不一致，"
            "请检查 cams_inputs.py。"
        )

    if abs(Q_condenser - Q_cond_calculated) > 1.0:
        raise ValueError(
            "冷凝器散热量与能量平衡计算结果不一致，"
            "请检查 cams_inputs.py。"
        )

    # --------------------------------------------------------
    # Step 3：计算冷凝器入口空气状态
    # --------------------------------------------------------

    W_air_in = humidity_ratio(
        T_air_in,
        RH_air_in,
        pressure,
    )

    rho_air_in = moist_air_density(
        T_air_in,
        W_air_in,
        pressure,
    )

    # 湿空气比热，按每kg干空气计算
    cp_air = 1.006 + 1.86 * W_air_in

    # --------------------------------------------------------
    # Step 4：计算冷凝器所需干空气质量流量
    # --------------------------------------------------------

    # Q = m_da * cp * delta_T
    #
    # Q：W
    # cp：kJ/(kg干空气*K)
    # m_da：kg/s

    m_da_air = Q_condenser / (
        cp_air * delta_T_air * 1000.0
    )

    # --------------------------------------------------------
    # Step 5：计算空气侧出口温度
    # --------------------------------------------------------

    T_air_out = T_air_in + delta_T_air

    # --------------------------------------------------------
    # Step 6：计算湿空气总质量流量
    # --------------------------------------------------------

    m_moist_air = m_da_air * (
        1.0 + W_air_in
    )

    # --------------------------------------------------------
    # Step 7：计算入口空气体积流量
    # --------------------------------------------------------

    V_air = m_moist_air / rho_air_in

    V_air_m3h = V_air * 3600.0

    V_air_Ls = V_air * 1000.0

    # --------------------------------------------------------
    # Step 8：估算冷凝器迎风面积
    # --------------------------------------------------------

    A_face = V_air / v_face

    # --------------------------------------------------------
    # Step 9：估算冲压空气捕获面积
    # --------------------------------------------------------

    # V_air = A_capture * V_flight * efficiency

    A_capture = V_air / (
        v_flight * capture_efficiency
    )

    # --------------------------------------------------------
    # Step 10：计算自由来流动压
    # --------------------------------------------------------

    q_dynamic = (
        0.5
        * rho_air_in
        * v_flight ** 2
    )

    # --------------------------------------------------------
    # Step 11：计算能量平衡误差
    # --------------------------------------------------------

    Q_air_side = (
        m_da_air
        * cp_air
        * delta_T_air
        * 1000.0
    )

    energy_balance_error = (
        Q_air_side - Q_condenser
    )

    # --------------------------------------------------------
    # Step 12：结果汇总
    # --------------------------------------------------------

    return {
        # 制冷循环
        "Q_evaporator": Q_evaporator,
        "COP": COP,
        "P_compressor_shaft": P_compressor_shaft,
        "Q_condenser": Q_condenser,

        # 空气状态
        "T_air_in": T_air_in,
        "RH_air_in": RH_air_in,
        "W_air_in": W_air_in,
        "rho_air_in": rho_air_in,
        "cp_air": cp_air,

        "T_air_out": T_air_out,
        "delta_T_air": delta_T_air,

        # 空气流量
        "m_da_air": m_da_air,
        "m_moist_air": m_moist_air,
        "V_air": V_air,
        "V_air_m3h": V_air_m3h,
        "V_air_Ls": V_air_Ls,

        # 几何参数
        "v_face": v_face,
        "A_face": A_face,
        "A_capture": A_capture,

        # 冲压空气
        "v_flight": v_flight,
        "capture_efficiency": capture_efficiency,
        "q_dynamic": q_dynamic,

        # 能量校核
        "Q_air_side": Q_air_side,
        "energy_balance_error": energy_balance_error,
    }


# ============================================================
# 3. 主程序
# ============================================================

if __name__ == "__main__":

    result = calculate_condenser(
        Q_evaporator=Q_EVAPORATOR_DESIGN,
        COP=COP_COOLING,
        P_compressor_shaft=P_COMPRESSOR_SHAFT,
        Q_condenser=Q_CONDENSER,

        T_air_in=T_OUTDOOR,
        RH_air_in=RH_OUTDOOR,
        pressure=P_AMBIENT,

        delta_T_air=DELTA_T_CONDENSER_AIR,
        v_flight=V_FLIGHT,
        v_face=V_CONDENSER_FACE,
        capture_efficiency=RAM_AIR_CAPTURE_EFFICIENCY,
    )

    # --------------------------------------------------------
    # 输出：制冷循环参数
    # --------------------------------------------------------

    print("\n========== CAMS Condenser Analysis ==========")

    print("\n--- Refrigeration Cycle ---")

    print(
        f"Evaporator Cooling       : "
        f"{result['Q_evaporator']:.2f} W"
    )

    print(
        f"Cooling COP              : "
        f"{result['COP']:.2f}"
    )

    print(
        f"Compressor Shaft Power  : "
        f"{result['P_compressor_shaft']:.2f} W"
    )

    print(
        f"Condenser Heat Rejection: "
        f"{result['Q_condenser']:.2f} W"
    )

    # --------------------------------------------------------
    # 输出：空气侧参数
    # --------------------------------------------------------

    print("\n--- Condenser Air Side ---")

    print(
        f"Air Inlet Temperature   : "
        f"{result['T_air_in']:.2f} degC"
    )

    print(
        f"Air Outlet Temperature  : "
        f"{result['T_air_out']:.2f} degC"
    )

    print(
        f"Air Temperature Rise    : "
        f"{result['delta_T_air']:.2f} K"
    )

    print(
        f"Air Relative Humidity   : "
        f"{result['RH_air_in'] * 100:.2f} %"
    )

    print(
        f"Air Humidity Ratio      : "
        f"{result['W_air_in']:.6f} kg/kg"
    )

    print(
        f"Air Density             : "
        f"{result['rho_air_in']:.4f} kg/m3"
    )

    print(
        f"Air Specific Heat       : "
        f"{result['cp_air']:.4f} kJ/(kg*K)"
    )

    # --------------------------------------------------------
    # 输出：空气流量
    # --------------------------------------------------------

    print("\n--- Air Flow Requirements ---")

    print(
        f"Dry Air Mass Flow       : "
        f"{result['m_da_air']:.4f} kg/s"
    )

    print(
        f"Moist Air Mass Flow     : "
        f"{result['m_moist_air']:.4f} kg/s"
    )

    print(
        f"Air Volume Flow         : "
        f"{result['V_air']:.4f} m3/s"
    )

    print(
        f"Air Volume Flow         : "
        f"{result['V_air_m3h']:.2f} m3/h"
    )

    print(
        f"Air Volume Flow         : "
        f"{result['V_air_Ls']:.2f} L/s"
    )

    # --------------------------------------------------------
    # 输出：冷凝器几何参数
    # --------------------------------------------------------

    print("\n--- Condenser Geometry Estimate ---")

    print(
        f"Face Velocity           : "
        f"{result['v_face']:.2f} m/s"
    )

    print(
        f"Estimated Face Area     : "
        f"{result['A_face']:.4f} m2"
    )

    print(
        f"Estimated Capture Area  : "
        f"{result['A_capture']:.4f} m2"
    )

    # --------------------------------------------------------
    # 输出：冲压空气参数
    # --------------------------------------------------------

    print("\n--- Ram Air ---")

    print(
        f"Flight Speed            : "
        f"{result['v_flight']:.2f} m/s"
    )

    print(
        f"Capture Efficiency      : "
        f"{result['capture_efficiency']:.2f}"
    )

    print(
        f"Free Stream Dynamic P   : "
        f"{result['q_dynamic']:.2f} Pa"
    )

    # --------------------------------------------------------
    # 输出：能量平衡校核
    # --------------------------------------------------------

    print("\n--- Energy Balance Check ---")

    print(
        f"Condenser Heat Load     : "
        f"{result['Q_condenser']:.2f} W"
    )

    print(
        f"Air Side Heat Transfer  : "
        f"{result['Q_air_side']:.2f} W"
    )

    print(
        f"Energy Balance Error    : "
        f"{result['energy_balance_error']:.8f} W"
    )

    print("\n=============================================")
