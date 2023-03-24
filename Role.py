from Parameter import *
from Schedule import log
from collections import OrderedDict
from vector import Vector2, Line
import rvo_math as rvo_math

robots = []
workbenches = []
times = 0
# ----------------------------------------
# 每个平台的订单表
# ----------------------------------------
request_form = {0: {i: {} for i in range(1, 8)},  # 1:[bid_1:bid_11, bid_11}, bid_2]
                1: {i: {} for i in range(1, 8)}}  # 0 位置表示购买需求， 1 位置表示售卖需求

request_form_record = {}  # key 为 (bid, product_id), value 为(0->购买,1->售卖,2->已接,3->预定)
stop_rcv_order = False



class Robot:
    __slots__ = ['rid', 'take_type', 'factor_time_value', 'factor_collision_value', "bench_id", 'jobs',
                 'speed_angular', 'speed_linear', 'direction', 'pos', 'action_list', 'busy_to_idle_func', 'agent']

    def __init__(self, robot_id, x, y, func):
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
        self.busy_to_idle_func = func

        self.agent = self.Agent(x, y)

    def add_job(self, jobs):
        rcv_request((jobs[0][0], jobs[0][2]))
        rcv_request((jobs[1][0], jobs[1][2]))
        self.jobs.extend(jobs)

    def can_recv_job(self):
        return 1 <= len(self.jobs) <= 2 and self.take_type == 0   #1 <= len(self.jobs) <= 2

    def get_final_bench_1(self):
        return self.jobs[-1][0]

    def get_final_bench_0(self):
        return self.jobs[-2][0]

    def set_busy_to_idle_func(self, func):
        self.busy_to_idle_func = func

    def get_job(self):
        """
        获取当前工作
        :return: (x, y, z) x: 工作台id，y: 0买入1卖出，z: 产品id
        """
        if len(self.jobs) > 0:
            log("robot_id_job: " + str(self.rid) + "  job : " + str(self.jobs[0]))
            return self.jobs[0]

    def replace_job(self, jobs):
        if len(self.jobs) == 2:
            add_request(Request(jobs[0][0], jobs[0][2], jobs[0][1]))
            add_request(Request(jobs[1][0], jobs[1][2], jobs[1][1]))
            self.add_job(jobs)


    def insert_job(self, jobs, pos=0):
        if pos == 0:
            rcv_request((jobs[0][0], jobs[0][2]))
            rcv_request((jobs[1][0], jobs[1][2]))
            self.jobs.insert(0, jobs[1])
            self.jobs.insert(0, jobs[0])
        else:
            self.add_job(jobs)

    def finish_job(self):
        if len(self.jobs) > 0:
            job = self.jobs.pop(0)
            del_request((job[0], job[2]))
            if stop_rcv_order:
                self.jobs.clear()
            if not self.is_busy() and self.busy_to_idle_func is not None:
                self.busy_to_idle_func(self.rid)

    def set_pos(self, x, y):
        self.pos = (x, y)

    def get_pos(self):
        return self.pos

    def forward(self, line_speed):
        self.action_list["forward"] = [self.rid, line_speed]

    def rotate(self, angle_speed):
        self.action_list["rotate"] = [self.rid, angle_speed]

    def buy(self):
        if not stop_rcv_order:
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
        self.agent.update(self.speed_linear, self.pos, self.get_radius())

    def is_busy(self):
        return len(self.jobs) > 0

    def is_in_bench(self):
        if self.bench_id != -1:
            log("location: " + str(self.bench_id) + "  job : " + str(self.get_job()))
        if self.bench_id != -1 and self.is_busy() and self.get_job()[0] == self.bench_id:
            if self.get_job()[1] == 0 and workbenches[self.bench_id].has_product(self.get_job()[2]):
                self.buy()
            elif self.get_job()[1] == 1 and workbenches[self.bench_id].need_product(self.get_job()[2]):
                self.sell()

    def get_va(self):
        """
        :return: 机器人当前线加速度
        """
        return line_accelerated_speed_normal if self.take_type == 0 else line_accelerated_speed_hold

    def get_wa(self):
        """
        :return: 机器人当前角加速度
        """
        return angular_accelerated_speed_normal if self.take_type == 0 else angular_accelerated_speed_hold

    def get_v0(self):
        """
        :return: 线速度的初速度
        """
        return self.speed_linear

    def get_w0(self):
        """
        :return: 角速度的初速度
        """
        return self.speed_angular

    def get_weight(self):
        """
        :return: 获得当前机器人重量
        """
        return robot_weight_normal if self.take_type == 0 else robot_weight_hold

    def get_radius(self):
        """
        :return: 获得当前机器人重量
        """
        return robot_radius_normal if self.take_type == 0 else robot_radius_hold

    class Agent:
        def __init__(self, x, y):
            self.orca_lines_ = []
            self.time_horizon_obst_ = 300
            self.time_horizon_ = 30

            self.time_step_ = 0.02  # 20ms 间隔
            self.agent_neighbors_ = []  # dis, agent

            self.position_ = Vector2(x, y)
            self.velocity_ = Vector2()
            self.radius_ = 0.0
            self.goal_ = Vector2()

            self.max_speed_ = 6
            self.pref_velocity_ = Vector2()
            self.new_velocity_ = Vector2()

        def update(self, v, p, r):
            """
            Updates the two-dimensional position and two-dimensional velocity of this agent.
            """
            self.velocity_ = Vector2(v[0], v[1])
            self.position_ = Vector2(p[0], p[1])
            self.radius_ = r + 0.1

        def set_preferred_velocities(self, goal):
            """
            Set the preferred velocity to be a vector of unit magnitude (speed) in the direction of the goal.
            """
            self.goal_ = Vector2(goal[0], goal[1])
            goal_vector = self.goal_ - self.position_

            if rvo_math.abs_sq(goal_vector) > 0.2:
                goal_vector = rvo_math.normalize(goal_vector)  # 变成速度的单位向量

            self.pref_velocity_ = goal_vector

        def compute_new_velocity(self):
            """
            Computes the new velocity of this agent.
            """
            self.orca_lines_ = []
            # timeHorizonobst_是安全的时间单位，它乘以速度的值就可以理解为agent的避障探针，此数值越大
            # agent就会越早做出避障反应 // 此处就是取它的倒数（invertor)以方便后续的计算
            invTimeHorizonObst = 1.0 / self.time_horizon_obst_

            # 记录一下静态障碍增加了多少条障碍线
            numObstLines = len(self.orca_lines_)
            invTimeHorizon = 1.0 / self.time_horizon_

            # Create agent ORCA lines.
            for i in range(len(self.agent_neighbors_)):
                other = self.agent_neighbors_[i][1]
                # 相对距离，me-》you
                relativePosition = other.position_ - self.position_
                # 相对速度，you-》me
                relativeVelocity = self.velocity_ - other.velocity_
                # 距离的平方
                distSq = rvo_math.abs_sq(relativePosition)
                # 半径和
                combinedRadius = self.radius_ + other.radius_
                # 半径和的平方
                combinedRadiusSq = rvo_math.square(combinedRadius)

                line = Line()
                u = Vector2()
                # 尚未接触
                if distSq > combinedRadiusSq:
                    # No collision.
                    w = relativeVelocity - invTimeHorizon * relativePosition

                    # Vector from cutoff center to relative velocity.
                    wLengthSq = rvo_math.abs_sq(w)
                    dotProduct1 = w @ relativePosition  # 叉乘

                    if dotProduct1 < 0.0 and rvo_math.square(dotProduct1) > combinedRadiusSq * wLengthSq:
                        # Project on cut-off circle.
                        wLength = math.sqrt(wLengthSq)
                        unitW = w / wLength
                        # 方向为w顺时针转90°，相当于是当前速度相对于小圆的切线
                        line.direction = Vector2(unitW.y, -unitW.x)
                        # 此处combinedRadius * invTimeHorizon为小圆半径 // 减去wlLength就是把w放在小圆圆心时，w终点到小圆表面的距离
                        u = (combinedRadius * invTimeHorizon - wLength) * unitW
                    else:
                        # Project on legs.
                        leg = math.sqrt(distSq - combinedRadiusSq)

                        if rvo_math.det(relativePosition, w) > 0.0:
                            # Project on left leg.
                            line.direction = Vector2(relativePosition.x * leg - relativePosition.y * combinedRadius,
                                                     relativePosition.x * combinedRadius + relativePosition.y * leg) / distSq
                        else:
                            # Project on right leg.
                            line.direction = -Vector2(relativePosition.x * leg + relativePosition.y * combinedRadius,
                                                      -relativePosition.x * combinedRadius + relativePosition.y * leg) / distSq

                        dotProduct2 = relativeVelocity @ line.direction
                        u = dotProduct2 * line.direction - relativeVelocity
                # 即将接触
                else:
                    # Collision. Project on cut-off circle of time timeStep.
                    invTimeStep = 1.0 / self.time_step_

                    # Vector from cutoff center to relative velocity.跟前面的w一个意思，指小圆中心到当前速度的向量
                    w = relativeVelocity - invTimeStep * relativePosition

                    wLength = abs(w)
                    unitW = w / wLength

                    line.direction = Vector2(unitW.y, -unitW.x)
                    # 此处的u还是指到小圆圆周，类似上面的第一种情况, 此处u是当前速度到障碍体表面最近点的向量
                    u = (combinedRadius * invTimeStep - wLength) * unitW

                line.point = self.velocity_ + 0.5 * u
                self.orca_lines_.append(line)

            lineFail, self.new_velocity_ = self.linear_program2(self.orca_lines_, self.max_speed_, self.pref_velocity_,
                                                                False, self.new_velocity_)

            if lineFail < len(self.orca_lines_):
                self.new_velocity_ = self.linear_program3(self.orca_lines_, numObstLines, lineFail, self.max_speed_,
                                                          self.new_velocity_)
            return self.new_velocity_.x, self.new_velocity_.y

        def linear_program1(self, lines, lineNo, radius, optVelocity, directionOpt):
            """
            Solves a one-dimensional linear program on a specified line subject to linear constraints defined by lines and a circular constraint.

            Args:
                lines (list): Lines defining the linear constraints.
                lineNo (int): The specified line constraint.
                radius (float): The radius of the circular constraint.
                optVelocity (Vector2): The optimization velocity.
                directionOpt (bool): True if the direction should be optimized.

            Returns:
                bool: True if successful.
                Vector2: A reference to the result of the linear program.
            """
            dotProduct = lines[lineNo].point @ lines[lineNo].direction
            discriminant = rvo_math.square(dotProduct) + rvo_math.square(radius) - rvo_math.abs_sq(lines[lineNo].point)

            if discriminant < 0.0:
                # Max speed circle fully invalidates line lineNo.
                return False, None

            sqrtDiscriminant = math.sqrt(discriminant)
            tLeft = -dotProduct - sqrtDiscriminant
            tRight = -dotProduct + sqrtDiscriminant

            for i in range(lineNo):
                denominator = rvo_math.det(lines[lineNo].direction, lines[i].direction)
                numerator = rvo_math.det(lines[i].direction, lines[lineNo].point - lines[i].point)

                if abs(denominator) <= rvo_math.EPSILON:
                    # Lines lineNo and i are (almost) parallel.
                    if numerator < 0.0:
                        return False, None
                    continue

                t = numerator / denominator

                if denominator >= 0.0:
                    # Line i bounds line lineNo on the right.
                    tRight = min(tRight, t)
                else:
                    # Line i bounds line lineNo on the left.
                    tLeft = max(tLeft, t)

                if tLeft > tRight:
                    return False, None

            if directionOpt:
                # Optimize direction.
                if optVelocity @ lines[lineNo].direction > 0.0:
                    # Take right extreme.
                    result = lines[lineNo].point + tRight * lines[lineNo].direction
                else:
                    # Take left extreme.
                    result = lines[lineNo].point + tLeft * lines[lineNo].direction
            else:
                # Optimize closest point.
                t = lines[lineNo].direction @ (optVelocity - lines[lineNo].point)

                if t < tLeft:
                    result = lines[lineNo].point + tLeft * lines[lineNo].direction
                elif t > tRight:
                    result = lines[lineNo].point + tRight * lines[lineNo].direction
                else:
                    result = lines[lineNo].point + t * lines[lineNo].direction

            return True, result

        def linear_program2(self, lines, radius, optVelocity, directionOpt, result):
            """
            Solves a two-dimensional linear program subject to linear constraints defined by lines and a circular constraint.

            Args:
                lines (list): Lines defining the linear constraints.
                radius (float): The radius of the circular constraint.
                optVelocity (Vector2): The optimization velocity.
                directionOpt (bool): True if the direction should be optimized.
                result (Vector2): A reference to the result of the linear program.

            Returns:
                int: The number of the line it fails on, and the number of lines if successful.
                Vector2: A reference to the result of the linear program.
            """
            if directionOpt:
                # Optimize direction. Note that the optimization velocity is of unit length in this case.
                result = optVelocity * radius
            elif rvo_math.abs_sq(optVelocity) > rvo_math.square(radius):
                # Optimize closest point and outside circle.
                result = rvo_math.normalize(optVelocity) * radius
            else:
                # Optimize closest point and inside circle.
                result = optVelocity

            for i in range(len(lines)):
                if rvo_math.det(lines[i].direction, lines[i].point - result) > 0.0:
                    # Result does not satisfy constraint i. Compute new optimal result.
                    tempResult = result
                    success, result = self.linear_program1(lines, i, radius, optVelocity, directionOpt)
                    if not success:
                        result = tempResult
                        return i, result

            return len(lines), result

        def linear_program3(self, lines, numObstLines, beginLine, radius, result):
            """
            Solves a two-dimensional linear program subject to linear constraints defined by lines and a circular constraint.

            Args:
                lines (list): Lines defining the linear constraints.
                numObstLines (int): Count of obstacle lines.
                beginLine (int): The line on which the 2-d linear program failed.
                radius (float): The radius of the circular constraint.
                result (Vector2): A reference to the result of the linear program.

            Returns:
                Vector2: A reference to the result of the linear program.
            """
            distance = 0.0

            for i in range(beginLine, len(lines)):
                if rvo_math.det(lines[i].direction, lines[i].point - result) > distance:
                    # Result does not satisfy constraint of line i.
                    projLines = []

                    for ii in range(numObstLines):
                        projLines.append(lines[ii])

                    for j in range(numObstLines, i):
                        line = Line()
                        determinant = rvo_math.det(lines[i].direction, lines[j].direction)

                        if abs(determinant) <= rvo_math.EPSILON:
                            # Line i and line j are parallel.
                            if lines[i].direction @ lines[j].direction > 0.0:
                                # Line i and line j point in the same direction.
                                continue
                            else:
                                # Line i and line j point in opposite direction.
                                line.point = 0.5 * (lines[i].point + lines[j].point)
                        else:
                            line.point = lines[i].point + (rvo_math.det(lines[j].direction, lines[i].point - lines[
                                j].point) / determinant) * lines[i].direction

                        line.direction = rvo_math.normalize(lines[j].direction - lines[i].direction)
                        projLines.append(line)

                    tempResult = result
                    lineFail, result = self.linear_program2(projLines, radius,
                                                            Vector2(-lines[i].direction.y, lines[i].direction.x), True,
                                                            result)
                    if lineFail < len(projLines):
                        """
                        This should in principle not happen. The result is by definition already in the feasible region of this linear program. If it fails, it is due to small floating point error, and the current result is kept.
                        """
                        result = tempResult

                    distance = rvo_math.det(lines[i].direction, lines[i].point - result)
            return result


