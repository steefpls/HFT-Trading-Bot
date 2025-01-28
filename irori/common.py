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
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.common.util.order_utils import limit_order, trail_order, market_order, order_leg, limit_order_with_legs
from tigeropen.common.consts import Market
from tigeropen.common.util.contract_utils import stock_contract
from tigeropen.common.exceptions import ApiException
import ctypes # for preventing sleep
from datetime import datetime, timezone, timedelta
import time
from typing import List, Dict
from enum import Enum
import pandas as pd
import pandas_market_calendars as mcal
import pytz
from jproperties import Properties
import yfinance as yf

# Define Windows API Constants
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
USER = ""

#for tickers not in NYSE, if it is not in this dict, it will use NYSE calendar by default
market_ticker_dict ={
    "NOVOBDKK":"XCSE"
}

empty_day_dict ={
    "NOVOBDKK":["2023-05-01"]
}

def convert_yfin_ticker(string):
    match string:
        case 'SPX':
            return '^GSPC'
        case 'USA500IDX':
            return '^GSPC'
        case 'NOVOBDKK':
            return 'NVO'
        # Add more cases as needed
        case _:
            # Return original string if no pattern matched
            return string

# ENUMS
class Broker(Enum):
    NIL = 0
    TIGER = 1
    MOOMOO = 2
    BACKTEST = 3
    BT_DAY = 4

class Markets(Enum):
    US = 'US'
    HK = 'HK'
    SG = 'SG'

class OrderStatus(Enum):
    NONE = 'NONE'
    NEW = 'NEW'
    FILLED = 'FILLED'
    PARTIALLY_FILLED = 'PARTIALLY_FILLED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'
    OTHERS = 'OTHERS'

class OrderType(Enum):
    NONE = 'NONE'
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'
    STOP = 'STOP' # Stop Loss Order
    STOP_LMT = 'STOP_LIMIT'
    TRAIL = 'TRAIL' # Trailing stop order
    TRAIL_LMT = 'TRAIL_LMT'

class OrderAction(Enum):
    NONE = 'N/A'
    BUY = 'BUY'
    SELL = 'SELL'
    SHORT_OPEN = 'SHORT_OPEN'
    SHORT_CLOSE = 'SHORT_CLOSE'
    MODIFY = 'MODIFY'
    CANCEL = 'CANCEL'

class TrailType(Enum):
    PERCENT = 'PERCENT'
    VALUE = 'VALUE'

class TimeInForce(Enum):
    DAY = 'DAY'
    GTC = 'GTC'

class PriceType(Enum):
    CURRENT = 'CURRENT'
    HIGH = 'HIGH'
    LOW = 'LOW'
    OPEN = 'OPEN'
    CLOSE = 'CLOSE'

# Command Classes
class AccountQuery:
    def __init__(self) -> None:
        self.currency = 'USD'

    def __init__(self, currency) -> None:
        self.currency = currency

class StockBriefsQuery:
    def __init__(self, ticker: str = None) -> None:
        self.tickerList = []
        if ticker is not None:
            self.tickerList.append(ticker)
    
    def add_ticker(self, ticker):
        self.tickerList.append(ticker)

class StockBriefsResponse:
    def __init__(self):
        self.price: dict[str, int] | None = {}

    def add_price(self, ticker: str, price: int):
        if price <= 0 or ticker == "":
            return

        self.price[ticker] = price

    def get_price(self, ticker: str):
        """
        Returns -1 if ticker not found
        """
        
        return self.price.get(ticker, -1)

class OrderCommand:
    def __init__(self) -> None:
        self.price = 0.0
        self.aux_price = 0.0
        self.quantity = 0
        self.ticker = ''
        self.market = Markets.US
        self.trail_type = TrailType.PERCENT
        self.trail_price = 0.0
        self.time_in_force: TimeInForce = TimeInForce.GTC

    def __init__(self, ticker = '', price = 0.0, aux_price = 0.0, quantity = 1, trail_type = TrailType.PERCENT, trail_price = 0.0, time_in_force = TimeInForce.GTC) -> None:
        # general
        self.ticker = ticker
        self.price = price # only used for limit
        self.quantity = quantity

        # stop order
        self.aux_price = aux_price # used for stop orders

        #trailing stop
        self.trail_type = trail_type
        self.trail_price = trail_price  #trail price will be a percentage if trail_type is PERCENT, and will be a flat value if trail_type = VALUE

        self.market = Markets.US

        self.time_in_force = time_in_force

