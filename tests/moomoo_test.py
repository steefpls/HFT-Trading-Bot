"""
Copyright (c) 2024 Steven Koe and Tan Chuan Hong Algene

All rights reserved.

This code and any works derived from it are owned by Steven Koe and Tan Chuan Hong Algene.
Permission must be obtained from Steven Koe and Tan Chuan Hong Algene to use, modify, distribute, sell, 
or create derivative works from this code.

Contact Information:
Steven Koe - steven.koe80@gmail.com
Tan Chuan Hong Algene - hydrater@gmail.com

Any unauthorized use, modification, distribution, sale, or creation of derivative works is strictly prohibited.

"""
from moomoo import *
from time import sleep

def place_buy_limit_order(trade_client, price, quantity, ticker, accData, accIndex):
    ret, data = trade_client.place_order(price = price, qty = quantity, code = ticker, trd_side = TrdSide.BUY, order_type = OrderType.NORMAL, acc_id = accData['acc_id'][accIndex], trd_env=accData['trd_env'][accIndex])
    if ret == RET_OK:
        print(data)
        print(data['order_id'][0])  # Get the order ID of the placed order
        print(data['order_id'].values.tolist())  # Convert to list
    else:
        print('place buy limit order error: ', data)
        return -1

def place_buy_market_order(trade_client, quantity, ticker, accData, accIndex):
    ret, data = trade_client.place_order(price = 0, qty = quantity, code = ticker, trd_side = TrdSide.BUY, order_type = OrderType.MARKET, acc_id=accData['acc_id'][accIndex], trd_env=accData['trd_env'][accIndex]) 
    if ret == RET_OK:
        print(data)
        print(data['order_id'][0])  # Get the order ID of the placed order
        print(data['order_id'].values.tolist())  # Convert to list
    else:
        print('place buy market order error: ', data)
        return -1

def place_sell_limit_order(trade_client, price, quantity, ticker, accData, accIndex):
    ret, data = trade_client.place_order(price = price, qty = quantity, code = ticker, trd_side = TrdSide.SELL, order_type = OrderType.NORMAL, acc_id = accData['acc_id'][accIndex], trd_env=accData['trd_env'][accIndex])
    if ret == RET_OK:
        print(data)
        print(data['order_id'][0])  # Get the order ID of the placed order
        print(data['order_id'].values.tolist())  # Convert to list
    else:
        print('place sell limit order error: ', data)
        return -1

def place_sell_market_order(trade_client, quantity, ticker, accData, accIndex):
    ret, data = trade_client.place_order(price = 0, qty = quantity, code = ticker, trd_side = TrdSide.SELL, order_type = OrderType.MARKET, acc_id = accData['acc_id'][accIndex], trd_env=accData['trd_env'][accIndex])
    if ret == RET_OK:
        print(data)
        print(data['order_id'][0])  # Get the order ID of the placed order
        print(data['order_id'].values.tolist())  # Convert to list
    else:
        print('place sell market order error: ', data)
        return -1
    
def modify_order(trade_client, price, quantity, accData, accIndex):
    ret, data = trade_client.modify_order(price = price, qty = quantity, modify_order_op=ModifyOrderOp.NORMAL, acc_id = accData['acc_id'][accIndex], trd_env=accData['trd_env'][accIndex])
    if ret == RET_OK:
        print(data)
        print(data['order_id'][0])  # Get the order ID of the placed order
        print(data['order_id'].values.tolist())  # Convert to list
    else:
        print('modify order error: ', data)
        return -1

def get_order_by_stock(trade_client, ticker, accData, accIndex):
    ret, data =trade_client.order_list_query(code=ticker, acc_id = accData['acc_id'][accIndex], trd_env=accData['trd_env'][accIndex], refresh_cache=False)
    if ret == RET_OK:
        print(data)
        return data
    else:
        print('get order by stock error: ', data)
        return -1
    
def get_all_orders(trade_client, accData, accIndex):
    ret, data =trade_client.order_list_query(acc_id = accData['acc_id'][accIndex], trd_env=accData['trd_env'][accIndex], refresh_cache=False)
    if ret == RET_OK:
        print(data)
        return data
    else:
        print('get all orders error: ', data)
        return -1

def average_cost_for_stock(trade_client, ticker, accData, accIndex):
    ret, data = trade_client.position_list_query(code = ticker, acc_id = accData['acc_id'][accIndex], trd_env=accData['trd_env'][accIndex], refresh_cache=False)
    if ret == RET_OK:
        return data.cost_price
    else:
        print('average cost for stock error: ', data)
        return -1
    
#callbacks
class TradeOrder(TradeOrderHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret, content = super(TradeOrder, self).on_recv_rsp(rsp_pb)
        if ret == RET_OK:
            print("* Trade Order content={}\n".format(content))
        return ret, content

class QuoteTicker(TickerHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, data = super(QuoteTicker,self).on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print("Ticker: error, msg: %s"% data)
            return RET_ERROR, data
        print("Ticker:", data) # TickerTest's own processing logic
        return RET_OK, data
    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~/ᐠ - ˕ -マ Ⳋ~~~~~~~~~~~~~~~~~~~~~~~₍^ >ヮ<^₎ .ᐟ.ᐟ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pwd_unlock = '123456'
current_acc_index = 1
trd_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host='127.0.0.1', port=11111, security_firm=SecurityFirm.FUTUSG)
ret, accData = trd_ctx.get_acc_list()
if ret == RET_OK:
    #run code
    print(accData)
    print(accData['acc_id'][1])  # Get the order ID of the placed order
    print(accData['acc_id'].values.tolist())  # Convert to list

else:
    print('get_acc_list error: ', accData)

if accData['trd_env'][current_acc_index]==TrdEnv.REAL:
    ret, data = trd_ctx.unlock_trade(pwd_unlock)
    if ret == RET_ERROR:
        print('unlock_trade failed: ', data)

orderHandler = TradeOrder()
trd_ctx.set_handler(orderHandler)

trd_ctx.place_order(price=11.0, qty=2, code="US.SOUN", trd_side=TrdSide.BUY, trd_env = TrdEnv.SIMULATE)
sleep (100)


#place_buy_limit_order(3, 1, 'US.SOUN', accData, 1)
#place_buy_market_order(1,'US.SOUN', accData, 1)

#place order(price, qty, code, BUY/SELL/SELL_SHORT/BUY_BACK, adjust_limit, trd_env(SIMULATE/REAL), account id, time_in_force, aux_price, trail_type, trail_value, trail_spread)

trd_ctx.close()


