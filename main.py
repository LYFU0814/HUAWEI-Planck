#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import numpy as np
import sys
import re
from Schedule import *
from Parameter import *
from Role import *


product_from = {}
frame_id = -1


def collision_detection(positions):
    distances = {}
    for x in range(len(positions)):
        for y in range(x + 1, len(positions)):
            distances[(x, y)] = distance_m(positions[x], positions[y])
    return distances


table_request = []
schedule = Schedule()
bench_bw_dis = {}  # {(bid1, bid2): 距离}


def start_task(job):
    if job.speed_linear != robots[job.key[0]].speed_linear[0]:
        robots[job.key[0]].forward(job.speed_linear)
    if job.speed_angular != robots[job.key[0]].speed_angular:
        robots[job.key[0]].rotate(job.speed_angular)


def stop_task(job):
    # TODO
    # 判断是否到达平台

    # 判断购入或者卖出
    # robots[job.key[0]].sell()
    # robots[job.key[0]].buy()

    # 是否进行下次任务
    if robots[job.key[0]].speed_linear != 0:
        robots[job.key[0]].forward(0)
    if robots[job.key[0]].speed_angular != 0:
        robots[job.key[0]].rotate(0)

    # robots[job.id[0]].del_job()
    # schedule.cancel_job(job)


def choose_workbench(rid):
    """
    根据request_form来计算下一个移动目的地,元组形式(x, y, z)
    :return: 两个目的地，先去第一个再去第二个，x表示目的平台id，y表示买卖，买，用0表示，卖用1表示, 第三位表示产品id
    request_form[0]//购买表,即产出表["key", "price", "relevant_bench"]
    request_form[1]//售卖表，即收购表
    """
    fin__buy_bid = 0
    fin__buy_pid = 0
    fin__sell_bid = 0
    fin__sell_pid = 0
    robot_position = robots[rid].get_pos()
    if (len(request_form[0])) != 0:
        product = cacula_product_score(request_form)  # 记录了每一条产品request的得分
        MAX_P = product[0]
        j = 0  # 记录是第几条订单
        for i in range(len(product)):
            if (product[i] > MAX_P):
                MAX_P = product[i]
                j = j + 1
            else:
                MAX_P = MAX_P
                j = j
        best_buy_bid, best_buy_pid = request_form[0][j].key[0], request_form[0][j].key[1]
        best_buy_price, best_buy_relevant_bench = request_form[0][j].price, request_form[0][j].relevant_bench
        fin__buy_bid, fin__buy_pid = best_buy_bid, best_buy_pid
        ################################################
        acq_score = []  # 保存收购request的得分，在最好的购买的基础上由差价+距离最近构成得分
        for k in range(len(request_form[1])):
            score = 0
            if (best_buy_pid == request_form[1][k].key[1]):
                score = score + profit_score(best_buy_price, request_form[1][k].price)
            else:
                score = score
            for bid in range(len(best_buy_relevant_bench)):
                if (request_form[0][j].key[0] == best_buy_relevant_bench[bid]):
                    score = score - 10 * bid
            acq_score.append(score)
        MAX_a = acq_score[0]
        num = 0
        for m in range(len(acq_score)):
            if (acq_score[m] > MAX_a):
                MAX_a = acq_score[m]
                num = num + 1
            else:
                MAX_a = MAX_a
                num = num
        best_sell_bid, best_sell_pid = request_form[1][num].key[0], request_form[1][num].key[1]
        fin__sell_bid, fin__sell_pid = best_sell_bid, best_sell_pid
        log("###############" + str(fin__buy_bid) + str(fin__buy_pid) + "#####################")
        log("###############" + str(fin__sell_bid) + str(fin__sell_pid) + "#####################")
    #########################################################

    else:
        closest = 20000
        ori_bid = 0
        # for cid in range(1, 4):  # 去距离最近的1-3台子等着
        if (rid != 0):  # 为了使机器人分开，各去各的，0号机器人先随机去
            for bench in (workbenches_category[rid]):
                distance = int(distance_m(robot_position, bench.get_pos()))
                if (distance < closest):
                    closest = distance
                    ori_bid = bench.bid
                else:
                    closest = closest
                    ori_bid = ori_bid
            fin__buy_bid, fin__buy_pid = ori_bid, workbenches[ori_bid].get_type()
        else:
            fin__buy_bid, fin__buy_pid = workbenches_category[3][0].bid, 3

        for n in range(len(request_form[1])):
            if (request_form[1][n].key[1] == fin__buy_pid):
                fin__sell_bid, fin__sell_pid = request_form[1][n].key[0], request_form[1][n].key[1]
                break;
        log("###############" + str(fin__buy_bid) + str(fin__buy_pid) + "#####################")
        log("###############" + str((fin__sell_bid)) + str(fin__sell_pid) + "#####################")
    log("####################################")

    return (fin__buy_bid, 0, fin__buy_pid), (fin__sell_bid, 1, fin__sell_pid)


