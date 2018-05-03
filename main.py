# -*- coding:utf8 -*-
'''
author:ayogg
'''

import json, hashlib, struct, time, sys
import urllib.request
import time
import text

eos_num = 44.03
access_key = ' '
access_secret = ' '


def time2cov(time_):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_))


def cov2time(time_):
    return time.mktime(time.strptime(time_, "%Y-%m-%d %H:%M:%S"))


def transdate(time):
    if int(time) / 10 ** 11 != 0:
        return int(time) / 1000
    else:
        return int(time)


class zb_api:
    def __init__(self, mykey, mysecret, path, addr, method):
        self.mykey = mykey
        self.mysecret = mysecret
        self.jm = ''
        self.path = path
        self.addr = addr
        self.method = method

    def __fill(self, value, lenght, fillByte):
        if len(value) >= lenght:
            return value
        else:
            fillSize = lenght - len(value)
        return value + chr(fillByte) * fillSize

    def __doXOr(self, s, value):
        slist = list(s.decode('utf-8'))
        for index in range(len(slist)):
            slist[index] = chr(ord(slist[index]) ^ value)
        return "".join(slist)

    def __hmacSign(self, aValue, aKey):
        keyb = struct.pack("%ds" % len(aKey), aKey.encode('utf-8'))
        value = struct.pack("%ds" % len(aValue), aValue.encode('utf-8'))
        k_ipad = self.__doXOr(keyb, 0x36)
        k_opad = self.__doXOr(keyb, 0x5c)
        k_ipad = self.__fill(k_ipad, 64, 54)
        k_opad = self.__fill(k_opad, 64, 92)
        m = hashlib.md5()
        m.update(k_ipad.encode('utf-8'))
        m.update(value)
        dg = m.digest()

        m = hashlib.md5()
        m.update(k_opad.encode('utf-8'))
        subStr = dg[0:16]
        m.update(subStr)
        dg = m.hexdigest()
        return dg

    def __digest(self, aValue):
        value = struct.pack("%ds" % len(aValue), aValue.encode('utf-8'))
        # print(value)
        h = hashlib.sha1()
        h.update(value)
        dg = h.hexdigest()
        return dg

    def __api_call(self, path, params=''):
        try:
            SHA_secret = self.__digest(self.mysecret)
            sign = self.__hmacSign(params, SHA_secret)
            self.jm = sign
            reqTime = (int)(time.time() * 1000)
            params += '&sign=%s&reqTime=%d' % (sign, reqTime)
            url = self.addr + path + '?' + params
            req = urllib.request.Request(url)
            res = urllib.request.urlopen(req, timeout=2)
            doc = json.loads(res.read())
            return doc
        except Exception as ex:
            print(sys.stderr, 'zb request ex: ', ex)
            return None

    def query_account(self):
        try:
            params = "accesskey=" + self.mykey + "&" + self.method
            path = self.path

            obj = self.__api_call(path, params)
            # print obj
            return obj
        except Exception as ex:
            print(sys.stderr, 'zb query_account exception,', ex)
            return None


def todaySaleBuyLowHigh(cointype):
    '''
    行情
    包括：
    high : 最高价
    low : 最低价
    buy : 买一价
    sell : 卖一价
    last : 最新成交价
    vol : 成交量(最近的24小时)
    :return:
    '''
    addr = 'http://api.zb.com/data/v1/'
    path = 'ticker'
    method = "market=" + cointype
    api = zb_api(access_key, access_secret, path, addr, method)
    # 将日期转换成标准
    feature = api.query_account()
    if feature is None:
        return -1
    feature['date'] = time2cov(transdate(int(feature['date'])))
    return feature


def Kline(cointype, timetype):
    '''
    K线
    内容：
    data : K线内容
    moneyType : 买入货币
    symbol : 卖出货币
    data : 内容说明
    [
    1417536000000, 时间戳
    2370.16, 开
    2380, 高
    2352, 低
    2367.37, 收
    17259.83 交易量
    ]
    :param cointype:
    :param timetype:
    :return:
    '''
    addr = 'http://api.zb.com/data/v1/'
    path = 'kline'
    method = 'market=' + cointype
    type = timetype
    size = "12"

    method = method + '&' + "type=" + type + '&' + "size=" + size
    api = zb_api(access_key, access_secret, path, addr, method)
    feature = api.query_account()
    if feature is None:
        return -1
    for i in range(len(feature['data'])):
        feature['data'][i][0] = time2cov(transdate(feature['data'][i][0]))

    return feature


