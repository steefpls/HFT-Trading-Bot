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

class Strategy_Straight(strategyBase.StrategyBase):

    def get_percentange(self, input_number):
        if (input_number < 1 or input_number > 5):
            raise ValueError("Number out of range")

        mapping = {
            1: 0.1,
            2: 0.2,
            3: 0.4,
            4: 0.8,
            5: 1.5,
            6: 2
        }
        
        return mapping.get(input_number, None)
    
    def get_next_buy(self, phase:int):
        match (phase):
            case 1:
                return self.entry_price * 0.99
            case 2:
                return self.entry_price * 0.95
            case 3:
                return self.entry_price * 0.90
            case 4:
                return self.entry_price * 0.85
            case 5:
                return self.entry_price * 0.80
            case 6:
                return self.entry_price * 0.75
            case _:
                raise ValueError("Phase out of range")
    
    # Date time is not initialized here. Use this to set up any custom objects or variables
    # Super class init method should be called to initialize the ticker and mediator class
    def init(self):
        super().init()
        self.current_ticker = "QQQ"
        self.targeted_profits = 1.01

        # Strat variables
        self.is_exposed = False
        self.entry_price = 0
        self.target_price = 0
        self.phase = 0
        self.highest_phase = 0
        self.invested = 0

        # mandatory call to assign ticker list
        self.tickers.tickerList = [self.current_ticker]

    # Calls when strategy is ready to be used
    # Super class start method should be called to set up the broker within mediator
    # This is called once after init with essential variables have been set up
    def start(self):
        super().start()
        pass

    # Calls 5 minutes before market opens
    def intraday_start(self):
        self.done_for_day = False
        pass

    # Calls when market opens
    def day_start(self):
        pass

    # Calls when market closes
    def day_end(self):
        if (self.phase > self.highest_phase):
            self.highest_phase = self.phase
        print(f"Phase: {self.phase}, Highest Phase: {self.highest_phase}, self.target_price: {self.target_price}, self.entry_price: {self.entry_price}")
        print(self.mediator.get_positions())
        pass

    # Calls when tick is sent
    def on_tick_changed(self, frame: TickChangeData):
        if (self.done_for_day):
            self.stop()
            return

        if (not self.is_exposed):
            self.is_exposed = True
            self.entry_price = frame.price
            self.phase = 1

            self.capital = self.mediator.get_account_information().cash_balance
            percent = self.get_percentange(self.phase)
            funds = self.capital * percent
            self.buy_quantity = funds // frame.price

            self.target_price = self.entry_price * self.targeted_profits
            self.next_buy = self.get_next_buy(self.phase)

            buy = OrderCommand(ticker=self.current_ticker, quantity=self.buy_quantity)
            self.mediator.buy_market_order(buy)

            self.invested = self.buy_quantity * frame.price
        elif (frame.price >= self.target_price):
            self.is_exposed = False
            self.phase = 0
            self.entry_price = 0
            self.target_price = 0
            self.invested = 0

            sell = OrderCommand(ticker=self.current_ticker, quantity=self.buy_quantity)
            self.mediator.sell_market_order(sell)
            self.done_for_day = True
        elif (frame.price <= self.next_buy):
            self.phase += 1

            self.capital = self.mediator.get_account_information().cash_balance
            percent = self.get_percentange(self.phase)
            funds = self.capital * percent
            self.buy_quantity = funds // frame.price

            self.target_price = frame.price * (self.targeted_profits ** self.phase)
            self.next_buy = self.get_next_buy(self.phase)

            buy = OrderCommand(ticker=self.current_ticker, quantity=self.buy_quantity)
            self.mediator.buy_market_order(buy)
            pass

    # Calls when any order is updated
    def on_order_changed(self, frame: strategyBase.OrderChangeData):
        pass

    # Calls when strategy is stopped
    def stop(self):
        super().stop()
        pass