def profit_score(buy_price, sell_price):  # buy_price是一个负值
    p_score = (sell_price + buy_price) / (-1 * buy_price)
    p_score = p_score * 100
    return p_score


def cacula_product_score(request_form):
    product = []
    for i in range(len(request_form[0])):  # 计算每一个平台产出订单的得分，购买得分最高者
        p_score = 0
        bid, pid = request_form[0][i].key[0], request_form[0][i].key[1]
        if (workbenches[bid].get_type() == 4 or workbenches[bid].get_type() == 5 or workbenches[bid].get_type() == 6 or
                workbenches[bid].get_type() == 7):
            p_score = p_score + 100
        elif (workbenches[bid].get_type() == 1 or workbenches[bid].get_type() == 2 or workbenches[bid].get_type() == 3):
            p_score = p_score + 50
        else:
            log("啊？")
        product.append(p_score)
    return product


def movement(rid, bid):
    v0, w0 = robots[rid].get_v0(), robots[rid].get_w0()
    start_time, stop_time = 3, 100
    robot_pos, bench_pos = robots[rid].get_pos(), workbenches[bid].get_pos()
    line_accelerated_speed = line_accelerated_speed_hold if robots[rid].is_busy() else line_accelerated_speed_normal
    angular_accelerated_speed = angular_accelerated_speed_hold if robots[rid].is_busy() else angular_accelerated_speed_normal
    line_dst = distance_o(robot_pos, bench_pos)
    direction = robots[rid].direction
    x_dis, y_dis = bench_pos[0] - robot_pos[0], bench_pos[1] - robot_pos[1]
    # log("line_speed_cur = %.3f--%.3f angular_speed_cur =  %.3f" % (line_speed_cur[0], line_speed_cur[1], angular_speed_cur))
    # log("x_dis = %.3f  y_dis = %.3f /n" %(x_dis, y_dis))
    if x_dis == 0:
        angular_dst = math.pi
    else:
        angular_dst = (1 if x_dis > 0 else -1) * (math.atan(y_dis / x_dis) - direction)
    log("angle_dst = %.3f" % (angular_dst))
    line_speed = math.sqrt(v0 ** 2 + 2 * line_accelerated_speed * line_dst)
    angular_speed = (-1 if angular_dst < 0 else 1) * math.sqrt(w0 ** 2 + angular_accelerated_speed * abs(angular_dst))
    log("line_speed_cur = %.3f angular_speed_cur =  %.3f" % (line_speed, angular_speed))
    return start_time, stop_time, min(line_speed, speed_forward_max), min(angular_speed, math.pi)


def process():
    # log(collision_detection([robot.get_pos() for robot in robots]))
    for robot in robots:
        # if robot.rid != 0:
        #     continue
        if robot.is_busy():
            '''修正过程'''
            bid = robot.get_job()[0]
            start_time, stop_time, line_speed, angular_speed = movement(robot.rid, bid)
            schedule.add_job(Job(frame_id, robot.rid, bid, angular_speed, line_speed, start_task))
            continue
        # 选择平台，总共两个阶段
        job_1, job_2 = choose_workbench(robot.rid)
        # 进行线速度和角速度计算, 并添加任务，计算第一个阶段
        start_time, stop_time, line_speed, angular_speed = movement(robot.rid, job_1[0])
        schedule.add_job(Job(frame_id, robot.rid, job_1, angular_speed, line_speed, start_task))
        robot.set_job([job_1, job_2])  # 表示工作忙, 0 在bench_id1买x号产品，1 在bench_id2卖


def init_env():
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

    for bid_1 in range(len(workbenches)):
        bench_1 = workbenches[bid_1]
        for bid_2 in range(bid_1 + 1, len(workbenches)):
            bench_2 = workbenches[bid_2]
            bench_bw_dis[(bench_1.bid, bench_2.bid)] = distance_m(bench_1.get_pos(), bench_2.get_pos())
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


# ----------------------------------------
# 交互主体逻辑
# ----------------------------------------
def interact():
    data = input_data()
    update_venue(data)
    log("第%d帧：" % frame_id)
    log("平台需要售卖")
    for request in request_form[0]:
        log(request)
    log("平台需要购买")
    for request in request_form[1]:
        log(request)
    process()
    schedule.running(frame_id)
    output_result()


init_env()
while True:
    interact()
# ----------------------------------------
