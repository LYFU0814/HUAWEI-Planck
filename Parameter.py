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
line_accelerated_speed_normal = traction_max / robot_weight_normal  # 机器人未带货物时的线加速度
line_accelerated_speed_hold = traction_max / robot_weight_hold  # 机器人带货物时的线加速度
angular_accelerated_speed_normal = torque_max / robot_weight_normal  # 机器人未带货物时的角加速度
angular_accelerated_speed_hold = torque_max / robot_weight_hold  # 机器人带货物时的角加速度

product_buy_price = [0, 3000, 4400, 5800, 15400, 17200, 19200, 76000]  # 产品购买价格
product_sell_price = [0, 6000, 7600, 9200, 22500, 25000, 27500, 105000]  # 产品售卖价格
bench_work_time = [0, 50, 50, 50, 500, 500, 500, 1000, 1, 1]  # 工作台工作时间
bench_type_need = [[], [], [], [], [1, 2], [1, 3], [2, 3], [4, 5, 6], [7], [1, 2, 3, 4, 5, 6, 7]]  # 工作台需要的原材料类型


# ----------------------------------------


# ----------------------------------------
# 工具函数
# ----------------------------------------
def distance_m(pos_a, pos_b):  # 计算曼哈顿距离
    return abs(pos_a[0] - pos_b[0]) + abs(pos_a[1] - pos_b[1])


def distance_o(pos_a, pos_b):  # 计算欧式距离
    return math.sqrt(abs(pos_a[0] - pos_b[0]) ** 2 + abs(pos_a[1] - pos_b[1]) ** 2)
