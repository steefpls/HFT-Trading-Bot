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
import time
import atexit # for handling exit
import ctypes # for preventing sleep
import sys # for handling exceptions
from tigeropen.common.consts import (
    Language,  # Language
    Market,  # Market
    BarPeriod,  # Size of each time window of the K-Line
    QuoteRight,
)  # Price adjustment type
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.push.push_client import PushClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.common.consts import Market, SecurityType, Currency
from tigeropen.common.util.contract_utils import stock_contract
from tigeropen.push.pb.OrderStatusData_pb2 import OrderStatusData
from tigeropen.push.push_client import PushClient
from tigeropen.tiger_open_config import get_client_config

# Supported order types
from tigeropen.common.util.order_utils import (
    market_order,  # Market Order
    limit_order,  # Limit Order
    stop_order,  # Stop Order
    stop_limit_order,  # Stop Limit Order
    trail_order,  # Trailing Stop Order
    order_leg,
)  # Attached Order

from jproperties import Properties
from typing import List
import os
from datetime import datetime, timezone
from savedata import (analysis_data_dict, stock_names_save, add_analysis_data, add_scalp_data, save_analysis_data, save_scalp_data)
import pandas as pd

order_dict = {'BUY':[], 'SELL':[]}

###------------------------------------------------------------- Configs

class StockConfig:
    openPrice = 0
    currentPrice = 0
    stopLossPrice = 0

    highestTarget = 0
    highestOrderID = 0
    
    def __init__(
        self,
        stockName,
        allocatedBudget,
        downBuyDelta,
        upBuyDelta,
        targetedPrice,
        stopLoss,
        stopLossPercent,
        purchaseScale,
        maxConcurrentTrades,
        clearExistingOrders
    ):
        self.stockName = stockName
        self.allocatedBudget = float(allocatedBudget)
        self.downBuyDelta = float(downBuyDelta)
        self.upBuyDelta = float(upBuyDelta)
        self.targetedPrice = float(targetedPrice)
        self.stopLoss = stopLoss.lower() in ["true", "1", "t", "y", "yes"]
        self.stopLossPercent = float(stopLossPercent)
        self.purchaseScale = int(purchaseScale)
        self.maxConcurrentTrades = int(maxConcurrentTrades)
        self.clearExistingOrders = clearExistingOrders.lower() in ["true", "1", "t", "y", "yes"]

def ReadStockConfigs(folder_path: str) -> List[StockConfig]:
    stock_configs = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".config"):
            file_path = os.path.join(folder_path, filename)

            with open(file_path, "rb") as config_file:
                properties = Properties()
                properties.load(config_file)

                stock_configs.append(
                    StockConfig(
                        stockName=os.path.splitext(filename)[0],
                        allocatedBudget=properties.get("allocatedBudget").data,
                        downBuyDelta=properties.get("downBuyDelta").data,
                        upBuyDelta=properties.get("upBuyDelta").data,
                        targetedPrice=properties.get("targetedPrice").data,
                        stopLoss=properties.get("stopLoss").data,
                        stopLossPercent=properties.get("stopLossPercent").data,
                        purchaseScale=properties.get("purchaseScale").data,
                        maxConcurrentTrades=properties.get("maxConcurrentTrades").data,
                        clearExistingOrders=properties.get("clearExistingOrders").data
                    )
                )

    return stock_configs

def GetStockConfig(target_stock_name):
    for stock_config in stockConfigs:
        if stock_config.stockName == target_stock_name:
            return stock_config
    return None

# Almost all requests related to pulling market quote data use the methods of QuoteClient,
# first generate the client config which used to initialize QuoteClient. The config contain developer's information like tiger_id, private_key, account
def get_client_config(sandbox=False):
    """
    https://quant.itigerup.com/#developer   query developer infos
    """
    client_config = TigerOpenClientConfig(sandbox_debug=sandbox)
    # if use windows system, need to add "r", like: read_private_key(r'C:\Users\admin\tiger.pem')
    client_config.private_key = accPrivateKey
    client_config.tiger_id = tigerId
    client_config.account = tigerAccount
    # client_config.timezone = 'US/Eastern' # default timezone
    return client_config

###------------------------------------------------------------- I/O / Controls

