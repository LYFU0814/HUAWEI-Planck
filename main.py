#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
import sys
import time

import numpy as np

from Role import *
from Schedule import *

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
    # TODO: request_form[0]
    request_form_0 = get_request_form(0)
    if (len(request_form_0)) != 0:
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
            # TODO: best_buy_price, best_buy_relevant_bench = request_form[0][MAX_KEY].price, request_form[0][MAX_KEY].relevant_bench
            best_buy_relevant_bench = sorted(get_relevant_order_sell(best_buy_pid),
                                             key=lambda oid: get_bench_bw_dis(best_buy_bid, oid))

        fin__buy_bid, fin__buy_pid = best_buy_bid, best_buy_pid
        ################################################
        # TODO: request_form[1]
        request_form_1 = get_request_form(1)
        if (len(request_form_1)) != 0:
            fin__sell_bid, fin__sell_pid = cacula_sell_score(best_buy_pid, best_buy_relevant_bench)
        else:
            while (1):
                # TODO: if len(request_form[1]) == 0:
                if len(request_form_1) == 0:
                    fin__sell_bid, fin__sell_pid = None, None
                else:
                    break
    elif (len(get_request_form(1))) == 0:
        # 双表空，最后几秒
        return None, None
    else:
        # 初始化
        fin__buy_bid, fin__buy_pid, fin__sell_bid, fin__sell_pid = init_choice(rid)

    bench_1, bench_2 = (fin__buy_bid, 0, fin__buy_pid), (fin__sell_bid, 1, fin__buy_pid)
    log("choose job result : " + str(bench_1) + "  " + str(bench_2))
    # return None, None
    return bench_1, bench_2


def profit_score(pid):  # buy_price是一个负值
    # p_score = (sell_price + buy_price) / (-1 * buy_price)
    p_score = get_product_profit(pid) / -product_buy_price[pid]
    p_score = p_score * 100
    return p_score


def cacula_product_score(rid):
    product = {}
    robot_position = robots[rid].get_pos()
    # TODO:request_form[0]
    request_form_0 = get_request_form(0)
    for order0_key in request_form_0:  # 计算每一个平台产出订单的得分，购买得分最高者
        p_score = 10000
        bid, pid = order0_key[0], order0_key[1]
        distance = distance_m(robot_position, workbenches[bid].get_pos())
        yaw = abs(get_clock_angle(robot_position, workbenches[bid].get_pos(), robots[rid].direction))
        p_score = p_score / (distance)  # - 10 * yaw# 距离机器人此时距离得分权重最大
        # if workbenches[bid].get_type() == 7: # 台子产品处理的优先级权重较小
        #     # temp
        #     if frame_id > 8000:
        #         p_score = p_score - 1000
        #     else:
        #         p_score = p_score + 1200
        # elif workbenches[bid].get_type() in (4, 5, 6) :
        #     p_score = p_score + 800
        # elif workbenches[bid].get_type() in (1, 2, 3):
        #     p_score = p_score + 400
        temp_score = 0
        request_form_1 = get_request_form(1)
        for order1_key in request_form_1:  # 平台需求量大的产品订单加分，无需求订单的产品订单直接变0分
            if order1_key[1] == pid:
                temp_score = temp_score + 200
        if (temp_score == 0):
            p_score = -10000
        else:
            p_score = p_score + temp_score

        product[order0_key] = p_score
    return product


def cacula_sell_score(best_buy_pid, best_buy_relevant_bench):
    acq_score = {}  # 保存收购request的得分，在最好的购买的基础上由差价+距离最近构成得分
    # TODO : for order_key in request_form[1].keys():  # order_key == request.key()
    request_form_1 = get_request_form(1)
    for order_key in request_form_1:  # order_key == request.key()
        score = 10000
        if (best_buy_pid == order_key[1]):
            # TODO: score = score + profit_score(best_buy_price, request_form[1][order_key].price)  # 利润得分
            score = score + profit_score(best_buy_pid)  # 利润得分
            for x in range(len(best_buy_relevant_bench)):  # 距离得分
                if (order_key[0] == best_buy_relevant_bench[x]):
                    # yaw = abs(get_workbench_angle(robot_position, workbenches[best_buy_bid].get_pos(), workbenches[best_buy_relevant_bench[x]].get_pos()))
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
        fin__sell_bid, fin__sell_pid = MAX_A_KEY[0], best_buy_pid
        return fin__sell_bid, fin__sell_pid


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

    # best_buy_relevant_bench = sorted(list(request_form[1][fin__buy_pid].keys()),
    #                                  key=lambda oid: get_bench_bw_dis(fin__buy_bid, oid))
    # if rid != 0:
    #     fin__sell_bid, fin__sell_pid = best_buy_relevant_bench[0], fin__buy_pid
    # else:
    #     fin__sell_bid, fin__sell_pid = best_buy_relevant_bench[1], fin__buy_pid
    request_form_1 = get_request_form(1)
    for order_key in request_form_1:
        if order_key[1] == fin__buy_pid:
            fin__sell_bid, fin__sell_pid = order_key[0], order_key[1]
            break

    return fin__buy_bid, fin__buy_pid, fin__sell_bid, fin__sell_pid


