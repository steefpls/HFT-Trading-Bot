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
from irori import irori_constants
from irori.common import *
from irori.BrokerBase import BrokerBase
from irori.irori_constants import GST

class BacktestBroker(BrokerBase):
    def __init__(self):
        super().__init__()
        
        self.brokerForFees:Broker = None

        self.order_event:callable = None

        self.order_id_tracker:int

        self.shares_owned_list: list[OwnedStock] = []
        self.shorts_owned_list: list[OwnedShort] = []

        self.buy_order_list: list[BuyOrder] = []
        self.sell_order_list: list[SellOrder] = []

        self.short_open_list: list[ShortOrder] = []
        self.short_close_list: list[SellOrder] = []

        self.transaction_list = []
        self.ticker_list = []

        self.working_currency = 0 #current funds
        self.total_fees = 0 #fee tracking
        self.total_short_scalps = 0
        self.unprofitable_trades = 0
        self.order_id_tracker = 0
        
        self.stop_buy_list: list[BuyOrder] = []
        self.stop_sell_list: list[SellOrder] = []
        self.stop_short_open_list: list[ShortOrder] = []
        self.stop_short_sell_list: list[SellOrder] = []
        self.trailing_stop_loss_list = []

        self.activeLong = False

        self.shortToggle = True

        self.brokerForFees = Broker.MOOMOO
        self.toggle_fees = True
        self.toggle_margin = irori_constants.ALLOW_MARGIN_TRADING
        self.money_owed_to_broker = 0.0

        self.current_tick = 0
        
    def setup_broker(self,brokerForFees:Broker):
        self.brokerForFees = brokerForFees

    def setup_callbacks(self, tick_event_callable:callable, order_event_callable:callable, tickers: Tickers):
        self.tick_event = tick_event_callable
        self.order_event = order_event_callable

    def setup_first_tick(self, f: TickChangeData):
        tick_exist = False
        ####################
        # Ticker: T1 T2 T3
        # Data:   P1 P2 P3
        # Data is latest price

        self.set_current_price(f.ticker, f.price)

        self.current_time = f.time
        self.current_tick += 1

        if not tick_exist:
            tick_data = [f.ticker, f.price]
            self.ticker_list.append(tick_data)

    def trigger_tick_callback(self, f: TickChangeData):
        tick_exist = False
        ####################
        # Ticker: T1 T2 T3
        # Data:   P1 P2 P3
        # Data is latest price

        self.set_current_price(f.ticker, f.price)

        self.current_time = f.time
        self.current_tick += 1

        if not tick_exist:
            tick_data = [f.ticker, f.price]
            self.ticker_list.append(tick_data)

        if self.tick_event is not None:
            self.tick_event(f)
            self.fill_orders()
            self.check_force_liquidate()

    def set_current_price(self, ticker: str, price: float):
        for tick in self.ticker_list:
            if ticker == tick[0]:
                tick[1] = price
                return True
            
        return False

    def get_current_price(self, ticker: str)->int:
        for tick in self.ticker_list:
            if ticker == tick[0]:
                return tick[1]
        return 0        
    
    def query_stock_briefs(self, stock_briefs_query: StockBriefsQuery)->StockBriefsResponse:
        response: StockBriefsResponse = StockBriefsResponse()
        for ticker in self.ticker_list:
            if ticker[0] in stock_briefs_query.tickerList:
                response.add_price(ticker[0], ticker[1])
        return response

    def trigger_order_callback(self, frame: OrderChangeData):
        if self.order_event is not None:
            self.order_event(frame)
        if (frame.order_status == OrderStatus.FILLED and self.mediator):
            self.mediator.resolve_purchase(frame.ticker, self.current_time, frame.filled_quantity, frame.avg_fill_price, frame.commissionAndFee, frame.action)

    def get_account_details(self, acc_detail_obj : AccountQuery)->AccountResponse:
        response = AccountResponse()
        response.cash_balance = self.working_currency
        current_positions_value = 0.0
        positions_entered_value = 0.0
        for shares in self.shares_owned_list:
            current_positions_value+=self.get_current_price(shares.ticker) * shares.num_shares
            positions_entered_value+=shares.avg_price * shares.num_shares
        for shorts in self.shorts_owned_list:
            current_positions_value-= self.get_current_price(shorts.ticker) * shorts.num_shares
            positions_entered_value-= shorts.price * shorts.num_shares

        response.unrealized_pl = current_positions_value-positions_entered_value
        response.assets_value = self.working_currency + current_positions_value
        response.gross_position_value = response.assets_value - self.money_owed_to_broker

        response.available_cash_for_withdrawal = response.cash_balance
        response.available_cash_for_trading = response.cash_balance
        response.buying_power = response.cash_balance*4

        return response

    def modify_order(self, modify_order_command: ModifyOrderCommand)->int:
        error_msg = ''
        remarks = ''
        status_code = IroriOrderStatusCode.ERROR

        success = True
        id_found = False

        orderChangeData = OrderChangeData()

        order_id_modified = -1

        for i in self.buy_order_list:
            if modify_order_command.orderID == i.block_id:
                id_found = True
                order_id_modified = i.block_id
                if(modify_order_command.new_quantity*modify_order_command.new_price > self.working_currency):
                    success = False
                    error_msg = 'Unable to modify order due to lack of working currency'
                else:
                    i.num_shares = modify_order_command.new_quantity
                    i.limit_price = modify_order_command.new_price
                    orderChangeData.order_type = i.order_type
                    success = True
        
        if not id_found:
            for i in self.sell_order_list:
                if modify_order_command.orderID == i.block_id:
                    order_id_modified = i.block_id
                    if(modify_order_command.new_quantity > self.total_shares_sellable()):
                        success = False
                        error_msg = 'Unable to modify order due to lack of shares sellable'
                    else:
                        i.num_shares = modify_order_command.new_quantity
                        i.limit_price = modify_order_command.new_price
                        orderChangeData.order_type = i.order_type
                        success = True
            
        if not id_found:
            for i in self.short_open_list:
                if modify_order_command.orderID == i.block_id:
                    order_id_modified = i.block_id
                    if(modify_order_command.new_quantity*modify_order_command.new_price > self.working_currency):
                        success = False
                        error_msg = 'Unable to modify order due to lack of working currency'
                    else:
                        i.num_shares = modify_order_command.new_quantity
                        i.limit_price = modify_order_command.new_price
                        orderChangeData.order_type = i.order_type
                        success = True
            
        if not id_found:
            for i in self.short_close_list:
                if modify_order_command.orderID == i.block_id:
                    order_id_modified = i.block_id
                    if(modify_order_command.new_quantity > self.total_shorts_sellable()):
                        success = False
                        error_msg = 'Unable to modify order due to lack of shorts sellable'
                    else:
                        i.num_shares = modify_order_command.new_quantity
                        i.limit_price = modify_order_command.new_price
                        orderChangeData.order_type = i.order_type
                        success = True
        
        orderChangeData.orderID = order_id_modified
        
        orderChangeData.action = OrderAction.MODIFY
        orderChangeData.limit_price = modify_order_command.new_price
        orderChangeData.total_quantity = modify_order_command.new_quantity
        if success:
            orderChangeData.order_status = OrderStatus.OTHERS
            status_code = IroriOrderStatusCode.SUCCESSFUL
        else:
            orderChangeData.order_status = OrderStatus.FAILED
            
        self.trigger_order_callback(orderChangeData)

        return IroriOrderResponse(order_id_modified, error_msg, remarks, status_code)
        
    # buy order list is passed in 
    def buy_shares(self, buy_order_list: list, buy_command: OrderCommand, type:OrderType)->int:
        success = True
        price = 0
        stop_price = 0
        order_type = OrderType.NONE
        quantity = (int)(buy_command.quantity)
        orderChangeData = OrderChangeData()

        error_message = ''
        remarks = ''
        status_code = IroriOrderStatusCode.SUCCESSFUL

        # If no leverage and not enough currency to buy, dont place buy order
        if not self.toggle_margin and self.working_currency < price * quantity:
            error_message = f"Buying shares: Insufficient funds to place order. Current {self.working_currency} Required {price * quantity}"
            success = False
        elif quantity <= 0:
            error_message = f"Buying shares: Buying of quantity {quantity} is not allowed"
            success = False
        elif self.has_short_order(buy_command.ticker):
            error_message = "Buying shares: Cannot long while going short"
            success = False

        # For limit and market, places in buy_order_list
        # For stop orders, places in stop_buy_list
        if type is OrderType.LIMIT:
            price = buy_command.price
            order_type = OrderType.LIMIT
        elif type is OrderType.MARKET:
            price = self.get_current_price(buy_command.ticker)
            order_type = OrderType.MARKET
        elif type is OrderType.STOP:
            price = 0
            stop_price = buy_command.aux_price
            order_type = OrderType.STOP
        elif type is OrderType.STOP_LMT:
            price = buy_command.price
            stop_price = buy_command.aux_price
            order_type = OrderType.STOP_LMT
        else:
            error_message = "Buying shares: Invalid order type"
            success = False
        
        self.order_id_tracker+=1
        
        for i in range(len(buy_order_list)):
            if (buy_order_list[i].block_id == self.order_id_tracker):
                print("Block ID already exists in buy order list")
                success = False

        for x in range(len(self.shares_owned_list)):
            if (self.shares_owned_list[x].block_id == self.order_id_tracker):
                print("Block ID already exists in shares owned list")
                success = False

        order = BuyOrder(block_id = self.order_id_tracker,ticker = buy_command.ticker, num_shares=quantity, order_type=type)
        order.limit_price = price
        order.stop_price = stop_price
        orderChangeData.order_type = order_type

        if success:
            buy_order_list.append(order)

        orderChangeData.ticker = order.ticker
        orderChangeData.orderID = self.order_id_tracker
        orderChangeData.action = OrderAction.BUY
        orderChangeData.limit_price = order.limit_price
        orderChangeData.total_quantity = quantity
        orderChangeData.stop_price = order.stop_price
        orderChangeData.order_type = order.order_type
        if success:
            orderChangeData.order_status = OrderStatus.NEW
            status_code = IroriOrderStatusCode.SUCCESSFUL
        else:
            orderChangeData.order_status = OrderStatus.FAILED
            status_code = IroriOrderStatusCode.ERROR
            order.block_id = -1
        
        #print(f"Placing buy order for {buy_command.quantity} shares.")
        orderChangeData.error_message = error_message
        self.trigger_order_callback(orderChangeData)
        
        return IroriOrderResponse(order.block_id, error_message, remarks, status_code)
    
    def sell_shares(self, sell_order_list:list, sell_command: OrderCommand, type:OrderType)->int:
        success = True
        orderChangeData = OrderChangeData()
        error_message = ''
        remarks = ''
        status_code = IroriOrderStatusCode.SUCCESSFUL

        #checks to see if sell amount is greater than shares held minus existing sell order amount, throws an error if it is
        if(sell_command.quantity > self.total_shares_sellable(sell_command.ticker)):
            error_message = "Selling shares: Not enough shares to sell"
            success = False
        elif sell_command.quantity <= 0:
            error_message = f"Selling shares: Sell quantity cannot be {sell_command.quantity}"
            success = False
        
        self.order_id_tracker+=1
        
        for i in range(len(sell_order_list)):
            if (sell_order_list[i].block_id == self.order_id_tracker):
                success = False
        for x in range(len(self.shares_owned_list)):
            if (self.shares_owned_list[x].block_id == self.order_id_tracker):
                success = False
            
        order = SellOrder(num_shares = sell_command.quantity,\
                            block_id = self.order_id_tracker,\
                            ticker=sell_command.ticker,\
                                order_type=type)
        
        if type is OrderType.LIMIT:
            # order.limit_price = sell_command.price
            order.limit_price = sell_command.price
            orderChangeData.order_type = OrderType.LIMIT
        elif type is OrderType.MARKET:
            order.limit_price = self.get_current_price(sell_command.ticker)
            orderChangeData.order_type = OrderType.MARKET
        elif type is OrderType.STOP:
            order.stop_price = sell_command.aux_price
            orderChangeData.order_type = OrderType.STOP
        elif type is OrderType.STOP_LMT:
            order.limit_price = sell_command.price
            order.stop_price = sell_command.aux_price
            orderChangeData.order_type = OrderType.STOP_LMT
        elif type is OrderType.TRAIL:
            order.trail_type = sell_command.trail_type
            order.trail_price = sell_command.trail_price
            orderChangeData.order_type = OrderType.TRAIL
        else:
            error_message = "Selling shares: invalid order type"
            success = False
        
        if success:
            sell_order_list.append(order)
        orderChangeData.ticker = order.ticker
        orderChangeData.orderID = self.order_id_tracker
        orderChangeData.action = OrderAction.SELL
        orderChangeData.limit_price = order.limit_price
        orderChangeData.total_quantity = sell_command.quantity
        orderChangeData.order_type = order.order_type
        if success:
            orderChangeData.order_status = OrderStatus.NEW
            status_code = IroriOrderStatusCode.SUCCESSFUL
        else:
            orderChangeData.order_status = OrderStatus.FAILED
            status_code = IroriOrderStatusCode.ERROR
            order.block_id = -1

        #print(f"Placing market sell order for {sell_command.quantity} shares.")
        orderChangeData.error_message = error_message
        self.trigger_order_callback(orderChangeData)
        
        return IroriOrderResponse(order.block_id, error_message, remarks, status_code)
    
    # buy
    def buy_limit_order(self, buy_command : OrderCommand)->int:
        return self.buy_shares(self.buy_order_list, buy_command, OrderType.LIMIT)
    
    def buy_market_order(self, buy_command : OrderCommand)->int:
        return self.buy_shares(self.buy_order_list, buy_command, OrderType.MARKET)
    
    def stop_market_buy_order(self, stop_buy_command : OrderCommand)->int:
        return self.buy_shares(self.stop_buy_list, stop_buy_command, OrderType.STOP)
        #print(f"Placing stop loss buy order for {stop_buy_command.quantity} shares.")
        #self.trigger_order_callback(orderChangeData)

    def stop_limit_buy_order(self, stop_buy_command : OrderCommand)->int:
        return self.buy_shares(self.stop_buy_list, stop_buy_command, OrderType.STOP_LMT)
        #print(f"Placing stop loss buy order for {stop_buy_command.quantity} shares.")
        #self.trigger_order_callback(orderChangeData)

    # sell
    def sell_limit_order(self, sell_command : OrderCommand)->int:
        return self.sell_shares(self.sell_order_list, sell_command, OrderType.LIMIT)
        
    def sell_market_order(self, sell_command: OrderCommand)->int:
        return self.sell_shares(self.sell_order_list, sell_command, OrderType.MARKET)

    def stop_market_sell_order(self, stop_sell_command : OrderCommand)->int:
        return self.sell_shares(self.stop_sell_list, stop_sell_command, OrderType.STOP)
        #self.trigger_order_callback(orderChangeData)    
        #print(f"Placing stop loss sell order for {stop_sell_command.quantity} shares.")

    def stop_limit_sell_order(self, stop_sell_command : OrderCommand)->int:
        return self.sell_shares(self.stop_sell_list, stop_sell_command, OrderType.STOP_LMT)
        #self.trigger_order_callback(orderChangeData)    
        #print(f"Placing stop loss sell order for {stop_sell_command.quantity} shares.")

    def trailing_stop_market_order(self, trailing_command: OrderCommand)->int:
        return self.sell_shares(self.trailing_stop_loss_list, trailing_command, OrderType.TRAIL)
    
    def trailing_stop_limit_order(self, trailing_command: OrderCommand)->int:
        return self.sell_shares(self.trailing_stop_loss_list, trailing_command, OrderType.TRAIL_LMT)


    def short_open_order(self, short_order_list:list, short_command: OrderCommand, type:OrderType)->int:
        """
        Short order borrowing stocks from the broker and selling it immediately.
        """
        success = True
        price = 0
        stop_price = 0
        order_type = OrderType.NONE
        orderChangeData = OrderChangeData()

        error_message = ''
        remarks = ''
        status_code = IroriOrderStatusCode.SUCCESSFUL

        if type is OrderType.LIMIT:
            price = short_command.price
            order_type = OrderType.LIMIT
        elif type is OrderType.MARKET:
            price = self.get_current_price(short_command.ticker)
            order_type = OrderType.MARKET
        elif type is OrderType.STOP: # Stop Market
            stop_price = short_command.aux_price
            order_type = OrderType.STOP
        elif type is OrderType.STOP_LMT:
            price = short_command.price
            stop_price = short_command.aux_price
            order_type = OrderType.STOP
        else:
            error_message = "Short open: Invalid order type"
            success = False

        self.order_id_tracker+=1  

        for i in range(len(short_order_list)):
            if (short_order_list[i].block_id == self.order_id_tracker):
                print("Block ID already exists in buy order list")
                success = False
        for x in range(len(self.shorts_owned_list)):
            if (self.shorts_owned_list[x].block_id == self.order_id_tracker):
                print("Block ID already exists in shares owned list")
                success = False
        
        quantity = short_command.quantity

        if not self.shortToggle:
            error_message = "Short open: Shorts not toggled"
            success = False
        elif quantity <= 0:
            error_message = f"Short open: Quantity cannot be {quantity}"
            success = False
        elif self.has_long_order(short_command.ticker):
            error_message = "Short open: Cannot short while going long"
            success = False
            
        order = ShortOrder(block_id = self.order_id_tracker, 
                           lim_price=self.get_current_price(short_command.ticker),
                           ticker=short_command.ticker, 
                           num_shares=short_command.quantity,
                           order_type=order_type)
        
        if success:
            short_order_list.append(order)
        
        orderChangeData.ticker = order.ticker
        orderChangeData.orderID = self.order_id_tracker
        orderChangeData.order_type = order_type
        orderChangeData.action = OrderAction.SHORT_OPEN
        orderChangeData.limit_price = price
        orderChangeData.stop_price = stop_price
        orderChangeData.total_quantity = short_command.quantity
        if success:
            orderChangeData.order_status = OrderStatus.NEW
            status_code = IroriOrderStatusCode.SUCCESSFUL
        else:
            orderChangeData.order_status = OrderStatus.FAILED
            status_code = IroriOrderStatusCode.ERROR
            order.block_id = -1

        orderChangeData.is_short = True
        
        # print(f"Placing market short order for {short_command.quantity} shares.")
        orderChangeData.error_message = error_message
        self.trigger_order_callback(orderChangeData)
        
        return IroriOrderResponse(order.block_id, error_message, remarks, status_code)


    def short_close_order(self, short_order_list:list, short_command: OrderCommand, type:OrderType)->int:
        success = True
        orderChangeData = OrderChangeData()
        error_message = ''
        remarks = ''
        status_code = IroriOrderStatusCode.SUCCESSFUL

        if(short_command.quantity > self.total_shorts_sellable(short_command.ticker)):
            error_message = "Shorts close: No shorts to close"
            success = False
        elif short_command.quantity <= 0:
            error_message = f"Shorts close: Closing shorts quantity cannot be {short_command.quantity}"
            success = False
    
        self.order_id_tracker+=1
        
        for i in range(len(short_order_list)):
            if (short_order_list[i].block_id == self.order_id_tracker):
                success = False
        for x in range(len(self.shares_owned_list)):
            if (self.shares_owned_list[x].block_id == self.order_id_tracker):
                success = False

        order = SellOrder(num_shares = short_command.quantity,\
                            block_id = self.order_id_tracker,\
                            ticker = short_command.ticker,\
                                order_type=type)
        
        if type is OrderType.LIMIT:
            # order.limit_price = sell_command.price
            order.limit_price = short_command.price
            orderChangeData.order_type = OrderType.LIMIT
        elif type is OrderType.MARKET:
            order.limit_price = self.get_current_price(short_command.ticker)
            orderChangeData.order_type = OrderType.MARKET
        elif type is OrderType.STOP: # Stop Market
            order.stop_price = short_command.aux_price
            orderChangeData.order_type = OrderType.STOP
        elif type is OrderType.STOP_LMT:
            order.limit_price = short_command.price
            order.stop_price = short_command.aux_price
            orderChangeData.order_type = OrderType.STOP_LMT
        else:
            error_message = "Shorts close: Invalid order type"
            success = False
        
        if success:
            short_order_list.append(order)
        orderChangeData.ticker = order.ticker
        orderChangeData.orderID = self.order_id_tracker
        orderChangeData.action = OrderAction.SHORT_CLOSE
        orderChangeData.limit_price = order.limit_price
        orderChangeData.total_quantity = short_command.quantity
        if success:
            orderChangeData.order_status = OrderStatus.NEW
            status_code = IroriOrderStatusCode.SUCCESSFUL
        else:
            orderChangeData.order_status = OrderStatus.FAILED
            status_code = IroriOrderStatusCode.ERROR
            order.block_id = -1

        orderChangeData.is_short = True

        # print(f"Placing market sell order for {short_command.quantity} shares.")
        orderChangeData.error_message = error_message
        self.trigger_order_callback(orderChangeData)

        return IroriOrderResponse(order.block_id, error_message, remarks, status_code)

    #Short Function, puts in a short order
    def short_open_limit_order(self, short_buy:OrderCommand)->int:
        return self.short_open_order(self.short_open_list, short_buy, OrderType.LIMIT)
    
    def short_open_market_order(self, short_buy:OrderCommand)->int:
        return self.short_open_order(self.short_open_list, short_buy, OrderType.MARKET)

    def short_open_stop_market_order(self, short_buy:OrderCommand):
        return self.short_open_order(self.stop_short_open_list, short_buy, OrderType.STOP)
    
    def short_open_stop_limit_order(self, short_buy:OrderCommand):
        return self.short_open_order(self.stop_short_open_list, short_buy, OrderType.STOP_LMT)
    
    #Short Sell Function puts in a short sell order
    def short_close_limit_order(self, short_sell:OrderCommand)->int:
        return self.short_close_order(self.short_close_list, short_sell, OrderType.LIMIT)
    
    def short_close_market_order(self, short_sell:OrderCommand)->int:
        return self.short_close_order(self.short_close_list, short_sell, OrderType.MARKET)
    
    def short_close_stop_market_order(self, short_sell_command:OrderCommand)->int:
        return self.short_close_order(self.stop_short_sell_list, short_sell_command, OrderType.STOP)
    
    def short_close_stop_limit_order(self, short_sell_command:OrderCommand)->int:
        return self.short_close_order(self.stop_short_sell_list, short_sell_command, OrderType.STOP_LMT)
    
    def cancel_order(self, cancel_order_command: CancelOrderCommand)->int:
        orderChangeData = OrderChangeData()
        removed = [False,0,0, OrderType.NONE]

        id = cancel_order_command.orderID
        removed = self.remove_from_order_list(self.buy_order_list, id)
        if not removed[0]:
            removed = self.remove_from_order_list(self.sell_order_list, id)
        if not removed [0]:
            removed = self.remove_from_order_list(self.stop_sell_list, id)
        if not removed [0]:
            removed = self.remove_from_order_list(self.stop_buy_list, id)
        if not removed[0]:
            removed = self.remove_from_order_list(self.short_open_list, id)
        if not removed[0]:
            removed = self.remove_from_order_list(self.short_close_list, id)

        orderChangeData.action = OrderAction.CANCEL
        orderChangeData.limit_price = removed[1]
        orderChangeData.total_quantity = removed[2]
        orderChangeData.order_type = removed[3]
        orderChangeData.orderID = id

        if removed[0]:
            orderChangeData.order_status = OrderStatus.CANCELLED
            self.trigger_order_callback(orderChangeData)
            return IroriOrderResponse(id, '', f'Successfully cancelled order with id {id}')
        else:
            orderChangeData.order_status = OrderStatus.FAILED
            self.trigger_order_callback(orderChangeData)
            return IroriOrderResponse(-1, f'Failed to cancel order with id {id}', '', IroriOrderStatusCode.ERROR)

    def remove_from_order_list(self, order_list:list, order_id)->bool:
        removed = False
        price = 0
        quantity = 0
        order_type = OrderType.NONE

        for i in range(0, len(order_list)):
            if order_list[i].block_id == order_id:
                price = order_list[i].limit_price
                quantity = order_list[i].num_shares
                order_type = order_list[i].order_type
                order_list.pop(i)
                removed = True
                
                break
        return [removed, price, quantity, order_type]
                
    def clear_existing_orders(self, clear_order : ClearExistingOrderCommand):
        # TODO
        # self.buy_limit_list.clear()
        # self.sell_limit_list.clear()
        # self.short_buy_list.clear()
        # self.short_sell_list.clear()
        pass

    def get_positions(self):
        """
        Returns all positions held by default
        """
        response = PositionsResponse()
        response.stockList = []

        for shares in self.shares_owned_list:
            stock = Stock()
            stock.ticker = shares.ticker
            stock.quantity = shares.num_shares
            stock.average_cost = shares.avg_price
            stock.market_price = self.get_current_price(shares.ticker) # is there a function to get the current price of a stock by looking up the ticker? this needs trigger_tick_callback to return multiple tickers data
            response.stockList.append(stock)

        for shorts in self.shorts_owned_list:
            short = Stock()
            short.ticker = shorts.ticker
            short.quantity = shorts.num_shares
            short.average_cost = shorts.price
            short.market_price = self.get_current_price(shorts.ticker) # is there a function to get the current price of a stock by looking up the ticker? this needs trigger_tick_callback to return multiple tickers data
            response.stockList.append(short)

        return response
    
    def get_total_asset_value(self):
        asset_value = self.working_currency

        for shares in self.shares_owned_list:
            asset_value += shares.num_shares * self.get_current_price(ticker=shares.ticker)
        
        return asset_value

    def get_ticker_asset_value(self, ticker):
        asset_value = 0.0

        for shares in self.shares_owned_list:
            if shares.ticker == ticker:
                asset_value += shares.num_shares * self.get_current_price(ticker=ticker)
        
        return asset_value

    def sell_all_existing_stocks(self):
        for i in range(len(self.shares_owned_list)):
            i_ticker = self.shares_owned_list[i].ticker
            #calculate total cost
            total_cost = self.get_current_price(i_ticker)*self.shares_owned_list[i].num_shares
            #calculate total fees
            total_fees = self.calculate_fees(self.get_current_price(i_ticker), self.shares_owned_list[i].num_shares,False)
            #add total cost to working currency
            self.working_currency = self.working_currency + total_cost - total_fees
        self.shares_owned_list.clear()
        return self.working_currency
    
    def sell_all_existing_stocks_for_ticker(self, ticker):
        for i in range(len(self.shares_owned_list)):
            i_ticker = self.shares_owned_list[i].ticker
            if i_ticker != ticker:
                continue

            #calculate total cost
            total_cost = self.get_current_price(i_ticker)*self.shares_owned_list[i].num_shares
            #calculate total fees
            total_fees = self.calculate_fees(self.get_current_price(i_ticker), self.shares_owned_list[i].num_shares,False)
            #add total cost to working currency
            self.working_currency = self.working_currency + total_cost - total_fees

            self.shares_owned_list.remove(self.shares_owned_list[i])
        
        return self.working_currency

    def exit_all_positions_immediately(self, clear_order : ClearExistingOrderCommand):
        pass

    def stop(self):
        super().stop()

    def fill_buy_order(self, i):
        buy_order: BuyOrder = self.buy_order_list[i]
        
        current_price = self.get_current_price(buy_order.ticker)
        buy_position_size = current_price * buy_order.num_shares
        fees_incurred = self.calculate_fees(current_price,buy_order.num_shares,True)

        total_buy_cost = buy_position_size + fees_incurred

        difference = total_buy_cost - self.working_currency
        if difference > 0:
            if self.toggle_margin:
                self.working_currency = 0
                self.borrow_money_from_broker(difference)
            else:
                return
        else:
            self.working_currency -= total_buy_cost

        self.total_fees = self.total_fees + fees_incurred
            
        # Add asset part to owned stock.
        newStock = OwnedStock(block_id=buy_order.block_id, 
                                            ticker=buy_order.ticker, 
                                            price=current_price, 
                                            num_shares=buy_order.num_shares)

        #check the existing list for any matches before we run loops to find the specific match
        if any(owned.ticker == newStock.ticker for owned in self.shares_owned_list):
            for owned in self.shares_owned_list:
                if newStock.ticker == owned.ticker:
                    # avg price = (old total price + new position price) / new total shares
                    old_total_price = owned.num_shares * owned.avg_price
                    owned.num_shares += newStock.num_shares
                    owned.avg_price = (old_total_price + buy_position_size) / owned.num_shares
        # if theres no matching ticker THEN we append a new ticker to the shares owned list  
        else:
            self.shares_owned_list.append(newStock)
       
        #create transaction and add to list
        self.transaction_list.append(Transaction(ticker=buy_order.ticker,\
                                                    p_price=current_price,\
                                                    num_shares=self.buy_order_list[i].num_shares,\
                                                    block_id=self.buy_order_list[i].block_id,\
                                                    is_buy=True,\
                                                    is_recalculate=False,\
                                                    tick_number = self.current_tick))

        # TODO: Add returns gross qty as well??
        orderChangeData = OrderChangeData()
        orderChangeData.orderID = buy_order.block_id
        orderChangeData.ticker = buy_order.ticker
        orderChangeData.action = OrderAction.BUY
        orderChangeData.avg_fill_price = current_price
        orderChangeData.filled_quantity = buy_order.num_shares
        orderChangeData.total_quantity = buy_order.num_shares
        orderChangeData.commissionAndFee = fees_incurred
        orderChangeData.order_status = OrderStatus.FILLED
        orderChangeData.order_type = buy_order.order_type

        self.buy_order_list.remove(buy_order)

        # print(f"filled buy order for {buy_order.num_shares} shares.")
        self.trigger_order_callback(orderChangeData)
    
    def fill_sell_order(self, i):
        sell_order: SellOrder = self.sell_order_list[i]
        current_price = self.get_current_price(sell_order.ticker)
        sell_fee = self.calculate_fees(current_price,sell_order.num_shares,False)

        # Find quantity owned, number of instances, money owed to broker
        owned_stock: OwnedStock = None
        for shares in self.shares_owned_list:
            if shares.ticker != sell_order.ticker:
                continue
            owned_stock = shares
            break
        
        # If we dont own stocks with the ticker or we are trying to sell more than shares held, return
        if owned_stock == None or sell_order.num_shares > owned_stock.num_shares:
            return
        
        sell_total_amount = current_price * sell_order.num_shares

        # If working currency becomes negative after selling, abort!! 
        # Some reasons might be because we cant afford fees. 
        # E.g. we have $0 working currency, we sell $1 but fees are $3
        if self.working_currency + sell_total_amount - sell_fee < 0:
            return
        
        self.working_currency += sell_total_amount - sell_fee
        owned_stock.num_shares -= sell_order.num_shares

        self.payback_money_to_broker()

        #remove if quantity is 0
        if owned_stock.num_shares == 0:
            self.shares_owned_list.remove(owned_stock)

        self.total_fees = self.total_fees + sell_fee
        #print(f"\nBought Block {buyOrderList[i].blockID} at {lastSale}")
        #create transaction and add to list
        self.transaction_list.append(Transaction(ticker=sell_order.ticker,\
                                                    p_price=current_price,\
                                                    num_shares=sell_order.num_shares,\
                                                    block_id=sell_order.block_id,\
                                                    is_buy=False,\
                                                    is_recalculate=False,\
                                                    tick_number = self.current_tick))

        orderChangeData = OrderChangeData()
        orderChangeData.orderID = sell_order.block_id
        orderChangeData.ticker = sell_order.ticker
        orderChangeData.action = OrderAction.SELL
        orderChangeData.avg_fill_price = current_price
        orderChangeData.filled_quantity = sell_order.num_shares
        orderChangeData.total_quantity = sell_order.num_shares
        orderChangeData.commissionAndFee = sell_fee
        orderChangeData.order_status = OrderStatus.FILLED
        orderChangeData.order_type = sell_order.order_type

        self.sell_order_list.remove(sell_order)

        # print(f"filled sell order for {sell_order.num_shares} shares.")
        self.trigger_order_callback(orderChangeData)

    def fill_stop_buy_order(self, i):
        order: SellOrder = self.stop_sell_list[i]

        if(order.order_type == OrderType.STOP):
            buy_market_order_command = OrderCommand(order.ticker, order.num_shares, Broker.BACKTEST)
            self.stop_buy_list.remove(order)
            self.buy_market_order(buy_market_order_command)

        elif(order.order_type == OrderType.STOP_LMT):
            buy_limit_order_command = OrderCommand(order.ticker, order.limit_price, order.num_shares, Broker.BACKTEST)
            self.stop_buy_list.remove(order)
            self.buy_limit_order(buy_limit_order_command)

    def fill_stop_sell_order(self, i):
        order: SellOrder = self.stop_sell_list[i]
        num_shares_to_sell = order.num_shares

        has_enough_owned_stocks_to_sell = num_shares_to_sell > self.total_shares_sellable(order.ticker)

        if not has_enough_owned_stocks_to_sell:
            orderChangeData = OrderChangeData()
            orderChangeData.orderID = order.block_id
            orderChangeData.action = OrderAction.SELL
            orderChangeData.order_status = OrderStatus.FAILED
            orderChangeData.order_type = order.order_type
            self.stop_sell_list.remove(order)
            self.trigger_order_callback(orderChangeData)
            return

        if(order.order_type == OrderType.STOP or order.order_type == OrderType.TRAIL):
            sell_market_order_command = OrderCommand(ticker = order.ticker, quantity = num_shares_to_sell)
            print(f"=============== stop price triggered, selling {num_shares_to_sell} stocks of {order.order_type} ========================")
            self.stop_sell_list.remove(order)
            self.sell_market_order(sell_market_order_command)

        elif(order.order_type == OrderType.STOP_LMT or order.order_type == OrderType.TRAIL_LMT):
            sell_limit_order_command = OrderCommand(ticker = order.ticker,price = order.limit_price, quantity = num_shares_to_sell)
            self.stop_sell_list.remove(order)
            self.sell_limit_order(sell_limit_order_command)
        
        orderChangeData = OrderChangeData()
        orderChangeData.orderID = order.block_id
        orderChangeData.action = OrderAction.SELL
        orderChangeData.order_status = OrderStatus.FILLED
        orderChangeData.order_type = order.order_type
        self.trigger_order_callback(orderChangeData)

    
    def update_trailing_stop_loss(self, i):
        new_stop_price = 0
        order = self.trailing_stop_loss_list[i]
        current_price = self.get_current_price(order.ticker)
        if order.trail_type is TrailType.PERCENT:
            new_stop_price = current_price * (1-(order.trail_price/100))
        elif order.trail_type is TrailType.VALUE:
            new_stop_price = current_price-order.trail_price

        if new_stop_price>order.stop_price:
            order.stop_price = new_stop_price
        
    def fill_short_open(self, i):
        short_order: ShortOrder = self.short_open_list[i]
        current_price = self.get_current_price(short_order.ticker)

        open_cost = current_price * short_order.num_shares
        fees_incurred = self.calculate_fees(short_order.limit_price, short_order.num_shares, False)
        cost = open_cost - fees_incurred
        self.working_currency = self.working_currency + cost

        #Declaring owned short first so that it is easier to manipulate
        newShort = OwnedShort(short_order.block_id,
                              short_order.ticker, 
                              current_price, 
                              short_order.num_shares)

        if any(ownedShrt.ticker == newShort.ticker for ownedShrt in self.shorts_owned_list):
            for ownedShrt in self.shorts_owned_list:
                if newShort.ticker == ownedShrt.ticker:
                    # avg price = (old total price + new position price) / new total shares
                    old_total_price = ownedShrt.num_shares * ownedShrt.avg_price
                    ownedShrt.num_shares += newShort.num_shares
                    ownedShrt.avg_price = (old_total_price + open_cost) / ownedShrt.num_shares

        # if theres no matching ticker THAN we append a new ticker to the shares owned list  
        else:
            self.shorts_owned_list.append(newShort)

        # self.shorts_owned_list.append(newShort)
        #create transaction and add to list
        self.transaction_list.append(Transaction(ticker=short_order.ticker,\
                                                p_price=current_price, \
                                                num_shares=short_order.num_shares,\
                                                block_id=short_order.block_id,\
                                                is_buy=False,\
                                                is_recalculate=False,\
                                                tick_number=self.current_tick))

        self.total_fees = self.total_fees + fees_incurred

        orderChangeData = OrderChangeData()
        orderChangeData.orderID = short_order.block_id
        orderChangeData.ticker = short_order.ticker
        orderChangeData.action = OrderAction.SHORT_OPEN
        orderChangeData.avg_fill_price = current_price
        orderChangeData.filled_quantity = short_order.num_shares
        orderChangeData.total_quantity = short_order.num_shares
        orderChangeData.commissionAndFee = fees_incurred
        orderChangeData.order_status = OrderStatus.FILLED
        orderChangeData.order_type = short_order.order_type
        orderChangeData.is_short = True

        self.short_open_list.pop(i)

        #print(f"\nShort sold Block {shortBuyList[i].blockID} at {lastSale} ")
        #self.pop_off_shorts_owned_list_after_selling(short_order.num_shares)
        # tempVar = self.clearShortStopLoss(self.short_buy_list[i].block_id,self.short_stop_loss_list)
        # if isinstance(tempVar,list):
        #     self.short_stop_loss_list = tempVar

        self.trigger_order_callback(orderChangeData)

    def fill_short_close(self, i):
        short_order: ShortOrder = self.short_close_list[i]
        current_price = self.get_current_price(short_order.ticker)
        
        owned_short: OwnedShort = next(filter(lambda x: x.ticker == short_order.ticker, self.shorts_owned_list), None)

        if owned_short is None:
            return
        
        if short_order.num_shares > owned_short.num_shares:
            return

        #short calculation logic
        short_fee = self.calculate_fees(current_price,short_order.num_shares,False)
        short_amt = (current_price*short_order.num_shares)-short_fee
        self.working_currency = self.working_currency - short_amt
        
        # Remove our owned shorts num shares. If we closed all, remove it from owned shorts entirely
        owned_short.num_shares -= short_order.num_shares
        if owned_short.num_shares <= 0:
            self.shorts_owned_list.remove(owned_short)
        
        # TODO: Maybe calculate new average price?
        
        self.total_fees = self.total_fees + self.calculate_fees(current_price,short_order.num_shares,True)
        #print(f"\nBought Block {buyOrderList[i].blockID} at {lastSale}")
        #create transaction and add to list
        self.transaction_list.append(Transaction(ticker=short_order.ticker,\
                                                    p_price=current_price,\
                                                    num_shares=short_order.num_shares,\
                                                    block_id=short_order.block_id,\
                                                    is_buy=True,\
                                                    is_recalculate=False,\
                                                    tick_number = self.current_tick))

        orderChangeData = OrderChangeData()
        orderChangeData.orderID = short_order.block_id
        orderChangeData.ticker = short_order.ticker
        orderChangeData.action = OrderAction.SHORT_CLOSE
        orderChangeData.avg_fill_price = current_price
        orderChangeData.filled_quantity = short_order.num_shares
        orderChangeData.total_quantity = short_order.num_shares
        orderChangeData.commissionAndFee = short_fee
        orderChangeData.order_status = OrderStatus.FILLED
        orderChangeData.order_type = short_order.order_type
        orderChangeData.is_short = True
        orderChangeData.limit_price = owned_short.avg_price

        self.short_close_list.pop(i)

        self.trigger_order_callback(orderChangeData)
        # print(f"filled short sell order for {self.short_buy_list[i].num_shares} shares.")

    def fill_stop_short_open_order(self, i):
        order: ShortOrder = self.stop_short_open_list[i]

        if order.order_type == OrderType.STOP: # Market
            short_open_market_order_command = OrderCommand(order.ticker, order.num_shares, Broker.BACKTEST)
            self.short_open_market_order(short_open_market_order_command)
        elif(order.order_type == OrderType.STOP_LMT): # Limit
            short_open_stop_limit_order_command = OrderCommand(order.ticker,order.limit_price, order.num_shares, Broker.BACKTEST)
            self.short_open_limit_order(short_open_stop_limit_order_command)
    
    def fill_stop_short_close_order(self, i):
        order: SellOrder = self.stop_short_sell_list[i]
        num_stocks_to_sell = order.num_shares

        has_enough_owned_stocks_to_sell = num_stocks_to_sell > self.total_shorts_sellable(order.ticker)

        if not has_enough_owned_stocks_to_sell:
            orderChangeData = OrderChangeData()
            orderChangeData.orderID = order.block_id
            orderChangeData.action = OrderAction.SELL
            orderChangeData.order_status = OrderStatus.FAILED
            orderChangeData.order_type = OrderType.STOP
            self.trigger_order_callback(orderChangeData)
            return
        
        if(order.order_type == OrderType.STOP):
            short_sell_market_order_command = OrderCommand(order.ticker, num_stocks_to_sell, Broker.BACKTEST)
            self.short_close_market_order(short_sell_market_order_command)

        elif(order.order_type == OrderType.STOP_LMT):
            short_close_stop_limit_order_command = OrderCommand(order.ticker, order.limit_price, num_stocks_to_sell,Broker.BACKTEST)
            self.short_close_stop_limit_order(short_close_stop_limit_order_command)

    def fill_orders(self):
        # --- Buy Order Acceptance ---
        for i in range(len(self.buy_order_list) - 1, -1, -1):
            current_price = self.get_current_price(self.buy_order_list[i].ticker)
            if self.buy_order_list[i].limit_price >= current_price or self.buy_order_list[i].order_type == OrderType.MARKET:
                self.fill_buy_order(i)

        # --- Sell Order Acceptance ---
        for i in range(len(self.sell_order_list) - 1, -1, -1):
            current_price = self.get_current_price(self.sell_order_list[i].ticker)
            if self.sell_order_list[i].limit_price <= current_price or self.sell_order_list[i].order_type == OrderType.MARKET:
                self.fill_sell_order(i)

        if self.shortToggle:
            # --- Short Buy Order Acceptance ---
            for i in range(len(self.short_open_list) - 1, -1, -1):
                current_price = self.get_current_price(self.short_open_list[i].ticker)
                if current_price >= self.short_open_list[i].limit_price:
                    self.fill_short_open(i)

            # --- Short Sell Order Acceptance ---
            for i in range(len(self.short_close_list) - 1, -1, -1):
                current_price = self.get_current_price(self.short_close_list[i].ticker)
                if current_price <= self.short_close_list[i].limit_price:
                    self.fill_short_close(i)

        # Stop Logic
        # Check if stop loss is hit
        for i in range(len(self.stop_buy_list) - 1, -1, -1):
            current_price = self.get_current_price(self.stop_buy_list[i].ticker)
            if self.stop_buy_list[i].stop_price >= current_price:
                self.fill_stop_buy_order(i)

        for i in range(len(self.stop_sell_list) - 1, -1, -1):
            current_price = self.get_current_price(self.stop_sell_list[i].ticker)
            if self.stop_sell_list[i].stop_price >= current_price:
                self.fill_stop_sell_order(i)

        # ~~~ Trailing Stop Loss Update ~~~
        for i in range(len(self.trailing_stop_loss_list) - 1, -1, -1):
            current_price = self.get_current_price(self.trailing_stop_loss_list[i].ticker)
            self.update_trailing_stop_loss(i)
            if self.trailing_stop_loss_list[i].stop_price >= current_price:
                self.fill_stop_sell_order(i)

        # ~~~ Short Stop Market Acceptance ~~~
        for i in range(len(self.stop_short_open_list) - 1, -1, -1):
            current_price = self.get_current_price(self.stop_short_open_list[i].ticker)
            if self.stop_short_open_list[i].stop_price <= current_price:
                self.fill_stop_short_open_order(i)

        # ~~~ Short Stop Sell Market Acceptance ~~~
        for i in range(len(self.stop_short_sell_list) - 1, -1, -1):
            current_price = self.get_current_price(self.stop_short_sell_list[i].ticker)
            if self.stop_short_sell_list[i].stop_price <= current_price:
                self.fill_stop_short_close_order(i)

    def total_shares_held(self, ticker)->int:
        for shares in self.shares_owned_list:
            if ticker == shares.ticker:
                shares_held=shares.num_shares
                return shares_held
        return 0
    
    def total_shorts_held(self, ticker)->int:
        for shorts in self.shorts_owned_list:
            if ticker == shorts.ticker:
                shorts_held=shorts.num_shares
                return shorts_held
        return 0
    
    def get_total_sell_orders_num_shares(self, ticker)->int:
        sell_orders_qty = 0
        for sells in self.sell_order_list:
            if sells.ticker == ticker:
                sell_orders_qty+=sells.num_shares
        for sells in self.stop_sell_list:
            if sells.ticker == ticker:
                sell_orders_qty+=sells.num_shares
        return sell_orders_qty
    
    def get_total_sell_short_orders_num_shares(self, ticker)->int:
        sell_short_orders_qty = 0
        for sell_shorts in self.short_close_list:
            if sell_shorts.ticker == ticker:
                sell_short_orders_qty+=sell_shorts.num_shares
        
        for sells in self.stop_short_sell_list:
            if sells.ticker == ticker:
                sell_orders_qty+=sells.num_shares
        return sell_short_orders_qty
    
    def total_shares_sellable(self, ticker)->int:
        shares_held = self.total_shares_held(ticker)
        sell_orders_qty = self.get_total_sell_orders_num_shares(ticker)
        shares_sellable = shares_held - sell_orders_qty
        return shares_sellable
    
    def total_shorts_sellable(self, ticker)->int:
        shorts_held = self.total_shorts_held(ticker)
        short_orders_qty = self.get_total_sell_short_orders_num_shares(ticker)
        shorts_sellable = shorts_held-short_orders_qty
        return shorts_sellable

    def pop_off_shares_owned_list_after_selling(self, sold_qty):
        list_size = len(self.shares_owned_list)

        qty_to_remove = sold_qty

        for i in range(list_size - 1, -1, -1):
            owned_stock = self.shares_owned_list[i]
            
            if qty_to_remove >= owned_stock.num_shares:
                qty_to_remove -= owned_stock.num_shares
                self.shares_owned_list.pop(i)
            else:
                owned_stock.num_shares -= qty_to_remove
                break
    
    def pop_off_shorts_owned_list_after_selling(self, sold_qty):
        list_size = len(self.shorts_owned_list)

        qty_to_remove = sold_qty

        for i in range(list_size - 1, -1, -1):
            owned_short = self.shorts_owned_list[i]
            
            if qty_to_remove >= owned_short.num_shares:
                qty_to_remove -= owned_short.num_shares
                self.shorts_owned_list.pop(i)
            else:
                owned_short.num_shares -= qty_to_remove
                break

    def clearShortStopLoss(self, blockID:int,shortStopLossList):
        for i in range(len(shortStopLossList)):
            if (shortStopLossList[i].blockID == blockID):
                shortStopLossList.pop(i)
                return shortStopLossList
        return -1
    
    #close orders
    def sell_all_shares(self)->bool:
        self.buy_order_list.clear()
        retunVal = False
        if (len(self.shares_owned_list) > 0):
            retunVal = True
        for i in range(len(self.shares_owned_list)):
            #calculate total cost
            sell_order = OrderCommand(ticker = self.shares_owned_list[i].ticker ,price = 0, quantity=self.shares_owned_list[i].num_shares)
            self.sell_market_order(sell_order)
        return retunVal
    
    def close_all_shorts(self)->bool:
        self.short_open_list.clear()
        retunVal = False
        if (len(self.shorts_owned_list) > 0):
            retunVal = True
        for i in range(len(self.shorts_owned_list)):
            #calculate total cost
            short_order = OrderCommand(ticker = self.shorts_owned_list[i].ticker, price = 0, quantity=self.shorts_owned_list[i].num_shares)
            self.short_close_market_order(short_order)
        return retunVal

    def sell_all_positions(self)->bool:
        # close all shorts
        has_shorts_to_close = self.close_all_shorts()
        # sell all shares
        has_shares_to_sell = self.sell_all_shares()

        self.fill_orders()

        if (has_shorts_to_close or has_shares_to_sell):
            return True
        return False
    
    def calculate_fees(self, stock_price:float, num_shares:float, is_buy:bool)->float:
        if not self.toggle_fees:
            return 0
        if self.brokerForFees is Broker.MOOMOO:
            return self.calculate_fees_moomoo(stock_price, num_shares, is_buy)
        elif self.brokerForFees is Broker.TIGER:
            return self.calculate_fees_tiger(stock_price, num_shares, is_buy)
    
    def calculate_fees_moomoo(self, stock_price:float, num_shares:float, is_buy:bool)->float:
        trx_amt = stock_price*num_shares
        commission = 0
        platform_fee = 0.99

        #Fractional shares = if trade size<1 share: commission = 0, platform fees = 0.99% * trx_amt, if platform fees>0.99:platform fees =0.99
        #else if trade size>=1 share: commission = standard US stock trading fees, platform = standard US trading fees

        settlement_fee = 0.003 * num_shares
        if settlement_fee>0.01*trx_amt:
            settlement_fee = 0.01* trx_amt

        sec_fee = 0
        taf_fee = 0

        if not is_buy:

            sec_fee = 0.000008 * trx_amt
            if sec_fee < 0.01:
                sec_fee = 0.01

            taf_fee = 0.000166*num_shares
            if taf_fee<0.01:
                taf_fee=0.01
            elif taf_fee>8.3:
                taf_fee = 8.3
        
        total_fee_value = (commission + platform_fee + settlement_fee + sec_fee + taf_fee)*(1+GST)

        return total_fee_value  

    def calculate_fees_tiger(self, stock_price:float, num_shares:float, is_buy:bool)->float:
        trade_value = stock_price * num_shares
        total_fee_value = 0

        # Commission calculations
        temp_commission = 0.005*num_shares
        if(temp_commission<0.99):
            temp_commission = 0.99
        elif(temp_commission>0.005*trade_value):
            temp_commission = 0.005*trade_value
        #print(f"Commission: {tempCommission}")
        total_fee_value = total_fee_value+temp_commission
    
        # Platform Fee Calculations
        platform_fee = 0.005*num_shares
        if(platform_fee<1):
            platform_fee = 1
        elif(platform_fee>0.005*trade_value):
            platform_fee = 0.005*trade_value
        #print(f"platformFee: {platformFee}")
        total_fee_value = total_fee_value+platform_fee

        # SEC Membership Fee Calculations (only if isBuy is false)
        if (not is_buy):
            SEC_fee = 0.000008*trade_value
            if (SEC_fee<0.01):
                SEC_fee = 0.01
            #print(f"SECFee: {SECFee}")
            total_fee_value = total_fee_value + SEC_fee

        # Settlement Fee Calculations
        settlement_fee = 0.003*num_shares
        if (settlement_fee> 0.07*trade_value):
            settlement_fee = 0.07*trade_value
        #print(f"settlementFee: {settlementFee}")
        total_fee_value = total_fee_value + settlement_fee

        # Trading Activity Fee (only if isBuy is false)
        if (not is_buy):
            TA_fee = 0.000166*num_shares
            if (TA_fee<0.01):
                TA_fee = 0.01
            elif(TA_fee>8.30):
                TA_fee = 8.30
            #print(f"TAFee: {TAFee}")
            total_fee_value = total_fee_value+TA_fee

        #print(f"GST: {GST*totalFeeValue}")
        total_fee_value = total_fee_value*(1+GST)

        return total_fee_value

    def check_force_liquidate(self):
        for i in range(len(self.shares_owned_list) - 1, -1, -1):
            share: OwnedStock = self.shares_owned_list[i]
            stock_value = self.get_ticker_asset_value(share.ticker)

            # If what we owe goes below what we owe to broker, liquidate everything and repay to broker. 
            if self.money_owed_to_broker > 0 and self.money_owed_to_broker >= stock_value:
                print(f"Force liquidating {share.ticker} Asset value: {stock_value}")
                self.sell_all_existing_stocks_for_ticker(share.ticker)
                self.working_currency = 0
                self.money_owed_to_broker = 0

    def borrow_money_from_broker(self, amount):
        self.money_owed_to_broker += amount
    
    def payback_money_to_broker(self):
        """
        Payback whatever we can pay to the broker
        """
        if self.working_currency >= self.money_owed_to_broker:
            self.working_currency -= self.money_owed_to_broker
            self.money_owed_to_broker = 0
        else:
            self.money_owed_to_broker -= self.working_currency
            self.working_currency = 0

    def has_long_order(self, ticker: str):
        owned_stock = next((x for x in self.shares_owned_list if x.ticker == ticker), None)

        if owned_stock is not None:
            return True
        return False
    
    def has_short_order(self, ticker: str):
        owned_short = next((x for x in self.shorts_owned_list if x.ticker == ticker), None)

        if owned_short is not None:
            return True
        return False

