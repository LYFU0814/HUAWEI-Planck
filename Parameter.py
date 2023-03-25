import math
import numpy as np
import sys


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
bench_raw_map = [[], [], [], [], [1, 2], [1, 3], [2, 3], [4, 5, 6], [7], [1, 2, 3, 4, 5, 6, 7]]  # 工作台需要的原材料类型
raw_bench_map = [[4, 5], [4, 6], [5, 6], [7], [7], [7], [], []]  # 原材料供给工作台
bench_bw_dis = {}  # 任意两个工作台之间的距离 {(bid1, bid2): 距离}
workbenches_category = [[] for _ in range(10)]  # i类型工作台 = [b_1, b_2,...]
buyer = [[] for _ in range(8)]  # 需要i号产品的工作台列表

# ----------------------------------------
frame_id = -1


# ----------------------------------------
# 工具函数
# ----------------------------------------
def log(content, clear=False):
    """
    打印每一帧的日志
    :param content: 打印内容
    :param clear: 是否清空文件
    """
    # pass
    with open("log.txt", mode='a+', encoding='utf-8') as file:
        if clear:
            file.truncate(0)
        file.write(str(content))
        file.write("\n")


def in_range(n, start, end=0):
    return start <= n <= end if end >= start else end <= n <= start


def get_product_profit(pid):
    return product_sell_price[pid] - product_buy_price[pid]


def get_bench_bw_dis(bid, oid):
    """
    获得两个工作台之间的距离
    :param bid: 工作台id 1
    :param oid: 工作台id 2
    :return: 平台之间的距离
    """
    if bid == oid:
        return 0
    return bench_bw_dis[bid, oid] if bid < oid else bench_bw_dis[oid, bid]


def get_category_size(bench_type):
    """
    获得某种类型工作台的数量
    :param bench_type: 工作台类型
    :return: 工作台数量
    """
    return len(workbenches_category[bench_type])


def distance_m(pos_a, pos_b):  # 计算曼哈顿距离
    return abs(pos_a[0] - pos_b[0]) + abs(pos_a[1] - pos_b[1])


def distance_o(pos_a, pos_b):  # 计算欧式距离
    return math.sqrt(abs(pos_a[0] - pos_b[0]) ** 2 + abs(pos_a[1] - pos_b[1]) ** 2)


def get_clock_angle(pos_1, pos_2, dir):
    """
    计算最小偏向角
    :param pos_1: 机器人位置
    :param pos_2: 平台位置
    :param dir: 机器人当前方向
    :return: 最小偏向角，单位弧度，负表示顺时针，正表示逆时针
    """
    v1, v2 = [np.cos(dir), np.sin(dir)], [pos_2[0] - pos_1[0], pos_2[1] - pos_1[1]]
    return get_vector_angle(v1, v2)


def get_workbench_angle(pos_1, pos_2, pos_3):
    """
    计算机器人从平台1到平台2的最小偏向角
    :param pos_1: 机器人位置
    :param pos_2: 平台1位置
    :param pos_3: 平台2位置
    :return: 最小偏向角，单位弧度，负表示顺时针，正表示逆时针
    """
    v1, v2 = [pos_2[0] - pos_1[0], pos_2[1] - pos_1[1]], [pos_3[0] - pos_2[0], pos_3[1] - pos_2[1]]
    return get_vector_angle(v1, v2)


def get_vector_angle(v1, v2):
    # 2个向量模的乘积
    TheNorm = np.linalg.norm(v1) * np.linalg.norm(v2)
    # 叉乘
    rho = np.rad2deg(np.arcsin(np.cross(v1, v2) / TheNorm))
    # 点乘
    # theta = np.rad2deg(np.arccos(np.dot(v1,v2)/TheNorm))
    theta = np.arccos(np.dot(v1, v2) / TheNorm)
    if rho < 0:
        return - theta
    else:
        return theta


if __name__ == '__main__':
    print(get_vector_angle((1, 0), (0, -1)) * 57.3)