class ModifyOrderCommand:
    def __init__(self) -> None:
        self.orderID = ''
        self.new_quantity = 0
        self.new_price = 0.0
        self.ticker = ''
        self.market = Markets.US

    def __init__(self, orderID = '', new_quantity = 0, new_price = 0.0, ticker = '', market = Markets.US) -> None:
        self.orderID = orderID
        self.new_quantity = new_quantity
        self.new_price = new_price
        self.ticker = ticker
        self.market = market

class CancelOrderCommand:
    def __init__(self) -> None:
        self.orderID = ''
        self.ticker = ''
        self.market = Markets.US

    def __init__(self, orderID = '', ticker = '', market = Markets.US) -> None:
        self.orderID = orderID
        self.ticker = ticker
        self.market = market

class ClearExistingOrderCommand:
    def __init__(self) -> None:
        self.ticker = ''
        self.market = Markets.US

    def __init__(self, ticker = '', market = Markets.US) -> None:
        self.ticker = ticker
        self.market = market

class SellAllPositionsCommand:
    def __init__(self) -> None:
        self.ticker = ''
        self.market = Markets.US

    def __init__(self, ticker = '', market = Markets.US) -> None:
        self.ticker = ticker
        self.market = market

class Tickers:
    tickerList = []

#Response Classes
class TickChangeData:
    def __init__(self) -> None:
        self.ticker = ''
        self.time = datetime.now()
        self.price = 0

    def __init__(self, ticker, time, price) -> None:
        self.ticker = ticker
        self.time = time
        self.price = price

# ACTIONS
# BUY
# SELL
# SELL_SHORT
# BUY_BACK

class OrderChangeData:
    def __init__(self) -> None:
        self.orderID = ''
        self.ticker = ''
        self.order_status : OrderStatus = OrderStatus.NEW
        self.avg_fill_price = 0.0
        self.limit_price = 0.0
        self.stop_price = 0.0
        self.total_quantity = 0
        self.filled_quantity = 0
        self.action = OrderAction.NONE # 'BUY', 'SELL'
        self.order_type : OrderType = None
        self.commissionAndFee = 0.0
        self.timestamp = ''
        self.error_message = ''
        self.liquidation = False

        self.trail_type : TrailType = TrailType.VALUE
        self.trail_price = 0.0
        self.is_short = False

    def __init__(self, orderID = '', ticker = '', order_status = OrderStatus.NEW, avg_fill_price = 0, limit_price = 0, stop_price = 0, total_quantity = 0, 
                filled_quantity = 0, action = OrderAction.NONE, order_type = OrderType.NONE, commissionAndFee = 0.0, timestamp = '', error_message = '', trail_type = TrailType.VALUE, trail_price = 0.0,
                is_short = False) -> None:
        self.orderID = orderID
        self.ticker = ticker
        self.order_status = order_status
        self.avg_fill_price = avg_fill_price
        self.limit_price = limit_price
        self.stop_price = stop_price
        self.total_quantity = total_quantity
        self.filled_quantity = filled_quantity
        self.action = action
        self.order_type = order_type
        self.commissionAndFee = commissionAndFee
        self.timestamp = timestamp
        self.filled_quantity = filled_quantity
        self.error_message = error_message
        self.trail_type = trail_type
        self.trail_price = trail_price
        self.is_short = is_short

class Order:
    def __init__(self):
        self.order_id = ''
        self.ticker = ''
        self.order_type : OrderType = OrderType.NONE
        self.order_status : OrderStatus = OrderStatus.OTHERS
        self.total_quantity = 0
        self.price = 0.0
        self.action = OrderAction.NONE
        self.created_time = ''
        self.aux_price = 0.0
        self.error_message = ''
        self.trail_type : TrailType = TrailType.VALUE
        self.trail_price = 0.0

    def __init__(self, order_id = '', ticker = '', order_type = OrderType.NONE, order_status = OrderStatus.OTHERS, total_quantity = 0, price = 0.0,
                 created_time = '', aux_price = 0.0, error_message = '', trail_type = TrailType.VALUE, trail_price = 0.0, action = OrderAction.NONE):
        self.order_id = order_id
        self.ticker = ticker
        self.order_type : OrderType = order_type
        self.order_status : OrderStatus = order_status
        self.total_quantity = total_quantity
        self.price = price
        self.action = action
        self.created_time = created_time
        self.aux_price = aux_price
        self.error_message = error_message
        self.trail_type = trail_type
        self.trail_price = trail_price