class Workbench:
    __slots__ = ['bid', 'pos', '_type', 'remaining_time', 'status_ingredient_value',
                 'product_status', 'work_time', 'ingredient_status', 'notifyRobot']

    def __init__(self, bid, _type, x, y, notifyRobot):
        self.bid = bid
        self._type = _type
        self.work_time = bench_work_time[self._type]
        self.remaining_time = self.work_time
        self.status_ingredient_value = -1
        self.ingredient_status = {}
        for product_id in bench_raw_map[self._type]:
            self.ingredient_status[product_id] = 0  # 原材料格状态 二进制位表描述，例如 48(110000)表示拥有物品 4 和 5。
        self.product_status = {}
        self.pos = (x, y)
        if self._type <= 7:
            self.product_status[self._type] = 0  # 产品格状态

        self.notifyRobot = notifyRobot

    def get_pos(self):
        return self.pos

    def update(self, arr):
        """
        更新平台当前信息
        :param arr: 输入数据
        """
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
                add_request(Request(self.bid, pid, 1))  # 需要购买

    # def query_short_supply(self):
    #     return self.status_ingredient.difference(bench_type_need[self._type])

    # 需要先买后卖
    def update_product(self, param):
        if self._type in self.product_status:  # 确实成产该产品
            self.product_status[self._type] = param
            if self.product_status[self._type] == 1 and not stop_rcv_order:
                add_request(Request(self.bid, self._type, 0))  # 可以买
                self.notifyRobot(self.bid, self._type)

    def has_product(self, pid):
        """
        该平台是否已经生产出产品
        :param pid: 产品id
        :return: bool
        """
        if pid in self.product_status and self.product_status[self._type] == 1:
            return True
        return False

    def get_remaining_time(self):
        return self.remaining_time

    def has_ingredient(self, pid):
        """
        该平台是否需要原材料
        :param pid: 产品id
        :return: bool
        """
        if pid in self.ingredient_status and self.ingredient_status[self._type] == 1:
            return True
        return False

    def need_product(self, pid):
        """
        平台需要这个产品，并且原材料格为空
        :param pid: 产品id
        :return: 是否需要
        """
        return pid in self.ingredient_status.keys() and self.ingredient_status[pid] == 0

    def relevant_product(self, pid):
        return pid in self.ingredient_status.keys() or pid in self.product_status.keys()

    def get_type(self):
        return self._type


