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
from datetime import date
from datetime import datetime
from pytz import timezone
import yfinance as yf
import pandas as pd
# https://quantitativo.substack.com/p/turnaround-tuesdays-on-steroids

'''
Entry Rules:

    Today is Tuesday or Wednesday;

    Yesterday's close was lower than the close of 2 days ago;

    The close of 2 days ago was lower than the close of 3 days ago;

    Go long at the opening.
    
    
    Exit Rules:

    Exit the trade when the close is higher than yesterday's high.
'''

"""
pseudo Code:

    if today is Tuesday or Wednesday:
        if yesterday's close < 2 days ago close:
            if 2 days ago close < 3 days ago close:
                go long at the opening
    else:
        exit the trade when the close is higher than yesterday's high

        
- Gather data for the all the days -- DONE
- Check Today's Date -- DONE
- If Tuesday or Wednesday -- DONE

- Check to see if data is available for yesterday, 2 days ago, and 3 days ago -- DONE
    - If data is available, check the following:
        - Yesterday's close < 2 days ago close -- DONE
        - 2 days ago close < 3 days ago close -- DONE

5. Check Yesterday's High -- DONE
7. Check Today's Close    -- DONE

"""

class TurnaroundTuesdaysV2(strategyBase.StrategyBase):
    # Super class init method should be called to initialize the ticker and mediator class
    def init(self):
        super().init()

        #Initialize list of dates, Highprice and Endprice tuples. They should correspond to each other
        self.priceHistory = dict() #dict of tuples [Ticker,(date, DayHighPrice, CloseingPrice)]
        self.todayDateTime = dict()
        self.todayHigh = dict()
        self.todayClose = dict()
        self.goLongAtOpen = dict()
        self.isCurrentlyLong = (False, "") #tuple of boolean and ticker
        self.quantity = 0

    # Calls when strategy is ready to be used
    # Super class start method should be called to set up the broker within mediator
    # This is called once everyday, reset immediate variables here
    def start(self):
        super().start()
        
    # Calls 5 minutes before market opens
    def intraday_start(self):
        #Reset the high price and close price for the day
        today = self.datetime_utc
        self.todayDateTime = today
        
        #set TodayHigh to 0 for all tickers
        for ticker, price in self.todayHigh.items():
            self.todayHigh[ticker] = 0

        for ticker,priceHistory in self.priceHistory.items():
            if ticker not in self.goLongAtOpen:
                self.goLongAtOpen[ticker] = False
            self.goLongAtOpen[ticker] = self.should_go_long(self.priceHistory[ticker])

        #print unmodified goLongAtOpen dictionary
        print("goLongAtOpen: "+ str(self.goLongAtOpen))

        #Traverse goLongAtOpen dictionary. If the value is True, then set all other values to False
        hasGoLong = False
        for ticker, goLong in self.goLongAtOpen.items():
            if goLong:
                hasGoLong = True
                self.goLongAtOpen[ticker] = True
            else:
                self.goLongAtOpen[ticker] = False
        
    
    def should_go_long(self,priceHistoryList,days_of_week=[1,2]):
        #get the day of the week
        today = self.datetime_utc
        day_of_week = today.weekday()
        
        #check if day of week is within the list of days of the week
        #0 = Monday, 1 = Tuesday, 2 = Wednesday, 3 = Thursday, 4 = Friday, 5 = Saturday, 6 = Sunday
        if day_of_week in days_of_week:
            #get the data for last 3 trading days (last 3 appended price History tuples)
            if len(priceHistoryList) >= 3:
                yesterday = priceHistoryList[-1]
                two_days_ago = priceHistoryList[-2]
                three_days_ago = priceHistoryList[-3]
                if yesterday[2] < two_days_ago[2] and two_days_ago[2] < three_days_ago[2]:
                    #go long at the opening
                    #print("Conditions met to go long at the opening")
                    return True
                else:
                    return False
            else:
                print("Not enough data to make a decision")
                return False
        else:
            return False
    
    # Calls when market opens
    def day_start(self):
        if self.mediator.get_account_information().gross_position_value == 0:
            self.stop()
        pass

    # Calls when market closes
    def day_end(self):
        #append today's data to the priceHistoryList
        for ticker,priceHistory in self.priceHistory.items():
            if ticker not in self.priceHistory:
                self.priceHistory[ticker] = []

            self.priceHistory[ticker].append((self.todayDateTime, self.todayHigh[ticker], self.todayClose[ticker]))

        #sell if we're currently long and conditions are met
        if (self.isCurrentlyLong[0]):
            currentTicker = self.isCurrentlyLong[1]

            print(f"\nToday's close: {self.todayClose[currentTicker]}")
            print(f"Yesterday's High: {self.priceHistory[currentTicker][-2][1]}\n")

            #exit the trade when the close is higher than yesterday's high
            if self.todayClose[currentTicker] > self.priceHistory[currentTicker][-2][1]:
                #print("Selling since today's close is higher than yesterday's high")
                sell = OrderCommand(ticker=currentTicker, quantity=self.quantity)
                print(f"\nSelling {self.quantity} shares of {currentTicker} at the close price of {self.todayClose}\n")
                self.mediator.sell_market_order(sell)
                self.isCurrentlyLong = (False,"")
                pass
    # Calls when tick is sent
    def on_tick_changed(self, frame: TickChangeData):
        print('\nTEST\n')
        #check if dictionary has the ticker
        if frame.ticker not in self.todayHigh:
            self.todayHigh[frame.ticker] = 0
        
        if frame.price > self.todayHigh[frame.ticker]:
            self.todayHigh[frame.ticker] = frame.price
        self.todayClose[frame.ticker] = frame.price

        if frame.ticker not in self.priceHistory:
            self.priceHistory[frame.ticker] = []
        if frame.ticker not in self.goLongAtOpen:
            self.goLongAtOpen[frame.ticker] = False

        #If we're supposed to go long at the open and we're not currently long, then go long
        if not self.isCurrentlyLong[0] and self.goLongAtOpen[frame.ticker]:
            self.quantity = int(self.mediator.get_account_information().cash_balance // frame.price) * 3
            buy = OrderCommand(ticker=frame.ticker, quantity=self.quantity)
            print(f"\nBuying {self.quantity} shares of {frame.ticker} at the open price of {frame.price}\n")
            self.mediator.buy_market_order(buy)
            self.isCurrentlyLong = (True, frame.ticker)
        pass


    # Calls when any order is updated
    def on_order_changed(self, frame: strategyBase.OrderChangeData):
        pass

    # Calls when strategy is stopped
    def stop(self):
        super().stop()
        pass
