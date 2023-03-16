#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import numpy as np
import sys
import re
from Schedule import *
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

    if (len(request_form[0])) != 0:
        product = cacula_product_score(rid)  # 记录了每一条产品request的得分
        # MAX_P = product[0]
        MAX_P = -10000
        MAX_KEY = None  # 记录是第几条订单

        for key in product.keys():
            if product[key] > MAX_P:
                MAX_P = product[key]
                MAX_KEY = key
        if (MAX_P == -10000):
            return None, None
        else:
            best_buy_bid, best_buy_pid = MAX_KEY[0], MAX_KEY[1]
            best_buy_price, best_buy_relevant_bench = request_form[0][MAX_KEY].price, request_form[0][
                MAX_KEY].relevant_bench

        fin__buy_bid, fin__buy_pid = best_buy_bid, best_buy_pid
        ################################################
        if (len(request_form[1])) != 0:
            acq_score = {}  # 保存收购request的得分，在最好的购买的基础上由差价+距离最近构成得分
            for order_key in request_form[1].keys():  # order_key == request.key()
                score = 1000
                if (best_buy_pid == order_key[1]):
                    score = score + profit_score(best_buy_price, request_form[1][order_key].price)  # 利润得分
                    for x in range(len(best_buy_relevant_bench)):  # 距离得分
                        if (order_key[0] == best_buy_relevant_bench[x]):
                            score = score - 20 * x
                    if (workbenches[order_key[0]].get_type() == 4 or workbenches[
                        order_key[0]].get_type() == 5 or workbenches[
                        order_key[0]].get_type() == 6):
                        score = score + 100
                else:
                    score = -10000
                acq_score[order_key] = score
            MAX_A = -10000
            MAX_A_KEY = None

            for key in acq_score.keys():
                if acq_score[key] > MAX_A:
                    MAX_A = acq_score[key]
                    MAX_A_KEY = key
            if(MAX_A == -10000 ):
                return None, None
            else:
                fin__sell_bid, fin__sell_pid = MAX_A_KEY[0], fin__buy_pid

        else:
            while (1):
                if len(request_form[1]) == 0:
                    fin__sell_bid, fin__sell_pid = None, None
                else:
                    break
    elif(len(request_form[1])) == 0:
        #双表空，最后几秒
        return None,None
    else:
        #初始化
        fin__buy_bid, fin__buy_pid, fin__sell_bid, fin__sell_pid = init_choice(rid)

    bench_1, bench_2 = (fin__buy_bid, 0, fin__buy_pid), (fin__sell_bid, 1, fin__buy_pid)
    log("choose job result : " + str(bench_1) + "  " + str(bench_2))
    return bench_1, bench_2


def profit_score(buy_price, sell_price):  # buy_price是一个负值
    p_score = (sell_price + buy_price) / (-1 * buy_price)
    p_score = p_score * 100
    return p_score


def cacula_product_score(rid):
    product = {}
    robot_position = robots[rid].get_pos()
    for order0_key in request_form[0].keys():  # 计算每一个平台产出订单的得分，购买得分最高者
        p_score = 0
        bid, pid = order0_key[0], order0_key[1]
        distance = distance_m(robot_position, workbenches[bid].get_pos())
        p_score = p_score + 200 - distance  # 距离机器人此时距离得分权重最大
        if workbenches[bid].get_type() == 7: # 台子产品处理的优先级权重较小
            # temp
            if frame_id > 8600:
                p_score = p_score - 100
            else:
                p_score = p_score + 120
        elif workbenches[bid].get_type() in (4, 5, 6):
            p_score = p_score + 50
        elif workbenches[bid].get_type() in (1, 2, 3):
            p_score = p_score + 40
        temp_score = 0
        for order1_key in request_form[1].keys():  # 平台需求量大的产品订单加分，无需求订单的产品订单直接变0分
            if order1_key[1] == pid:
                temp_score = temp_score + 100
        if (temp_score == 0):
            p_score = -10000
        else:
            p_score = p_score + temp_score

        product[order0_key] = p_score
    return product


def init_choice(rid):
    closest = 20000
    ori_bid = 0
    robot_position = robots[rid].get_pos()
    if (rid != 3):  # 为了使机器人分开，各去各的，0号机器人先随机去
        for bid in (workbenches_category[rid + 1]):
            distance = int(distance_m(robot_position, workbenches[bid].get_pos()))
            if (distance < closest):
                closest = distance
                ori_bid = bid
            else:
                closest = closest
                ori_bid = ori_bid

        fin__buy_bid, fin__buy_pid = ori_bid, workbenches[ori_bid].get_type()
    else:
        if robots[1].get_job()[0] != workbenches_category[1][0]:
            fin__buy_bid, fin__buy_pid = workbenches_category[1][0], 1
        else:
            fin__buy_bid, fin__buy_pid = workbenches_category[1][1], 1

    for order_key in request_form[1].keys():
        if order_key[1] == fin__buy_pid:
            fin__sell_bid, fin__sell_pid = order_key[0], order_key[1]
            break

    return fin__buy_bid, fin__buy_pid, fin__sell_bid, fin__sell_pid