product_demand_table = [0 for _ in range(8)]
def add_request(request):
    """
    发布订单
    :param request: 订单描述
    """
    if stop_rcv_order:
        return

    bid = request.key[0]
    pid = request.key[1]
    key = (bid, pid)
    if key not in request_form_record:
        req_idx = request.req_type
        # 需求表操作
        request_form[req_idx][pid][bid] = -1
        request_form_record[(bid, pid)] = req_idx
        product_demand_table[pid] += req_idx
    elif key in request_form_record and request_form_record[key] == 3:  # 预定订单变为已接订单
        request_form_record[key] = 2
    else:
        return
    # update_supply_and_demand(pid)


def get_relevant_order_buy(pid):
    """
    :param pid: 产品
    :return: 返回可以购买的平台
    """
    return list(request_form[0][pid].keys())

def get_relevant_order_sell(pid):
    """
    :param pid: 产品
    :return: 返回可以售卖的平台
    """
    return list(request_form[1][pid].keys())

def get_request_form(req_type):
    orders = []
    for pid in request_form[req_type]:
        for bid in request_form[req_type][pid]:
            orders.append((bid, pid))
    return orders


def has_request(key):
    """
    订单状态可接
    :param key: 订单关键词, (bid, pid)
    """
    if key in request_form_record and request_form_record[key] != 2 and request_form_record[key] != 3:
        return request_form_record[key]
    else:
        return -1


