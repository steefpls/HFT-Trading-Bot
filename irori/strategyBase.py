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
from datetime import datetime, timedelta
from irori.common import *

import asyncio

class StrategyBase(object):
    # Call this to true at the end of the overridden init
    def __init__(self):
        self.is_running_on_backtesting = False
        self.is_backtest_skipped = False
        self.stop_event = asyncio.Event()

    def init(self, *args, **kwargs):
        global Mediator
        from irori.mediator import Mediator
        self.mediator = Mediator()
        self.tickers = Tickers()
    
    def set_backtest(self):
        self.is_running_on_backtesting = True

    def start(self):
        self.mediator.start()

    def init_datetime(self, datetime_utc:datetime):
        """
        datetime UTC. is the day the strategy is currently running on
        """
        self.is_backtest_skipped = False
        self.datetime_utc = datetime_utc
        self.datetime_started_utc = datetime_utc 

        nyse = mcal.get_calendar('NYSE')

        schedule = nyse.schedule(start_date=datetime_utc, end_date=datetime_utc + timedelta(days=2))

        if schedule.empty:
            print("The trading schedule is empty for the current date.")
            return -1

        try:
            self.market_open_datetime = schedule.iloc[0]['market_open']
        except:
            self.market_open_datetime = None

    def get_elapsed_time(self, date_utc_now: datetime):
        """
        For backtesting, pass in the date from tick frame
        For live, pass in utc now
        Gets the elapsed time since the bot ran on the trading day
        e.g. market opens at 1330 , bot starts at 1400, time now is 1430, elapsed time will be 30mins or 30*60 seconds
        """

        # new_york_time_zone = pytz.timezone('America/New_York')
        # current_time_ny = datetime.now(new_york_time_zone)

        difference = (date_utc_now - self.datetime_started_utc).total_seconds()

        return difference

    def get_elapsed_time_since_market_open(self, date_utc_now: datetime):
        """
        Gets elapsed time since market open
        Returns -1 if before market open
        """
        
        if date_utc_now >= self.market_open_datetime:
            return (date_utc_now - self.market_open_datetime).total_seconds()
        else:
            return -1

    def intraday_start(self):
        pass

    def day_start(self):
        pass

    def day_end(self):
        print("Day End StrategyBase")
        pass

    def skip(self):
        self.is_backtest_skipped = True

    def stop(self):
        self.mediator.stop()

    def on_order_changed(self, frame: OrderChangeData):
        # logger.info(f'order changed: {frame}')
        print(f'order changed: {frame}')

    def on_tick_changed(self, frame: TickChangeData):
        # logger.info(f'tick changed: {frame.ticker} {frame.price}')
        print(f'tick changed: {frame.ticker} {frame.price}')

    # Async functions
    async def async_task(self):
        print("Task executed")

    def on_exit(self):
        pass