class Stock:
    def __init__(self) -> None:
        self.ticker = ''
        self.quantity = 0
        self.average_cost = 0.0
        self.market_price = 0.0

    def __init__(self, ticker = '', quantity = 0, average_cost = 0.0, market_price = 0.0) -> None:
        self.ticker = ticker
        self.quantity = quantity
        self.average_cost = average_cost
        self.market_price = market_price

    def __str__(self) -> str:
        return (f"Ticker: {self.ticker}, "
                f"Quantity: {self.quantity}, "
                f"Market Price: ${self.market_price:.2f}")

class AccountResponse:
    def __init__(self) -> None:
        self.cash_balance = 0.0
        self.available_cash_for_trading = 0.0
        self.available_cash_for_withdrawal = 0.0
        self.buying_power = 0.0
        self.assets_value = 0.0
        self.gross_position_value = 0.0
        self.unrealized_pl = 0.0
        self.realized_pl = 0.0
    
    def __init__(self, cash_balance = 0.0, buying_power = 0.0, available_cash_for_trading = 0.0, available_cash_for_withdrawal = 0.0, assets_value = 0.0, gross_position_value = 0.0, unrealized_pl = 0.0, realized_pl = 0.0) -> None:
        self.cash_balance = cash_balance
        self.available_cash_for_trading =available_cash_for_trading
        self.available_cash_for_withdrawal = available_cash_for_withdrawal
        self.buying_power = buying_power
        self.assets_value = assets_value
        self.gross_position_value = gross_position_value
        self.unrealized_pl = unrealized_pl
        self.realized_pl = realized_pl

    def __str__(self):
        return (f"-------------------- Account Information --------------------\n"
                f"Cash balance: {self.cash_balance:.2f}\n"
                f"Gross position value: {self.gross_position_value:.2f}\n"
                f"Unrealized PL: {self.unrealized_pl:.2f}\n"
                f"Realized PL: {self.realized_pl:.2f}"
                )

class PositionsResponse:
    def __init__(self):
        self.stockList : List[Stock] = []

    def __str__(self) -> str:
        if not self.stockList:  # Check if the list is empty
            # return "No stocks in portfolio."
            return (f"-------------------- Positions Information --------------------\n"
                    f"No stocks in portfolio")
        output = [] 
        for stock in self.stockList:
            output.append(f"{stock.ticker} (${stock.market_price:.2f}): {stock.quantity}")
        return (f'\n'.join(output))
    
    def get_stock_by_ticker(self, ticker: str) -> Stock:
        """Returns the stock object with the given ticker or None if not found."""
        for stock in self.stockList:
            if stock.ticker == ticker:
                return stock
        return None


class IroriOrderStatusCode(Enum):
    SUCCESSFUL = 200
    ERROR = 500

class IroriOrderResponse:
    def __init__(self):
        self.remarks: str = ''
        self.error_message: str = ''
        self.status_code: IroriOrderStatusCode = IroriOrderStatusCode.SUCCESSFUL
        self.order_id: int = -1
    
    def __init__(self, order_id: int = -1, error_message: str = '', remarks: str = '', status_code:IroriOrderStatusCode = IroriOrderStatusCode.SUCCESSFUL):
        self.order_id = order_id
        self.error_message = error_message
        self.status_code = status_code
        self.remarks = remarks
        if order_id <= -1:
            status_code = IroriOrderStatusCode.ERROR

def init_time(config:Properties):
    global precision
    
    time_property = int(config.get("Time").data)
    
    if time_property is not None:
        precision = time_property
    else:
        precision = 0