def update_request(seller, buyer, pid):
    """
    订单状态更新
    :param seller: 卖家id
    :param buyer: 买家id
    :param pid: 产品id
    """
    request_form[0][pid][seller] = buyer


def get_buyer(key):
    req_type = request_form_record[key]
    bid = key[0]
    pid = key[1]
    return request_form[req_type][pid][bid]


# def update_supply_and_demand(pid):
#     supplier = [sid for sid in request_form[0][pid]]
#     demander = [did for did in request_form[1][pid]]
#     if len(supplier) == 0 or len(demander) == 0:
#         return
#     weight = []
#     for sid in supplier:
#         weight_arr = []
#         for did in demander:
#             weight_arr.append(get_bench_bw_dis(sid, did))
#         weight.append(weight_arr)
#     km = KM(graph=np.array(weight))
#     km.Kuh_Munkras()
#     res = km.getResult()
#     log("km result : " + str(res))
#     for didx, sidx in enumerate(res):
#         if not np.isnan(sidx):
#             update_request(supplier[int(sidx)], demander[didx], pid)


def rcv_request(key):
    """
    对订单进行接单、预定操作
    :param key: 订单关键词, (bid, pid)
    """
    if stop_rcv_order:
        return
    bid = key[0]
    pid = key[1]
    if has_request(key) != -1:
        req_type = request_form_record[key]
        product_demand_table[pid] -= req_type
        if req_type == 1:  # 产品需求减少
            product_demand_table[pid] -= 1
        del request_form[req_type][pid][bid]
        # 此时暂时实际并没有放入2号数组
        request_form_record[key] = 2  # 已接订单列表，request_form没有2，3类型的字段，所以request，此处只为标识
    elif workbenches[bid].relevant_product(pid):
        request_form_record[key] = 3  # 预定


