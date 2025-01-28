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
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from irori.mediator import Mediator

class BrokerBase:
    def __init__(self):
        self.mediator: 'Mediator' = None

    def start(self, mediator:'Mediator'):
        self.mediator = mediator

    def authenticate(self):
        pass

    def get_account_details(self, account_query: AccountQuery):
        pass

    def get_positions(self):
        pass

    def query_stock_briefs(self, stock_briefs_query: StockBriefsQuery):
        pass
        
    def get_order(self, id):
        pass

    def cancel_order(self, id):
        pass

    def buy_market_order(self, buy_market_order_command: OrderCommand):
        pass

    def sell_market_order(self, sell_market_order_command: OrderCommand):
        pass

    def buy_limit_order(self, buy_limit_order_command: OrderCommand):
        pass

    def sell_limit_order(self, sell_limit_order_command: OrderCommand):
        pass

    def stop_market_buy_order(self, stop_market_buy_order_command : OrderCommand):
        pass

    def stop_market_sell_order(self, stop_market_sell_order_command : OrderCommand):
        pass

    def stop_limit_buy_order(self, stop_limit_buy_order_command: OrderCommand):
        pass

    def stop_limit_sell_order(self, stop_limit_sell_order_command: OrderCommand):
        pass

    def trailing_stop_market_order(self, trailing_command:OrderCommand):
        pass

    def trailing_stop_limit_order(self, trailing_command:OrderCommand):
        pass

    def short_open_limit_order(self, short_limit_order_command: OrderCommand):
        pass
    
    def short_close_limit_order(self, short_sell_limit_order_command:OrderCommand):
        pass

    def short_open_market_order(self, short_market_order_command:OrderCommand):
        pass

    def short_close_market_order(self, short_sell_market_order_command:OrderCommand):
        pass

    def short_open_stop_market_order(self, short_stop_market_order_command:OrderCommand):
        pass

    def short_close_stop_market_order(self, short_stop_sell_market_order_command:OrderCommand):
        pass

    def short_open_stop_limit_order(self, short_stop_limit_order_command: OrderCommand):
        pass

    def short_close_stop_limit_order(self, short_stop_limit_sell_order_command: OrderCommand):
        pass

    def modify_order(self, modify_order_command: ModifyOrderCommand):
        pass

    # Cancels existing orders
    def clear_existing_orders(self, clear_order : ClearExistingOrderCommand):
        pass

    # SELLS AT MARKET ORDER
    def sell_all_existing_stocks(self, ticker):
        pass

    # Cancels all orders and sells all existing stocks
    def exit_all_positions_immediately(self, clear_order : ClearExistingOrderCommand):
        pass

    def setup_callbacks(self, tick_event_callable:callable, order_event_callable:callable, tickers: Tickers):
        pass

    def stop(self):
        pass
