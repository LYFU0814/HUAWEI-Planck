from Role import *

bench_score = [0, 40, 40, 40, 60, 60, 60, 80, 100, 10]
dis_score = 100
profit_score = 100
demand_score = 100

score = 0.3 * dis_score + 0.2 * profit_score + 0.2 * demand_score + 0.3 * bench_score[0]
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
    request_form_1 = get_request_form(1)
    if (len(request_form_0) != 0 and len(request_form_1) != 0 ) :
        product = cacula_product_score(rid)  # 记录了每一条产品request的得分
        log("$$$$$$$$$" + str(product) + "########")
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
            best_buy_relevant_bench = sorted(get_relevant_order_sell(best_buy_pid),
                                             key=lambda oid: get_bench_bw_dis(best_buy_bid, oid))

        fin__buy_bid, fin__buy_pid = best_buy_bid, best_buy_pid
        ################################################################################################
        fin__sell_bid, fin__sell_pid = cacula_sell_score(best_buy_pid, best_buy_relevant_bench)



    elif( len(request_form_0) != 0 and len(request_form_1) == 0):
        return None, None
    elif (len(request_form_0) == 0 and len(request_form_1) != 0):
        # 初始化
        fin__buy_bid, fin__buy_pid, fin__sell_bid, fin__sell_pid = init_choice(rid)
        if(fin__sell_bid == None or fin__sell_pid == None):
            return None, None
    elif(len(request_form_0) == 0 and len(request_form_1) == 0):

        # 双表空，最后几秒
        return None, None
    bench_1, bench_2 = (fin__buy_bid, 0, fin__buy_pid), (fin__sell_bid, 1, fin__sell_pid)
    log("choose job result : " + str(bench_1) + "  " + str(bench_2))
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
        p_score = 1
        bid, pid = order0_key[0], order0_key[1]
        distance = distance_m(robot_position, workbenches[bid].get_pos())
        #yaw = abs(get_clock_angle(robot_position, workbenches[bid].get_pos(), robots[rid].direction))
        p_score = (1000 * p_score * get_product_profit(pid)) / (distance)  #这部分分值大约是几十分到100+，得大一点
        #if(get_category_size(7) != 0):
        # if workbenches[bid].get_type() == 7:  # 台子产品处理的优先级权重较小
        #     p_score = p_score + 1200 * (get_category_size(8) + get_category_size(9))
        # elif workbenches[bid].get_type() in (4, 5, 6):
        #     p_score = p_score + 800 * get_category_size(7)
        # elif workbenches[bid].get_type() == 1:
        #     p_score = p_score + 400 * (get_category_size(4) + get_category_size(5))
        # elif workbenches[bid].get_type() == 2:
        #     p_score = p_score + 400 * (get_category_size(4) + get_category_size(6))
        # elif workbenches[bid].get_type() == 3:
        #     p_score = p_score + 400 * (get_category_size(5) + get_category_size(6))




        temp_score = 0
        request_form_1 = get_request_form(1)
        for order1_key in request_form_1:  # 平台需求量大的产品订单加分，无需求订单的产品订单直接变0分
            if order1_key[1] == pid:
                temp_score = temp_score + 200#这个在台子多的时候可达几千分
        # temp_score = product_demand_table[pid] * 200
        log("$$$$$$$$$" + str(temp_score) + "########")
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
        score = 1
        if (best_buy_pid == order_key[1]):
            # TODO: score = score + profit_score(best_buy_price, request_form[1][order_key].price)  # 利润得分
            score = score * profit_score(best_buy_pid)  # 利润得分3000-29000
            for x in range(len(best_buy_relevant_bench)):  # 距离得分1,20,40
                if (order_key[0] == best_buy_relevant_bench[x]):
                    score = score / (20 * x + 1)