def alarm_good(todaySBLH, Kline, thresh):
    '''
    需要报警的情况：（需要提前报警）
    1.价格比1hour前涨幅多thresh
    2.价格比0.5hour前多thresh
    3.价格比5分钟前多1.5
    :param todaySBLH:
    :param Kline:
    :return:
    '''
    nowPrice = todaySBLH['ticker']['last']

    # 1.价格比1hour前多10
    hourBeforePrice = Kline['data'][0][1]
    halfLevel = float(float(nowPrice) - float(hourBeforePrice)) / float(hourBeforePrice) * 100
    if halfLevel > thresh:
        return 1, nowPrice
    # 2.价格比0.5hour前多10
    halfBeforePrice = Kline['data'][6][1]
    hourLevel = float(float(nowPrice) - float(halfBeforePrice)) / float(halfBeforePrice) * 100
    if hourLevel > thresh:
        return 1, nowPrice
    # 3.价格比5分钟前多1.5
    if float(nowPrice) - float(Kline['data'][11][1]) > 1.5:
        return 1, nowPrice
    return 0, nowPrice


def alarm_bad(todaySBLH, Kline, thresh):
    '''
    需要报警的情况：（需要提前报警）
    1.价格比15min之前跌幅大于3%
    2.价格比30min之前跌幅大于3%
    3.价格比60min之前跌幅大于3%
    4.价格低于最低价
    5.价格比5分钟前少1.5
    :param todaySBLH:
    :param Kline:
    :return:
    '''
    nowPrice = todaySBLH['ticker']['last']
    lowPrice = todaySBLH['ticker']['low']
    # 1.价格比15min之前跌幅大于3%
    fifBeforePrice = Kline['data'][9][1]
    fifLevel = (float(fifBeforePrice) - float(nowPrice)) / float(fifBeforePrice) * 100
    if fifLevel > thresh:
        return 1, nowPrice
    # 2.价格比30min之前跌幅大于3%
    halfBeforePrice = Kline['data'][6][1]
    halfLevel = (float(halfBeforePrice) - float(nowPrice)) / float(halfBeforePrice) * 100
    if halfLevel > thresh:
        return 1, nowPrice
    # 3.价格比60min之前跌幅大于3%
    hourBeforePrice = Kline['data'][0][1]
    hourLevel = float(float(hourBeforePrice) - float(nowPrice)) / float(halfBeforePrice) * 100
    if hourLevel > thresh:
        return 1, nowPrice
    # 4.价格低于最低价
    if float(nowPrice) < float(lowPrice) + 1.3:
        return 1, nowPrice
    # 5.价格比5分钟前少1.5
    if float(Kline['data'][11][1]) - float(nowPrice) > 1.5:
        return 1, nowPrice
    return 0, nowPrice


def startDetectCoin(cointype, num, thresh_good, thresh_bad):
    '''
    行情监测
    发送买报警信号和卖报警信号，这两种信号会发送邮件
    另外输出现在的价值
    :param cointype: 币类型
    :param num:币的数量
    :param thresh_good：增幅
    :param thresh_bad：跌幅
    :return:

    '''
    # 行情
    todayFeature = todaySaleBuyLowHigh(cointype)

    # k线
    timetype = '5min'
    KlineFeature = Kline(cointype, timetype)

    if (todayFeature == -1 or KlineFeature == -1):
        return -1

    # 报警 good是赚钱，要抛；bad是赔钱，要抛;thresh是幅度
    alarm_good_flag, nowPrice = alarm_good(todayFeature, KlineFeature, thresh=thresh_good)
    alarm_bad_flag, nowPrice = alarm_bad(todayFeature, KlineFeature, thresh=thresh_bad)

    time_now = todayFeature['date']
    print("-" * 50 + "现在时间是：" + time_now + "-" * 50)
    if (alarm_good_flag):
        Mine = float(nowPrice) * num
        print(" " * 50 + "赚！！！！！" + " " * 10 + "现在价格是:" + nowPrice + " " * 50)
        print(" " * 50 + "赚！！！！！" + " " * 10 + "现在价格是:" + nowPrice + " " * 50)
        print(" " * 50 + "赚！！！！！" + " " * 10 + "现在价格是:" + nowPrice + " " * 50)
        contentMsg = "现在" + cointype + "价格是:" + nowPrice + " " * 50 + "\n" + "总共" + str(Mine) + "元"
        text.sendMail("赚了" + " " + "价格是:" + nowPrice, contentMsg)

    if (alarm_bad_flag):
        Mine = float(nowPrice) * num
        print(" " * 50 + "赔赔赔赔赔赔赔" + " " * 10 + "现在价格是:" + nowPrice + " " * 50)
        print(" " * 50 + "赔赔赔赔赔赔赔" + " " * 10 + "现在价格是:" + nowPrice + " " * 50)
        print(" " * 50 + "赔赔赔赔赔赔赔" + " " * 10 + "现在价格是:" + nowPrice + " " * 50)
        contentMsg = "现在" + cointype + "价格是:" + nowPrice + " " * 50 + "\n" + "总共" + str(Mine) + "元"
        text.sendMail("赔了" + " " + "价格是:" + nowPrice, contentMsg)

    if (alarm_good_flag != 1 and alarm_bad_flag != 1):
        halfBeforePrice = KlineFeature['data'][6][1]

        fifUp = (float(nowPrice) - float(halfBeforePrice)) / float(halfBeforePrice) * 100
        Mine = float(nowPrice) * num
        print(" " * 10 + "现在价格是" + nowPrice + "人民币")
        print(" " * 10 + "现资产" + cointype + "是" + str(Mine) + "人民币")
        print(" " * 50 + "比较15min前涨跌幅为" + " " * 10 + str(fifUp) + "%")
        print(" " * 50 + "安心学习，别看了")

    return Mine
    del todayFeature
    del KlineFeature