def retry(times, exceptions):
    """
    Retry Decorator
    Retries the wrapped function/method `times` times if the exceptions listed
    in ``exceptions`` are thrown
    :param times: The number of times to repeat the wrapped function/method
    :type times: Int
    :param Exceptions: Lists of exceptions that trigger a retry attempt
    :type Exceptions: Tuple of Exceptions
    """
    def decorator(func):
        def newfn(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    # logger.error(
                    #     'Exception thrown when attempting to run %s, attempt '
                    #     '%d of %d' % (func, attempt, times)
                    # )
                    print(
                        'Exception thrown when attempting to run %s, attempt '
                        '%d of %d' % (func, attempt, times)
                    )
                    attempt += 1
            return func(*args, **kwargs)
        return newfn
    return decorator

def prevent_sleep():
    """
    Prevents the system from going to sleep.
    """
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    
def allow_sleep():
    """
    Allows the system to go to sleep.
    """
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS)

def open_config_file(file_path) -> Properties:
    jPropertyConfigs = Properties()
    with open("configs/" + file_path, "rb") as config_file:
        jPropertyConfigs.load(config_file)
        
    return jPropertyConfigs

def properties_to_dict(properties) -> dict:
    prop_dict = {}
    # Assuming `properties` has an iterator or can be accessed like a dictionary
    for key in properties:
        prop_dict[key] = properties[key]
    return prop_dict