class BuyOrder:
    def __init__(self):
        self.ticker =''
        self.limit_price = 0.0
        self.num_shares = 0
        self.block_id = 0
        self.stop_price = 0.0
        self.order_type = OrderType.NONE
        self.time_in_force = TimeInForce.DAY
    
    def __init__(
        self,
        block_id,
        ticker = '',
        limit_price = 0.0,
        num_shares = 0,
        order_type = OrderType.NONE,
        stop_price = 0.0,
        remarks = '',
        time_in_force: TimeInForce = TimeInForce.DAY
    ):
        self.limit_price = limit_price
        self.num_shares = num_shares
        self.block_id = block_id
        self.order_type = order_type
        self.stop_price = stop_price
        self.ticker = ticker
        self.remarks = remarks
        self.time_in_force = time_in_force

class ShortOrder:
    ticker=''
    limit_price = 0.0
    num_shares = 0
    block_id = 0
    order_type = OrderType.NONE
    stop_price = 0.0
    def __init__(
        self,
        block_id,
        ticker = '',
        lim_price = 0.0,
        num_shares=0,
        order_type = OrderType.NONE,
        stop_price = 0.0
    ):
        self.limit_price = lim_price
        self.num_shares = num_shares
        self.block_id = block_id
        self.order_type = order_type
        self.stop_price = stop_price
        self.ticker = ticker