def by_way_bussiness(rid, new_bid, new_pid):  # 计算够不够顺风，够的话返回顺风job，不够的话返回none
    """
    :param rid: 机器人id
    :param new_bid: 产生新订单平台
    :param new_pid: 产生新产品
    :return: 工作
    """
    robot_position = robots[rid].get_pos()
    final_buy_bid, final_sell_bid = None, robots[rid].get_final_bench_1()
    if final_sell_bid == new_bid:
        best_buy_relevant_bench = sorted(get_relevant_order_sell(new_pid),
                                         key=lambda oid: get_bench_bw_dis(new_bid, oid))
        best_sell_bid, best_sell_pid = cacula_sell_score(new_pid, best_buy_relevant_bench)
        if best_sell_bid is None:
            return None, None
        best_sell_bid = best_buy_relevant_bench[0]
        bench_1, bench_2 = (new_bid, 0, new_pid), (best_sell_bid, 1, new_pid)
        log("choose by way bussiness job result : " + str(bench_1) + "  " + str(bench_2))
        return bench_1, bench_2
    else:
        return None, None


    # best_sell_bid, best_sell_pid = cacula_sell_score(new_pid, best_buy_relevant_bench)
    best_sell_bid = None
    if len(best_buy_relevant_bench) > 0:
        best_sell_bid = best_buy_relevant_bench[0]
    distance_3 = int(distance_o(robot_position, workbenches[new_bid].get_pos()))  # 3
    distance_1 = int(distance_o(robot_position, workbenches[final_buy_bid].get_pos()))  # 1

    # TODO:
    if best_sell_bid is None:
        return None, None

    distance_2 = get_bench_bw_dis(final_buy_bid, final_sell_bid)
    distance_4 = get_bench_bw_dis(new_bid, best_sell_bid)
    distance_5 = get_bench_bw_dis(best_sell_bid, final_buy_bid)

    profit_ori = get_product_profit(robots[rid].get_job()[2]) / (distance_1 + distance_2)
    profit_new = (get_product_profit(robots[rid].get_job()[2]) + get_product_profit(new_pid)) / (distance_3 + distance_4 + distance_5 + distance_2)

    if profit_ori < 0.95 * profit_new:
        temporary_buy_bid, temporary_buy_pid = new_bid, new_pid
        temporary_sell_bid, temporary_sell_pid = best_sell_bid, new_pid
    else:
        return None, None
    bench_1, bench_2 = (temporary_buy_bid, 0, temporary_buy_pid), (temporary_sell_bid, 1, temporary_buy_pid)
    log("choose job result : " + str(bench_1) + "  " + str(bench_2))
    # return None, None
    # return bench_1, bench_2
    return None, None