def del_request(key):
    """
    删除订单
    :param key: 订单描述, (bid, pid)
    """
    global times
    if key not in request_form_record:
        return
    bid = key[0]
    pid = key[1]
    if request_form_record[key] == 0 or request_form_record[key] == 1:
        req_type = request_form_record[key]
        del request_form[req_type][pid][bid]
    del request_form_record[key]
    times += 1


def del_all_request():
    """
    删除所有订单
    """
    global stop_rcv_order, product_demand_table
    for pid in range(1, 8):
        request_form[0][pid].clear()
        request_form[1][pid].clear()
    request_form_record.clear()
    product_demand_table = [0 for _ in range(8)]
    stop_rcv_order = True


class Request:
    __slots__ = ["key", "req_type", "relevant_bench"]

    def __init__(self, bid, pid, req_type):
        self.key = (bid, pid)
        self.req_type = req_type
        # self.price = price  # 负表示买，正表示卖
        business = []
        if req_type == 0:  # 需要买了之后再卖，寻找买家
            business = buyer[pid]
        elif req_type == 1:  # 寻找卖家
            business = workbenches_category[pid]  # [wb.bid for wb in workbenches_category[product_id]]
        self.relevant_bench = sorted(business, key=lambda oid: get_bench_bw_dis(bid, oid))
    # def __lt__(self, other):
    #     if self.price != other.price:
    #         return self.price > other.price  # 价格从大到小
    #     else:
    #         if len(self.relevant_bench) != len(other.relevant_bench):  # 相关平台按个数从大到小
    #             return len(self.relevant_bench) > len(other.relevant_bench)

    def __eq__(self, other):
        return self.key == other.key

    def __str__(self):
        return " ".join(str(item) for item in (self.key, self.req_type, self.relevant_bench))


from queue import Queue
class PriorityQueue:
    def __init__(self, n):
        self.queues = []
        for i in n:
            self.queues.append(Queue())

    def get(self):
        for q in self.queues:
            if not q.empty():
                return q.get()
        return None

    def put(self, req, priority):
        self.queues[priority].append(req)

    def del_all(self):
        self.queues.clear()
