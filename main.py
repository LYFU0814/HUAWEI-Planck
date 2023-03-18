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
    robot_position = robots[rid].get_pos()
    if (len(request_form[0])) != 0:
        product = cacula_product_score(rid)  # 记录了每一条产品request的得分
        # MAX_P = product[0]
        log("#########" + str(product) + "########")
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
                score = 10000
                if (best_buy_pid == order_key[1]):
                    score = score + profit_score(best_buy_price, request_form[1][order_key].price)  # 利润得分
                    for x in range(len(best_buy_relevant_bench)):  # 距离得分
                        if (order_key[0] == best_buy_relevant_bench[x]):
                            yaw = abs(get_workbench_angle(robot_position, workbenches[best_buy_bid].get_pos(),
                                                          workbenches[best_buy_relevant_bench[x]].get_pos()))
                            # score = score - 20 * x #- yaw
                            score = score / (20 * x + 1)

                    if workbenches[order_key[0]].get_type() in (4, 5, 6):
                        score = score + 100
                else:
                    score = -10000
                acq_score[order_key] = score
            MAX_A = -10000
            MAX_A_KEY = None
            log("#########" + str(acq_score) + "########")
            for key in acq_score.keys():
                if acq_score[key] > MAX_A:
                    MAX_A = acq_score[key]
                    MAX_A_KEY = key
            if (MAX_A == -10000):
                return None, None
            else:
                fin__sell_bid, fin__sell_pid = MAX_A_KEY[0], fin__buy_pid

        else:
            while (1):
                if len(request_form[1]) == 0:
                    fin__sell_bid, fin__sell_pid = None, None
                else:
                    break
    elif (len(request_form[1])) == 0:
        # 双表空，最后几秒
        return None, None
    else:
        # 初始化
        fin__buy_bid, fin__buy_pid, fin__sell_bid, fin__sell_pid = init_choice(rid)

    bench_1, bench_2 = (fin__buy_bid, 0, fin__buy_pid), (fin__sell_bid, 1, fin__buy_pid)
    log("choose job result : " + str(bench_1) + "  " + str(bench_2))
    # return None, None
    return bench_1, bench_2


def profit_score(buy_price, sell_price):  # buy_price是一个负值
    p_score = (sell_price + buy_price) / (-1 * buy_price)
    p_score = p_score * 100
    return p_score


def cacula_product_score(rid):
    product = {}
    robot_position = robots[rid].get_pos()
    # 对订单打分
    for order0_key in request_form[0].keys():  # 计算每一个平台产出订单的得分，购买得分最高者
        # 初始分
        p_score = 10000
        bid, pid = order0_key[0], order0_key[1]
        distance = distance_m(robot_position, workbenches[bid].get_pos())
        yaw = abs(get_clock_angle(robot_position, workbenches[bid].get_pos(), robots[rid].direction))
        # 对距离打分
        p_score = p_score / (distance)  # - 10 * yaw# 距离机器人此时距离得分权重最大
        # 对产品类型打分
        if workbenches[bid].get_type() == 7:  # 台子产品处理的优先级权重较小
            # temp
            if frame_id > 8000:
                p_score = p_score - 1000
            else:
                p_score = p_score + 1200
        elif workbenches[bid].get_type() in (4, 5, 6):
            p_score = p_score + 800
        elif workbenches[bid].get_type() in (1, 2, 3):
            p_score = p_score + 400
        # 对订单需求打分 平台需求量大的产品订单加分，无需求订单的产品订单直接变0分
        temp_score = product_demand_table[pid] * 200
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
    """
    计算运动速度
    :param rid: 机器人编号
    :param bid: 平台编号
    :return: 线速度，角速度（负号为顺时针， 正号为逆时针）
    """
    robot_pos, bench_pos = robots[rid].get_pos(), workbenches[bid].get_pos()
    v0, w0 = robots[rid].get_v0()[0], robots[rid].get_w0()
    start_time, stop_time = 3, 100
    line_dis = distance_o(robot_pos, bench_pos)
    direction = robots[rid].direction
    x_dis, y_dis = bench_pos[0] - robot_pos[0], bench_pos[1] - robot_pos[1]

    # 获取和目的节点的方向角
    angular = get_dst_angular(x_dis, y_dis)

    log("angular %.3f" % angular)
    log("direction %.3f" % direction)

    yaw = get_clock_angle(robot_pos, bench_pos, direction)

    if abs(yaw) > math.pi / 9:
        angular_speed = (-1 if yaw < 0 else 1) * 1 * math.pi
        line_speed = 4
    else:
        angular_speed = yaw # (-1 if yaw < 0 else 1) * 0.2 * math.pi
        line_speed = 6

    if line_dis < 1:
        angular_speed = (-1 if yaw < 0 else 1) * 1 * math.pi
        line_speed = 2

    # 撞墙检测，负优化，还需调参
    # if clash_wall(robot_pos, angular):
    #     line_speed = 2

    # 碰撞检测1，半径+视野
    # for robot_id in range(0, 4):
    #     if robot_id == rid:
    #         continue
    #     else:
    #         adj_robot_pos = robots[robot_id].get_pos()
    #         adj_direction = robots[robot_id].direction
    #         robots_angular = abs(direction - adj_direction)
    #         robots_dis = distance_o(robot_pos, adj_robot_pos)
    #         if robots_dis < 2 and robots_angular > 0.75 * math.pi and robots_angular < 1.25 * math.pi:
    #             line_speed = 4
    #             angular_speed = w0 - 0.1 * math.pi

    # 碰撞检测2，速度方向及机器人位置和半径
    # 不同碰撞情况需要处理（锐角、钝角）；
    for robot_id in range(0, 4):
        if robot_id == rid:
            continue
        else:
            if v0 > 4:
                clash_radius = 6
            else:
                clash_radius = 4
            if distance_o(robots[rid].get_pos(), robots[robot_id].get_pos()) < clash_radius:
                clash_type = get_clash_type(rid, robot_id)
                adj_direction = robots[robot_id].direction
                robots_angular = abs(direction - adj_direction)
                if 0 < robots_angular < 0.45 * math.pi: #不考虑锐角碰撞,目前0.45最好
                    continue
                if clash_type == 3: # 对撞
                    log("对撞")
                    log("机器人减速前速度：%.2f" % line_speed)
                    log("机器人减速前角度：%.2f" % angular_speed)
                    line_speed = 3
                    angular_speed = w0 - 0.1 * math.pi
                    log("==================碰撞处理====================")
                    log("机器人减速后速度：%.2f" % line_speed)
                    log("机器人减速后角度：%.2f" % angular_speed)
                elif clash_type == 2: # 擦边碰撞
                    log("擦边碰撞")
                    log("机器人减速前速度：%.2f" % line_speed)
                    log("机器人减速前角度：%.2f" % angular_speed)
                    line_speed = 5
                    angular_speed = w0 - 0.05 * math.pi
                    log("机器人减速后速度：%.2f" % line_speed)
                    log("机器人减速后角度：%.2f" % angular_speed)

    return start_time, stop_time, line_speed, angular_speed