def movement(rid, bid):
    """
    计算运动速度
    :param rid: 机器人编号
    :param bid: 平台编号
    :return: 线速度，角速度（负号为顺时针， 正号为逆时针）
    """
    robot_pos, bench_pos = robots[rid].get_pos(), workbenches[bid].get_pos()
    v0, w0 = robots[rid].get_v0(), robots[rid].get_w0()
    start_time, stop_time = 3, 100
    line_dis = distance_o(robot_pos, bench_pos)
    direction = robots[rid].direction
    x_dis, y_dis = bench_pos[0] - robot_pos[0], bench_pos[1] - robot_pos[1]

    # 获取和目的节点的方向角
    angular = get_dst_angular(x_dis, y_dis)

    log("angular %.3f" % angular)
    log("direction %.3f" % direction)

    yaw = get_clock_angle(robot_pos, bench_pos, direction)

    # 接近目的地，入弯阶段
    if in_range(line_dis, 0, 0.86):  # TODO: 接近目的地时改变速度
        angular_speed = (-1 if yaw < 0 else 1) * 0.8 * math.pi
        forward_speed = 1.6
    # 重新瞄准目的地
    else:
        # 到达目的地，出弯阶段，目标角度大于90°
        if abs(yaw) > math.pi / 2.5:  # TODO: 目标角度
            angular_speed = (-1 if yaw < 0 else 1) * 1 * math.pi  # TODO: 越小，出完半径越大
            forward_speed = 1
        # 到达目的地，出弯阶段，目标角度小于90°
        elif abs(yaw) > math.pi / 10.5:  # TODO: 目标角度
            angular_speed = (-1 if yaw < 0 else 1) * 1 * math.pi  # TODO: 越小，出完半径越大
            forward_speed = 3.8
        # 角度稳定后
        elif in_range(abs(yaw), 0, math.pi / 10.5):  # TODO: 稳定角度
            forward_speed = 6
            angular_speed = 0
        # 出弯后到稳定前
        else:  # TODO: 不稳定-稳定，选择合适的转动半径
            angular_speed = yaw # (-1 if yaw < 0 else 1) * math.pi * 0.25  # yaw
            forward_speed = 3

    log("line_speed_before : " + str(robots[rid].get_v0()) + "  line_speed_after : " + str((forward_speed, angular_speed * 57.3)))


    # 撞墙检测，负优化，还需调参
    # if clash_wall_2(robot_pos, robots[rid].get_radius(), forward_speed, direction):
    #     log("撞墙")
    #     forward_speed = 0.5
        # angular_speed = (-1 if yaw < 0 else 1) * 1 * math.pi

    # 碰撞检测2，速度方向及机器人位置和半径
    # 不同碰撞情况需要处理（锐角、钝角）；
    obstract = []

    clash_list = [[-1, -10], [-1, -10], [-1, -10], [-1, -10]]
    clash_num = 0
    for robot_id in range(0, 4):
        if robot_id == rid:
            continue
        else:
            if forward_speed > 4.5:
                clash_radius = 6
            else:
                clash_radius = 3
            robots_dist = distance_o(robots[rid].get_pos(), robots[robot_id].get_pos())
            if robots_dist < clash_radius:
                clash_type = get_clash_type(rid, robot_id)
                adj_direction = robots[robot_id].direction
                robots_angular = direction - adj_direction
                if 0 < abs(robots_angular) < 0.45 * math.pi:  # 不考虑锐角碰撞,目前0.45最好
                    continue
                if clash_type != 1:
                    clash_num += 1
                obstract.append((robots_dist, robots[rid].agent, clash_type))
                clash_list[robot_id] = [clash_type, robots_angular, robots_dist]  # 碰撞类型,碰撞夹角,距离

    if clash_num == 1:
        for robot_id in range(0, 4):
            clash_type = clash_list[robot_id][0]
            robots_angular = clash_list[robot_id][1]
            if clash_type == 0:
                continue
            if clash_type == 3:  # 对撞
                robots_dist = clash_list[robot_id][2]
                forward_speed = 3
                angular_speed = w0 - 0.11 * math.pi if abs(robots_angular) < (math.pi * 0.65) else w0 - 0.15 * math.pi
                # angular_speed = w0 - 0.1 * math.pi if robots_dist > 1 else w0 - 0.15 * math.pi
                # angular_speed = w0 - 0.1 * math.pi
            elif clash_type == 2:  # 擦边碰撞
                forward_speed = 6
                angular_speed = w0 - 0.05 * math.pi
    elif clash_num > 1:
        # robots[rid].agent.set_preferred_velocities(workbenches[bid].get_pos())
        # robots[rid].agent.obstacle_neighbors_ = obstract
        # vx, vy = robots[rid].agent.compute_new_velocity()
        # forward_speed = np.dot((vx, vy), v0)
        # angular_speed = get_vector_angle((vx, 0), (vx, vy))
        # angular_speed = angular_speed + get_vector_angle((vx, 0), (vx, vy))
        # log("rvo2 : line_speed : " + str((vx, vy)) + "  line : " + str(
        #     robots[rid].get_v0()) + "  forward_speed : " + str(forward_speed))

        robots_angulars = []
        for robot_id in range(0, 4):
            robots_angular = clash_list[robot_id][1]
            robots_angulars.append(robots_angular)
            if len(robots_angulars) != 0:
                if (robots_angular * robots_angulars[0] < 0):
                    forward_speed = -2

    return start_time, stop_time, forward_speed, angular_speed


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