def savedata():
    for buy_id, sell_id in zip(order_dict['BUY'], order_dict['SELL']):
        buy_order = fetch_order_details(buy_id)
        sell_order = fetch_order_details(sell_id)
    
        add_scalp_data(
            stock_name=buy_order.contract.symbol, 
            Buy_Order_ID=str(buy_id),
            Sell_Order_Id=str(sell_id),
            Buy_price=buy_order.avg_fill_price, 
            Buy_time=str(buy_order.order_time),
            Sell_price=sell_order.avg_fill_price, 
            Sell_time=str(sell_order.trade_time), 
            Profit_Loss=sell_order.realized_pnl - buy_order.realized_pnl,
            Fees=buy_order.commission + sell_order.commission,
            Net_Profit_loss=(sell_order.realized_pnl - buy_order.realized_pnl) - (buy_order.commission + sell_order.commission),
            Buy_Quantity=buy_order.quantity,
            Sell_Quantity = sell_order.quantity
        )

    save_scalp_data()

    positions = trade_client.get_positions(sec_type=SecurityType.STK, currency = Currency.ALL, market=Market.ALL)


    for names in stock_names:
        print(names)
        briefs = quote_client.get_stock_briefs([names])
        add_analysis_data(names,            # name of stock
                          0,                # p&l including unrealised gains usd
                          0,                # p&l % including unrealised gains
                          0,                # stocks not sold
                          0,                # value of stock not sold
                          0,                # p&l from completed orders
                          0,                # successful profitable scalps
                          0,                # stock are not sold at the end of the day
                          0,                # profitable scalps that were successfully sold %    
            float(briefs.open[0]),          # market open price
            float(briefs.close[0]),         # market close price
            float(briefs.low[0]),           # market low price
            float(briefs.high[0]),          # market high price
                        0,                  # amount of budget used in flat USD. (Not total cost)
                        0,                  # money is being moved within our bot including platform and commission fees
            float(briefs.volume[0])         # stock trading vol
            )
        
    save_analysis_data()

# Crash and runtime error handling
def on_exit():
    print("Compile analysis data and serialize data to file.")
    savedata()
    print("Done close")
    # max_length = max(len(order_dict['BUY']), len(order_dict['SELL']))
    # df_orders = pd.DataFrame({
    #     'BUY': order_dict['BUY'] + [None] * (max_length - len(order_dict['BUY'])),
    #     'SELL': order_dict['SELL'] + [None] * (max_length - len(order_dict['SELL']))
    # })

    # filename = datetime.now().strftime('%Y%m%d') + '_OrderData.xlsx'

    # with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    #     df_orders.to_excel(writer, sheet_name='Order Data', index=False)

    # print(f"Data saved to Excel sheet named '{filename}'.")
    
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    print("Exception occurred: ", exc_value)
    on_exit()  # Call the same function used in atexit

# Register the exit function
atexit.register(on_exit)

# Set the global exception handler to our handling function
sys.excepthook = handle_exception

###-------------------------------------------------------------Trade Functions

def fetch_order_details(order_id):
    return trade_client.get_order(id=order_id)

def on_order_changed(frame: OrderStatusData):
    stockConfig = GetStockConfig(frame.symbol)
    if (frame.status == "FILLED" and frame.action == "BUY"):
        contract = stock_contract(symbol=frame.symbol, currency=frame.currency)
        stockConfig.currentPrice = frame.avgFillPrice
        newPrice = round((frame.avgFillPrice * stockConfig.targetedPrice), 2)
        if (newPrice <= frame.avgFillPrice):
            print(f"New price is lower than the current price. Sell order is skipped.")
        else:
            # Sell order
            time.sleep(5)
            order = limit_order(account=client_config.account, contract=contract, action='SELL', limit_price=newPrice, quantity=frame.filledQuantity)
            response = trade_client.place_order(order)
            order_dict['BUY'].append(frame.id)
            order_dict['SELL'].append(response)

            print(order_dict)
            print(f"Buy order filled at: {frame.avgFillPrice}. Placing sell order at: {newPrice}.")
    elif (frame.status == "FILLED" and frame.action == "SELL"):
        # Buy order
        contract = stock_contract(symbol=frame.symbol, currency=frame.currency)
        newPrice = round(frame.avgFillPrice-stockConfig.downBuyDelta, 2)
        if (newPrice <= stockConfig.stopLossPrice and stockConfig.stopLoss):
            print(f"New price is lower than the stop loss price. Sell order is skipped.")
        else:
            time.sleep(5)
            order = limit_order(account=client_config.account, contract=contract, action='BUY', limit_price=newPrice, quantity=stockConfig.purchaseScale)
            trade_client.place_order(order)
            print(f"Sell order filled at: {frame.avgFillPrice}. Placing buy order at: {newPrice}.")

