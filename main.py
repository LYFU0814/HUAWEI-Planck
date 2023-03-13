#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import numpy as np
import sys
import re
from Schedule import *
from Parameter import *


product_from = {}
frame_id = -1


class Robot:
    __slots__ = ['rid', 'take_type', 'factor_time_value', 'factor_collision_value', "bench_id", 'old_pos', 'jobs',
                 'speed_angular', 'speed_linear', 'direction', 'pos', 'action_list']

    def __init__(self, robot_id, x, y):
        self.rid = robot_id
        self.pos = (x, y)
        self.direction = math.pi  # 弧度，范围[-π,π]。
        self.take_type = 0  # 0 没有拿
        self.factor_time_value = 0.0  # 时间价值系数 携带物品时为[0.8, 1]的浮点数，不携带物品时为0
        self.factor_collision_value = 0.0  # 碰撞价值系数 携带物品时为[0.8, 1]的浮点数，不携带物品时为0。
        self.speed_linear = (0.0, 0.0)  # x, y 方向线速度 设置前进速度，单位为米/秒。 - 正数表示前进 - 负数表示后退。
        self.speed_angular = 0.0  # 设置旋转速度，单位为弧度/秒。 - 负数表示顺时针旋转 - 正数表示逆时针旋转。
        self.action_list = {}  # key
        self.bench_id = -1
        self.jobs = []

    def set_job(self, jobs):
        self.jobs.extend(jobs)

    def get_job(self):
        """
        获取当前工作
        :return: (x, y, z) x: 工作台id，y: 0买入1卖出，z: 产品id
        """
        if len(self.jobs) > 0:
            return self.jobs[0]

    def finish_job(self):
        if len(self.jobs) > 0:
            self.jobs.pop(0)

    def set_pos(self, x, y):
        self.pos = (x, y)

    def get_pos(self):
        return self.pos

    def forward(self, line_speed):
        self.action_list["forward"] = [self.rid, line_speed]

    def rotate(self, angle_speed):
        self.action_list["rotate"] = [self.rid, angle_speed]

    def buy(self):
        self.action_list["buy"] = [self.rid]
        self.finish_job()

    def sell(self):
        self.action_list["sell"] = [self.rid]
        self.finish_job()

    def destroy(self):
        self.action_list["destroy"] = [self.rid]
        self.finish_job()

    def update(self, data):
        self.bench_id = int(data[0])
        self.take_type = int(data[1])
        self.factor_time_value = data[2]
        self.factor_collision_value = data[3]
        self.speed_angular = data[4]
        self.speed_linear = (data[5], data[6])
        self.direction = data[7]
        self.set_pos(data[8], data[9])
        self.is_in_bench()

    def is_busy(self):
        return len(self.jobs) > 0

    def is_in_bench(self):
        if self.bench_id != -1:
            log("location: " + str(self.bench_id) + "  job : " + str(self.get_job()))
        if self.bench_id != -1 and self.get_job()[0] == self.bench_id:
            if self.get_job()[1] == 0 and workbenches[self.bench_id].has_product(self.get_job()[2]):
                self.buy()
            elif self.get_job()[1] == 1 and workbenches[self.bench_id].need_product(self.get_job()[2]):
                self.sell()

    def get_v0(self):
        """
        :return: 线速度的初速度
        """
        return self.speed_linear[0]

    def get_w0(self):
        """
        :return: 角速度的初速度
        """
        return self.speed_angular

    def get_weight(self):
        """
        :return: 获得当前机器人重量
        """
        if self.take_type == 0:
            return robot_weight_normal
        else:
            return robot_weight_hold


