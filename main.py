#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from Role import *
from Move import movement
from Choose import choose_workbench, free_ride_bussiness


schedule = Schedule()


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
        log("robot recv job : " + str((job_1, job_2)))
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
            job_1, job_2 = free_ride_bussiness(robot.rid, bid, pid)
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
    while True:
        line = sys.stdin.readline().strip('\n')
        if "OK" == line:
            break
        elif "" == line:
            log("Total transaction times : " + str(transactions_times))
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