def movement(rid, bid):
    robot_pos, bench_pos = robots[rid].get_pos(), workbenches[bid].get_pos()
    v0, w0 = robots[rid].get_v0(), robots[rid].get_w0()
    start_time, stop_time = 3, 100
    line_dst = distance_o(robot_pos, bench_pos)
    direction = robots[rid].direction
    x_dis, y_dis = bench_pos[0] - robot_pos[0], bench_pos[1] - robot_pos[1]

    if x_dis == 0 and y_dis == 0:
        angular = 0
    elif x_dis == 0 and y_dis > 0:
        angular = math.pi / 2
    elif x_dis == 0 and y_dis < 0:
        angular = -math.pi / 2
    elif x_dis > 0 and y_dis >= 0:
        angular = math.atan(y_dis / x_dis)
    elif x_dis < 0 and y_dis >= 0:
        angular = math.pi + math.atan(y_dis / x_dis)
    elif x_dis < 0 and y_dis <= 0:
        angular = -math.pi + math.atan(y_dis / x_dis)
    elif x_dis > 0 and y_dis <= 0:
        angular = math.atan(y_dis / x_dis)
    # else:
    #     angular = math.atan(y_dis / x_dis)

    log("angular %.3f" % angular)
    log("direction %.3f" % direction)
    flag = 1
    if 0 <= angular <= math.pi and 0 <= direction <= math.pi:
        if angular > direction:
            flag = 1
        else:
            flag = -1
    elif -math.pi <= angular <= 0 and -math.pi <= direction <= 0:
        if angular > direction:
            flag = 1
        else:
            flag = -1
    elif 0 <= angular <= math.pi and -math.pi <= direction <= 0:
        if angular - direction < math.pi:
            flag = 1
        else:
            flag = -1
    elif -math.pi <= angular <= 0 and 0 <= direction <= math.pi:
        if direction - angular < math.pi:
            flag = -1
        else:
            flag = 1

    line_speed = 6
    angular_speed = flag * math.pi
    if line_dst < 1 or abs(angular - direction) > math.pi / 2:
        if v0 > 1:
            line_speed = -0.5
        else:
            line_speed = 1

    return start_time, stop_time, line_speed, angular_speed

def movement1(rid, bid):
    robot_pos, bench_pos = robots[rid].get_pos(), workbenches[bid].get_pos()
    v0, w0 = robots[rid].get_v0(), robots[rid].get_w0()
    start_time, stop_time = 3, 100
    line_dis = distance_o(robot_pos, bench_pos)
    direction = robots[rid].direction
    x_dis, y_dis = bench_pos[0] - robot_pos[0], bench_pos[1] - robot_pos[1]

    # 获取和目的节点的方向角
    if x_dis == 0 and y_dis == 0:
        angular = 0
    elif x_dis == 0 and y_dis > 0:
        angular = math.pi / 2
    elif x_dis == 0 and y_dis < 0:
        angular = -math.pi / 2
    elif x_dis > 0 and y_dis >= 0:
        angular = math.atan(y_dis / x_dis)
    elif x_dis < 0 and y_dis >= 0:
        angular = math.pi + math.atan(y_dis / x_dis)
    elif x_dis < 0 and y_dis <= 0:
        angular = -math.pi + math.atan(y_dis / x_dis)
    elif x_dis > 0 and y_dis <= 0:
        angular = math.atan(y_dis / x_dis)
    # else:
    #     angular = math.atan(y_dis / x_dis)

    log("angular %.3f" % angular)
    log("direction %.3f" % direction)
    flag = 1

    # 当前方向和方向角的关系
    if 0 <= angular <= math.pi and 0 <= direction <= math.pi:
        if angular > direction:
            flag = 1
        else:
            flag = -1
    elif -math.pi <= angular <= 0 and -math.pi <= direction <= 0:
        if angular > direction:
            flag = 1
        else:
            flag = -1
    elif 0 <= angular <= math.pi and -math.pi <= direction <= 0:
        if angular - direction < math.pi:
            flag = 1
        else:
            flag = -1
    elif -math.pi <= angular <= 0 and 0 <= direction <= math.pi:
        if direction - angular < math.pi:
            flag = -1
        else:
            flag = 1

    line_speed = 6

    if line_dis < 2:
        angular_speed = flag * 1 * math.pi
    else:
        angular_speed = flag * 0.5 * math.pi

    # 减速
    if line_dis < 1 or abs(angular - direction) > 0.5 * math.pi:
        if v0 > 1:
            line_speed = 0
        else:
            line_speed = 1

    # 碰撞检测
    for robot_id in range(0, 4):
        if robot_id == rid:
            continue
        else:
            adj_robot_pos = robots[robot_id].get_pos()
            adj_direction = robots[robot_id].direction
            robots_angular = abs(direction - adj_direction)
            robots_dis = distance_o(robot_pos, adj_robot_pos)
            if robots_dis < 2 and robots_angular > 0.75 * math.pi and robots_angular < 1.25 * math.pi:
                if robots[robot_id].speed_linear[0] > 0 and (
                        robots[rid].take_type == 0 and robots[robot_id].take_type == 1):
                    line_speed = -2
                else:
                    line_speed = 4
                angular_speed = - flag * math.pi

    return start_time, stop_time, line_speed, angular_speed