###-------------------------------------------------------------Init
# Init account
jPropertyConfigs = Properties()
tigerAccPropertiesFile = "./TigerIroriDemoAccount.properties"
with open(tigerAccPropertiesFile, "rb") as config_file:
    jPropertyConfigs.load(config_file)

accPrivateKey = jPropertyConfigs.get("private_key_pk1").data
tigerId = jPropertyConfigs.get("tiger_id").data
tigerAccount = jPropertyConfigs.get("account").data

client_config = get_client_config()
protocol, host, port = client_config.socket_host_port
push_client = PushClient(host, port, use_ssl=(protocol == 'ssl'), use_protobuf=True)

print("-----------------Starting Irori Alpha-----------------")
if len(tigerAccount) == 17:
    print("Trading using demo account")
else:
    print("Trading using prime account")

# Init stock configs
strategy_folder_path = "alpha"
stockConfigs = ReadStockConfigs(strategy_folder_path)

if stockConfigs:
    stockNames = [config.stockName for config in stockConfigs]
    stock_names_save = [config.stockName for config in stockConfigs]
    print("Stock configurations found:\n" + ", ".join(stockNames))
else:
    print("No stock configurations found.")
    exit()
    
# Bind the callback method
push_client.order_changed = on_order_changed
# Connect
push_client.connect(client_config.tiger_id, client_config.private_key)
# Subscribe
push_client.subscribe_order(account=client_config.account)

# Variables
isMarketClosed = True

# Initialize clients
quote_client = QuoteClient(client_config)
trade_client = TradeClient(client_config)

# Market check
while isMarketClosed:
    market_status_list = quote_client.get_market_status(Market.US)
    isMarketClosed = market_status_list[0].trading_status == "MARKET_CLOSED"

    if isMarketClosed:
        open_time = market_status_list[0].open_time
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
        print("Market is open.")
        isMarketClosed = False

# Get stock briefs
stock_names = [stock_config.stockName for stock_config in stockConfigs]
briefs = quote_client.get_stock_briefs(stock_names)

# Init stockConfigs
for stockConfig in stockConfigs:
    row = briefs[briefs['symbol'] == stockConfig.stockName.upper()]
    stockConfig.openPrice = round(row['latest_price'].iloc[0])
    stockConfig.currentPrice = stockConfig.openPrice
    stockConfig.stopLossPrice = round(stockConfig.openPrice * stockConfig.stopLossPercent, 2)
    print(f"{stockConfig.stockName} open price: {stockConfig.openPrice}")

###--------------------------------------------------------- Start
print("-----------------Irori successfully started-----------------")
# Start algo for each stock config
# Clear ALL orders from all stocks
# Check existing stocks and clear if set to
# Buy X amount of stocks up until max concurrent trades

# Cancel existing Orders
orders = trade_client.get_orders(sec_type=SecurityType.STK, market=Market.ALL, states=["HELD"])
for order in orders:
    if (GetStockConfig(order.contract.symbol).clearExistingOrders):
        trade_client.cancel_order(order.id)

