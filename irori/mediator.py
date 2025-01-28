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
from typing import *
from irori.common import *
from irori.stats import *

from irori.Broker_Tiger import *
from irori.Broker_Backtest import *
from irori.Broker_Moomoo import *
from irori.Broker_YFinance import *

class Mediator:
    tiger_obj:TigerBroker = None
    #moomoo_obj:MooMooBroker = None
    backtest_obj:BacktestBroker = None
    bt_day_obj:YFinanceBroker = None

    stats:IntradayStats = None
    current_sharpe_trade:Trade = None
    returns:list[float] = []
    valid_sharpe = True

    selected_broker = Broker.NIL

    def __init__(self):
        pass

    def init(self, broker : Broker):
        self.bt_day_obj = YFinanceBroker()
        self.bt_day_obj.start(self)    
        self.notification_on = False
        
        match(broker):
            case Broker.TIGER:
                self.tiger_obj = TigerBroker()
                self.tiger_obj.authenticate()
            case Broker.MOOMOO:
                #self.moomoo_obj = MooMooBroker()
                #self.moomoo_obj.authenticate()
                pass
            case Broker.BACKTEST:
                self.backtest_obj = BacktestBroker()
                self.backtest_obj.start(self)
            case Broker.BT_DAY:
                pass
            case _:
                raise Exception("Invalid Broker")
            
        self.selected_broker = broker
    
    def start(self):
        match(self.selected_broker):
            case Broker.TIGER:
                self.tiger_obj.start(self)
            case Broker.MOOMOO:
                #self.moomoo_obj.start(self)
                pass
            case Broker.BACKTEST:
                self.backtest_obj.start(self)
            case Broker.BT_DAY:
                self.bt_day_obj.start(self)
            case _:
                raise Exception("Invalid Broker")
    
    def start_stats(self, date_time:datetime):
        self.date_time_start = date_time
        account_response = self.get_account_information(AccountQuery(currency='USD'))
        self.stats = IntradayStats(self.date_time_start, account_response.cash_balance, account_response.gross_position_value, self.get_positions())
        self.stats.trades = []

    def resolve_purchase(self, ticker:str, datetime:datetime, quantity:int, price:float, fee:float, action:OrderAction):
        trade:Trade = Trade()
        trade.ticker = ticker
        trade.date_time = datetime
        trade.price = price
        trade.quantity = quantity
        trade.fees = fee
        trade.buy_sell = action.name
        if action == OrderAction.BUY or action == OrderAction.SHORT_OPEN:
            trade.net_returns = -1 * (price * quantity + fee)
            if self.current_sharpe_trade == None:
                self.current_sharpe_trade = Trade()
                self.current_sharpe_trade.price = price
                self.current_sharpe_trade.quantity = quantity
                self.current_sharpe_trade.fees = fee
            else:
                total_cost = (self.current_sharpe_trade.price * self.current_sharpe_trade.quantity) + (price * quantity)
                total_quantity = self.current_sharpe_trade.quantity + quantity
                avg_price = total_cost / total_quantity
                self.current_sharpe_trade.price = avg_price
                self.current_sharpe_trade.quantity = total_quantity
                self.current_sharpe_trade.fees += fee
                #self.valid_sharpe = False
                #self.returns = []

        elif action == OrderAction.SELL or action == OrderAction.SHORT_CLOSE:
            trade.net_returns = price * quantity - fee
            if (self.current_sharpe_trade != None):
                initial_cost = self.current_sharpe_trade.price * self.current_sharpe_trade.quantity + self.current_sharpe_trade.fees
                net_return = (price * quantity - fee - initial_cost) / initial_cost
                self.current_sharpe_trade.quantity -= quantity
                if self.current_sharpe_trade.quantity == 0:
                    self.current_sharpe_trade = None  # Reset if all shares are sold
                    self.returns.append(net_return)
                else:
                    self.valid_sharpe = False
                    self.returns = []
            else:
                self.valid_sharpe = False
                self.returns = []
        else:
            print(f"resolve_purchase action should be valid: {action}")
        
        if not self.stats:
            return
        
        self.stats.exposure_tracker.update_expoure_time(self.get_positions(), datetime)
        self.stats.trades.append(trade)
    
    def calculate_stats(self, last_tick_time:datetime):
        try:
            match self.selected_broker:
                case Broker.BACKTEST:
                    self.stats.calculate_end(self.backtest_obj.get_account_details(AccountQuery('USD')).gross_position_value, last_tick_time)
                case Broker.BT_DAY:
                    self.stats.calculate_end(self.bt_day_obj.get_account_details(AccountQuery('USD')).gross_position_value, last_tick_time)
        except Exception as ex:
            print(f"Error calculating stats. Broker {self.selected_broker}. Err {ex}")

    def setup_backtest_broker(self, brokerForFees:Broker):
        match self.selected_broker:
            case Broker.BACKTEST:
                self.backtest_obj.setup_broker(brokerForFees)
            case Broker.BT_DAY:
                self.bt_day_obj.setup_broker(brokerForFees)
            case _:
                pass
    
    def set_working_currency(self, working_currency: float):
        match self.selected_broker:
            case Broker.BACKTEST:
                self.backtest_obj.working_currency = working_currency
            case Broker.BT_DAY:
                self.bt_day_obj.working_currency = working_currency
            case _:
                pass

    def get_account_information(self, query_command : AccountQuery = AccountQuery('USD')) -> AccountResponse:
        match (self.selected_broker):
            case Broker.TIGER:
                # call tiger function
                query_response = self.tiger_obj.get_account_details(acc_detail_obj=query_command)
                return query_response
            case Broker.MOOMOO:
                # call moomoo function
                query_response = self.moomoo_obj.get_account_details(acc_detail_obj=query_command)
                return query_response
            case Broker.BACKTEST:
                query_response = self.backtest_obj.get_account_details(acc_detail_obj=query_command)
                return query_response
            case Broker.BT_DAY:
                query_response = self.bt_day_obj.get_account_details(acc_detail_obj=query_command)
                return query_response
            case _:
                raise Exception("Invalid Broker")

    def get_positions(self) -> PositionsResponse:
        match (self.selected_broker):
            case Broker.TIGER:
                # call tiger function
                pos_response = self.tiger_obj.get_positions()
                return pos_response
            case Broker.MOOMOO:
                # call moomoo function
                pos_response = self.moomoo_obj.get_positions()
                return pos_response
            case Broker.BACKTEST:
                pos_response = self.backtest_obj.get_positions()
                return pos_response
            case Broker.BT_DAY:
                pos_response = self.bt_day_obj.get_positions()
                return pos_response
            case _:
                raise Exception("Invalid Broker")

    def query_stock_briefs(self, stock_briefs_query: StockBriefsQuery = StockBriefsQuery())->StockBriefsResponse:
        match (self.selected_broker):
            case Broker.TIGER:
                # call tiger function
                pos_response = self.tiger_obj.query_stock_briefs(stock_briefs_query)
                return pos_response
            case Broker.MOOMOO:
                pos_response = self.moomoo_obj.query_stock_briefs(stock_briefs_query)
                return pos_response
            case Broker.BACKTEST:
                pos_response = self.backtest_obj.query_stock_briefs(stock_briefs_query)
                return pos_response
            case Broker.BT_DAY:
                pos_response = self.bt_day_obj.query_stock_briefs(stock_briefs_query)
                return pos_response
            case _:
                raise Exception("Invalid Broker")
    
    def get_raw_order(self, id):
        match (self.selected_broker):
            case Broker.TIGER:
                #return self.tiger_obj.get_order(id)
                pass
            case Broker.MOOMOO:
                return self.moomoo_obj.get_raw_order(id)
            case Broker.BACKTEST:
                #return self.backtest_obj.get_order(id)
                pass
            case _:
                raise Exception("Invalid Broker")

    def get_order(self, id):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.get_order(id)
            case Broker.MOOMOO:
                return self.moomoo_obj.get_order(id)
            case Broker.BACKTEST:
                return self.backtest_obj.get_order(id)
            case Broker.BT_DAY:
                return self.bt_day_obj.get_order(id)
            case _:
                raise Exception("Invalid Broker")

    def buy_market_order(self, buy_market_order_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.buy_market_order(buy_command=buy_market_order_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.buy_market_order(buy_command=buy_market_order_command)
            case Broker.BACKTEST:
                return self.backtest_obj.buy_market_order(buy_command=buy_market_order_command)
            case Broker.BT_DAY:
                return self.bt_day_obj.buy_market_order(buy_market_order_command)
            case _:
                raise Exception("Invalid Broker")

    def sell_market_order(self, sell_market_order_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.sell_market_order(sell_command=sell_market_order_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.sell_market_order(sell_command=sell_market_order_command)
            case Broker.BACKTEST:
                return self.backtest_obj.sell_market_order(sell_command=sell_market_order_command)
            case Broker.BT_DAY:
                return self.bt_day_obj.sell_market_order(sell_market_order_command)
            case _:
                raise Exception("Invalid Broker")

    def buy_limit_order(self, buy_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.buy_limit_order(buy_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.buy_limit_order(buy_command)
            case Broker.BACKTEST:
                return self.backtest_obj.buy_limit_order(buy_command)
            case Broker.BT_DAY:
                return self.bt_day_obj.buy_limit_order(buy_command)
            case _:
                raise Exception("Invalid Broker")

    def sell_limit_order(self, sell_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.sell_limit_order(sell_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.sell_limit_order(sell_command)
            case Broker.BACKTEST:
                return self.backtest_obj.sell_limit_order(sell_command)
            case Broker.BT_DAY:
                return self.bt_day_obj.sell_limit_order(sell_command)
            case _:
                raise Exception("Invalid Broker")
            
    def stop_market_buy_order(self, buy_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.stop_market_buy_order(buy_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.stop_market_buy_order(buy_command)
            case Broker.BACKTEST:
                return self.backtest_obj.stop_market_buy_order(buy_command)
            case _:
                raise Exception("Invalid Broker")
            
    def stop_market_sell_order(self, sell_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.stop_market_sell_order(sell_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.stop_market_sell_order(sell_command)
            case Broker.BACKTEST:
                return self.backtest_obj.stop_market_sell_order(sell_command)
            case _:
                raise Exception("Invalid Broker")
            
    def stop_limit_buy_order(self, buy_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.stop_limit_buy_order(buy_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.stop_limit_buy_order(buy_command)
            case Broker.BACKTEST:
                return self.backtest_obj.stop_limit_buy_order(buy_command)
            case _:
                raise Exception("Invalid Broker")
            
    def stop_limit_sell_order(self, sell_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.stop_limit_sell_order(sell_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.stop_limit_sell_order(sell_command)
            case Broker.BACKTEST:
                return self.backtest_obj.stop_limit_sell_order(sell_command)
            case _:
                raise Exception("Invalid Broker")
            
    def trailing_stop_market_order(self, trailing_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.trailing_stop_market_order(trailing_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.trailing_stop_market_order(trailing_command)
            case Broker.BACKTEST:
                return self.backtest_obj.trailing_stop_market_order(trailing_command)
            case _:
                raise Exception("Invalid Broker")
            
    def trailing_stop_limit_order(self, trailing_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.trailing_stop_limit_order(trailing_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.trailing_stop_limit_order(trailing_command)
            case Broker.BACKTEST:
                return self.backtest_obj.trailing_stop_limit_order(trailing_command)
            case _:
                raise Exception("Invalid Broker")
            
    def short_open_limit_order(self, short_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.short_open_limit_order(short_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.short_open_limit_order(short_command)
            case Broker.BACKTEST:
                return self.backtest_obj.short_open_limit_order(short_command)
            case _:
                raise Exception("Invalid Broker")

    def short_close_limit_order(self, short_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.short_close_limit_order(short_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.short_close_limit_order(short_command)
            case Broker.BACKTEST:
                return self.backtest_obj.short_close_limit_order(short_command)
            case _:
                raise Exception("Invalid Broker")

    def short_open_market_order(self, short_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.short_open_market_order(short_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.short_open_market_order(short_command)
            case Broker.BACKTEST:
                return self.backtest_obj.short_open_market_order(short_command)
            case _:
                raise Exception("Invalid Broker")

    def short_close_market_order(self, short_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.short_close_market_order(short_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.short_close_market_order(short_command)
            case Broker.BACKTEST:
                return self.backtest_obj.short_close_market_order(short_command)
            case _:
                raise Exception("Invalid Broker")

    def short_open_stop_market_order(self, short_stop_market_order_command:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.short_open_stop_market_order(short_stop_market_order_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.short_open_stop_market_order(short_stop_market_order_command)
            case Broker.BACKTEST:
                return self.backtest_obj.short_open_stop_market_order(short_stop_market_order_command)
            case _:
                raise Exception("Invalid Broker")

    def short_close_stop_market_order(self, short_sell:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.short_close_stop_market_order(short_sell)
            case Broker.MOOMOO:
                return self.moomoo_obj.short_close_stop_market_order(short_sell)
            case Broker.BACKTEST:
                return self.backtest_obj.short_close_stop_market_order(short_sell)
            case _:
                raise Exception("Invalid Broker")

    def short_open_stop_limit_order(self, short_buy:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.short_open_stop_limit_order(short_buy)
            case Broker.MOOMOO:
                return self.moomoo_obj.short_open_stop_limit_order(short_buy)
            case Broker.BACKTEST:
                return self.backtest_obj.short_open_stop_limit_order(short_buy)
            case _:
                raise Exception("Invalid Broker")

    def short_close_stop_limit_order(self, short_sell:OrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.short_close_stop_limit_order(short_sell)
            case Broker.MOOMOO:
                return self.moomoo_obj.short_close_stop_limit_order(short_sell)
            case Broker.BACKTEST:
                return self.backtest_obj.short_close_stop_limit_order(short_sell)
            case _:
                raise Exception("Invalid Broker")
            
    def get_ticker_today_open(self, ticker):
        match self.selected_broker:
            case Broker.BT_DAY:
                return self.bt_day_obj.get_current_day_data(ticker)['Open'].iloc[0]
            case _:
                raise Exception("Not implemented: get_today_close")

    def get_ticker_today_close(self, ticker):
        match self.selected_broker:
            case Broker.BT_DAY:
                return self.bt_day_obj.get_current_day_data(ticker)['Close'].iloc[0]
            case _:
                raise Exception("Not implemented: get_today_close")

    def modify_order(self, modify_command:ModifyOrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.modify_order(modify_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.modify_order(modify_command)
            case Broker.BACKTEST:
                return self.backtest_obj.modify_order(modify_command)
            case _:
                raise Exception("Invalid Broker")

    def cancel_order(self, cancel_command:CancelOrderCommand):
        match (self.selected_broker):
            case Broker.TIGER:
                return self.tiger_obj.cancel_order(cancel_command)
            case Broker.MOOMOO:
                return self.moomoo_obj.cancel_order(cancel_command)
            case Broker.BACKTEST:
                return self.backtest_obj.cancel_order(cancel_command)
            case _:
                raise Exception("Invalid Broker")

    # Do not put default values for tickers / markets
    def setup_callbacks(self, tick_event, order_event, broker:Broker, tickers : Tickers):
        match (broker):
            case Broker.TIGER:
                self.tiger_obj.setup_callbacks(tick_event, order_event, tickers)
            case Broker.MOOMOO:
                self.moomoo_obj.setup_callbacks(tick_event, order_event, tickers)
            case Broker.BACKTEST:
                self.backtest_obj.setup_callbacks(tick_event, order_event, tickers)
            case Broker.BT_DAY:
                return # TODO: Add order change callbacks maybe??
            case _:
                raise Exception("Invalid Broker")

    def stop(self):
        match (self.selected_broker):
            case Broker.TIGER:
                self.tiger_obj.stop()
            case Broker.MOOMOO:
                self.moomoo_obj.stop()
            case Broker.BACKTEST:
                self.backtest_obj.stop()
            case Broker.BT_DAY:
                self.bt_day_obj.stop()
            case _:
                raise Exception("Invalid Broker")

    def print_account_info(self):
        account = self.get_account_information(AccountQuery(currency='USD'))
        positions = self.get_positions()
        print(account)
        print(f"{positions}")

    def get_yfin_data(self, ticker: str, start_date: datetime, end_date: datetime):
        return self.bt_day_obj.get_data(ticker, start_date, end_date)
    
    async def emergency_stop_option(self, offset:float):
        match self.selected_broker:
            case Broker.TIGER:
                self.tiger_obj.emergency_stop_option(offset)
            case Broker.MOOMOO:
                pass
            case Broker.BACKTEST:
                pass
            case Broker.BT_DAY:
                pass
            case _:
                raise Exception("Invalid Broker")
    
    def set_up_discord(self, discord_notify):
        self.notification_on = discord_notify
    
    def discord_notify(self, header:str, message:str, color=15219518, is_error=True):
        import requests

        if self.notification_on == False:
            return

        # String construction
        webhook_url = ""
        content_str = ""
        if (is_error):
            webhook_url = 'https://discord.com/api/webhooks/1210893936747352084/mBS3dgGZl7TKCM8ER63fAIRdnLWyVGhw45ZXdBZgtG2gUtcJcnuVV9dRerOnL6iiAOlR'
            content_str = "Error detected <@134499528660221961> <@224437447059177472>"
        else:
            webhook_url = 'https://discord.com/api/webhooks/1210877934739390545/8HD2n__okWvSMMp81Z5qg36Xsla_JN5ppA_LwVFwBOfPXzTo6yBteGM-9lqcZndhKX4w'
            content_str = "Status Update"

        # The JSON payload you want to send to the webhook
        data = {
            "content": content_str,
            "username": "Irori",  # Optional: Set the username that will display for the bot
            "embeds": [
                {
                    "title": header,
                    "description": message,
                    "color": color  # Optional: Color of the embed in decimal form
                }
            ]
        }

        # Send the POST request with the JSON payload
        response = requests.post(webhook_url, json=data)

        # Check if the request was successful
        if response.status_code == 204:
            #print("Message successfully sent")
            pass
        else:
            print(f"Failed to send message. Response code: {response.status_code}, Response text: {response.text}")
    
    def create_contract(self, strike_price, option_type, close_price, quantity, time, underlying_price, contract_list: list):
        if (quantity == 0):
            return 0
        # Validate the option type
        if option_type not in ['c', 'p']:
            raise ValueError("Invalid option type. Use 'c' for Call or 'p' for Put.")
        
        # Construct the contract object (a dictionary)
        contract = {
            'strike_price': strike_price,
            'option_type': option_type,
            'close_price': close_price,
            'quantity': quantity,
            'time': time
        }
        #print("Quantity: "+str(contract["quantity"]))
        contract_list.append(contract)
        
        # Call to calculate profit/loss for the portfolio based on the contract creation
        return self.calculate_option_profit_loss(contract, underlying_price)

    def calculate_option_profit_loss(self, contract, underlying_price:float):
        """
        This function calculates the premium and updates the working currency.
        If the quantity is negative, it's a sale, and the portfolio receives a credit (premium).
        If the quantity is positive, it's a purchase, and the portfolio is debited.
        """
        premium = round(contract['close_price'] * abs(contract['quantity']) * 100, 2)
        fee = self.calculate_option_fees_ibf(abs(contract['quantity']),contract['close_price'])
        self.backtest_obj.working_currency -= fee

        trade:Trade = Trade()
        trade.ticker = f"OPT {contract['strike_price']} {contract['option_type']}"
        trade.date_time = contract['time']
        trade.price = contract['close_price']
        trade.quantity = abs(contract['quantity'])
        trade.fees = fee
        trade.buy_sell = "BUY" if contract['quantity'] > 0 else "SELL"
        trade.net_returns = "N/A"
        trade.remarks = underlying_price
        self.stats.trades.append(trade)

        if contract['quantity'] > 0:
            # Buying the option, so debit the portfolio
            self.backtest_obj.working_currency -= premium
            #print(f"\nOption bought at {contract['close_price']}, premium paid: -{premium:.2f}")
            #print(f"Strike: {contract['strike_price']}, Type: {contract['option_type']}, closed price: {contract['close_price']}")
        else:
            # Selling the option, so credit the portfolio
            self.backtest_obj.working_currency += premium
            #print(f"\nOption sold at {contract['close_price']}, premium received: +{premium:.2f}")
            #print(f"Strike: {contract['strike_price']}, Type: {contract['option_type']}, closed price: {contract['close_price']}")
        
        return premium

    #call this function every single time a trade is made
    def calculate_option_fees_ibf(self, qty: int,contractprice:float):
        orf = 0.012*qty
        sec = max(0.02,0.0000278*contractprice*100*qty)
        finra = max(0.02,0.00279*qty)
        occ = min(110,0.02*qty*4)

        platform = 0.65*qty*1.09
        slippage = 0
        #slippage = 1.2*qty
        return orf+sec+finra+occ+platform+slippage

    def calculate_option_profit_loss_market_end(self, contracts, market_price):
        """
        This function calculates the profit or loss at market close based on the market price.
        After the calculation, the contract list is emptied.
        """
        #print("\nMarket closed. Calculating profit/loss for the contracts:")
        total_profit = 0
        for contract in contracts:
            strike_price = contract['strike_price']
            quantity = contract['quantity']
            option_type = contract['option_type']
            closed_price = contract['close_price']
            
            #net_debit = round(sell_price_put + sell_price_call - buy_price_put - buy_price_call, 2)
            if option_type == 'c':
                # Call option
                intrinsic_value = max(0, market_price - strike_price)
            elif option_type == 'p':
                # Put option
                intrinsic_value = max(0, strike_price - market_price)

            # Total profit/loss depends on whether it's a buy (positive quantity) or sell (negative quantity)
            profit_loss = round(intrinsic_value * abs(quantity) * 100, 2)

            if quantity > 0:
                # Bought the contract, so profit means positive change in currency, loss means negative
                self.backtest_obj.working_currency += profit_loss
                #print(f"Strike: {strike_price}, Type: {option_type}, closed price: {closed_price}, Market: {market_price:.2f}, Profit: +{profit_loss:.2f}, Quantity: {quantity}")
                total_profit += profit_loss
            else:
                # Sold the contract, so loss means negative change in currency, profit means positive
                self.backtest_obj.working_currency -= profit_loss
                #print(f"Strike: {strike_price}, Type: {option_type}, closed price: {closed_price}, Market: {market_price:.2f}, Profit: -{profit_loss:.2f}, Quantity: {quantity}")
                total_profit -= profit_loss

        # After calculating profit and loss, clear the contract list
        contracts.clear()
        if round(total_profit, 2) != 0.0:
            print(f"\nExcess: {total_profit:.2f}")
            raise ValueError("Total profit/loss not zero.")

        #print(f"Open price: {self.open}\nClose price: {self.close}")