class Workbench:
    __slots__ = ['bid', 'pos', '_type', 'remaining_time', 'status_ingredient_value',
                 'product_status', 'work_time', 'ingredient_status']

    def __init__(self, bid, _type, x, y):
        self.bid = bid
        self._type = _type
        self.work_time = bench_work_time[self._type]
        self.remaining_time = self.work_time
        self.status_ingredient_value = -1
        self.ingredient_status = {}
        for product_id in bench_type_need[self._type]:
            self.ingredient_status[product_id] = 0  # 原材料格状态 二进制位表描述，例如 48(110000)表示拥有物品 4 和 5。
        self.product_status = {}
        self.pos = (0, 0)
        if self._type <= 7:
            self.product_status[self._type] = 0  # 产品格状态

    def get_pos(self):
        return self.pos

    def update(self, arr):
        self.pos = (arr[1], arr[2])
        self.remaining_time = arr[3]
        self.update_ingredient(int(arr[4]))
        self.update_product(int(arr[5]))

    def update_ingredient(self, param):
        if self.status_ingredient_value == param:
            return
        for pid in self.ingredient_status.keys():
            if (1 << pid) & param != 0:  # 拥有原材料
                self.ingredient_status[pid] = 1
            else:
                self.ingredient_status[pid] = 0
                add_request(Request(self.bid, pid, product_buy_price[pid]))  # 需要购买

    # def query_short_supply(self):
    #     return self.status_ingredient.difference(bench_type_need[self._type])

    # 需要先买后卖
    def update_product(self, param):
        self.product_status[self._type] = param
        if self.product_status[self._type] == 1:
            add_request(Request(self.bid, self._type, -product_sell_price[self._type]))

    def has_product(self, pid):
        if pid in self.product_status and self.product_status[self._type] == 1:
            return True
        return False

    def need_product(self, pid):
        """
        平台需要这个产品，并且原材料格为空
        :param pid: 产品id
        :return: 是否需要
        """
        return pid in self.ingredient_status.keys() and self.ingredient_status[pid] == 0


def collision_detection(positions):
    distances = {}
    for x in range(len(positions)):
        for y in range(x + 1, len(positions)):
            distances[(x, y)] = distance_m(positions[x], positions[y])
    return distances


robots = []
workbenches = []
workbenches_category = [[] for _ in range(10)]  # i类型工作台 = [b_1, b_2,...]
buyer = [[] for _ in range(8)]  # 需要i号产品的工作台列表
table_request = []
schedule = Schedule()

# ----------------------------------------
# 每个平台的订单表
# ----------------------------------------
request_form = [[], []]  # 0 位置表示购买需求， 1 位置表示售卖需求
request_form_record = {}  # key 为 (bid, product_id)


def distance_m(pos_a, pos_b):  # 计算曼哈顿距离
    return abs(pos_a[0] - pos_b[0]) + abs(pos_a[1] - pos_b[1])


def distance_o(pos_a, pos_b):  # 计算欧式距离
    return math.sqrt(abs(pos_a[0] - pos_b[0]) ** 2 + abs(pos_a[1] - pos_b[1]) ** 2)


class Request:
    __slots__ = ["key", "price", "relevant_bench"]

    def __init__(self, bid, product_id, price):
        self.key = (bid, product_id)
        self.price = price  # 负表示买，正表示卖
        if price < 0:  # 需要买了之后再卖，寻找卖家
            self.relevant_bench = [wb.bid for wb in workbenches_category[product_id]]
        else:  # 需要卖出去，寻找买家
            self.relevant_bench = buyer[product_id]
        sorted(self.relevant_bench, key=lambda oid: distance_m(workbenches[oid].get_pos(), workbenches[bid].get_pos()))

    def __lt__(self, other):
        if self.price != other.price:
            return self.price > other.price  # 价格从大到小
        else:
            if len(self.relevant_bench) != len(other.relevant_bench):  # 相关平台按个数从大到小
                return len(self.relevant_bench) > len(other.relevant_bench)

    def __str__(self):
        return " ".join(str(item) for item in (self.key, self.price, self.relevant_bench))


def add_request(request):
    if request.key in request_form_record:
        return
    if request.price < 0:
        request_form[0].append(request)
        request_form_record[request.key] = 0
    else:
        request_form[1].append(request)
        request_form_record[request.key] = 1


def del_request(request):
    if request.key not in request_form_record:
        return
    _type = request_form_record[request.key]
    request_form[_type].remove(request)
    del request_form_record[request.key]


def init_env():
    global robots
    graph = input_data()
    log("初始化：", True)
    bw = graph_width / len(graph[0]) / 2.0
    bench_id = 0
    robot_id = 0
    for x, line in enumerate(graph):
        for y, ch in enumerate(line):
            if ch.isdigit():
                w = Workbench(bench_id, int(ch), 0.5 * y + bw, 49.75 - 0.5 * x)
                workbenches_category[int(ch)].append(w)
                workbenches.append(w)
                bench_id += 1
            elif "A" == ch:
                robots.append(Robot(robot_id, 0.5 * y + bw, 49.75 - 0.5 * x))
                robot_id += 1
    for bi, bench in enumerate(bench_type_need):
        for pi in bench:
            buyer[pi].extend([b.bid for b in workbenches_category[bi]])
    finish()