def movement1(rid, bid):
    """
    计算运动速度
    :param rid: 机器人编号
    :param bid: 平台编号
    :return: 线速度，角速度（负号为顺时针， 正号为逆时针）
    """
    robot_pos, bench_pos = robots[rid].get_pos(), workbenches[bid].get_pos()
    v0, w0 = robots[rid].get_v0(), robots[rid].get_w0()
    start_time, stop_time = 3, 100
    line_dis = distance_o(robot_pos, bench_pos)
    direction = robots[rid].direction
    x_dis, y_dis = bench_pos[0] - robot_pos[0], bench_pos[1] - robot_pos[1]

    # 获取和目的节点的方向角
    angular = get_dst_angular(x_dis, y_dis)

    log("angular %.3f" % angular)
    log("direction %.3f" % direction)

    yaw = get_clock_angle(robot_pos, bench_pos, direction)
    forward_speed = math.sqrt(v0[0] ** 2 + v0[1] ** 2)

    if abs(yaw) > math.pi / 9:
        angular_speed = (-1 if yaw < 0 else 1) * 1 * math.pi
        forward_speed = 4
    else:
        angular_speed = yaw  # (-1 if yaw < 0 else 1) * 0.2 * math.pi
        forward_speed = 6

    if line_dis < 1:
        angular_speed = (-1 if yaw < 0 else 1) * 1 * math.pi
        forward_speed = 1.5

    # 撞墙检测，负优化，还需调参
    # if clash_wall(robot_pos, angular):
    #     line_speed = 2

    # 碰撞检测
    clash_list = [[-1, -10], [-1, -10],[-1, -10],[-1, -10]]
    clash_num = 0
    # 不同碰撞情况需要处理（锐角、钝角）；
    for robot_id in range(0, 4):
        if robot_id == rid:
            continue
        else:
            if forward_speed > 4:
                clash_radius = 6
            else:
                clash_radius = 4
            robots_dist = distance_o(robots[rid].get_pos(), robots[robot_id].get_pos())
            if robots_dist < clash_radius:
                clash_type = get_clash_type(rid, robot_id)
                adj_direction = robots[robot_id].direction
                robots_angular = direction - adj_direction
                if 0 < abs(robots_angular) < 0.45 * math.pi:  # 不考虑锐角碰撞,目前0.45最好
                    continue
                clash_num += 1
                clash_list[robot_id] = [clash_type, robots_angular, robots_dist] # 碰撞类型,碰撞夹角,距离


    if clash_num == 1:
        for robot_id in range(0, 4):
            clash_type = clash_list[robot_id][0]
            robots_angular = clash_list[robot_id][1]
            if clash_type == 0:
                continue
            if clash_type == 3:  # 对撞
                robots_dist = clash_list[robot_id][2]
                forward_speed = 3
                angular_speed = w0 - 0.1 * math.pi if abs(robots_angular) < (math.pi * 0.65) else w0 - 0.15 * math.pi
                # angular_speed = w0 - 0.1 * math.pi if robots_dist > 1 else w0 - 0.15 * math.pi
                # angular_speed = w0 - 0.1 * math.pi
            elif clash_type == 2:  # 擦边碰撞
                forward_speed = 6
                angular_speed = w0 - 0.05 * math.pi
    elif clash_num > 1:
        robots_angulars = []
        for robot_id in range(0, 4):
            robots_angular = clash_list[robot_id][1]
            robots_angulars.append(robots_angular)
            if len(robots_angulars) != 0:
                if (robots_angular * robots_angulars[0] < 0):
                    forward_speed = -2
                    # angular_speed = w0 - 0.1 * math.pi
                # break



    return start_time, stop_time, forward_speed, angular_speed


