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
Sudo Code:

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

current_ticker = "QQQ"
useYFinance = False #true = use yfinance for tracking high and close prices, false = use own tracked data for tracking high and close prices. This is only used for backtest broker

class TwinBreak(strategyBase.StrategyBase):
    # Super class init method should be called to initialize the ticker and mediator class
    def init(self):
        # print("TT INIT")
        super().init()

        # mandatory call to assign ticker list
        self.tickers.tickerList = [current_ticker]

        #Initialize list of dates, Highprice and Endprice tuples. They should correspond to each other
        self.priceHistory = [] #list of tuples (date, DayHighPrice, CloseingPrice)
        self.todayDateTime = None
        self.todayHigh = 0
        self.todayClose = None
        self.isCurrentlyLong = False
        self.quantity = 0
        self.intraday_start_called = False
        self.goLongAtOpen = False

    # Calls when strategy is ready to be used
    # Super class start method should be called to set up the broker within mediator
    # This is called once everyday, reset immediate variables here
    def start(self):
        global useYFinance
        # print("TT START")
        super().start()
        if not (self.is_running_on_backtesting):
            useYFinance = True

        if len(self.priceHistory) == 0:
            if (useYFinance):
                print(f"Price history empty, retrieving from yFinance")
            else:
                print(f"self tracked backtest data")

    # Calls 5 minutes before market opens
    def intraday_start(self):
        # print("TT INTRADAY START")
        #Reset the high price and close price for the day
        today = self.datetime_utc
        self.todayDateTime = today
        self.todayHigh = 0
        self.todayClose = 0
        #self.goLongAtOpen = False

        self.intraday_start_called = True
        self.check_for_trade()
        pass

    def check_for_trade(self):
        #0 = Monday, 1 = Tuesday, 2 = Wednesday, 3 = Thursday, 4 = Friday, 5 = Saturday, 6 = Sunday
        if self.todayDateTime.weekday() == 1 or self.todayDateTime.weekday() == 2:
            #get the data for last 3 trading days (last 3 appended price History tuples)
            if len(self.priceHistory) >= 3:
                yesterday = self.priceHistory[-1]
                two_days_ago = self.priceHistory[-2]
                three_days_ago = self.priceHistory[-3]
                if yesterday[2] < two_days_ago[2] and two_days_ago[2] < three_days_ago[2]:
                    if not self.isCurrentlyLong:
                        self.goLongAtOpen = True

            else:
                print("Not enough data to make a decision")
    
    def buy(self, price, open_or_close):

        self.quantity = int(self.mediator.get_account_information().cash_balance // price) * 3
        if self.quantity != 0:
            buy = OrderCommand(ticker=current_ticker, quantity=self.quantity, price = price)
            print(f"Buying {self.quantity} shares of {current_ticker} at the {open_or_close} price of {price}")
            self.mediator.buy_limit_order(buy)
            self.isCurrentlyLong = True
        else:
            print("cannot buy since quantity is 0")

    def sell(self):
        sell = OrderCommand(ticker=current_ticker, quantity=self.quantity, price = self.todayClose)
        print(f"Selling {self.quantity} shares of {current_ticker} at the close price of {self.todayClose}")
        self.mediator.sell_limit_order(sell)
        self.isCurrentlyLong = False
        self.quantity = 0


    # Calls when market opens
    def day_start(self):
        # print("TT DAY START")
        pass

    def enter_midday(self):
        if(self.mediator.get_positions().get_stock_by_ticker(current_ticker)!=None):
            self.quantity = self.mediator.get_positions().get_stock_by_ticker(current_ticker).quantity #sets quantity if there is already stock
        self.intraday_start()
        pass
    
    # Calls when market closes
    def day_end(self):
        # print("TT DAY END")
        #print(f"{self.priceHistory[-1]} vs {self.priceHistory_yahoo[-1]}")
        #should_sell = False

        if (self.isCurrentlyLong):
            #exit the trade when the close is higher than yesterday's high
            if self.todayClose > self.priceHistory[-1][1]:
                #print("Selling since today's close is higher than yesterday's high")
                self.sell()
            else:
                print("Conditions not met to sell at the opening")
                #print(f"Today's close: {self.todayClose} Yesterday's High: {self.priceHistory[-1][1]}")

        if useYFinance:
            #get only the date, not time or seconds. This is important as yahoo finance tracks time for opening/closing differently
            date_only = self.todayDateTime.replace(hour = 0, minute=0, second = 0, microsecond = 0)
            #create the data point and add it to the price history
            self.get_ticker_data(self.tickers.tickerList[0], date_only)    
        else:
            #create tuple of todayDateTime, highprice, endprice
            dataPoint = (self.todayDateTime, self.todayHigh, self.todayClose)
            self.priceHistory.append(dataPoint)
            #remove the oldest price history item if it gets too long, since it won't be used anymore
            if(len(self.priceHistory) > 4):
                self.priceHistory.pop(0)

        self.check_for_trade()

        #print(f"go long: {self.goLongAtOpen}")
        #print(f"is currently long: {self.isCurrentlyLong}")
        #print(f"should sell: {should_sell}")

        if(self.goLongAtOpen and not self.isCurrentlyLong):
            print("buy at end")
            self.buy(self.todayClose, "close")
        

    def get_ticker_data(self, ticker, input_date):
        # print("TT GETTING TICKER DATA")
        symbol = ''
        if ticker in tickerDict:
            symbol = tickerDict.get(ticker)
        else:
            symbol = ticker

        tick = yf.Ticker(symbol)

        # Calculate the start and end dates for fetching data
        end_date = input_date + timedelta(days=1)
        start_date = input_date + timedelta(days=-7)  # Fetch a wider range to ensure we get 3 valid trading days
        
        hist = tick.history(start = start_date, end = end_date)

        temp_list = []

        for date, row in hist.iterrows():
            date_val = date.to_pydatetime()
            date_val_utc = date_val.astimezone(timezone('UTC'))
            high_val = row['High']
            close_val = row['Close']

            dataPoint = (date_val_utc, high_val, close_val)
            temp_list.append(dataPoint)

        self.priceHistory = temp_list
        

    # Calls when tick is sent
    def on_tick_changed(self, frame: TickChangeData):
        #track the high price of the day
        if frame.ticker != current_ticker:
            return
        
        if frame.price > self.todayHigh:
            self.todayHigh = frame.price

        self.todayClose = frame.price

        if self.goLongAtOpen and not self.isCurrentlyLong:
            self.buy(frame.price, "open")

    # Calls when any order is updated
    def on_order_changed(self, frame: strategyBase.OrderChangeData):
        # print(f"ORDER CHANGED {frame.avg_fill_price}")
        pass

    # Calls when strategy is stopped
    def stop(self):
        pass

tickerDict = {
    'USA500IDX': '^GSPC',
    'NOVOBDKK' : 'NVO'
}