def input_data():
    venue = []
    while True:
        line = sys.stdin.readline().strip('\n')
        if "OK" == line:
            break
        elif "" == line:
            sys.exit(0)
        venue.append(line)
    return venue


def start_task(job):
    if job.speed_linear != robots[job.key[0]].speed_linear[0]:
        robots[job.key[0]].forward(job.speed_linear)
    if job.speed_angular != robots[job.key[0]].speed_angular:
        robots[job.key[0]].rotate(job.speed_angular)


def stop_task(job):
    # TODO

    # 是否进行下次任务
    if robots[job.key[0]].speed_linear != 0:
        robots[job.key[0]].forward(0)
    if robots[job.key[0]].speed_angular != 0:
        robots[job.key[0]].rotate(0)

    # robots[job.id[0]].del_job()
    # schedule.cancel_job(job)


def update_venue(data):
    global money, frame_id
    parser_arr = list(map(int, data[0].split(" ")))
    frame_id, money = parser_arr[0], parser_arr[1]
    bench_cnt = int(data[1])
    line_cnt = 2
    for index in range(bench_cnt):
        parser_arr = list(map(float, data[line_cnt].split(" ")))
        workbenches[index].update(parser_arr)
        line_cnt += 1
    for index in range(robot_size):
        parser_arr = list(map(float, data[line_cnt].split(" ")))
        robots[index].update(parser_arr)
        line_cnt += 1


def output_result():
    log("传递指令开始---")
    sys.stdout.write('%d\n' % frame_id)
    log('%d' % frame_id)
    for robot in robots:
        for action, value in robot.action_list.items():
            sys.stdout.write('%s %s\n' % (action, ' '.join(str(v) for v in value)))
            log('%s %s' % (action, ' '.join(str(v) for v in value)))
        robot.action_list.clear()
    finish()
    log("传递指令结束---")


def finish():
    sys.stdout.write('OK\n')
    sys.stdout.flush()


def choose_workbench():
    """
    根据request_form来计算下一个移动目的地,元组形式(x, y, z)
    :return: 两个目的地，先去第一个再去第二个，x表示目的平台id，y表示买卖，买，用0表示，卖用1表示, 第三位表示产品id
    """
    return (13, 0, 1), (20, 1, 1)


def movement(rid, bid):
    robot_pos, bench_pos = robots[rid].get_pos(), workbenches[bid].get_pos()
    v0, w0 = robots[rid].get_v0(), robots[rid].get_w0()
    start_time, stop_time = 3, 100
    line_speed, angular_speed = 4, math.pi
    return start_time, stop_time, line_speed, angular_speed


def movement2(rid, bid):
    robot_pos, bench_pos = robots[rid].get_pos(), workbenches[bid].get_pos()
    v0, w0 = robots[rid].get_v0(), robots[rid].get_w0()
    start_time, stop_time = 3, 100
    line_speed, angular_speed = 5.8, math.pi / 7
    return start_time, stop_time, line_speed, angular_speed


def process():
    log(collision_detection([robot.get_pos() for robot in robots]))
    for robot in robots:
        if robot.is_busy():
            bid = robot.get_job()[0]
            start_time, stop_time, line_speed, angular_speed = movement(robot.rid, bid) if len(robot.jobs) == 2 else movement2(robot.rid, bid)
            schedule.add_job(Job(frame_id, robot.rid, bid, angular_speed, line_speed, start_task))
            continue
        # 选择平台，总共两个阶段
        job_1, job_2 = choose_workbench()
        # 进行线速度和角速度计算, 并添加任务，计算第一个阶段
        start_time, stop_time, line_speed, angular_speed = movement(robot.rid, job_1[0])
        schedule.add_job(Job(frame_id, robot.rid, job_1, angular_speed, line_speed, start_task))
        robot.set_job([job_1, job_2])  # 表示工作忙, 0 在bench_id1买x号产品，1 在bench_id2卖


# ----------------------------------------
# 交互主体逻辑
# ----------------------------------------
def interact():
    data = input_data()
    stat_time = time.time()
    update_venue(data)
    log("第%d帧：" % frame_id)
    log("购买")
    for request in request_form[0]:
        log(request)
    log("售卖")
    for request in request_form[1]:
        log(request)
    process()
    schedule.running(frame_id)
    output_result()
    stop_time = time.time()
    if stop_time - stat_time > 0.0149:
        log("timeout")


init_env()
while True:
    interact()
# ----------------------------------------