def clash_wall_2(robot_pos, radius, forward_sp, dir):
    x, y = robot_pos[0], robot_pos[1]
    radius += 0.1
    if (x <= radius or x >= 50 - radius) and forward_sp != 0 and (math.pi >= abs(dir) >= (3 / 4) * math.pi or \
                                                                (1 / 4)* math.pi >= abs(dir) >= 0):
        return True
    if (y <= radius or y >= 50 - radius) and forward_sp != 0 and (3 / 4) * math.pi >= abs(dir) >= (1 / 4) * math.pi:
        return True
    return False


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
    direction_A, direction_B = robots[robotA].direction, robots[robotB].direction
    v0_A, v0_B = robots[robotA].get_v0(), robots[robotB].get_v0()
    v_A, v_B = [v0_A[0], v0_A[1]], [v0_B[0], v0_B[1]]
    c_A, c_B = robots[robotA].get_pos(), robots[robotB].get_pos()
    r_A, r_B = robots[robotA].get_radius(), robots[robotB].get_radius()
    v = [v_A[0] - v_B[0], v_A[1] - v_B[1]]
    c = [c_A[0] - c_B[0], c_A[1] - c_B[1]]
    r = r_A + r_B
    # 方程为 (v dot v) * t **2 + 2(v dot c) * t + (c dot c) - r**2 = 0
    a, b = np.dot(v, v), 2 * np.dot(v, c)
    delta = b ** 2 - 4 * a * (np.dot(c, c) - r ** 2)
    if delta > 0:
        log("====================碰撞======================")
        log("距离：%.2f" % distance_o(c_A, c_B))
        log("robotA位置：(%.2f,%.2f)" % (c_A[0], c_A[1]))
        log("robotB位置：(%.2f,%.2f)" % (c_B[0], c_B[1]))
        log("robotA朝向：%.2f" % direction_A)
        log("robotB朝向：%.2f" % direction_B)
        t1, t2 = (-b + math.sqrt(delta)) / (2 * a), (-b - math.sqrt(delta)) / (2 * a)
        if t1 < 0 and t2 < 0:
            return 1
        elif t1 < 0 or t2 < 0:
            return 2
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
            schedule.add_job(Job(frame_id + 100, robot.rid, None, 0, 0, stop_task))
            continue
        # 进行线速度和角速度计算, 并添加任务，计算第一个阶段
        start = time.time()
        start_time, stop_time, line_speed, angular_speed = movement(robot.rid, job_1[0])
        movement_time += time.time() - start
        schedule.add_job(Job(frame_id, robot.rid, job_1, angular_speed, line_speed, start_task))
        robot.add_job([job_1, job_2])  # 表示工作忙, 0 在bench_id1买x号产品，1 在bench_id2卖
    if choose_workbench_time != 0:
        log("choose_workbench()结束耗时：" + str(choose_workbench_time))
    log("movement()结束耗时：" + str(movement_time))


def busy_to_idle_func(rid):
    schedule.add_job(Job(frame_id, rid, None, math.pi / 4, 3, start_task))


def notify_product_update(bid, pid):
    for robot in robots:
        if robot.can_recv_job():
            # log(str(robot.rid) + "  " + str(robot.get_final_bench_1()[0]) + "  " + str(bid) + "  " + str(pid))
            job_1, job_2 = by_way_bussiness(robot.rid, bid, pid)
            if job_1 is None or job_2 is None:
                continue
            robot.insert_job([job_1, job_2], pos=1)
            log("robot " + str(robot.rid) + " add new job, current job is : " + str(robot.jobs))


def init_env():
    graph = input_data()
    log("初始化：", True)
    bw = graph_width / len(graph[0]) / 2.0
    bench_id = 0
    robot_id = 0
    for x, line in enumerate(graph):
        for y, ch in enumerate(line):
            if ch.isdigit():
                w = Workbench(bench_id, int(ch), 0.5 * y + bw, 49.75 - 0.5 * x, notify_product_update)
                workbenches_category[int(ch)].append(bench_id)
                workbenches.append(w)
                bench_id += 1
            elif "A" == ch:
                robots.append(Robot(robot_id, 0.5 * y + bw, 49.75 - 0.5 * x, busy_to_idle_func))
                robot_id += 1
    for bi, bench in enumerate(bench_raw_map):
        for pi in bench:
            buyer[pi].extend(workbenches_category[bi])

    for bid_1 in range(len(workbenches)):
        bench_1 = workbenches[bid_1]
        for bid_2 in range(bid_1 + 1, len(workbenches)):
            bench_2 = workbenches[bid_2]
            bench_bw_dis[(bench_1.bid, bench_2.bid)] = distance_o(bench_1.get_pos(), bench_2.get_pos())
    schedule.add_job(Job((duration * 60 - 7) * fps, 74, 74, 0, 0, clear_task))
    finish()


def input_data():
    venue = []
    global transactions_times
    while True:
        line = sys.stdin.readline().strip('\n')
        if "OK" == line:
            break
        elif "" == line:
            log("Total transaction times : " + str(times))
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
    s = "平台需要售卖"
    for pid in request_form[0]:
        s += "\npid: " + str(pid) + " bid: "
        for bid in request_form[0][pid]:
            s += str(bid) + " "
    s += "\n平台需要购买"
    for pid in request_form[1]:
        s += "\npid: " + str(pid) + " bid: "
        for bid in request_form[1][pid]:
            s += str(bid) + " "
    log(s)
    log(request_form)
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
