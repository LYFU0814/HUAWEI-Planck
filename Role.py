from Parameter import *
from Schedule import log


robots = []
workbenches = []
workbenches_category = [[] for _ in range(10)]  # i类型工作台 = [b_1, b_2,...]
buyer = [[] for _ in range(8)]  # 需要i号产品的工作台列表

# ----------------------------------------
# 每个平台的订单表
# ----------------------------------------
request_form = [[], []]  # 0 位置表示购买需求， 1 位置表示售卖需求
request_form_record = {}  # key 为 (bid, product_id), value 为(0->购买,1->售卖,2->已接,3->预定)


class Robot:
    __slots__ = ['rid', 'take_type', 'factor_time_value', 'factor_collision_value', "bench_id", 'jobs',
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
            log("robot_id_job: " + str(self.rid) + "  job : " + str(self.jobs[0]))
            return self.jobs[0]

    def finish_job(self):
        if len(self.jobs) > 0:
            job = self.jobs.pop(0)
            del_request(Request(job[0], job[2], 0))

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
        return robot_weight_normal if self.take_type == 0 else robot_weight_hold


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
        self.pos = (x, y)
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
                add_request(Request(self.bid, pid, product_sell_price[pid]))  # 需要购买

    # def query_short_supply(self):
    #     return self.status_ingredient.difference(bench_type_need[self._type])

    # 需要先买后卖
    def update_product(self, param):
        self.product_status[self._type] = param
        if self.product_status[self._type] == 1:
            add_request(Request(self.bid, self._type, -product_buy_price[self._type]))

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

    def relevant_product(self, pid):
        return pid in self.ingredient_status.keys() or pid in self.product_status.keys()

    def get_type(self):
        return self._type


def add_request(request):
    """
    发布订单
    :param request: 订单描述
    """
    if request.key not in request_form_record:
        if request.price < 0:
            request_form[0].append(request)
            request_form_record[request.key] = 0
        else:
            request_form[1].append(request)
            request_form_record[request.key] = 1
    elif request.key in request_form_record and request_form_record[request.key] == 3:
        request_form_record[request.key] = 2


def rcv_request(request):
    """
    对订单进行接单、预定操作
    :param request: 订单描述
    """
    if has_request(request):
        need_type = request_form_record[request.key]
        log(request)
        request_form[need_type].remove(request)
        # 此时暂时实际并没有放入2号数组
        request_form_record[request.key] = 2
    elif workbenches[request.key[0]].relevant_product(request.key[1]):
        request_form_record[request.key] = 3  # 预定


def has_request(request):
    """
    判断是否已经发布过请求
    :param request: 订单描述
    """
    return request.key in request_form_record and request_form_record[request.key] != 2


def del_request(request):
    """
    删除订单
    :param request: 订单描述
    """
    if request.key not in request_form_record:
        return
    del request_form_record[request.key]


class Request:
    __slots__ = ["key", "price", "relevant_bench"]

    def __init__(self, bid, product_id, price):
        self.key = (bid, product_id)
        self.price = price  # 负表示买，正表示卖
        if price < 0:  # 需要买了之后再卖，寻找买家
            self.relevant_bench = buyer[product_id]
        else:  # 寻找卖家
            self.relevant_bench = [wb.bid for wb in workbenches_category[product_id]]
        sorted(self.relevant_bench, key=lambda oid: distance_m(workbenches[oid].get_pos(), workbenches[bid].get_pos()))

    def __lt__(self, other):
        if self.price != other.price:
            return self.price > other.price  # 价格从大到小
        else:
            if len(self.relevant_bench) != len(other.relevant_bench):  # 相关平台按个数从大到小
                return len(self.relevant_bench) > len(other.relevant_bench)

    def __eq__(self, other):
        return self.key == other.key and self.price == other.price and self.relevant_bench == other.relevant_bench

    def __str__(self):
        return " ".join(str(item) for item in (self.key, self.price, self.relevant_bench))