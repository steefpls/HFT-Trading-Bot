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
from tigeropen.common.consts import (Language,        # Language
                                Market,           # Market
                                BarPeriod,        # Size of each time window of the K-Line
                                QuoteRight)       # Price adjustment type
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.push.push_client import PushClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.common.consts import Market, SecurityType, Currency
from tigeropen.common.util.contract_utils import stock_contract
# Supported order types
from tigeropen.common.util.order_utils import (market_order,         # Market Order
                                                limit_order,         # Limit Order
                                                stop_order,          # Stop Order
                                                stop_limit_order,    # Stop Limit Order
                                                trail_order,         # Trailing Stop Order
                                                order_leg)           # Attached Order

from jproperties import Properties
from savedata import (analysis_data_dict, scalp_data_dict, add_analysis_data, add_scalp_data, save_analysis_data, save_scalp_data)
import re

jPropertyConfigs = Properties()
tigerAccPropertiesFile = './TigerIroriDemoAccount.properties'
with open(tigerAccPropertiesFile, 'rb') as config_file:
    jPropertyConfigs.load(config_file)

accPrivateKey = jPropertyConfigs.get("private_key_pk1").data
tigerId = jPropertyConfigs.get("tiger_id").data
tigerAccount = jPropertyConfigs.get("account").data

# print(f'PrivateKey: {accPrivateKey}\nId: {tigerId}\nAcc: {tigerAccount}')
if (len(tigerAccount) == 17):
    print("Trading using paper account")
else:
    print("Trading using prime account")


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

# initialize ClientConfig 
client_config = get_client_config()

# Initialize an instance of TradeClient
trade_client = TradeClient(client_config)

#Place order
contract = stock_contract(symbol='NVDA', currency='USD')
# order = limit_order(account=client_config.account, contract=contract, action='BUY', limit_price=717, quantity=1)
# oid = trade_client. place_order(order)


# orders = trade_client.get_orders(sec_type=SecurityType.STK, market=Market.ALL,start_time='2024-02-23', end_time='2024-02-24')
# print(orders)

# order_dict = {'BUY':{}, 'SELL':{}}

# # Loop through each order in the orders list
# for order in orders:

#     order_action = order.action
#     stock_name = order.contract.symbol
#     order_type = 'BUY' if order.action == 'BUY' else 'SELL'
    
#     if stock_name not in order_dict[order_type]:
#         order_dict[order_type][stock_name] = []

#     if order.status != order.status.CANCELLED:   
#         order_dict[order_type][stock_name].append(order)


#     print(order.id)  # Print the order ID
#     # print(order.action)     # Buy or Sell order
#     # print(order.limit_price)
#     # print(order.avg_fill_price) # price that you buy or sell at
#     # print(order.commission)
#     # print(order.status)
#     # print(order.filled) # print the filled orders
#     # print(order.order_time) # print the order time
#     # print(order.trade_time)  # Print the trade time
#     # print(order.realized_pnl) # print the realised profit and loss
#     # print(order.contract.symbol)  # Print the order contract symbol
#     # print(order.filled_cash_amount) # print the filled cash amount
#     # print(order.quantity)  # Print the order type (security type)

 

# order_dict = {
#     'BUY': [34052439217931264, 34052439180837888, 34042152206729216],
#     'SELL': [34052439217931264, 34052439197090816, 34052439180837888]
# }

# def fetch_order_details(order_id):
#     return trade_client.get_order(id=order_id)

# for buy_id, sell_id in zip(order_dict['BUY'], order_dict['SELL']):
#     buy_order = fetch_order_details(buy_id)
#     sell_order = fetch_order_details(sell_id)
    
#     # Assuming the orders contain all the necessary information and the following attributes are accessible
#     add_scalp_data(
#         stock_name=buy_order.contract.symbol,  
#         Buy_Order_ID=str(buy_id),
#         Sell_Order_Id=str(sell_id),
#         Buy_price=buy_order.avg_fill_price,  
#         Buy_time=str(buy_order.order_time),  
#         Sell_price=sell_order.avg_fill_price,  
#         Sell_time=str(sell_order.trade_time),  
#         Profit_Loss=sell_order.realized_pnl - buy_order.realized_pnl, 
#         Fees=buy_order.commission + sell_order.commission,  
#         Net_Profit_loss=(sell_order.realized_pnl - buy_order.realized_pnl) - (buy_order.commission + sell_order.commission),
#         Buy_Quantity=buy_order.quantity, 
#         Sell_Quantity = sell_order.quantity
#     )

# # After processing all orders, save the scalp data to an Excel file
# save_scalp_data()


# asset_val = trade_client.get_assets(account=None, sub_accounts=None, segment=False, market_value=False)
# print(asset_val)
# portfolioacc = asset_val[0]
# print(portfolioacc.summary.unrealized_pnl)
# print("done")
# quote_client = QuoteClient(client_config)
# name = "NVDA"
# briefs = quote_client.get_stock_briefs([name])
# print(briefs)
# print(type(briefs))



# # print(briefs)
# # print(briefs.high)
# # print(str(float(briefs.close[0])))

# positions = trade_client.get_positions(sec_type=SecurityType.STK, currency=Currency.ALL, market=Market.ALL)

# def extract_values(info_str):
#     # Split the string by comma to separate each piece of information
#     info_parts = info_str.split(", ")
#     print("hi")
#     print(info_str)
#     # Dictionary to hold the extracted values
#     extracted_values = {}

#     print("hello")
#     print(info_parts)
    
#     # Iterate through the parts to extract key-value pairs
#     for part in info_parts:
#         print(part)
#         # Split by colon to separate key and value, then strip whitespace
#         key, value = part.split(": ")
#         extracted_values[key.strip()] = value.strip()
    
#     # Extract specific values and convert to appropriate types
#     quantity = int(extracted_values.get("quantity", 0))
#     average_cost = float(extracted_values.get("average_cost", 0.0))
#     market_price = float(extracted_values.get("market_price", 0.0))
    
#     return quantity, average_cost, market_price

# # Search for the pattern in the input string
# quant = 0
# average_cost = 0
# market_price = 0
# s_name = "NVDA"
# for pos in positions:
#     print(pos)
#     name = str(pos.contract)
#     print(name)
#     quantity, average_cost, market_price = extract_values(str(pos))
#     print(quantity)
#     print(average_cost)
#     print(market_price)
#     parts = name.split('/')
#     val = parts[0]
#     if val == s_name:
#         print(f"The symbol {val} matches {s_name}.")
#         quant = quantity
#         print(quant)

#     print(parts[0])



# cancelled_orders = trade_client.get_cancelled_orders(sec_type=SecurityType.STK, market=Market.ALL)
#filled_orders = trade_client.get_filled_orders(sec_type=SecurityType.STK, market=Market.ALL
#                                               start_time='2024-02-27 01:00:00', end_time='2024-02-28 00:00:00')

# # print(cancelled_orders)
# # print(filled_orders)

orders = trade_client.get_open_orders(sec_type=SecurityType.STK, market=Market.ALL, symbol='NVDA')
for order in orders:
    print(order)
    print("--------------------")