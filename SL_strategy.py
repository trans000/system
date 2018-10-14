#!/usr/bin/python3
# coding: utf-8
import requests
import datetime
import time
import ccxt
import logging
from pytz import timezone, utc
import json

LOT  = 10
SLEEP = 30
LEN = 5
global counter
counter = 0
    
highPriceList = []
lowPriceList = []

bitmex = ccxt.bitmex({
    'apiKey': 'Your Key',
    'secret': 'Your Secret',
})

bitmex.urls['api'] = bitmex.urls['test']

def calPrice(coun):
    ticker = bitmex.fetch_ticker('BTC/JPY')
    global c_high
    global c_low
    global highPriceList
    global lowPriceList

    if coun == 0:
        highPriceList.insert(0, ticker['close'])
        c_high = max(highPriceList)
        lowPriceList.insert(0, ticker['close'])
        c_low = min(lowPriceList)

    else:
        if(len(highPriceList) > 19):       
            highPriceList.insert(0, ticker['close'])
            highPriceList.pop(20)
            c_high = max(highPriceList)
        else:
            highPriceList.insert(0, ticker['close'])
            c_high = max(highPriceList)

        if(len(lowPriceList) > 19):       
            lowPriceList.insert(0, ticker['close'])
            lowPriceList.pop(20)
            c_low = min(lowPriceList)
        else:
            lowPriceList.insert(0, ticker['close'])
            c_low = min(lowPriceList)

    return c_high,c_low
    
def customTime(*args):
    utc_dt = utc.localize(datetime.datetime.utcnow())
    my_tz = timezone("Japan")
    converted = utc_dt.astimezone(my_tz)
    return converted.timetuple()

def stop(side, price, size):
    o = bitmex.privatePostOrder({"symbol": "XBTJPY", "side": side, "orderQty": size, "ordType": "Stop", "stopPx": price, "execInst": "LastPrice", })
    logger.info('新規注文:%s %-4s %d @ %.1f %s' % (o['ordType'], o['side'], o['orderQty'], o['stopPx'], o['orderID']))
    return price
                              
def position():
    try:
        ret = bitmex.private_get_position({'filter': json.dumps({"symbol": "XBTJPY"})})[0]
    except Exception as e:
        logger.error("Error!")
        logger.error(e)
        return {'side': pos['side'], 'size': pos['size'], 'avgEntryPrice': pos['avgEntryPrice']}
    if ret['currentQty'] == 0:
        side = 'NO POSITION'
        ret['avgEntryPrice'] = 0
    elif ret['currentQty'] > 0:
        side = 'LONG'
    else:
        side = 'SHORT'
    return {'side': side, 'size': round(ret['currentQty']), 'avgEntryPrice': ret['avgEntryPrice']}

def balance():
    try:
        ret = bitmex.fetch_balance()
        pnl = ret['info'][0]['unrealisedPnl'] / 100000000
        btc = ret['BTC']['total']
        return {'pnl': pnl, 'btc': btc}
    except Exception as e:
        logger.error("Error!")
        logger.error(e)
        return {'pnl': bal['pnl'], 'btc': bal['btc']}

logger = logging.getLogger('LoggingTest')
logger.setLevel(10)
fh = logging.FileHandler('log1.log')
logger.addHandler(fh)
sh = logging.StreamHandler()
logger.addHandler(sh)
formatter = logging.Formatter('%(asctime)s %(lineno)03d: %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
fh.setFormatter(formatter)
sh.setFormatter(formatter)
logging.Formatter.converter = customTime

stop_long = 0
stop_short = 0
pos = {'side': 'NO POSITION', 'size': 0, 'avgEntryPrice': 0}
bal = {'pnl': 0, 'btc': 0}
    

print('========== Trade Start! ==========')
while True:
    try:
        calPrice(counter)
        counter+=1
        
        if counter > 2:
        #if counter > 2*60*18:
            orders = bitmex.fetch_open_orders()
            for o in orders:
                if o['symbol'] == 'BTC/JPY' and o['type'] == 'stop':
                    logger.info('トリガ待ち:%s %-4s %d @ %.1f %s' % (o['info']['ordType'], o['info']['side'], o['info']['orderQty'], o['info']['stopPx'], o['info']['orderID']))
            now = str(int(datetime.datetime.now().timestamp()))

            print('high:' + str(c_high))
            print('low:' + str(c_low))
            print('======================')
            pos = position()
            bal = balance()
            
            logger.info('設定ロット:%d' % LOT)
            logger.info('ポジション:%s %d @ %.1f' % (pos['side'], pos['size'], pos['avgEntryPrice']))
            logger.info('未実現損益:%+.6f' % bal['pnl'])
            logger.info('証拠金残高:%+.6f' % bal['btc'])
            
            if pos['side'] == 'LONG':
                for o in orders:
                    if o['symbol'] == 'BTC/JPY' and o['type'] == 'stop' and o['side'] == 'buy':
                        bitmex.cancel_order(o['id'])
            elif stop_long != c_high + 500:
                for o in orders:
                    if o['symbol'] == 'BTC/JPY' and o['type'] == 'stop' and o['side'] == 'buy':
                        bitmex.cancel_order(o['id'])
                stop_long = stop('Buy', c_high + 500, LOT - pos['size'])
                print('stop_long' + str(stop_long))
            if pos['side'] == 'SHORT':
                for o in orders:
                    if o['symbol'] == 'BTC/JPY' and o['type'] == 'stop' and o['side'] == 'sell':
                        bitmex.cancel_order(o['id'])
            elif stop_short != c_low - 500:
                for o in orders:
                    if o['symbol'] == 'BTC/JPY' and o['type'] == 'stop' and o['side'] == 'sell':
                        bitmex.cancel_order(o['id'])
                stop_short = stop('Sell', c_low - 500, LOT + pos['size'])
                print('stop_short' + str(stop_short))

            logger.info('L価格:%.1f' % c_high)
            logger.info('S価格:%.1f' % c_low)
            
        time.sleep(SLEEP)
    except Exception as e:
        print("Error!")
        print(e)
        time.sleep(5)