def get_dst_angular(x_dis, y_dis):
    """
        获取和目的节点的方向角
        :param x_dis: x方向距离
        :param y_dis: y方向距离
        :return: 方向角
        """
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
    return angular

def get_clock_angle(pos_1, pos_2, dir):
    """
    计算最小偏向角
    :param pos_1: 机器人位置
    :param pos_2: 平台位置
    :param dir: 机器人当前方向
    :return: 最小偏向角，单位弧度，负表示顺时针，正表示逆时针
    """
    v1, v2 = [np.cos(dir), np.sin(dir)], [pos_2[0] - pos_1[0], pos_2[1] - pos_1[1]]
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

def clash_wall(robot_pos, angular):
    if robot_pos[0] < 2 and abs(angular) < (1 / 4) * math.pi:
        return True
    if robot_pos[0] > 48 and abs(angular) > (3 / 4) * math.pi:
        return True
    if robot_pos[1] < 2 and (abs(angular) < (1 / 4) * math.pi or abs(angular) > (3 / 4) * math.pi):
        return True
    if robot_pos[1] > 48 and (1 / 4) * math.pi < abs(angular) < (3 / 4) * math.pi:
        return True
    return False

def get_clash_type(robotA, robotB):
    direction_A,  direction_B = robots[robotA].direction, robots[robotB].direction
    v0_A, v0_B = robots[robotA].get_v0(), robots[robotB].get_v0()
    v_A, v_B = [v0_A[0], v0_A[1]], [v0_B[0], v0_B[1]]
    c_A, c_B = robots[robotA].get_pos(), robots[robotB].get_pos()
    r_A, r_B = 0.45 if robots[robotA].take_type == 0 else 0.53, 0.45 if robots[robotB].take_type == 0 else 0.53
    v = [v_A[0] - v_B[0], v_A[1] - v_B[1]]
    c = [c_A[0] - c_B[0], c_A[1] - c_B[1]]
    r = r_A + r_B
    # 方程为 (v dot v) * t **2 + 2(v dot c) * t + (c dot c) - r**2 = 0
    delta =(2 * np.dot(v, c)) ** 2 - 4 * (np.dot(v, v)) * (np.dot(c, c) - r ** 2)
    if delta > 0:
        log("====================碰撞======================")
        log("距离：%.2f" % distance_o(c_A, c_B))
        log("robotA位置：(%.2f,%.2f)" % (c_A[0], c_A[1]))
        log("robotB位置：(%.2f,%.2f)" % (c_B[0], c_B[1]))
        log("robotA朝向：%.2f" % direction_A)
        log("robotB朝向：%.2f" % direction_B)
        return 3  # 对撞
    elif delta == 0:
        return 2  # 擦边撞
    else:
        return 1  # 不碰撞





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
            # schedule.add_job(Job(frame_id, robot.rid, None, math.pi, 3, stop_task))
            schedule.add_job(Job(frame_id + 100, robot.rid, None, 0, 0, stop_task))
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


def busy_to_idle_func(rid):
    schedule.add_job(Job(frame_id, rid, None, math.pi / 4, 3, start_task))


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
                robots.append(Robot(robot_id, 0.5 * y + bw, 49.75 - 0.5 * x, busy_to_idle_func))
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
