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
from irori.common import *
from irori import strategyBase
from irori.stats import *
from irori.Indicator_Realtime import *

class Phoenix(strategyBase.StrategyBase):
    expected_profit = 1000
    
    def init(self):
        super().init()

        # mandatory call to assign ticker list
        self.current_ticker = "QQQ"
        self.tickers.tickerList = [self.current_ticker]
        self.state = "RESOLVED"

    # Calls when strategy is started
    def start(self):
        super().start()
        
    # Calls 5 minutes before market opens
    def intraday_start(self):
        # self.last_close_price = self.ir.get_previous_day().get_close()
        #self.ir = Indicator_Realtime("NVDA", True, self.datetime)
        if (self.state != "TRAILING"):
            self.is_day_start = True
        else:
            self.is_day_start = False

    # Calls when market opens
    def day_start(self):
        pass

    # Calls when market closes
    def day_end(self):
        pass

    # Calls when tick is sent
    
    def on_tick_changed(self, frame: TickChangeData):
        # if (self.start_time is None):
        #     self.quantity = self.balance // frame.price - 10
        #     self.start_time = frame.time
        #     result = frame.price / self.last_close_price
        #     buy = OrderCommand(ticker="NVDA", quantity=self.quantity)
        #     self.mediator.buy_market_order(buy)
        #     self.open_state = "LONG"
        #     self.sell_price = self.expected_profit/frame.price + frame.price
        #     self.state = "PENDING"

        # if (self.open_state != "RESOLVED" and seconds_elapsed(self.start_time, frame.time) >= 1800):
        #     if (self.open_state == "LONG"):
        #         sell = OrderCommand(ticker="NVDA", quantity=self.quantity)
        #         self.mediator.sell_market_order(sell)
        #         self.open_state = "RESOLVED"
        #     elif (self.open_state == "SHORT"):
        #         cover = OrderCommand(ticker="NVDA", quantity=self.quantity)
        #         self.mediator.short_close_market_order(cover)
        #         self.open_state = "RESOLVED"
        
        # if (self.state == "PENDING" and frame.price >= self.sell_price):
        #     sell = OrderCommand(ticker="NVDA", quantity=self.quantity)
        #     self.mediator.sell_market_order(sell)
        #     self.state = "RESOLVED"

        if (self.state == "RESOLVED"):
            if (self.is_day_start):
                self.quantity = int(self.mediator.get_account_information().cash_balance // frame.price)
                buy = OrderCommand(ticker=self.current_ticker, quantity=self.quantity)
                self.mediator.buy_market_order(buy)
                self.is_day_start = False
            elif (frame.price <= self.buy_price):
                self.quantity = int(self.mediator.get_account_information().cash_balance // frame.price)
                buy = OrderCommand(ticker=self.current_ticker, quantity=self.quantity)
                self.mediator.buy_market_order(buy)
        if (self.state == "TRAILING"):
            new_stop = frame.price * 0.99
            if (new_stop > self.trailing_stop):
                self.trailing_stop = new_stop
            if frame.price <= self.trailing_stop:
                sell = OrderCommand(ticker=self.current_ticker, quantity=self.quantity)
                self.mediator.sell_market_order(sell)
        if (self.state == "PENDING"):
            if (frame.price >= self.sell_price):
                self.state = "TRAILING"
                self.trailing_stop = frame.price * 0.99
        # print(self.is_day_start)
                    
    # Calls when any order is updated
    def on_order_changed(self, frame: strategyBase.OrderChangeData):
        if (frame.order_status == OrderStatus.FILLED):
            if (frame.action == OrderAction.BUY):
                print("Bought")
                self.sell_price = self.expected_profit/self.quantity + frame.avg_fill_price + 1
                self.state = "PENDING"
            else:
                print("Sold")
                self.state = "RESOLVED"
                self.buy_price = frame.avg_fill_price * 0.98

    # Calls when strategy is stopped
    def stop(self):
        pass

def seconds_elapsed(time_start:datetime, time_end:datetime):
    # Calculate the difference in seconds
    return (time_end - time_start).total_seconds()