def sendBuyMessage(cointype, price):
    '''
    发送买信号
    :param cointype: 币的类型
    :param price: 单价小于这个价格则可以买
    :return: 如果连接失败直接返回
    '''
    todayFeature = todaySaleBuyLowHigh(cointype)
    if todayFeature == -1:
        return
    nowPrice = todayFeature['ticker']['last']
    if float(nowPrice) < price:
        contentMsg = "现在" + cointype + "价格是:" + nowPrice + " " * 50
        whatmsg = "好像可以买一波" + nowPrice
        text.sendMail(whatmsg, contentMsg)
    return


def sendSellMessage(cointype, price, num):
    '''
    发送买的信号
    :param cointype: 币种类
    :param price: 大于这个价格，则发送信号
    :param num: 币的数量
    :return: 如果连接失败直接返回
    '''
    # 赚了本金的20 %
    todayFeature = todaySaleBuyLowHigh(cointype)
    if todayFeature == -1:
        return
    nowPrice = todayFeature['ticker']['last']
    if float(nowPrice) * num > price:
        contentMsg = "现在" + cointype + "价格是:" + nowPrice + " " * 50
        whatmsg = "好像可以卖一波" + nowPrice
        text.sendMail(whatmsg, contentMsg)


def sendMessage(cointype):
    '''
    发送邮件
    现在价格是：
    :param cointype:币的类型
    :return: 如果连接失败直接返回
    '''
    todayFeature = todaySaleBuyLowHigh(cointype)
    if todayFeature == -1:
        return
    nowPrice = todayFeature['ticker']['last']

    contentMsg = "现在" + cointype + "价格是:" + nowPrice + " " * 50
    whatmsg = "zb监测程序在运行"
    text.sendMail(contentMsg, whatmsg)


if __name__=='__main__':


    time_start = time.time()

    while (1):
        print(" ")
        print(" ")
        print(" ")
        time.sleep(10)
        allMoney = 0

        cointype = 'eos_qc'
        print("-" * 50 + "开始" + cointype + "的监控" + "-" * 50)
        tmp = startDetectCoin(cointype, num=eos_num, thresh_good=3, thresh_bad=3)
        if tmp == -1:
            print("服务器可能出了点问题")
        else:
            allMoney += tmp

        '''
        print(" ")
        time.sleep(1)
        cointype = 'ae_qc'
        print("-" * 50 + "开始" + cointype + "的监控" + "-" * 50)
        tmp = startDetectCoin(cointype, num=12.99)
        if tmp == -1:
            print("服务器可能出了点问题")
        else:
            allMoney += tmp
        '''

        print(" ")
        print("现总资产为" + str(allMoney) + "人民币")

        #sendBuyMessage(cointype, 110.0)
        sendSellMessage(cointype, 124.0, num=1)
        sendSellMessage('ae_qc', 32, num=1)


        # 提醒运行正常email，运行半小时发一封邮件
        time_end = time.time()
        timedelta = time_end - time_start
        if timedelta % 600 < 30:
            sendMessage(cointype)
            sendMessage('ae_qc')
            time_end = time_start