#优先卖给哪个台子，稀缺台子（只针对4,5,6占比小于1/10）优先级最高，直接给10000，
            # 3缺1台子给8000，3缺2给6000，3缺3给4000，2缺1给,000,2缺2给2000,9号台一份不给
            if ((get_category_size(workbenches[order_key[0]].get_type()) / len(workbenches)) < 0.06):  # 台子数量小于1/15，说明是稀缺台子
                if(workbenches[order_key[0]].get_type() in (4,5,6,7)):
                    score = score + 30000
            elif(len(workbenches[order_key[0]].get_requirement()[0]) == 3 * len(workbenches[order_key[0]].get_requirement()[1])):#3缺一
                score = score + 30000
            elif (len(workbenches[order_key[0]].get_requirement()[0]) ==1.5 * (len(
                    workbenches[order_key[0]].get_requirement()[1]))):  # 3缺2
                score = score + 26000
            elif (len(workbenches[order_key[0]].get_requirement()[0]) == 2 * len(
                    workbenches[order_key[0]].get_requirement()[1])):  # 2缺1
                score = score + 26000
            elif (len(workbenches[order_key[0]].get_requirement()[0]) == len(
                    workbenches[order_key[0]].get_requirement()[1])):  # 3缺3和2缺2
                score = score + 5000
            if (workbenches[order_key[0]].get_type() == 9):
                score = score - 5000
            # if workbenches[order_key[0]].get_type() == 4:
            #     if((get_category_size(4)/len(workbenches)) < 0.06 ):#台子数量小于1/15，说明是稀缺台子
            #         score = score + 10000
            #
            #
            # elif workbenches[order_key[0]].get_type() == 5:
            #     score = score + 800
            # elif workbenches[order_key[0]].get_type() == 6:
            #     score = score + 800
            # elif workbenches[order_key[0]].get_type() == 7:
            #     score = score + 800
            # elif workbenches[order_key[0]].get_type() == 9:
            #     score = score - 10000

        else:
            score = -10000
        acq_score[order_key] = score
    MAX_A = -10000
    MAX_A_KEY = None
    log("!!!!!!!!!!" + str(acq_score) + "########")
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
    request_form_1 = get_request_form(1)
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

    best_buy_relevant_bench = sorted(list(request_form[1][fin__buy_pid].keys()),
                                     key=lambda oid: get_bench_bw_dis(fin__buy_bid, oid))
    # if rid != 0:
    #     fin__sell_bid, fin__sell_pid = best_buy_relevant_bench[0], fin__buy_pid
    # else:
    #     fin__sell_bid, fin__sell_pid = best_buy_relevant_bench[1], fin__buy_pid
    # if (len(request_form_1) == 0):
    #     fin__sell_bid, fin__sell_pid = None, None
    # request_form_1 = get_request_form(1)
    if(len(request_form_1)!= 0):
        for order_key in request_form_1:
            if order_key[1] == fin__buy_pid:
                fin__sell_bid, fin__sell_pid = order_key[0], order_key[1]
                break
    else:
        fin__sell_bid, fin__sell_pid = None,None

    return fin__buy_bid, fin__buy_pid, fin__sell_bid, fin__sell_pid


def free_ride_bussiness(rid, new_bid, new_pid):  # 计算够不够顺风，够的话返回顺风job，不够的话返回none
    """
    :param rid: 机器人id
    :param new_bid: 产生新订单平台
    :param new_pid: 产生新产品
    :return: 工作
    """
    return None, None
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
    # best_sell_bid = None
    # if len(best_buy_relevant_bench) > 0:
    #     best_sell_bid = best_buy_relevant_bench[0]
    # distance_3 = int(distance_o(robot_position, workbenches[new_bid].get_pos()))  # 3
    # distance_1 = int(distance_o(robot_position, workbenches[final_buy_bid].get_pos()))  # 1
    #
    # # TODO:
    # if best_sell_bid is None:
    #     return None, None
    #
    # distance_2 = get_bench_bw_dis(final_buy_bid, final_sell_bid)
    # distance_4 = get_bench_bw_dis(new_bid, best_sell_bid)
    # distance_5 = get_bench_bw_dis(best_sell_bid, final_buy_bid)
    #
    # profit_ori = get_product_profit(robots[rid].get_job()[2]) / (distance_1 + distance_2)
    # profit_new = (get_product_profit(robots[rid].get_job()[2]) + get_product_profit(new_pid)) / (distance_3 + distance_4 + distance_5 + distance_2)
    #
    # if profit_ori < 0.95 * profit_new:
    #     temporary_buy_bid, temporary_buy_pid = new_bid, new_pid
    #     temporary_sell_bid, temporary_sell_pid = best_sell_bid, new_pid
    # else:
    #     return None, None
    # bench_1, bench_2 = (temporary_buy_bid, 0, temporary_buy_pid), (temporary_sell_bid, 1, temporary_buy_pid)
    # log("choose job result : " + str(bench_1) + "  " + str(bench_2))
    # return None, None
