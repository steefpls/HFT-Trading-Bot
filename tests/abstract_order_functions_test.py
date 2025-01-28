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
import pandas as pd
import irori.common as common

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

quote_client = QuoteClient(client_config)

# Initialize an instance of TradeClient
trade_client = TradeClient(client_config)


# ------------------- Script to test abstracted trade functions ----------------------------
oid = common.place_limit_order(trade_client, tigerAccount, 'NVDA', 'BUY', 1, 700.00)
oid2 = common.place_limit_order(trade_client, tigerAccount, 'NVDA', 'BUY', 2, 700.00)

print(f"{oid} {oid2}")

time.sleep(10)

scalpList = []
s1 = common.Scalp()
s1.buy_order_id = oid
s1.current_action = 'BUY'
s1.buy_quantity = 1

s2 = common.Scalp()
s2.buy_order_id = oid2
s2.current_action = 'BUY'
s2.buy_quantity = 2

scalpList.append(s1)
scalpList.append(s2)

common.modify_order_batch(scalpList, trade_client, 900.00, 'BUY')

time.sleep(30)

common.place_limit_order(trade_client, tigerAccount, 'NVDA', 'SELL', 3, 700.00)
