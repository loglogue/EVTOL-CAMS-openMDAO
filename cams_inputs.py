
# cams_inputs.py
"""
CAMS 热性能模型统一输入参数

单位：
    温度：degC
    压力：Pa
    体积流量：m^3/s
    功率/热量：W
    相对湿度：0~1
"""

# ============================================================
# 1. 座舱及蒸发器设计参数
# ============================================================

Q_EVAPORATOR_DESIGN = 5500.0  # 蒸发器目标制冷量，W

OCCUPANT_NUMBER = 6

V_AIR_TOTAL = 150.0 / 1000.0  # 总送风量，m^3/s

FRESH_AIR_RATIO = 0.20
RETURN_AIR_RATIO = 1.0 - FRESH_AIR_RATIO

V_FRESH_AIR = V_AIR_TOTAL * FRESH_AIR_RATIO
V_RETURN_AIR = V_AIR_TOTAL * RETURN_AIR_RATIO

# ============================================================
# 2. 座舱及室外空气状态
# ============================================================

T_OUTDOOR = 35.0
RH_OUTDOOR = 0.50

T_CABIN = 24.0
RH_CABIN = 0.50

# 回风状态暂按座舱目标状态处理
T_RETURN_AIR = T_CABIN
RH_RETURN_AIR = RH_CABIN

P_AMBIENT = 101325.0

# ============================================================
# 3. 制冷循环参数
# ============================================================

REFRIGERANT = "R134a"

# 制冷系统 COP
# 当前暂定为 1.8
COP_COOLING = 1.8

# 压缩机轴功率
# 暂按 COP = 蒸发器制冷量 / 压缩机轴功率
P_COMPRESSOR_SHAFT = (
    Q_EVAPORATOR_DESIGN / COP_COOLING
)

# 冷凝器总散热量
# Q_cond = Q_evap + P_compressor_shaft
Q_CONDENSER = (
    Q_EVAPORATOR_DESIGN + P_COMPRESSOR_SHAFT
)
# R134a 制冷循环设计参数

# 蒸发温度
T_EVAPORATION = 0.0  # degC

# 蒸发器出口过热度
SUPERHEAT = 5.0  # K

# 冷凝饱和温度：初步计算假设，尚待冷凝器模型校核
T_CONDENSATION = 50.0  # degC

# 冷凝器出口过冷度：初步计算假设
SUBCOOLING = 5.0  # K

# 压缩机等熵效率：初步假设
COMPRESSOR_ISENTROPIC_EFFICIENCY = 0.70

# ============================================================
# 4. 飞行及冷凝器空气侧参数
# ============================================================

# 设计飞行速度：80 km/h
V_FLIGHT = 80.0 / 3.6

# 冷凝器空气侧温升，初步假设
DELTA_T_CONDENSER_AIR = 13.0

# 冷凝器迎面风速，初步假设
V_CONDENSER_FACE = 3.5

# 冲压空气捕获效率，初步假设
RAM_AIR_CAPTURE_EFFICIENCY = 0.70

# ============================================================
# 5. 参数检查及打印
# ============================================================

if __name__ == "__main__":

    print("\n========== CAMS Design Inputs ==========")

    print("\n--- Cabin and Evaporator ---")
    print(f"Occupants             : {OCCUPANT_NUMBER}")
    print(f"Total Air Flow        : {V_AIR_TOTAL * 1000:.2f} L/s")
    print(f"Fresh Air Flow        : {V_FRESH_AIR * 1000:.2f} L/s")
    print(f"Return Air Flow       : {V_RETURN_AIR * 1000:.2f} L/s")
    print(f"Evaporator Capacity   : {Q_EVAPORATOR_DESIGN:.2f} W")

    print("\n--- Refrigeration Cycle ---")
    print(f"Refrigerant           : {REFRIGERANT}")
    print(f"Cooling COP           : {COP_COOLING:.2f}")
    print(f"Compressor Shaft Power: {P_COMPRESSOR_SHAFT:.2f} W")
    print(f"Condenser Heat Load   : {Q_CONDENSER:.2f} W")

    print("\n--- Condenser Air Side ---")
    print(f"Flight Speed          : {V_FLIGHT:.2f} m/s")
    print(f"Air Temperature Rise  : {DELTA_T_CONDENSER_AIR:.2f} K")
    print(f"Face Velocity         : {V_CONDENSER_FACE:.2f} m/s")
    print(f"Capture Efficiency    : {RAM_AIR_CAPTURE_EFFICIENCY:.2f}")

    print("\n========================================")
# ============================================================
# 6. 压缩机电气设计参数
# ============================================================

COMPRESSOR_TYPE = "Electric Scroll"

DC_BUS_VOLTAGE = 800.0  # VDC

COMPRESSOR_POWER_SOURCE = "HVDC"

# 以下参数等待供应商提供
COMPRESSOR_RATED_POWER = None  # W

COMPRESSOR_MAX_POWER = None    # W

COMPRESSOR_RATED_SPEED = None  # rpm

COMPRESSOR_MIN_SPEED = None    # rpm

COMPRESSOR_MAX_SPEED = None    # rpm

# ============================================================
# 7. 高压直流电动涡旋压缩机参数
# ============================================================

# 压缩机类型
COMPRESSOR_TYPE = "Electric Scroll"

# 制冷剂
COMPRESSOR_REFRIGERANT = "R134a"

# 高压直流母线
DC_BUS_VOLTAGE = 800.0  # VDC

# 供应商性能数据状态
COMPRESSOR_VENDOR_DATA_AVAILABLE = False

# 供应商性能参数（待供应商提供）
COMPRESSOR_RATED_SPEED = None
COMPRESSOR_MIN_SPEED = None
COMPRESSOR_MAX_SPEED = None

COMPRESSOR_VENDOR_CAPACITY = None

# 供应商功率数值
COMPRESSOR_VENDOR_DC_POWER = None

# 功率边界：
# dc_input：直流输入功率
# shaft：压缩机轴功率
COMPRESSOR_VENDOR_POWER_TYPE = "dc_input"

# 电机及控制器综合效率
COMPRESSOR_DRIVE_EFFICIENCY = None

# 供应商性能数据对应工况
COMPRESSOR_VENDOR_T_EVAP = None
COMPRESSOR_VENDOR_T_COND = None

