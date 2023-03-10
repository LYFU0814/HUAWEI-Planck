#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import sys

duration = 0  # 比赛市场，单位分钟
graph_width = 0  # 地图宽度
graph_height = 0  # 地图高度
robot_size = 0  # 机器人数量
fps = 0  # 每秒帧数
money = 0  # 初始资金
table_scope = 0  # 工作台范围 二者距离小于该值时，视为机器人位于工作台上.
robot_scope_normal = 0  # 机器人半径（常态）
robot_scope_hold = 0  # 机器人半径（持有物品）
robot_dense = 0  # 机器人密度 单位：kg/m2.  质量=面积*密度，故机器人变大后质量也会变大
speed_forward_max = 0  # 最大前进速度 米/s
speed_backward_max = 0  # 最大后退速度 米/s
speed_rotate_max = 0  # 最大旋转速度  π/s
traction_max = 0  # 最大牵引力 N 机器人的加速/减速/防侧滑均由牵引力驱动
torque_max = 0  # 最大力矩 50 N*m  机器人的旋转由力矩驱动


class Robot:
    __slots__ = ['id', 'take_type', 'factor_time_value', 'factor_collision_value',
                 'rate_angular', 'rate_linear', 'direction', 'pox_x', 'pos_y']

    def __init__(self):
        pass

    def forward(self):
        pass

    def rotate(self):
        pass

    def buy(self):
        pass

    def sell(self):
        pass

    def destroy(self):
        pass


class Workbench:
    __slots__ = ['type', 'pos_x', 'pos_y', 'remaining_time', 'status_ingredient', 'status_box']

    def __init__(self, in_type=0, x=0.0, y=0.0, time=0, ingredient=0, box=0):
        self.type = in_type
        self.pos_x = x
        self.pos_y = y


def init_env():
    pass


def input_venue():
    venue = np.array([])
    while True:
        line = ""  # input()
        if "OK" == line:
            break
        elif "" == line:
            sys.exit(0)
    return venue


def output_result(result):
    pass


def process(venue):
    result = ""
    return result


def interact():
    venue = input_venue()
    result = process(venue)
    output_result(result)


init_env()
while True:
    interact()