def check_market_open(quote_client):
    isMarketClosed = True

    while isMarketClosed:
        market_status_list = quote_client.get_market_status(Market.US)
        marketStatus = market_status_list[0].trading_status 

        if marketStatus != "TRADING":
            # Offset market open time by 1 hour
            open_time = market_status_list[0].open_time # + timedelta(hours=1)
            if open_time.tzinfo:
                current_time = datetime.now(timezone.utc).astimezone(open_time.tzinfo)

            time_difference = open_time - current_time

            days = time_difference.days
            hours, remainder = divmod(time_difference.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            print(f"Market opens on: {open_time.strftime('%Y-%m-%d %H:%M:%S')}, Time until open: {days} days, {hours} hours, {minutes} minutes, {seconds} seconds.\nScript will sleep until market opens.")

            seconds_until_open = time_difference.total_seconds()
            time.sleep(seconds_until_open + 1)
        else:
            # logger.info("Market is open.")
            print("Market is open.")
            isMarketClosed = False

def is_market_open() -> bool:
    try:
        nyse = mcal.get_calendar('XNYS')
        new_york_time_zone = pytz.timezone('America/New_York')
        current_time = datetime.now(new_york_time_zone)
        current_date_str = current_time.strftime('%Y-%m-%d')

        schedule = nyse.schedule(start_date=current_date_str, end_date=current_date_str)

        # Check if the schedule is empty
        if schedule.empty:
            #print("The trading schedule is empty for the current date.")
            return False

        # Extract the open and close times from the schedule
        market_open = schedule.iloc[0]['market_open']
        market_close = schedule.iloc[0]['market_close']
        #print(f"Market open time: {market_open}")

        # Check if the current time is within the trading hours
        if market_open <= current_time <= market_close:
            print("The market is currently open.")
            return True
        elif current_time < market_open:
            time_until_open = market_open - current_time
            print(f"Time until market opens: {time_until_open}")
            return False
        else:
            print("The market is currently closed.")
            return False
    except Exception as err:
        print(f'Exception in is_market_open: {err}')
        return False

def time_until_market_open():
    nyse = mcal.get_calendar('NYSE')
    now = datetime.now(pytz.timezone('America/New_York'))

    # Format the current time to string because the market calendar uses string dates
    today_str = now.strftime('%Y-%m-%d')
    schedule = nyse.schedule(start_date=today_str, end_date=(now + timedelta(days=7)).strftime('%Y-%m-%d'))

    next_open = None
    for _, row in schedule.iterrows():
        if row['market_open'] > now:
            next_open = row['market_open']
            break

    if next_open:
        # Calculate the difference in seconds
        return (next_open - now).total_seconds()
    
    return 0

def time_until_market_close():
    nyse = mcal.get_calendar('NYSE')
    now = datetime.now(pytz.timezone('America/New_York'))

    today_str = now.strftime('%Y-%m-%d')
    schedule = nyse.schedule(start_date=today_str, end_date=today_str)

    # Assuming the market is open, find today's closing time
    if not schedule.empty:
        market_close = schedule.iloc[0]['market_close']

        # Adjust for early closes (subtracting 1 minute as market_calendars marks close as 1 minute past the actual close)
        # Extra 1 minute offset for a total of 2 minutes
        market_close = market_close - pd.Timedelta(minutes=2)

        # Calculate the difference in seconds
        return (market_close - now).total_seconds()
    
    return 0

def get_trading_time_seconds(input_date: datetime) -> int:
    # Convert the input to a date object if it's a string
    if isinstance(input_date, str):
        try:
            input_date = datetime.strptime(input_date, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Invalid date format. Please use 'YYYY-MM-DD'.")

    # Get the NYSE market calendar
    nyse = mcal.get_calendar('NYSE')
    
    # Fetch the schedule for the given date
    schedule = nyse.schedule(start_date=input_date, end_date=input_date)
    
    if schedule.empty:
        # If there's no schedule, it's not a trading day
        raise ValueError("No trading schedule found for the given date.")
        return 0
    
    # Get open and close times
    market_open = schedule.iloc[0]['market_open']
    market_close = schedule.iloc[0]['market_close']
    
    # Calculate trading hours
    trading_seconds = (market_close - market_open).seconds
    
    return trading_seconds

def sleep_irori_bot(seconds_to_sleep):
    global stop_sleep 
    stop_sleep = False
    global raiseerror
    raiseerror = False
    sgd_start_time_str = datetime.now().strftime("%m-%d %I:%M %p")
    sgt_end_time_str = (datetime.now() + timedelta(seconds=seconds_to_sleep)).strftime("%m-%d %I:%M %p")
    print(f"Irori sleeping from sg time {sgd_start_time_str} to {sgt_end_time_str}")
    for _ in range (int(seconds_to_sleep + precision)):
        if stop_sleep:
            print("Sleep interrupted by flag")
            return
        if raiseerror:
            print("Error raised, Sleep interrupted,")
            raise (InterruptedError("Error raised, Sleep Interrupted"))
        time.sleep(1)

def interrupt_sleep():
    global stop_sleep
    stop_sleep = True
    print("Flag set to stop sleep.")

def raise_error():
    global raiseerror
    raiseerror = True
    print("Flag set to raise error.")


def str_to_enum(enum_class:Enum, enum_str:str):
    if enum_str in enum_class.__members__:
        return enum_class[enum_str]
    else:
        raise ValueError(f"'{enum_str}' is not a valid member of {enum_class.__name__}")

class Backtest_Ticker:
    def __init__(self, ticker):
        self.ticker:str = ticker
        self.yfinance_ticker:str = convert_yfin_ticker(ticker)
        self.split_date:pd.Series = None
        from irori.stats import DailyStockStat
        self.stock_stat_list:list[DailyStockStat] = []
        self.yfinance_tick_data_df: pd.DataFrame = None # Will be populated only if yFin broker

class Backtest_MasterData:
    def __init__(self):
        self.tickers:Dict[str, Backtest_Ticker] = {}
        self.date_list:list[datetime] = []
    
    def add_ticker(self, ticker_name):
        if ticker_name not in self.tickers:
            self.tickers[ticker_name] = Backtest_Ticker(ticker_name)
            return self.tickers[ticker_name]
        
        return None
    
    def get_backtest_ticker(self, ticker_name):
        return self.tickers.get(ticker_name, None)

    def add_date(self, date):
        self.date_list.append(date)
    
    def adjust_for_splits(self, ticker_name:str, df:pd.DataFrame):
        ticker = self.tickers[ticker_name]
        df['Datetime'] = pd.to_datetime(df['Datetime'], format='ISO8601', errors='coerce')
        for split_date, split_ratio in ticker.split_date.items():
            df.loc[df['Datetime'] < split_date, 'Price'] /= split_ratio
        return df

def parse_datetime(date_value):
            if isinstance(date_value, str):
                try:
                    # First try parsing with microseconds
                    return datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S.%f%z')
                except ValueError:
                    # If it fails, try without microseconds
                    return datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S%z')
            elif isinstance(date_value, pd.Timestamp):
                return date_value.to_pydatetime()
            else:
                raise TypeError(f"Unsupported type for date parsing: {type(date_value)}")