class SellOrder:
    def __init__(
        self,
        block_id,
        ticker = '',
        lim_price = 0.0,
        num_shares = 0,
        order_type = OrderType.NONE,
        stop_price = 0.0,
        trail_type = TrailType.PERCENT,
        trail_price = 0.0,
        remarks = '',
        time_in_force: TimeInForce = TimeInForce.DAY
    ):
        self.limit_price = lim_price
        self.num_shares = num_shares
        self.block_id = block_id
        self.order_type = order_type
        self.stop_price = stop_price
        self.ticker = ticker
        self.trail_type = trail_type
        self.trail_price = trail_price       
        self.remarks = remarks
        self.time_in_force = time_in_force

class SellShortOrder:
    ticker = ''
    limit_price = 0.0
    num_shares = 0
    block_id = 0
    order_type = OrderType.NONE
    stop_price = 0.0
    def __init__(
        self,
        block_id,
        ticker = '',
        lim_price = 0.0,
        num_shares = 0,
        order_type = OrderType.NONE,
        stop_price = 0.0
    ):
        self.limit_price = lim_price
        self.num_shares = num_shares
        self.block_id = block_id
        self.order_type = order_type
        self.stop_price = stop_price
        self.ticker = ticker

class OwnedStock:
    def __init__(
        self,
        block_id,
        ticker = '',
        price = 0.0, # current
        num_shares = 0, # current
    ):
        self.avg_price = price
        self.num_shares = num_shares
        self.block_id = block_id
        self.ticker = ticker
    
    def add_stock(self, price, quantity):
        old_total_price = self.num_shares * self.avg_price
        self.num_shares += quantity
        self.avg_price = (old_total_price + (quantity * price)) / self.num_shares

    def remove_stock(self, price, quantity):
        if quantity > self.num_shares:
            return False
        elif quantity == self.num_shares:
            self.num_shares = 0
            self.avg_price = 0.0
            return True
        else:
            old_total_price = self.num_shares * self.avg_price
            self.num_shares -= quantity
            self.avg_price = (old_total_price - (quantity * price)) / self.num_shares

class OwnedShort:
    def __init__(
        self,
        block_id,
        ticker='',
        price=0.0,
        num_shares=0   
    ):
        self.price = price
        self.num_shares = num_shares
        self.block_id = block_id
        self.ticker = ticker
        self.avg_price = self.price

class Transaction:
    ticker = ''
    price = 0
    num_shares = 0
    block_id = 0
    is_buy = False
    is_recalculate = False
    tick_number = 0
    def __init__(
        self,
        ticker,
        p_price,
        num_shares,
        block_id,
        is_buy,
        is_recalculate,
        tick_number,
    ):
        self.price = p_price
        self.num_shares = num_shares
        self.block_id = block_id
        self.is_buy = is_buy
        self.is_recalculate = is_recalculate
        self.tick_number = tick_number
        self.ticker = ticker