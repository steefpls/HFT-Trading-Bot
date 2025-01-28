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
from dataclasses import field
from enum import Enum
import math

import pandas as pd
from irori.BrokerBase import BrokerBase
import yfinance as yf

from irori.Broker_Backtest import BuyOrder, OwnedShort, OwnedStock, SellOrder, ShortOrder
from irori.common import *
from irori.irori_constants import GST
from irori.stats import DailyStockStat

class YBrokerState(Enum):
    NoState = 0,
    IntradayStart = 1,
    DayStart = 2,
    DayEnd = 3,

class YFinanceBroker(BrokerBase):
    def __init__(self):
        super().__init__()

        self.mediator = None
        self.state = YBrokerState.NoState
        self.tickers: list[str] = [] # Used for initialization
        self.start_date = ''
        self.end_date = ''
        self.current_date: datetime = None
        self.initialized = False
        self.day_index = -1
        self.max_day_index = 0
        self.working_currency = 100000

        self.buy_order_list: list[BuyOrder] = []
        self.sell_order_list: list[SellOrder] = []
        self.short_open_list: list[ShortOrder] = []
        self.short_close_list: list[SellOrder] = []

        self.shares_owned_list: list[OwnedStock] = []
        self.shorts_owned_list: list[OwnedShort] = []

        self.order_id_tracker = 0

        self.current_prices_dict: dict[str, float] = {} 
        self.yfinance_df_dict: dict[str, pd.DataFrame] | None = {} 
        
        # Used for shorting
        self.toggle_margin = True
        self.money_owed_to_broker = 0.0

        self.toggle_fees = True
        self.brokerForFees: Broker = Broker.TIGER

    
    def init(self, tickers: list[str]):
        self.tickers = tickers

    def setup_broker(self,brokerForFees:Broker):
        self.brokerForFees = brokerForFees

    def start(self, mediator):
        """
        Called only once
        """
        if not mediator:
            raise Exception("Invalid mediator")
        
        self.mediator = mediator
        
        self.initialized = True

    def get_data(self, ticker: str, start_date: datetime, end_date: datetime):
        stock_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if stock_data.empty:
            raise ValueError("No data fetched for the given ticker and date range.")
        return stock_data

    def get_current_day_data(self, ticker: str):
        return self.yfinance_df_dict[ticker]

    def set_ticker_day_data(self, ticker: str, ticker_day_data):
        self.yfinance_df_dict[ticker] = ticker_day_data
        self.current_prices_dict[ticker] = self.get_current_day_data(ticker)['Open'].iloc[0]

    # day_data, To receive from backtester (Open, Close, High, Low, etc)
    def new_day(self, current_date):
        """
        Returns False if finished
        """
        self.state: YBrokerState = YBrokerState.IntradayStart
        self.day_index += 1

        self.current_date = current_date

        for ticker in self.yfinance_df_dict:
            self.current_prices_dict[ticker] = self.get_current_day_data(ticker)['Open'].iloc[0]

    def process_intraday_start(self):
        self.state = YBrokerState.IntradayStart

        self.process_orders()

        self.state = YBrokerState.DayStart

    def process_day_start(self):
        self.state = YBrokerState.DayStart
        for ticker in self.yfinance_df_dict:
            self.current_prices_dict[ticker] = self.get_current_day_data(ticker)['Open'].iloc[0]
        self.process_orders()

        self.state = YBrokerState.DayEnd

        for ticker in self.yfinance_df_dict:
            self.current_prices_dict[ticker] = self.get_current_day_data(ticker)['Close'].iloc[0]

    def process_day_end(self):
        """
        Day: Unfilled orders will automatically be cancelled at the end of the trading session.
        """
        self.state = YBrokerState.DayEnd

        for ticker in self.yfinance_df_dict:
            self.current_prices_dict[ticker] = self.get_current_day_data(ticker)['Close'].iloc[0]

        self.process_orders()
        self.cancel_expired_orders()

        self.state = YBrokerState.NoState

    def process_orders(self):
        self.process_buy_orders()
        self.process_sell_orders()

    def process_buy_orders(self):
        for i, x in reversed(list(enumerate(self.buy_order_list))):
            current_price = self.get_ticker_current_price(x.ticker)
            price = current_price

            # See if we can buy in between day_start and day_end
            # This will happen when placing a limit order at day start which price is lower than opening price (not filling)
            if x.order_type == OrderType.LIMIT and self.state == YBrokerState.DayEnd and self.get_current_day_data(x.ticker)['Low'].iloc[0] <= x.limit_price:
                price = x.limit_price
            elif current_price > x.limit_price:
                continue
            
            fees_incurred = self.calculate_fees(current_price, x.num_shares,True)

            # Buy if price is lower
            total_buy_cost = price * x.num_shares + fees_incurred

            difference = total_buy_cost - self.working_currency
            if difference > 0:
                if self.toggle_margin:
                    self.working_currency = 0
                    self.borrow_money_from_broker(difference)
                else:
                    return
            else:
                self.working_currency -= total_buy_cost

            self.get_owned_stock(x.ticker).add_stock(price, x.num_shares)
            self.buy_order_list.pop(i)
            if self.mediator:
                self.mediator.resolve_purchase(x.ticker, self.current_date, x.num_shares, price, fees_incurred, OrderAction.BUY)

    def process_sell_orders(self):
        for i, x in reversed(list(enumerate(self.sell_order_list))):
            current_price = self.get_ticker_current_price(x.ticker)
            price = current_price
            if x.order_type == OrderType.LIMIT and self.state == YBrokerState.DayEnd and self.get_current_day_data(x.ticker)['High'].iloc[0] >= x.limit_price:
                price = x.limit_price
            elif current_price < x.limit_price:
                continue
            if x.num_shares > self.get_owned_stock(x.ticker).num_shares:
                continue

            sell_fee = self.calculate_fees(current_price, x.num_shares,False)
            
            order_cost = price * x.num_shares
            self.working_currency += order_cost - sell_fee
            self.payback_money_to_broker()
            self.get_owned_stock(x.ticker).remove_stock(price, x.num_shares)
            self.sell_order_list.pop(i)
            if self.mediator:
                self.mediator.resolve_purchase(x.ticker, self.current_date, x.num_shares, price, sell_fee, OrderAction.SELL)

    def buy_market_order(self, buy_market_order_command: OrderCommand):
        return self.buy_shares(buy_market_order_command, OrderType.MARKET)

    def sell_market_order(self, sell_market_order_command: OrderCommand):
        return self.sell_shares(sell_market_order_command, OrderType.MARKET)

    def buy_limit_order(self, buy_limit_order_command: OrderCommand):
        """
        If buy higher than current price, it will buy as if a market order has been placed
        That means only orders placed with price lower than current price will 'stay' throughout the day
        """
        return self.buy_shares(buy_limit_order_command, OrderType.LIMIT)

    def sell_limit_order(self, sell_limit_order_command: OrderCommand):
        return self.sell_shares(sell_limit_order_command, OrderType.LIMIT)

    def buy_shares(self, buy_command: OrderCommand, order_type: OrderType):
        current_price = self.get_ticker_current_price(buy_command.ticker)
        price = current_price
        

        if buy_command.quantity <= 0:
            return IroriOrderResponse(-1, "Quantity cannot be 0", '', IroriOrderStatusCode.ERROR)
        
        cost = price * buy_command.quantity
        if not self.toggle_margin and cost > self.working_currency:
            return IroriOrderResponse(-1, "Not enough currency to buy", '', IroriOrderStatusCode.ERROR)

        if order_type == OrderType.MARKET:
            price = current_price
        elif order_type != OrderType.MARKET:
            price = buy_command.price

        if price <= 0:
            return IroriOrderResponse(-1, "Price cannot be 0", '', IroriOrderStatusCode.ERROR)
        
        self.order_id_tracker += 1

        order = BuyOrder(block_id=self.order_id_tracker, 
                         ticker=buy_command.ticker, 
                         num_shares=buy_command.quantity, 
                         order_type=order_type, 
                         stop_price=buy_command.aux_price,
                         limit_price=price,
                         remarks=self.state,
                         time_in_force=buy_command.time_in_force)
        
        self.buy_order_list.append(order)

        return IroriOrderResponse(order.block_id, '', f'Successfully bought shares of qty {buy_command.quantity} at price {price}')
    
    def sell_shares(self, sell_command: OrderCommand, order_type: OrderType):
        if sell_command.quantity > self.total_shares_sellable(sell_command.ticker):
            return IroriOrderResponse(-1, "Trying to sell more shares than sellable (check held or current pending sell orders)", '', IroriOrderStatusCode.ERROR)
        
        if sell_command.quantity <= 0:
            return IroriOrderResponse(-1, "Sell quantity cannot be less than 0", '', IroriOrderStatusCode.ERROR)
        
        price = 0.0
        if order_type == OrderType.LIMIT:
            price = sell_command.price
        else:
            price = self.get_ticker_current_price(sell_command.ticker)

        if price <= 0.0:
            return IroriOrderResponse(-1, "Sell price cannot be 0", '', IroriOrderStatusCode.ERROR)

        self.order_id_tracker += 1

        order = SellOrder(num_shares=sell_command.quantity,
                            block_id=self.order_id_tracker,
                            ticker=sell_command.ticker,
                                order_type=order_type,
                                remarks=self.state,
                                lim_price=price,
                                time_in_force=sell_command.time_in_force)
        self.sell_order_list.append(order)

        return IroriOrderResponse(order.block_id, '', f'Successfully sold shares of qty {sell_command.quantity} at price {price}')

    # SHORTS

    def short_open_limit_order(self, short_buy: OrderCommand)->int:
        return self.short_open_order(self.short_open_list, short_buy, OrderType.LIMIT)
    
    def short_open_market_order(self, short_buy: OrderCommand)->int:
        return self.short_open_order(self.short_open_list, short_buy, OrderType.MARKET)

    def short_close_limit_order(self, short_sell: OrderCommand)->int:
        return self.short_close_order(self.short_close_list, short_sell, OrderType.LIMIT)
    
    def short_close_market_order(self, short_sell: OrderCommand)->int:
        return self.short_close_order(self.short_close_list, short_sell, OrderType.MARKET)

    def short_open_order(self, short_order_list:list, short_command: OrderCommand, type:OrderType)->int:
        """
        Short order borrowing stocks from the broker and selling it immediately.
        """
        success = True
        price = 0
        stop_price = 0
        order_type = OrderType.NONE

        if type is OrderType.LIMIT:
            price = short_command.price
            order_type = OrderType.LIMIT
        elif type is OrderType.MARKET:
            price = self.get_ticker_current_price(short_command.ticker)
            order_type = OrderType.MARKET
        elif type is OrderType.STOP: # Stop Market
            stop_price = short_command.aux_price
            order_type = OrderType.STOP
        elif type is OrderType.STOP_LMT:
            price = short_command.price
            stop_price = short_command.aux_price
            order_type = OrderType.STOP


        quantity = short_command.quantity

        # # If no leverage and not enough currency to buy, dont place buy order
        # if (not self.toggle_margin and self.working_currency < price * quantity):
        #     return IroriOrderResponse(-1, '', '', IroriOrderStatusCode.ERROR)
        #     #print("Insufficient Funds for Short Order")
        #     #success = False
        
        if quantity <= 0:
            return IroriOrderResponse(-1, "Quantity cannot be less than 0", '', IroriOrderStatusCode.ERROR)
            
        self.order_id_tracker+=1  

        order = ShortOrder(block_id = self.order_id_tracker, 
                           lim_price=self.get_ticker_current_price(short_command.ticker),
                           ticker=short_command.ticker, 
                           num_shares=short_command.quantity,
                           order_type=order_type)
        
        if success:
            short_order_list.append(order)
        orderChangeData = OrderChangeData()
        orderChangeData.ticker = order.ticker
        orderChangeData.orderID = self.order_id_tracker
        orderChangeData.order_type = order_type
        orderChangeData.action = OrderAction.SHORT_OPEN
        orderChangeData.limit_price = price
        orderChangeData.stop_price = stop_price
        orderChangeData.total_quantity = short_command.quantity
        if success:
            orderChangeData.order_status = OrderStatus.NEW
        else:
            orderChangeData.order_status = OrderStatus.FAILED
        orderChangeData.is_short = True
        
        # print(f"Placing market short order for {short_command.quantity} shares.")
        #self.trigger_order_callback(orderChangeData)

        return IroriOrderResponse(order.block_id, '', f'Successfully open shorts of qty {short_command.quantity} at price {price}')

    def short_close_order(self, short_order_list:list, short_command: OrderCommand, type:OrderType)->int:
        success = True
        orderChangeData = OrderChangeData()
        
        if(short_command.quantity > self.total_shorts_sellable(short_command.ticker)):
            return IroriOrderResponse(-1, "Not enough shares to close (check held shorts or short orders)", '', IroriOrderStatusCode.ERROR)
    
        self.order_id_tracker+=1

        order = SellOrder(num_shares = short_command.quantity,\
                            block_id = self.order_id_tracker,\
                            ticker = short_command.ticker,\
                                order_type=type)
        
        if type is OrderType.LIMIT:
            # order.limit_price = sell_command.price
            order.limit_price = short_command.price
            orderChangeData.order_type = OrderType.LIMIT
        elif type is OrderType.MARKET:
            order.limit_price = self.get_ticker_current_price(short_command.ticker)
            orderChangeData.order_type = OrderType.MARKET
        elif type is OrderType.STOP: # Stop Market
            order.stop_price = short_command.aux_price
            orderChangeData.order_type = OrderType.STOP
        elif type is OrderType.STOP_LMT:
            order.limit_price = short_command.price
            order.stop_price = short_command.aux_price
            orderChangeData.order_type = OrderType.STOP_LMT
        
        if success:
            short_order_list.append(order)
        orderChangeData.ticker = order.ticker
        orderChangeData.orderID = self.order_id_tracker
        orderChangeData.action = OrderAction.SHORT_CLOSE
        orderChangeData.limit_price = order.limit_price
        orderChangeData.total_quantity = short_command.quantity
        if success:
            orderChangeData.order_status = OrderStatus.NEW
        else:
            orderChangeData.order_status = OrderStatus.FAILED
        orderChangeData.is_short = True

        # print(f"Placing market sell order for {short_command.quantity} shares.")
        #self.trigger_order_callback(orderChangeData)
        return IroriOrderResponse(order.block_id, '', f'Successfully open shorts of qty {short_command.quantity} at price {order.limit_price}')

    # END SHORTS

    def get_owned_stock(self, ticker):
        owned_stock = next((x for x in self.shares_owned_list if x.ticker == ticker), None)

        if owned_stock is None:
            self.order_id_tracker += 1
            owned_stock = OwnedStock(ticker=ticker, block_id=self.order_id_tracker)
            self.shares_owned_list.append(owned_stock)

        return owned_stock

    def get_total_sell_orders_num_shares(self, ticker: str):
        return next((x.num_shares for x in self.sell_order_list if x.ticker == ticker), 0)

    def total_shares_sellable(self, ticker):
        shares_held = self.get_owned_stock(ticker).num_shares
        sell_orders_qty = self.get_total_sell_orders_num_shares(ticker)
        return shares_held - sell_orders_qty

    # Shorts
    def get_owned_short(self, ticker):
        owned_short = next((x for x in self.shorts_owned_list if x.ticker == ticker), None)

        if owned_stock is None:
            self.order_id_tracker += 1
            owned_stock = OwnedShort(ticker=ticker, block_id=self.order_id_tracker)
            self.shorts_owned_list.append(owned_stock)

        return owned_short

    def get_total_sell_short_orders_num_shares(self, ticker)->int:
        sell_short_orders_qty = 0
        for sell_shorts in self.short_close_list:
            if sell_shorts.ticker == ticker:
                sell_short_orders_qty+=sell_shorts.num_shares
        return sell_short_orders_qty

    def total_shorts_sellable(self, ticker)->int:
        shorts_held = self.get_owned_short(ticker).num_shares
        short_orders_qty = self.get_total_sell_short_orders_num_shares(ticker)
        shorts_sellable = shorts_held-short_orders_qty
        return shorts_sellable
    
    # end shorts

    def cancel_expired_orders(self):
        for i, x in reversed(list(enumerate(self.buy_order_list))):
            if x.time_in_force is TimeInForce.DAY:
                self.buy_order_list.pop(i)
        
        for i, x in reversed(list(enumerate(self.sell_order_list))):
            if x.time_in_force is TimeInForce.DAY:
                self.sell_order_list.pop(i)

    def get_order(self, id):
        order = next((x for x in self.buy_order_list if x.block_id == id), None)
        if order is not None:
            return order
        order = next((x for x in self.sell_order_list if x.block_id == id), None)
        if order is not None:
            return order
        order = next((x for x in self.short_open_list if x.block_id == id), None)
        if order is not None:
            return order
        order = next((x for x in self.short_close_list if x.block_id == id), None)
        if order is not None:
            return order

        return order

    def cancel_order(self, order_id: int):
        order = next((x for x in self.buy_order_list if x.block_id == order_id), None)
        
        if order is not None:
            self.buy_order_list.remove(order)
            return True
        
        order = next((x for x in self.sell_order_list if x.block_id == order_id), None)

        if order is not None:
            self.sell_order_list.remove(order)
            return True
        
        order = next((x for x in self.sh if x.block_id == order_id), None)

        if order is not None:
            self.short_open_list.remove(order)
            return True
        
        if order is not None:
            self.short_close_list.remove(order)
            return True
        
        return False
    
    def get_yfinance_df(self, ticker, start_date, end_date):
        data = yf.download(ticker, start=start_date, end=end_date)

        # Print the dataframe
        # print(data)
        return data
    
    def get_ticker_current_price(self, ticker: str):
        return self.current_prices_dict[ticker]
    

    def calculate_fees(self, stock_price:float, num_shares:float, is_buy:bool):
        return 0
    
    def get_account_details(self, acc_detail_obj: AccountQuery):
        response: AccountResponse = AccountResponse()
        response.cash_balance = self.working_currency

        current_positions_value = 0.0
        positions_entered_value = 0.0

        for shares in self.shares_owned_list:
            current_positions_value+=self.get_ticker_current_price(shares.ticker) * shares.num_shares
            positions_entered_value+=shares.avg_price * shares.num_shares

        response.unrealized_pl = current_positions_value-positions_entered_value
        response.assets_value = self.working_currency + current_positions_value
        response.gross_position_value = response.assets_value - self.money_owed_to_broker

        return response
    
    def query_stock_briefs(self, stock_briefs_query: StockBriefsQuery):
        response: StockBriefsResponse = StockBriefsResponse()

        for ticker in self.current_prices_dict:
            if ticker in stock_briefs_query.tickerList:
                response.add_price(ticker, self.current_prices_dict[ticker])

        return response
    
    def get_positions(self):
        """
        Returns all positions held by default
        """
        response = PositionsResponse()
        response.stockList = []

        for shares in self.shares_owned_list:
            if math.isclose(shares.num_shares, 0):
                continue
            stock = Stock()
            stock.ticker = shares.ticker
            stock.quantity = shares.num_shares
            stock.average_cost = shares.avg_price
            stock.market_price = self.get_ticker_current_price(shares.ticker)
            response.stockList.append(stock)

        # for shorts in self.shorts_owned_list:
        #     short = Stock()
        #     short.ticker = shorts.ticker
        #     short.quantity = shorts.num_shares
        #     short.average_cost = shorts.price/shorts.num_shares
        #     short.market_price = self.get_current_price(shorts.ticker) # is there a function to get the current price of a stock by looking up the ticker? this needs trigger_tick_callback to return multiple tickers data
        #     response.stockList.append(short)

        return response
    

    def borrow_money_from_broker(self, amount):
        self.money_owed_to_broker += amount

    def payback_money_to_broker(self):
        """
        Payback whatever we can pay to the broker
        """
        if self.working_currency >= self.money_owed_to_broker:
            self.working_currency -= self.money_owed_to_broker
            self.money_owed_to_broker = 0
        else:
            self.money_owed_to_broker -= self.working_currency
            self.working_currency = 0

    def calculate_fees(self, stock_price:float, num_shares:float, is_buy:bool)->float:
        if not self.toggle_fees:
            return 0
        if self.brokerForFees is Broker.MOOMOO:
            return self.calculate_fees_moomoo(stock_price, num_shares, is_buy)
        elif self.brokerForFees is Broker.TIGER:
            return self.calculate_fees_tiger(stock_price, num_shares, is_buy)
        
    def calculate_fees_moomoo(self, stock_price:float, num_shares:float, is_buy:bool)->float:
        trx_amt = stock_price*num_shares
        commission = 0
        platform_fee = 0.99

        #Fractional shares = if trade size<1 share: commission = 0, platform fees = 0.99% * trx_amt, if platform fees>0.99:platform fees =0.99
        #else if trade size>=1 share: commission = standard US stock trading fees, platform = standard US trading fees

        settlement_fee = 0.003 * num_shares
        if settlement_fee>0.01*trx_amt:
            settlement_fee = 0.01* trx_amt

        sec_fee = 0
        taf_fee = 0

        if not is_buy:

            sec_fee = 0.000008 * trx_amt
            if sec_fee < 0.01:
                sec_fee = 0.01

            taf_fee = 0.000166*num_shares
            if taf_fee<0.01:
                taf_fee=0.01
            elif taf_fee>8.3:
                taf_fee = 8.3
        
        total_fee_value = (commission + platform_fee + settlement_fee + sec_fee + taf_fee)*(1+GST)

        return total_fee_value  

    def calculate_fees_tiger(self, stock_price:float, num_shares:float, is_buy:bool)->float:
        trade_value = stock_price * num_shares
        total_fee_value = 0

        # Commission calculations
        temp_commission = 0.005*num_shares
        if(temp_commission<0.99):
            temp_commission = 0.99
        elif(temp_commission>0.005*trade_value):
            temp_commission = 0.005*trade_value
        #print(f"Commission: {tempCommission}")
        total_fee_value = total_fee_value+temp_commission
    
        # Platform Fee Calculations
        platform_fee = 0.005*num_shares
        if(platform_fee<1):
            platform_fee = 1
        elif(platform_fee>0.005*trade_value):
            platform_fee = 0.005*trade_value
        #print(f"platformFee: {platformFee}")
        total_fee_value = total_fee_value+platform_fee

        # SEC Membership Fee Calculations (only if isBuy is false)
        if (not is_buy):
            SEC_fee = 0.000008*trade_value
            if (SEC_fee<0.01):
                SEC_fee = 0.01
            #print(f"SECFee: {SECFee}")
            total_fee_value = total_fee_value + SEC_fee

        # Settlement Fee Calculations
        settlement_fee = 0.003*num_shares
        if (settlement_fee> 0.07*trade_value):
            settlement_fee = 0.07*trade_value
        #print(f"settlementFee: {settlementFee}")
        total_fee_value = total_fee_value + settlement_fee

        # Trading Activity Fee (only if isBuy is false)
        if (not is_buy):
            TA_fee = 0.000166*num_shares
            if (TA_fee<0.01):
                TA_fee = 0.01
            elif(TA_fee>8.30):
                TA_fee = 8.30
            #print(f"TAFee: {TAFee}")
            total_fee_value = total_fee_value+TA_fee

        #print(f"GST: {GST*totalFeeValue}")
        total_fee_value = total_fee_value*(1+GST)

        return total_fee_value
