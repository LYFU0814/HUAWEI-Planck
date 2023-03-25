from Role import *


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
    log("去往目的地：" + str(bid) + ", 距离为：" + str(line_dis))
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
    # obstract = []

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
                # obstract.append((robots_dist, robots[rid].agent, clash_type))
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

