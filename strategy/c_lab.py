from irori.common import *
from irori import strategyBase
from irori.stats import *
from datetime import date
from datetime import datetime as dt
from pytz import timezone
import yfinance as yf
import pandas as pd
import math

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

class C_Lab(strategyBase.StrategyBase):
    # Super class init method should be called to initialize the ticker and mediator class
    def init(self):
        super().init()

        # mandatory call to assign ticker list
        self.tickers.tickerList = [current_ticker]

        #Initialize list of dates, Highprice and Endprice tuples. They should correspond to each other
        self.priceHistory = [] #list of tuples (date, DayHighPrice, CloseingPrice)
        self.todayHigh = 0
        self.todayClose = None
        self.isCurrentlyLong = False
        self.quantity = 0
        self.intraday_start_called = False
        self.mark_for_sell = False
        self.days:list[int] = []

    # Calls when strategy is ready to be used
    # Super class start method should be called to set up the broker within mediator
    # This is called once everyday, reset immediate variables here
    def start(self):
        super().start()
        self.todayDateTime = self.datetime_utc
        if not self.is_running_on_backtesting:
            print(self.is_running_on_backtesting)
            if  is_market_open():
                print("CURRENT HIGH NOT RECORDED, WILL DEVIATE ACCORDINGLY")
            positions:PositionsResponse = self.mediator.get_positions()
            if positions.stockList is not None and len(positions.stockList) > 0:
                for stock in positions.stockList:
                    stock:Stock = stock
                    if stock.ticker == current_ticker:
                        self.isCurrentlyLong = True
                        self.quantity = stock.quantity
                        print("Positions detected, setting isCurrentlyLong to True")
            self.days = self.get_adapt_day()

    # Calls 5 minutes before market opens
    def intraday_start(self):
        #Reset the high price and close price for the day
        self.todayDateTime = self.datetime_utc
        self.todayHigh = 0
        self.todayClose = 0

        self.intraday_start_called = True

    def check_for_trade(self):
        #0 = Monday, 1 = Tuesday, 2 = Wednesday, 3 = Thursday, 4 = Friday, 5 = Saturday, 6 = Sunday
        #TODO TEST: CHAMELEON ONLY RUNS after monday and tuesday only
        #if self.todayDateTime.weekday() in self.days or self.todayDateTime.weekday() == 1 or self.todayDateTime.weekday() == 2:
        if self.todayDateTime.weekday() in self.days or self.todayDateTime.weekday() == 1 or self.todayDateTime.weekday() == 2 or self.todayDateTime.weekday() == 3:
            #get the data for last 3 trading days (last 3 appended price History tuples)
            if len(self.priceHistory) >= 2:
                yesterday = self.priceHistory[-1]
                two_days_ago = self.priceHistory[-2]
                print(f"Self.todayClose: {self.todayClose:2f}, Yesterday: {yesterday[2]:2f}, Two days ago: {two_days_ago[2]:2f}")
                if self.todayClose < yesterday[2] < two_days_ago[2]:
                    print("Filter conditions HIT")
                    if not self.isCurrentlyLong:
                        self.quantity = math.floor(int(self.mediator.get_account_information().cash_balance // self.todayClose) * 3.33)
                        buy = OrderCommand(ticker=current_ticker, quantity=self.quantity)
                        self.mediator.buy_market_order(buy)
                        print(f"Buying {self.quantity} shares of {current_ticker} at the price of {self.todayClose}")
                        self.isCurrentlyLong = True
                else:
                    print(f"Filter conditions MISSED")
        
        if (self.mark_for_sell):
            sell = OrderCommand(ticker=current_ticker, quantity=self.quantity)
            self.mediator.sell_market_order(sell)
            print(f"Selling {self.quantity} shares of {current_ticker} at the close price of {self.todayClose}")
            self.isCurrentlyLong = False
            self.mark_for_sell = False

    # Calls when market opens
    def day_start(self):
        pass

    # Calls when market closes
    def day_end(self):
        print("Day End")
        if self.todayDateTime.weekday() == 1:
            self.days = self.get_adapt_day()

        #get only the date, not time or seconds. This is important as yahoo finance tracks time for opening/closing differently
        date_only = self.todayDateTime.replace(hour = 0, minute=0, second = 0, microsecond = 0)
        #create the data point and add it to the price history
        self.get_ticker_data(self.tickers.tickerList[0], date_only)

        print("Check if long")
        if (self.isCurrentlyLong):
            #exit the trade when the close is higher than yesterday's high
            if self.todayClose > self.priceHistory[-1][1]:
                self.mark_for_sell = True

        print("Check for trade")
        self.check_for_trade()

    def get_ticker_data(self, ticker, input_date):
        symbol = ''
        if ticker in tickerDict:
            symbol = tickerDict.get(ticker)
        else:
            symbol = ticker

        tick = yf.Ticker(symbol)

        # End date is set to the input date as yfin has not updated today's data. (Yfin updates 2 hours after market close)
        end_date = input_date
        start_date = input_date + timedelta(days=-7)  # Fetch a wider range to ensure we get 3 valid trading days
        
        hist = tick.history(start = start_date, end = end_date, auto_adjust=False)

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
        if frame.ticker != current_ticker:
            return
        
        if frame.price > self.todayHigh:
            self.todayHigh = frame.price

        self.todayClose = frame.price

    # Calls when any order is updated
    def on_order_changed(self, frame: strategyBase.OrderChangeData):
        # print(f"ORDER CHANGED {frame.avg_fill_price}")
        pass

    # Calls when strategy is stopped
    def stop(self):
        super().stop()
    
    def get_adapt_day(self):
        stock_data = get_stock_data(current_ticker, self.datetime_utc - timedelta(days=60), self.datetime_utc)
        stock_data = calculate_returns(stock_data)
        
        summary = classify_and_summarize_returns(stock_data)
        self.days = get_high_scores(summary)

        return self.days

def get_stock_data(ticker, start_date, end_date):
    # Convert the start_date to a datetime object
    start_date_obj = start_date
    # Subtract 3 days from the start_date
    adjusted_start_date = start_date_obj - datetime.timedelta(days=3)
    # Convert the adjusted date back to a string
    adjusted_start_date_str = adjusted_start_date.strftime('%Y-%m-%d')
    
    stock_data = yf.download(ticker, start=adjusted_start_date_str, end=end_date, progress=False)
    if stock_data.empty:
        raise ValueError("No data fetched for the given ticker and date range.")
    return stock_data

def calculate_returns(stock_data):
    # Regular exit
    # if 'Close' not in stock_data.columns:
    #     raise ValueError("The fetched data does not contain 'Close' prices.")
    
    # stock_data['Return'] = stock_data['Close'].pct_change()
    # stock_data.dropna(inplace=True)
    # return stock_data


    # Exit only if close is higher than buy in day's high
    # if 'Close' not in stock_data.columns or 'High' not in stock_data.columns:
    #     raise ValueError("The fetched data does not contain 'Close' or 'High' prices.")
    
    # stock_data['Return'] = None  # Initialize the 'Return' column with None

    # for i in range(len(stock_data) - 1):
    #     today_high = stock_data['High'].iloc[i]
    #     for j in range(i + 1, len(stock_data)):
    #         if stock_data['Close'].iloc[j] > stock_data['High'].iloc[i]:
    #             stock_data.loc[stock_data.index[i], 'Return'] = (stock_data['Close'].iloc[j] - today_high) / today_high
    #             break
    
    # stock_data.dropna(subset=['Return'], inplace=True)  # Remove rows where 'Return' is still None
    # return stock_data

    # TT exit
    if 'Close' not in stock_data.columns or 'High' not in stock_data.columns:
        raise ValueError("The fetched data does not contain 'Close' or 'High' prices.")
    
    stock_data['Return'] = None  # Initialize the 'Return' column with None

    for i in range(len(stock_data) - 1):
        today_high = stock_data['High'].iloc[i]
        for j in range(i + 1, len(stock_data)):
            if stock_data['Close'].iloc[j] > stock_data['High'].iloc[j-1]:
                stock_data.loc[stock_data.index[i], 'Return'] = (stock_data['Close'].iloc[j] - today_high) / today_high
                break
    
    stock_data.dropna(subset=['Return'], inplace=True)  # Remove rows where 'Return' is still None
    return stock_data

def classify_and_summarize_returns(stock_data):
    stock_data['Weekday'] = stock_data.index.day_name()

    valid_days = []
    for i in range(3, len(stock_data)):
        if stock_data['Close'].iloc[i-3] > stock_data['Close'].iloc[i-2] > stock_data['Close'].iloc[i-1]:
            valid_days.append(stock_data.index[i])
    
    valid_stock_data = stock_data.loc[valid_days]
    
    summary = {}
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        day_data = valid_stock_data[valid_stock_data['Weekday'] == day]
        positive_returns = day_data[day_data['Return'] > 0]
        non_positive_returns = day_data[day_data['Return'] <= 0]
        
        total_days_positive = len(positive_returns)
        total_days_non_positive = len(non_positive_returns)
        total_return_percent = day_data['Return'].sum() * 100

        if not day_data.empty:
            lowest_return = day_data['Return'].min() * 100
            highest_return = day_data['Return'].max() * 100
        else:
            lowest_return = None
            highest_return = None
        
        summary[day] = {
            'Total Trading Days': total_days_positive + total_days_non_positive,
            'Total Positive Days': total_days_positive,
            'Total Non-Positive Days': total_days_non_positive,
            'Total Return (%)': total_return_percent,
            'Lowest Return (%)': lowest_return,
            'Highest Return (%)': highest_return
        }
    
    return summary

def get_high_scores(summary):
    scores = {}
    for day in summary:
        total_positive_days = summary[day]['Total Positive Days']
        total_non_positive_days = summary[day]['Total Non-Positive Days']
        total_return_percent = summary[day]['Total Return (%)']
        
        # Calculate the score
        score = (total_positive_days - total_non_positive_days) * total_return_percent
        
        # Store the score in the dictionary
        scores[day] = score

    highest_score = max(scores.values())
    
    # Find all days with the highest score
    days_with_high_scores = [day for day, score in scores.items() if (highest_score - score <= 10) and score > 3]
    
    # Map days to integers
    day_to_int = {'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 'Thursday': 4, 'Friday': 5}
    days_as_ints = [day_to_int[day] for day in days_with_high_scores if day_to_int[day]]
    for day in scores:
        print(f"Day: {day} Score: {scores[day]}")
    print(f"Appointed days: {days_as_ints}")
    
    return days_as_ints

tickerDict = {
    'USA500IDX': '^GSPC',
    'NOVOBDKK' : 'NVO'
}