def start_task(job):
    if job is None:
        return
    if job.speed_linear != robots[job.key[0]].speed_linear[0]:
        robots[job.key[0]].forward(job.speed_linear)
    if job.speed_angular != robots[job.key[0]].speed_angular:
        robots[job.key[0]].rotate(job.speed_angular)


def stop_task(job):
    if robots[job.key[0]].speed_linear != 0:
        robots[job.key[0]].forward(0)
    if robots[job.key[0]].speed_angular != 0:
        robots[job.key[0]].rotate(0)


def clear_task(job):
    del_all_request()


def process():
    # log(collision_detection([robot.get_pos() for robot in robots]))
    choose_workbench_time = 0
    movement_time = 0
    for robot in robots:
        # if robot.rid != 0:
        #     continue
        if robot.is_busy():
            '''修正过程'''
            bid = robot.get_job()[0]
            start = time.time()
            start_time, stop_time, line_speed, angular_speed = movement(robot.rid, bid)
            movement_time += time.time() - start
            schedule.add_job(Job(frame_id, robot.rid, robot.get_job(), angular_speed, line_speed, start_task))
            continue
        # 选择平台，总共两个阶段
        start = time.time()
        job_1, job_2 = choose_workbench(robot.rid)
        choose_workbench_time += time.time() - start
        if job_1 is None or job_2 is None:
            schedule.add_job(Job(frame_id, robot.rid, None, 0, 0, stop_task))
            continue
        # 进行线速度和角速度计算, 并添加任务，计算第一个阶段
        start = time.time()
        start_time, stop_time, line_speed, angular_speed = movement(robot.rid, job_1[0])
        movement_time += time.time() - start
        schedule.add_job(Job(frame_id, robot.rid, job_1, angular_speed, line_speed, start_task))
        robot.set_job([job_1, job_2])  # 表示工作忙, 0 在bench_id1买x号产品，1 在bench_id2卖
    if choose_workbench_time != 0:
        log("choose_workbench()结束耗时：" + str(choose_workbench_time))
    log("movement()结束耗时：" + str(movement_time))


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
                workbenches_category[int(ch)].append(bench_id)
                workbenches.append(w)
                bench_id += 1
            elif "A" == ch:
                robots.append(Robot(robot_id, 0.5 * y + bw, 49.75 - 0.5 * x))
                robot_id += 1
    for bi, bench in enumerate(bench_type_need):
        for pi in bench:
            buyer[pi].extend(workbenches_category[bi])

    for bid_1 in range(len(workbenches)):
        bench_1 = workbenches[bid_1]
        for bid_2 in range(bid_1 + 1, len(workbenches)):
            bench_2 = workbenches[bid_2]
            bench_bw_dis[(bench_1.bid, bench_2.bid)] = distance_o(bench_1.get_pos(), bench_2.get_pos())
    schedule.add_job(Job((duration * 60 - 5) * fps, 74, 74, 0, 0, clear_task))
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
    start = time.time()
    update_venue(data)
    log("update_venue()结束耗时：" + str(time.time() - start))
    start = time.time()
    log("第%d帧：" % frame_id)
    s = "平台需要售卖\n"
    for request in request_form[0]:
        s += str(request) + "\n"
    s += "平台需要购买\n"
    for request in request_form[1]:
        s += str(request) + "\n"
    log(s)
    # log("category_type_workbench :" + str(
    #     [[wb.bid for wb in workbenches_category[i]] for i in range(len(workbenches_category))]))
    log("interval结束耗时：" + str(time.time() - start))
    start = time.time()
    process()
    log("process结束耗时：" + str(time.time() - start))
    schedule.running(frame_id)
    output_result()
    total = time.time() - start
    log("结束耗时：" + str(total))
    if total > 0.0149:
        log("timeout")


init_env()
while True:
    interact()
# ----------------------------------------
