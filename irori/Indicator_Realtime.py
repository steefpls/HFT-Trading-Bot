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
import yfinance as yf
import pandas as pd
import pandas_market_calendars as mcal
import numpy as np
from datetime import datetime, timedelta, timezone
from findatapy.market import Market, MarketDataRequest, MarketDataGenerator
from math import sqrt
import os

class Indicator_Parameters:

    def __init__(self, ) -> None:
        self
        pass

class Indicator_Realtime:

    class previous_day_class:
        def __init__(self, opening_price:float, closing_price:float) -> None:
            self.open_price = opening_price
            self.close_price = closing_price

        def get_open(self)->float:
            return self.open_price
        
        def get_close(self)->float:
            return self.close_price

    def __init__(self, ticker:str, empty_frame:bool, current_date:datetime = datetime.now(timezone.utc))->None:
        """
        Initializes the Indicator_Realtime class with the given ticker and empty_frame flag.

        Args:
            ticker (str): The ticker symbol of the stock.
            empty_frame (bool): A flag indicating whether the data should start empty or use the previous day's data.
        """
        self.ticker = ticker
        now = current_date  # Use the provided current_date as 'now'
        today = now.date()  # Extract the date part from the datetime object

        # Get the NYSE calendar
        nyse = mcal.get_calendar('NYSE')

        if empty_frame:
            self.simulated_df = pd.DataFrame(columns=['Date', 'Price'])

            # Find the closest previous trading day to the current date
            schedule = nyse.schedule(start_date=today - timedelta(days=10), end_date=today)
            schedule.index = schedule.index.date  # Convert the index to date format for comparison
            previous_days_schedule = schedule[schedule.index < today]

            if not previous_days_schedule.empty:
                last_row = previous_days_schedule.iloc[-1]  # Safely access the last row
                last_trading_day = last_row.name
            else:
                # Handle case where no trading days were found before 'today'
                last_trading_day = today  # Default to today if no previous days available

            self.last_trading_day = last_trading_day
        else:
            file_dir = os.path.dirname(os.path.realpath(__file__))
            dataLocation = os.path.join(file_dir, "BacktestData", ticker)

            # Get the trading schedule for the last 7 days including today
            schedule = nyse.schedule(start_date=today - timedelta(days=6), end_date=today)
            schedule.index = schedule.index.date  # Convert the index to date format for comparison

            last_row = schedule.iloc[-1]
            market_close_time = last_row['market_close']

            # Check if the current time is before the market close time of today
            if now < market_close_time.to_pydatetime():
                last_trading_day = schedule.iloc[-2].name if len(schedule) > 1 else today  # Use the previous session if available
            else:
                last_trading_day = schedule.iloc[-1].name

            if os.path.exists(dataLocation + f'\\{ticker}-{last_trading_day}.xlsx'):
                loaded_data = self.file_load(dataLocation, ticker, last_trading_day)
            else:
                startdate = last_trading_day.strftime("%d %b %Y")
                finishdate = last_trading_day + timedelta(days=1)
                finishdate = finishdate.strftime("%d %b %Y")
                market = Market(market_data_generator=MarketDataGenerator())
                loaded_data = self.file_download(ticker, file_dir, startdate, finishdate, market)

            self.simulated_df = self.convert_dataframe(loaded_data)
            self.previous_day = self.previous_day_class(self.simulated_df.iloc[0]['Price'], self.simulated_df.iloc[-1]['Price'])

    def convert_dataframe(self, dataFrame:pd.DataFrame)->pd.DataFrame:
        # Initialize the output DataFrame with the same time column and an empty price column
        result_df = pd.DataFrame({
            'Date': dataFrame['Date'],
            'Price': 0.0
        })

        # Initialize previous prices for comparison
        previous_bidPrice = None
        previous_askPrice = None

        for index, row in dataFrame.iterrows():
            bidPrice = float(row['Bid Price'])
            askPrice = float(row['Ask Price'])

            if previous_bidPrice is None and previous_askPrice is None:
                # This is the first iteration, both are considered changed
                price = (bidPrice + askPrice) / 2
            else:
                bid_changed = bidPrice != previous_bidPrice
                ask_changed = askPrice != previous_askPrice

                if bid_changed and not ask_changed:
                    # Only bidPrice changed
                    price = bidPrice
                elif ask_changed and not bid_changed:
                    # Only askPrice changed
                    price = askPrice
                else:
                    # Both changed or none changed
                    price = (bidPrice + askPrice) / 2

            # Update the price in the result DataFrame
            result_df.at[index, 'Price'] = price

            # Update previous prices for the next iteration
            previous_bidPrice = bidPrice
            previous_askPrice = askPrice

        return result_df

    def file_download(self, ticker:str,file_dir,startdate,finishdate,market)->None:
        #check if market is open
        md_request = MarketDataRequest(start_date= startdate,
                                finish_date=finishdate,
                                #get bid, ask data
                                fields=['bid', 'ask'],
                                vendor_fields=['bid', 'ask'],
                                freq='tick', data_source='dukascopy',
                                tickers=[ticker],
                                vendor_tickers=[(ticker+'USUSD')])
        df = market.fetch_market(md_request)
        if df is None:
            print(f"ERROR! No data for {startdate}!")
            return
        df = df/1000
        df.columns = ['Bid Price', 'Ask Price']
        df.index = df.index.astype(str)

        date_obj = datetime.strptime(startdate, "%d %b %Y")
        formatted_date = date_obj.strftime("%Y-%m-%d")

        df.to_excel(file_dir + f'\BacktestData\{ticker}\{ticker}-{formatted_date}.xlsx',engine='xlsxwriter')
        print(f"File saved to {file_dir}\BacktestData\{ticker} as {ticker}-{formatted_date}.xlsx")
        dataLocation = ((file_dir) + r"\BacktestData\\"+ ticker)
        return pd.read_excel(dataLocation + f'\{ticker}-{formatted_date}.xlsx')
    
    def get_previous_day(self)->previous_day_class:
        if not hasattr(self, 'previous_day'):
            file_dir = os.path.dirname(os.path.realpath(__file__))
            dataLocation = ((file_dir) + r"\BacktestData\\"+ self.ticker)
            if (os.path.exists(dataLocation + f'\\{self.ticker}-{self.last_trading_day}.xlsx')):
                loaded_data = self.file_load(dataLocation, self.ticker, self.last_trading_day)
            else:
                startdate = self.last_trading_day.strftime("%d %b %Y")
                finishdate = self.last_trading_day + timedelta(days=1)
                finishdate = finishdate.strftime("%d %b %Y")
                market = Market(market_data_generator=MarketDataGenerator())
                loaded_data = self.file_download(self.ticker, file_dir, startdate, finishdate, market)
            self.simulated_df = self.convert_dataframe(loaded_data)
            self.previous_day = self.previous_day_class(self.simulated_df.iloc[0]['Price'], self.simulated_df.iloc[-1]['Price'])
        return self.previous_day

    def file_load(self, dataLocation,ticker,startdate)->None:
        #print(f"Loading {ticker}-{startdate}.xlsx...")
        #read file and add framedata to list
        return pd.read_excel(dataLocation + f'\{ticker}-{startdate}.xlsx')
    
    def get_dataframe(self)->pd.DataFrame:
        """
        Returns the simulated DataFrame.

        Returns:
            pd.DataFrame: The simulated DataFrame.
        """
        return self.simulated_df

    def update_tick(self, price:float)->None:
        """
        Updates the simulated DataFrame with the given price.

        Args:
            price (float): The price to update the DataFrame with.
        """
        new_row = pd.DataFrame({
        'Date': [datetime.now(timezone.utc)],
        'Price': [price]
        })

        self.simulated_df = pd.concat([self.simulated_df, new_row], ignore_index=True)

    def sma(self, series, period=20):
        """
        Calculate the Simple Moving Average (SMA) of a given series.

        Args:
            series (pd.Series): The input series.
            period (int): The period over which to calculate the SMA. Defaults to 20.

        Returns:
            pd.Series: The SMA series.
        """
        return series.rolling(window=period, min_periods=1).mean()

    def ema(self, series, period=12):
        """
        Calculate the Exponential Moving Average (EMA) of a given series.

        Args:
            series (pd.Series): The input series.
            period (int): The period over which to calculate the EMA. Defaults to 12.

        Returns:
            pd.Series: The EMA series.
        """
        return series.ewm(span=period, adjust=False).mean()

    def wma(self, series, period=10):
        """
        Calculate the Weighted Moving Average (WMA) of a given series.
        Notes: Does not provide data for the first period - 1 rows.

        Args:
            series (pd.Series): The input series.
            period (int): The period over which to calculate the WMA. Defaults to 10.

        Returns:
            pd.Series: The WMA series.
        """
        weights = [i for i in range(1, period + 1)]
        return series.rolling(period).apply(lambda x: sum(x * weights) / sum(weights), raw=True)

    def hull_ma(self, series, period=9):
        """
        Calculate the Hull Moving Average (HMA) of a given series.
        Notes: Does not provide data for the first period - 1 rows.
        
        Args:
            series (pd.Series): The input series.
            period (int): The period over which to calculate the HMA. Defaults to 9.

        Returns:
            pd.Series: The HMA series.
        """
        return self.wma(2 * self.wma(series, period // 2) - self.wma(series, period), int(sqrt(period)))

    def rma(self, series, period=14):
        """
        Calculate the Relative Moving Average (RMA) of a given series.

        Args:
            series (pd.Series): The input series.
            period (int): The period over which to calculate the RMA. Defaults to 14.

        Returns:
            pd.Series: The RMA series.
        """
        return series.ewm(alpha=1/period, adjust=False).mean()

    def tilson_t3(self, series, period=5, volume_factor=0.7):
        """
        Calculate the Tilson T3 Moving Average of a given series.

        Args:
            series (pd.Series): The input series.
            period (int): The period over which to calculate the Tilson T3. Defaults to 5.
            volume_factor (float, optional): The volume factor. Defaults to 0.7.

        Returns:
            pd.Series: The Tilson T3 series.
        """
        vfact = volume_factor * 0.1

        def gd(x):
            ema1 = self.ema(x, period)
            ema2 = self.ema(ema1, period)
            return ema1 * (1 + vfact) - ema2 * vfact

        first = gd(series)
        second = gd(first)
        third = gd(second)
        return third
    
    def rsi(self, series, period=14):
        """
        Calculate the Relative Strength Index (RSI) of a given series.

        Args:
            series (pd.Series): The input series.
            period (int, optional): The period over which to calculate the RSI. Defaults to 14.

        Returns:
            pd.Series: The RSI series.
        """
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Adjust RSI calculation for the initial period
        for i in range(1, period):
            avg_gain = gain.iloc[:i].mean()
            avg_loss = loss.iloc[:i].mean()
            if avg_loss == 0 or avg_gain == 0:
                rsi.iloc[i-1] = 50
            else:
                rs = avg_gain / avg_loss
                rsi.iloc[i-1] = 100 - (100 / (1 + rs))

        return rsi

# test = Indicator_Realtime('NVDA', False)
# import time
# start_time = time.time()
# test.simulated_df['RSI'] = test.rsi(test.simulated_df['Price'], 5)
# end_time = time.time()
# print("Compute time: " + end_time - start_time)
# print(test.simulated_df)