# For each stock, start trading
for stockConfig in stockConfigs:
    if (stockConfig.maxConcurrentTrades < 2 or stockConfig.maxConcurrentTrades < stockConfig.purchaseScale):
        print(f"Max concurrent trades for {stockConfig.stockName} is too low. Skipping.")
        continue
    
    # Clear existing stock if flag set
    clearExistingOrders = stockConfig.clearExistingOrders
    existingOrderTrades = 0
    if clearExistingOrders:
        positions = trade_client.get_positions(sec_type=SecurityType.STK, currency=Currency.ALL, market=Market.ALL)

        # Stock config should only clear their own position (held stock), so we can keep track of its individual concurrent trades
        for p in positions:
            if p.contract.symbol != stockConfig.stockName:
                continue

            contract = stock_contract(symbol=stockConfig.stockName, currency='USD')
            order = market_order(account=client_config.account, contract=contract, action='SELL', quantity=p.quantity)
            try:
                response = trade_client.place_order(order)
                existingOrderTrades += 1
            except:
                # TODO: Decide course of action if we cant sell existing orders
                pass
    
    offsetTrades = stockConfig.maxConcurrentTrades - stockConfig.purchaseScale - existingOrderTrades

    # Buy stocks. Place upper trade
    targetPrice = round(stockConfig.openPrice + stockConfig.upBuyDelta, 2)
    contract = stock_contract(symbol=stockConfig.stockName, currency='USD')
    order = stop_limit_order(account=client_config.account, contract=contract, action='BUY', aux_price=targetPrice, limit_price=targetPrice, quantity = stockConfig.purchaseScale)
    response = trade_client.place_order(order)
    print(f"Placing upper trade for {stockConfig.stockName} at {targetPrice}.")
    print(response)

    # # Calculate the number of rows
    # n = 0
    # while n * (n + 1) / 2 <= offsetTrades:
    #     n += 1
    # n -= 1 # Adjust for the extra increment

    # # Calculate the leftover
    # leftover = offsetTrades - (n * (n + 1) // 2)

    # # Place orders
    # for i in range(n, 0, -1):
    #     if i == n:
    #         targetPrice = stockConfig.openPrice - stockConfig.downBuyDelta
    #         contract = stock_contract(symbol=stockConfig.stockName, currency='USD')
    #         order = limit_order(account=client_config.account, contract=contract, action='BUY', limit_price=round(targetPrice, 2), quantity= i + leftover)
    #         trade_client. place_order(order)
    #     else:
    #         targetPrice = stockConfig.openPrice - (stockConfig.downBuyDelta * (n - i))
    #         contract = stock_contract(symbol=stockConfig.stockName, currency='USD')
    #         order = limit_order(account=client_config.account, contract=contract, action='BUY', limit_price=round(targetPrice, 2), quantity=i)
    #         trade_client. place_order(order)

    # Calculate the number of rows
    n = offsetTrades / stockConfig.purchaseScale
    leftover = offsetTrades % stockConfig.purchaseScale

    for i in range(1, int(n) + 1):
        targetPrice = stockConfig.openPrice - (stockConfig.downBuyDelta * i)
        contract = stock_contract(symbol=stockConfig.stockName, currency='USD')
        if i == 1:
            order = limit_order(account=client_config.account, contract=contract, action='BUY', limit_price=round(targetPrice, 2), quantity=stockConfig.purchaseScale + leftover)
        else:
            order = limit_order(account=client_config.account, contract=contract, action='BUY', limit_price=round(targetPrice, 2), quantity=stockConfig.purchaseScale)
        trade_client. place_order(order)

time.sleep(30)
###--------------------------------------------------------- Update

# Update
while True:
    # Update current price
    for stockConfig in stockConfigs:
        row = briefs[briefs['symbol'] == stockConfig.stockName.upper()]
        stockConfig.currentPrice = row['latest_price'].iloc[0]

    # Instructions per stock
    # for stockConfig in stockConfigs:
    #     print()

    # Request limit    
    time.sleep(5)

# client_config = get_client_config()

# Place order
# contract = stock_contract(symbol='NVDA', currency='USD')
# order = limit_order(account=client_config.account, contract=contract, action='BUY', limit_price=741, quantity=1)
# oid = trade_client. place_order(order)

# Get order
# orders = trade_client.get_orders(sec_type=SecurityType.STK, market=Market.ALL)
# order1 = orders[0]
# print(order1)
# print(order1.status)  # order status
# print(order1.id)  # order id
# print(order1.contract.symbol) # order contract id
# print(order1.contract.sec_type) # order type

# exit()
    
#TODO
# import ctypes
# import time

# # Define Windows API Constants
# ES_CONTINUOUS = 0x80000000
# ES_SYSTEM_REQUIRED = 0x00000001

# def prevent_sleep():
#     """
#     Prevents the system from going to sleep.
#     """
#     ctypes.windll.kernel32.SetThreadExecutionState(
#         ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

# def allow_sleep():
#     """
#     Allows the system to go to sleep.
#     """
#     ctypes.windll.kernel32.SetThreadExecutionState(
#         ES_CONTINUOUS)

# # Prevent sleep
# prevent_sleep()

# # Your script's main logic here
# # Example: time.sleep(10) simulates a task running for 10 seconds
# try:
#     print("Script is running, system won't sleep...")
#     time.sleep(10)  # Replace with your script's workload
# finally:
#     # Revert to the original settings (allow sleep) when done
#     allow_sleep()
#     print("Script finished, system can sleep again.")
