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
""""
from irori.BrokerBase import BrokerBase
from irori import common as irori_common
from moomoo import *
from jproperties import Properties
from enum import Enum

class MooMooBroker(BrokerBase):
    pwd = None
    trade_env = None
    
    accData = None
    accIndex = -1

    trade_context = None
    quote_context = None
    push_client = None
    tickers = []

    market = irori_common.Market.US.value

    def __init__(self):
        super().__init__()

    def authenticate(self):
        jPropertyConfigs = Properties()
        MooMooAccPropertiesFile = "./Authentication.properties"
        with open(MooMooAccPropertiesFile, "rb") as config_file:
            jPropertyConfigs.load(config_file)

        self.trade_context = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host='127.0.0.1', port=11111, security_firm=SecurityFirm.FUTUSG)
        self.quote_context = OpenQuoteContext(host='127.0.0.1', port=11111, is_encrypt=False)

        self.setup(jPropertyConfigs.get("run_in_real_environment").data,jPropertyConfigs.get("password").data)
    

    def setup(self, runInRealEnv, password):
        ret, self.accData = self.trade_context.get_acc_list()

        if ret != RET_OK:
            print('get_acc_list error: ', self.accData)
        
        if runInRealEnv !="test":
            self.accIndex = 0
            ret, data = self.trade_context.unlock_trade(password)
            if ret == RET_ERROR:
                print('unlock_trade failed: ', data)
        else:
            self.accIndex = 1

    # Markets is a list of STR
    def setup_callbacks(self, tick_event:callable, order_event:callable, tickers: irori_common.Tickers):
        
        self.orderHandler = TradeOrder()
        self.orderHandler.event = order_event
        self.orderHandler.mediator = self.mediator
        self.trade_context.set_handler(self.orderHandler)

        self.tickers = []

        for t in tickers.tickerList:
            self.tickers.append(self.market + '.' + t)

        # for i in range(0,len(markets)):
            # self.tickers.append(markets[i]+'.'+tickers.tickerList[i])
        #add market to ticker list

        if tick_event == None:
            return
        
        ret, data = self.quote_context.subscribe(self.tickers, [SubType.TICKER], subscribe_push=True)
        if ret != RET_OK:
            print(data)
        else:
            tickerHandler = QuoteTicker()
            tickerHandler.event = tick_event
            self.quote_context.set_handler(tickerHandler)
    
    def get_account_details(self, acc_detail_obj : irori_common.AccountQuery):
        response = irori_common.AccountResponse()
        ret, data = self.trade_context.accinfo_query(acc_id=self.accData['acc_id'][self.accIndex], trd_env=self.accData['trd_env'][self.accIndex], currency=acc_detail_obj.currency)
        if ret==RET_OK:

            response.cash_balance = data['cash'][0]
            response.gross_position_value = data['market_val'][0]
            response.unrealized_pl = data['unrealized_pl'][0]
            response.realized_pl = data['realized_pl'][0]
            print(response)
            return response
        else:
            return -1

    # def get_positions(self):
    def get_positions(self):

        position_details = irori_common.PositionsResponse()

        positions = self.trade_context.position_list_query(acc_id=self.accData['acc_id'][self.accIndex], trd_env=self.accData['trd_env'][self.accIndex])
        print(positions)

        for i in range(0, len(positions["code"])):
            # prints
            # print('--------------------------------------')
            # print(f'S/N #{i}')
            # print(f'Contract: {p.contract.symbol}')  # contract， such as AAPL，CL2303
            # print(f'Average Cost: {p.average_cost}')  # position average cost
            # print(f'Qty: {p.quantity}')  # position quantity
            # #print(f'Contract Type: {p.contract.sec_type}')  # contract type， such as STK， FUT
            # #print(f'{p.contract.multiplier}')  # contract multiplier
            # print('--------------------------------------')
            stock = irori_common.Stock()
            stock.ticker = positions['code'][i]
            stock.quantity = positions['qty'][i]
            stock.average_cost = positions['cost_price'][i]
            stock.market_price = positions['nominal_price'][i]
            position_details.stockList.append(stock)

        return position_details

    # Gets Moomoo order (DOES NOT TRANSFORM INTO AN IRORI OBJECT)
    # USED FOR TESTING
    def get_raw_order(self, get_order_id : str):
        ret, data = self.trade_context.order_list_query(order_id=get_order_id,acc_id=self.accData['acc_id'][self.accIndex], trd_env=self.accData['trd_env'][self.accIndex])

        if ret == RET_OK:
            return data
        
        return None

    # Gets single order
    # Returns a list of orders (even if we retrieve one)
    def get_order(self, get_order_id : str):
        data = self.get_raw_order(get_order_id=get_order_id)

        if data is not None and data.shape[0] > 0:
            # Create 1 irori order object
            orders = self.create_irori_order_from_moomoo_data(data, 1)
            if len(orders) != 0:
                return orders[0]
        
        return None

    # Moomoo_data is the list of orders from order_list_query
    # indexes are the number of orders we want to retrieve from the data
    def create_irori_order_from_moomoo_data(self, data, count : int):
                #         col_list = [
        #     "code", "stock_name", "trd_side", "order_type", "order_status",
        #     "order_id", "qty", "price", "create_time", "updated_time",
        #     "dealt_qty", "dealt_avg_price", "last_err_msg", "remark",
        #     "time_in_force", "fill_outside_rth", "aux_price", "trail_type",
        #     "trail_value", "trail_spread", "currency",
        # ]
        
        orders = []

        size = data.shape[0]
        if count > size:
            return orders

        for x in range(0, count):
            order = irori_common.Order()
            order.order_id = data['order_id'][x]
            match data['order_status'][x]:
                case OrderStatus.SUBMITTED:
                    order.status = irori_common.OrderStatus.NEW
                case OrderStatus.FILLED_ALL:
                    order.status = irori_common.OrderStatus.FILLED
                case OrderStatus.FILLED_PART:
                    order.status = irori_common.OrderStatus.PARTIALLY_FILLED
                case OrderStatus.FAILED:
                    order.status = irori_common.OrderStatus.FAILED
                case OrderStatus.CANCELLED_PART:
                    order.status = irori_common.OrderStatus.CANCELLED
                case OrderStatus.CANCELLED_ALL: 
                    order.status = irori_common.OrderStatus.CANCELLED
                case OrderStatus.DELETED:
                    order.status = irori_common.OrderStatus.CANCELLED
                case _:
                    order.status = irori_common.OrderStatus.OTHERS
            match data['order_type'][x]:
                case OrderType.MARKET:
                    order.order_type = irori_common.OrderType.MARKET
                case OrderType.NORMAL:
                    order.order_type = irori_common.OrderType.LIMIT
                case OrderType.STOP:
                    order.order_type = irori_common.OrderType.STOP
                case OrderType.STOP_LIMIT:
                    order.order_type = irori_common.OrderType.STOP_LMT
                case OrderType.TRAILING_STOP:
                    order.order_type = irori_common.OrderType.TRAIL
                case OrderType.TRAILING_STOP_LIMIT:
                    order.order_type = irori_common.OrderType.TRAIL_LMT
            match data['trd_side'][x]:
                case TrdSide.BUY:
                    order.action = irori_common.OrderAction.BUY
                case TrdSide.SELL:
                    order.action = irori_common.OrderAction.SELL
                case TrdSide.SELL_SHORT:
                    order.action = irori_common.OrderAction.SHORT_OPEN
                case TrdSide.BUY_BACK:
                    order.action = irori_common.OrderAction.SHORT_CLOSE
            order.price = data['price'][x]
            order.total_quantity = data['qty'][x]
            order.aux_price = data['aux_price'][x]
            order.created_time = data['create_time'][x]
            order.error_message = data['last_err_msg'][x]
            order.ticker = data['code'][x]

            orders.append(order)
        return orders
    
    def buy_market_order(self, buy_command: irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = 0, qty = buy_command.quantity, \
                                                code = self.market+'.'+buy_command.ticker, \
                                                trd_side = TrdSide.BUY, order_type = OrderType.MARKET, \
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]

    def buy_limit_order(self, buy_command: irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = buy_command.price, \
                                                qty = buy_command.quantity, \
                                                code = self.market+'.'+buy_command.ticker, \
                                                trd_side = TrdSide.BUY, order_type = OrderType.NORMAL,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]

    def sell_market_order(self, sell_command: irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = 0, qty = sell_command.quantity, \
                                                code = self.market+'.'+sell_command.ticker, \
                                                trd_side = TrdSide.SELL, order_type = OrderType.MARKET, \
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]

    def sell_limit_order(self, sell_command: irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = sell_command.price, \
                                                qty = sell_command.quantity, \
                                                code = self.market+'.'+sell_command.ticker, \
                                                trd_side = TrdSide.SELL, order_type = OrderType.NORMAL, \
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]
        
    def stop_market_buy_order(self, stop_loss : irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = stop_loss.price, \
                                                qty = stop_loss.quantity, \
                                                code = self.market+'.'+stop_loss.ticker, \
                                                trd_side = TrdSide.BUY, order_type = OrderType.STOP,\
                                                aux_price=stop_loss.aux_price,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]
    
    def stop_market_sell_order(self, stop_loss : irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = stop_loss.price, \
                                                qty = stop_loss.quantity, \
                                                code = self.market+'.'+stop_loss.ticker, \
                                                trd_side = TrdSide.SELL, order_type = OrderType.STOP,\
                                                aux_price=stop_loss.aux_price,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]
        
    def stop_limit_buy_order(self, stop_loss : irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = stop_loss.price,\
                                                qty = stop_loss.quantity,\
                                                code = self.market+'.'+stop_loss.ticker,\
                                                trd_side = TrdSide.BUY, order_type=OrderType.STOP_LIMIT,\
                                                aux_price=stop_loss.aux_price,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]

    def stop_limit_sell_order(self, stop_loss : irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = stop_loss.price,\
                                                qty = stop_loss.quantity,\
                                                code = self.market+'.'+stop_loss.ticker,\
                                                trd_side = TrdSide.SELL, order_type=OrderType.STOP_LIMIT,\
                                                aux_price=stop_loss.aux_price,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]

    def trailing_stop_market_order(self, trailing_order : irori_common.OrderCommand):
        trailtype = TrailType.RATIO
        if(trailing_order.trail_type is irori_common.TrailType.VALUE):
            trailtype = TrailType.AMOUNT

        ret, data = self.trade_context.place_order(price = trailing_order.price,\
                                                qty = trailing_order.quantity,\
                                                code = self.market+'.'+trailing_order.ticker,\
                                                trd_side = TrdSide.SELL, order_type=OrderType.TRAILING_STOP,\
                                                trail_type = trailtype,\
                                                trail_value = trailing_order.trail_price,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]

    def trailing_stop_limit_order(self, trailing_order : irori_common.OrderCommand):
        pass

    def short_open_limit_order(self, short_command: irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = short_command.price,\
                                                qty = short_command.quantity,\
                                                code = self.market+'.'+short_command.ticker,\
                                                trd_side = TrdSide.SELL_SHORT, order_type=OrderType.NORMAL,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]
    
    def short_close_stop_limit_order(self, short_command:irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = short_command.price,\
                                                qty = short_command.quantity,\
                                                code = self.market+'.'+short_command.ticker,\
                                                trd_side = TrdSide.BUY_BACK, order_type=OrderType.NORMAL,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]

    def short_open_market_order(self, short_command:irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = short_command.price,\
                                                qty = short_command.quantity,\
                                                code = self.market+'.'+short_command.ticker,\
                                                trd_side = TrdSide.SELL_SHORT, order_type=OrderType.MARKET,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]

    def short_close_market_order(self, short_command:irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = short_command.price,\
                                                qty = short_command.quantity,\
                                                code = self.market+'.'+short_command.ticker,\
                                                trd_side = TrdSide.BUY_BACK, order_type=OrderType.MARKET,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]
        
    def short_open_stop_market_order(self, stop_loss_short : irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = stop_loss_short.price, \
                                                qty = stop_loss_short.quantity, \
                                                code = self.market+'.'+stop_loss_short.ticker, \
                                                trd_side = TrdSide.SELL_SHORT, order_type = OrderType.STOP,\
                                                aux_price=stop_loss_short.aux_price,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]
    
    def short_close_market_stop_order(self, stop_loss_short : irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = stop_loss_short.price, \
                                                qty = stop_loss_short.quantity, \
                                                code = self.market+'.'+stop_loss_short.ticker, \
                                                trd_side = TrdSide.BUY_BACK, order_type = OrderType.STOP,\
                                                aux_price=stop_loss_short.aux_price,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]
        
    def short_open_stop_limit_order(self, stop_loss : irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = stop_loss.price,\
                                                qty = stop_loss.quantity,\
                                                code = self.market+'.'+stop_loss.ticker,\
                                                trd_side = TrdSide.SELL_SHORT, order_type=OrderType.STOP_LIMIT,\
                                                aux_price=stop_loss.aux_price,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]

    def short_close_stop_limit_order(self, stop_loss : irori_common.OrderCommand):
        ret, data = self.trade_context.place_order(price = stop_loss.price,\
                                                qty = stop_loss.quantity,\
                                                code = self.market+'.'+stop_loss.ticker,\
                                                trd_side = TrdSide.BUY_BACK, order_type=OrderType.STOP_LIMIT,\
                                                aux_price=stop_loss.aux_price,\
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
        if ret != RET_OK:
            return -1
        else:
            return data['order_id'][0]


    def modify_order(self, modify_order_command: irori_common.ModifyOrderCommand):
        orderID = modify_order_command.orderID
        price = modify_order_command.new_price
        quantity = modify_order_command.new_quantity
        if price == 0:
            ret, data = self.trade_context.modify_order(modify_order_op = ModifyOrderOp.NORMAL, \
                                                        order_id = orderID, \
                                                        qty = quantity
                                                        )
            if ret != RET_OK:
                return -1
            else:
                return data['order_id'][0] 
        
        elif quantity == 0: 
            ret, data = self.trade_context.modify_order(modify_order_op = ModifyOrderOp.NORMAL, \
                                                        order_id = orderID, \
                                                        price = price
                                                        )
            if ret != RET_OK:
                return -1
            else:
                return data['order_id'][0]
            
        else:
            ret, data = self.trade_context.modify_order(modify_order_op = ModifyOrderOp.NORMAL, \
                                                        order_id = orderID, \
                                                        price = price, \
                                                        qty = quantity
                                                        )
            if ret != RET_OK:
                return -1
            else:
                return data['order_id'][0] 
    
    def cancel_order(self, cancel_command:irori_common.CancelOrderCommand):
            ret, data = self.trade_context.modify_order(modify_order_op = ModifyOrderOp.CANCEL, \
                                                        order_id = cancel_command.orderID
                                                        )
            if ret != RET_OK:
                return -1
            else:
                return data['order_id'][0]
    
    def clear_all_existing_orders(self, clear_order : irori_common.ClearExistingOrderCommand):
        ret, data = self.order_list_query(code = clear_order.broker+'.'+clear_order.ticker, acc_id=self.accData['acc_id'][self.accIndex], trd_env=self.accData['trd_env'][self.accIndex])
        total_orders = len(data['order_id'])
        print(f'{clear_order.ticker} Found {total_orders} orders to cancel')

        if ret!=RET_OK or total_orders == 0:
            return -1
        
        failed_cancel_orders = []
        for id in data['order_id']:
            ret, data = self.trade_context.modify_order(order_id=id,modify_order_op = ModifyOrderOp.CANCEL, acc_id=self.accData['acc_id'][self.accIndex], trd_env=self.accData['trd_env'][self.accIndex])
            if ret!=RET_OK:
                failed_cancel_orders.append(id)

        if len(failed_cancel_orders) != 0:
            print(f'Failed to cancel orders {failed_cancel_orders}')
            # logger.error(f'Failed to cancel orders {orders_failed_to_cancel}')
        
        print(f'{clear_order.ticker} Cancelled {total_orders - len(failed_cancel_orders)} orders successfully')
        # logger.info(f'{self.ticker} Cancelled {len(orders) - len(orders_failed_to_cancel)} orders successfully')

    def sell_all_existing_stocks(self, sell_all : irori_common.SellAllPositionsCommand):
        positions = self.trade_context.position_list_query(code = self.market+'.'+sell_all.ticker, acc_id=self.accData['acc_id'][self.accIndex], trd_env=self.accData['trd_env'][self.accIndex])

        sell_orders_placed_successfully = 0

        for p in positions:
            print(f'Average cost {p.cost_price}')
            # logger.info(f'Holding cost {p.average_cost}. Average cost {p.average_cost_by_average}')
                
            ret, data = self.trade_context.place_order(price = p['cost_price'][0], \
                                                qty = p['qty'][0], \
                                                code = self.market+'.'+sell_all.ticker, \
                                                trd_side = TrdSide.SELL, order_type = OrderType.NORMAL, \
                                                acc_id=self.accData['acc_id'][self.accIndex], \
                                                trd_env=self.accData['trd_env'][self.accIndex])
            if ret == RET_OK:
                sell_orders_placed_successfully += 1
        
        if sell_orders_placed_successfully == len(positions):
            print(f'{sell_all.ticker} Successfully placed sell orders for all existing stock {sell_all.ticker}')
        elif sell_orders_placed_successfully == 0:
            print(f'{sell_all.ticker} Unable to place any sell order for held stocks')
        else:
            print(f'{sell_all.ticker} Partial success placed sell order for {sell_orders_placed_successfully}/{len(positions)} held stocks')

    def exit_all_positions_immediately(self, clear_order : irori_common.ClearExistingOrderCommand):
        self.clear_existing_orders(self, clear_order)
        self.sell_all_existing_stocks(clear_order.ticker)

    ##moomoo only
    def stop(self):
        self.quote_context.unsubscribe(self.tickers, [SubType.TICKER], unsubscribe_all=True)

        self.trade_context.close()
        self.quote_context.close()
        if self.push_client:
            self.push_client.close()

#moomoo extra classes
class TradeOrder(TradeOrderHandlerBase):
    event = None

    def setEvent(self, orderEvent:callable):
        self.event = orderEvent

    def deconstructOrderData(self, orderData):
        order = irori_common.OrderChangeData()
        order.orderID = orderData['order_id'][0]
        status = orderData['order_status'][0]
        order.ticker = orderData['code'][0]
        order.filled_quantity = orderData['dealt_qty'][0]
        order.limit_price = orderData['price'][0]

        match status:
            case OrderStatus.SUBMITTED:
                order.order_status = irori_common.OrderStatus.NEW
            case OrderStatus.FILLED_ALL:
                order.order_status = irori_common.OrderStatus.FILLED
            case OrderStatus.FILLED_PART:
                order.order_status = irori_common.OrderStatus.PARTIALLY_FILLED
            case OrderStatus.FAILED:
                order.order_status = irori_common.OrderStatus.FAILED
            case OrderStatus.CANCELLED_PART:
                order.order_status = irori_common.OrderStatus.CANCELLED
            case OrderStatus.CANCELLED_ALL: 
                order.order_status = irori_common.OrderStatus.CANCELLED
            case OrderStatus.DELETED:
                order.order_status = irori_common.OrderStatus.CANCELLED
            case _:
                order.order_status = irori_common.OrderStatus.OTHERS
                
        return order

    def on_recv_rsp(self, rsp_pb):
        ret, content = super(TradeOrder, self).on_recv_rsp(rsp_pb)
        
        if ret == RET_OK and self.event!=None:
            frame = self.deconstructOrderData(content)
            self.event(frame)
            if (frame.order_status == irori_common.OrderStatus.FILLED and self.mediator):
                self.mediator.resolve_purchase(frame.ticker, frame.filled_quantity, frame.avg_fill_price, frame.commissionAndFee, frame.action)

class QuoteTicker(TickerHandlerBase):
    event = None
    def setEvent(self, tickerEvent:callable):
        self.event = tickerEvent

    def deconstructTickerData(self, tickData):
        tick = irori_common.TickChangeData()
        tick.ticker = tickData['code'][0]
        tick.price = tickData['price'][0]
        return tick
    
    def on_recv_rsp(self, rsp_pb):
        ret, data = super(QuoteTicker,self).on_recv_rsp(rsp_pb)
        
        if ret == RET_OK and self.event!=None:
            self.event(self.deconstructTickerData(data))
"""
