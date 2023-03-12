import math

# ----------------------------------------
# 环境参数设置
# ----------------------------------------
duration = 3  # 比赛时长，单位分钟
graph_width = 50  # 地图宽度 m
graph_height = 50  # 地图高度 m
robot_size = 4  # 机器人数量
fps = 50  # 每秒帧数
money = 200000  # 初始资金
table_scope = 0.4  # 工作台范围 二者距离小于该值时，视为机器人位于工作台上.
robot_radius_normal = 0.45  # 机器人半径（常态）
robot_radius_hold = 0.53  # 机器人半径（持有物品）
robot_dense = 20  # 机器人密度 单位：kg/m2.  质量=面积*密度，故机器人变大后质量也会变大
robot_weight_normal = math.pi * robot_radius_normal ** 2 * robot_dense
robot_weight_hold = math.pi * robot_radius_hold ** 2 * robot_dense
speed_forward_max = 6  # 最大前进速度 米/s
speed_backward_max = 2  # 最大后退速度 米/s
speed_rotate_max = math.pi  # 最大旋转速度  π/s
traction_max = 250  # 最大牵引力 N 机器人的加速/减速/防侧滑均由牵引力驱动
torque_max = 50  # 最大力矩 50 N*m  机器人的旋转由力矩驱动

product_buy_price = [0, 3000, 4400, 5800, 15400, 17200, 19200, 76000]
product_sell_price = [0, 6000, 7600, 9200, 22500, 25000, 27500, 105000]
bench_type_need = [[], [], [], [], [1, 2], [1, 3], [2, 3], [4, 5, 6], [7], [1, 2, 3, 4, 5, 6, 7]]
# ----------------------------------------
