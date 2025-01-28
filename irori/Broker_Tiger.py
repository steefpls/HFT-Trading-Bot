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
from irori.BrokerBase import BrokerBase
from irori.common import *
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
from tigeropen.common.consts import Market, SecurityType, Currency, Language
from tigeropen.common.util.contract_utils import stock_contract
from tigeropen.push.pb.OrderStatusData_pb2 import OrderStatusData
from tigeropen.push.pb.trade_tick import TradeTick
from tigeropen.push.push_client import PushClient
from tigeropen.tiger_open_config import get_client_config
from tigeropen.common.exceptions import ApiException
from tigeropen.trade.domain.order import Order as TigerOrder
from tigeropen.trade.domain.position import Position as TigerPosition
from tigeropen.push.pb.QuoteBasicData_pb2 import QuoteBasicData
from tigeropen.common.util.order_utils import (
    market_order,  # Market Order
    limit_order,  # Limit Order
    stop_order,  # Stop Order
    stop_limit_order,  # Stop Limit Order
    trail_order,  # Trailing Stop Order
    order_leg,
) 
from jproperties import Properties
from irori.common import *
import irori.irori_constants as irori_constants
from irori import common as irori_common


class TigerBroker(BrokerBase):

    # config stuff
    client_config = None
    quote_client = None
    trade_client = None
    push_client = None
    tickerList = None
    mediator = None
    paperaccount = True

    def __init__(self):
        super().__init__()

    def authenticate(self):
        jPropertyConfigs = Properties()
        tigerAccPropertiesFile = irori_constants.BROKER_AUTH_PROPERTIES_FILE
        with open(tigerAccPropertiesFile, "rb") as config_file:
            jPropertyConfigs.load(config_file)

        self.client_config = TigerOpenClientConfig(sandbox_debug=False)
        self.client_config.private_key = jPropertyConfigs.get(irori_constants.TIGER_PRIVATE_KEY_PROPERTY).data
        self.client_config.tiger_id = jPropertyConfigs.get(irori_constants.TIGER_ID_PROPERTY).data
        self.client_config.account = jPropertyConfigs.get(irori_constants.TIGER_ACCOUNT_PROPERTY).data
        self.client_config.language = Language.en_US 
        protocol, host, port = self.client_config.socket_host_port

        if len(self.client_config.account) > 8:
            print("trading on paper account")
        else:
            print("trading using prime account")
            self.paperaccount = False
        
        self.trade_client = TradeClient(self.client_config)
        self.quote_client = QuoteClient(self.client_config)
        self.push_client = PushClient(host, port, use_ssl=(protocol == 'ssl'), use_protobuf=True)

    def setup_callbacks(self, tick_event_callable:callable, order_event_callable:callable, tickers: Tickers):
        
        self.tick_event = tick_event_callable
        self.order_event = order_event_callable

        self.push_client.tick_changed = self.trigger_tick_callback
        self.push_client.order_changed = self.trigger_order_callback
        self.push_client.connect_callback = self.on_push_connected_callback
        self.push_client.disconnect_callback = self.on_push_disconnected_callback
        self.push_client.error_callback = self.on_push_disconnected_callback
        self.push_client.quote_changed = self.trigger_quote_callback
        self.tickerList = tickers.tickerList

    def start(self, mediator):
        self.mediator = mediator
        self.push_client.connect(self.client_config.tiger_id, self.client_config.private_key)
        self.push_client.query_subscribed_callback = self.query_subscribed_callback
        self.push_client.query_subscribed_quote()

    def query_subscribed_callback(self, data):
        import json
        parsed_data = json.loads(data)

        # Extract the lists of subscribed symbols for trade ticks and ask bids
        trade_tick_list = parsed_data.get('subscribedTradeTickSymbols', [])
        quote_list = parsed_data.get('subscribedSymbols', [])

        # Unsubscribe from the respective tickers and quotes
        self.push_client.unsubscribe_tick(trade_tick_list)
        self.push_client.unsubscribe_quote(quote_list)

        # Subscribe to the tickers
        self.push_client.subscribe_tick(self.tickerList)
        self.push_client.subscribe_quote(self.tickerList)

    def trigger_tick_callback(self, frame: TradeTick):
        if self.tick_event is not None:
            tickData = TickChangeData(ticker=str(frame.symbol), time=datetime.now(timezone.utc), price=frame.ticks[-1].price)
            self.tick_event(tickData)

    def trigger_quote_callback(self, frame: QuoteBasicData):
        if self.tick_event is not None:
            tickData = TickChangeData(ticker=str(frame.symbol), time=datetime.now(timezone.utc), price=frame.latestPrice)
            self.tick_event(tickData)

    def trigger_order_callback(self, frame: OrderStatusData):
        if self.order_event is not None:
            orderChangeData = OrderChangeData()
            orderChangeData.orderID = str(frame.id)
            # orderChangeData.status = frame.status
            status = frame.status
            print(str(frame))
            match status:
                case 'NEW':
                    orderChangeData.order_status = irori_common.OrderStatus.NEW
                case 'FILLED':
                    orderChangeData.order_status = irori_common.OrderStatus.FILLED
                case 'PARTIALLY_FILLED':
                    orderChangeData.order_status = irori_common.OrderStatus.PARTIALLY_FILLED
                case 'EXPIRED':
                    orderChangeData.order_status = irori_common.OrderStatus.FAILED
                case 'PENDING_CANCEL':
                    orderChangeData.order_status = irori_common.OrderStatus.CANCELLED
                case 'CANCELLED': 
                    orderChangeData.order_status = irori_common.OrderStatus.CANCELLED
                case 'REJECTED':
                    orderChangeData.order_status = irori_common.OrderStatus.FAILED
                case 'HELD':
                    orderChangeData.order_status = irori_common.OrderStatus.OTHERS
            
            orderChangeData.filled_quantity = frame.filledQuantity
            orderChangeData.ticker = str(frame.symbol)
            orderChangeData.commissionAndFee = frame.commissionAndFee
            orderChangeData.action = frame.action
            orderChangeData.avg_fill_price = frame.avgFillPrice
            orderChangeData.limit_price = frame.limitPrice
            orderChangeData.stop_price = frame.stopPrice
            orderChangeData.total_quantity = frame.totalQuantity
            orderChangeData.timestamp = frame.timestamp
            orderChangeData.liquidation = frame.liquidation
            ordertype = frame.orderType
            match ordertype:
                case 'MKT':
                    orderChangeData.order_type = irori_common.OrderType.MARKET
                case 'LMT':
                    orderChangeData.order_type = irori_common.OrderType.LIMIT
                case 'STP':
                    orderChangeData.order_type = irori_common.OrderType.STOP
                case 'STP_LMT':
                    orderChangeData.order_type = irori_common.OrderType.STOP_LMT
                case 'TRAIL':
                    orderChangeData.order_type = irori_common.OrderType.TRAIL

            self.order_event(orderChangeData)
            if (orderChangeData.order_status == irori_common.OrderStatus.FILLED and self.mediator):
                self.mediator.resolve_purchase(orderChangeData.ticker, datetime.now(timezone.utc),orderChangeData.filled_quantity, orderChangeData.avg_fill_price, orderChangeData.commissionAndFee, orderChangeData.action)

    def on_push_connected_callback(self, frame):
        print("Tiger push client connected")
    
    def on_push_disconnected_callback(self):
        print("Tiger push client disconnected")
        #self.mediator.discord_notify("Error", "Tiger push client disconnected")
        raise_error()
        raise TypeError("Tiger push client disconnected")

    def get_account_details(self, acc_detail_obj : AccountQuery):
        response = AccountResponse()
    # def get_account_details(self):
        # asset_details = self.trade_client.get_prime_assets(base_currency='USD').segments['S']
        response.cash_balance = self.trade_client.get_prime_assets(base_currency=acc_detail_obj.currency).segments['S'].cash_balance
        response.gross_position_value = self.trade_client.get_prime_assets(base_currency=acc_detail_obj.currency).segments['S'].gross_position_value
        response.unrealized_pl = self.trade_client.get_prime_assets(base_currency=acc_detail_obj.currency).segments['S'].unrealized_pl
        response.realized_pl = self.trade_client.get_prime_assets(base_currency=acc_detail_obj.currency).segments['S'].realized_pl
        response.available_cash_for_trading = self.trade_client.get_prime_assets(base_currency=acc_detail_obj.currency).segments['S'].cash_available_for_trade
        response.available_cash_for_withdrawal = self.trade_client.get_prime_assets(base_currency=acc_detail_obj.currency).segments['S'].cash_available_for_withdrawal
        response.buying_power = self.trade_client.get_prime_assets(base_currency=acc_detail_obj.currency).segments['S'].buying_power
        return response

    # def get_positions(self):
    def get_positions(self):
        # cash_balance = self.trade_client.get_prime_assets(base_currency='USD').segments['S'].cash_balance
        # print(f"Account cash balance: {cash_balance}")
        # logger.info(f"Account cash balance: {cash_balance}")

        positions = self.trade_client.get_positions(sec_type=SecurityType.STK, currency=Currency.ALL, market=Market.ALL)

        positions_response = PositionsResponse()

        for i in range(0, len(positions)):
            # prints
            p = positions[i]
            # print('--------------------------------------')
            # print(f'S/N #{i}')
            # print(f'Contract: {p.contract.symbol}')  # contract， such as AAPL，CL2303
            # print(f'Average Cost: {p.average_cost}')  # position average cost
            # print(f'Qty: {p.quantity}')  # position quantity
            # #print(f'Contract Type: {p.contract.sec_type}')  # contract type， such as STK， FUT
            # #print(f'{p.contract.multiplier}')  # contract multiplier
            # print('--------------------------------------')
            stock = Stock()
            stock.ticker = p.contract.symbol
            stock.quantity = p.quantity
            stock.average_cost = p.average_cost
            stock.market_price = p.market_price
            positions_response.stockList.append(stock)

        return positions_response
    
    def modify_order(self, modify_order_command: ModifyOrderCommand):
        order_id = modify_order_command.orderID
        order = self.trade_client.get_order(id=order_id)

        if order == None:
            print(f"Could not find order {order_id}. Skipping modifying order...")
            return False

        successfully_modified = self.trade_client.modify_order(order=order, limit_price=round(modify_order_command.newPrice, 2), quantity=modify_order_command.newQuantity)
        if (successfully_modified):
            print(f'Successfully modified order {order_id}')
            return True
        else:
            print(f'Failed to modify order {order_id}')
            return False
        
    # ----------------------------- ORDER FUNCTIONS -------------------------------
    def buy_limit_order(self, buy_command : OrderCommand):
        result_order_id = self.place_limit_order(buy_command.ticker, 'BUY', buy_command.quantity, buy_command.price)
        #result_order_id = limit_order_with_legs_buy(trade_client, account, self.ticker, quantity, price, self.stop_loss_price)

        return IroriOrderResponse(order_id=result_order_id)

    def sell_limit_order(self, sell_command : OrderCommand):
        result_order_id = self.place_limit_order(sell_command.ticker, 'SELL', sell_command.quantity, sell_command.price)

        return IroriOrderResponse(order_id=result_order_id)
    
    def stop_market_buy_order(self, stop_loss : OrderCommand):
        contract = stock_contract(symbol=str(stop_loss.ticker), currency=str(stop_loss.market))
        order = stop_order(account=self.client_config.account, contract=contract, action='BUY', aux_price=stop_loss.aux_price, quantity=stop_loss.quantity)
        print(order)
        oid = self.trade_client. place_order(order)
        print(oid)
        return IroriOrderResponse(order_id=oid)
    
    def stop_market_sell_order(self, stop_loss : OrderCommand):
        contract = stock_contract(symbol=str(stop_loss.ticker), currency=str(stop_loss.market))
        order = stop_order(account=self.client_config.account, contract=contract, action='SELL', aux_price=stop_loss.aux_price, quantity=stop_loss.quantity)
        oid = self.trade_client. place_order(order)
        return IroriOrderResponse(order_id=oid)
    
    def stop_limit_buy_order(self, stop_loss : irori_common.OrderCommand):
        # generate stock contracts
        contract = stock_contract(symbol=str(stop_loss.ticker), currency=str(stop_loss.market))
        # generate order object
        order = stop_limit_order(account=self.client_config.account, contract=contract, action='BUY', limit_price=round(stop_loss.price,2), aux_price=round(stop_loss.aux_price,2), quantity=stop_loss.quantity)
        if (self.paperaccount != True):
            order.time_in_force = "GTC"
        print("Order details:", order)
        # order
        oid = self.trade_client.place_order(order)
        return IroriOrderResponse(order_id=oid)
    
    def stop_limit_sell_order(self, stop_loss : irori_common.OrderCommand):
        # generate stock contracts
        contract = stock_contract(symbol=str(stop_loss.ticker), currency=str(stop_loss.market))
        # generate order object
        order = stop_limit_order(account=self.client_config.account, contract=contract, action='SELL', limit_price=round(stop_loss.price,2), aux_price=round(stop_loss.aux_price,2), quantity=stop_loss.quantity)
        if (self.paperaccount != True):
            order.time_in_force = "GTC"
        # order
        oid = self.trade_client.place_order(order)
        return IroriOrderResponse(order_id=oid)
    
    def trailing_stop_buy_order(self, trailing_order : irori_common.OrderCommand):
        # generate stock contracts
        contract = stock_contract(symbol=str(trailing_order.ticker), currency=str(trailing_order.market))
        if trailing_order.trail_type == TrailType.PERCENT:
            # generate order object
            order = trail_order(account=self.client_config.account, contract=contract, action='BUY', quantity=trailing_order.quantity, trailing_percent=round(trailing_order.trail_price,2))
        elif trailing_order.trail_type == TrailType.VALUE:
            order = trail_order(account=self.client_config.account, contract=contract, action='BUY', quantity=trailing_order.quantity, aux_price=round(trailing_order.trail_price,2))

        if (self.paperaccount != True):
            order.time_in_force = "GTC"
        # order
        oid = self.trade_client.place_order(order)
        return IroriOrderResponse(order_id=oid)
    
    def trailing_stop_sell_order(self, trailing_order : irori_common.OrderCommand):
        # generate stock contracts
        contract = stock_contract(symbol=str(trailing_order.ticker), currency=str(trailing_order.market))
        if trailing_order.trail_type == TrailType.PERCENT:
            # generate order object
            order = trail_order(account=self.client_config.account, contract=contract, action='SELL', quantity=trailing_order.quantity, trailing_percent=round(trailing_order.trail_price,2))
        elif trailing_order.trail_type == TrailType.VALUE:
            order = trail_order(account=self.client_config.account, contract=contract, action='SELL', quantity=trailing_order.quantity, aux_price=round(trailing_order.trail_price,2))

        if (self.paperaccount != True):
            order.time_in_force = "GTC"
        # order
        oid = self.trade_client.place_order(order)
        return IroriOrderResponse(order_id=oid)
    
    def short_open_market_order(self, short_command: irori_common.OrderCommand):
        if(self.trade_client == None):
            print("trade client empty")

        err_msg = ''
        # positions = self.get_positions()
        # for stock in positions.stockList:
        #     if stock.ticker == short_command.ticker and stock.quantity > 0:
        #         print(f"Cannot short {short_command.ticker} because there are existing holdings.")
        #         return -1
            
        #     print("trade client empty")
        if(self.get_positions().get_stock_by_ticker(short_command.ticker)!=None):
            if(self.get_positions().get_stock_by_ticker(short_command.ticker).quantity>0):
                err_msg = "stock is being held in long position"
                return IroriOrderResponse(error_message=err_msg)

        result_order_id = self.place_market_order(short_command.ticker, 'SELL', short_command.quantity)
        if result_order_id == -1:
            err_msg = "order failed from tiger side"

        return IroriOrderResponse(order_id=result_order_id, error_message=err_msg)
    
    def short_close_market_order(self, short_command: irori_common.OrderCommand):
        if(self.trade_client == None):
            print("trade client empty")

        # positions = self.get_positions()
        # for stock in positions.stockList:
        #     if stock.ticker == short_command.ticker and stock.quantity > 0:
        #         print(f"Cannot short {short_command.ticker} because there are existing holdings.")
        #         return -1
        err_msg = ''

        if(self.get_positions().get_stock_by_ticker(short_command.ticker) is None):
            err_msg = "stock not currently being held in short position"
            return IroriOrderResponse(error_message=err_msg)
        result_order_id = self.place_market_order(short_command.ticker, 'BUY', short_command.quantity)
        if result_order_id == -1:
            err_msg = "order failed from tiger side"
            
        return IroriOrderResponse(order_id=result_order_id, error_message=err_msg)
    
    def short_open_limit_order(self, short_command: irori_common.OrderCommand):

        err_msg = ''
        positions = self.get_positions()
        for stock in positions.stockList:
            if stock.ticker == short_command.ticker and stock.quantity > 0:
                err_msg = f"Cannot short {short_command.ticker} because there are existing holdings."
                return IroriOrderResponse(error_message=err_msg)

        result_order_id = self.place_limit_order(short_command.ticker, 'SELL', short_command.quantity, short_command.price)

        return IroriOrderResponse(order_id=result_order_id)
    
    def short_close_limit_order(self, short_command: irori_common.OrderCommand):

        positions = self.get_positions()
        for stock in positions.stockList:
            if stock.ticker == short_command.ticker and stock.quantity > 0:
                err_msg = f"Cannot short {short_command.ticker} because there are existing holdings."
                return IroriOrderResponse(error_message=err_msg)
            
        result_order_id = self.place_limit_order(short_command.ticker, 'BUY', short_command.quantity, short_command.price)

        return IroriOrderResponse(order_id=result_order_id)
    
    def short_open_stop_market_order(self, stop_loss : OrderCommand):

        positions = self.get_positions()
        for stock in positions.stockList:
            if stock.ticker == stop_loss.ticker and stock.quantity > 0:
                err_msg = f"Cannot short {stop_loss.ticker} because there are existing holdings."
                return IroriOrderResponse(error_message=err_msg)
            
        contract = stock_contract(symbol=str(stop_loss.ticker), currency=str(stop_loss.market))
        order = stop_order(account=self.client_config.account, contract=contract, action='SELL', aux_price=round(stop_loss.aux_price,2), quantity=stop_loss.quantity)

        oid = self.trade_client. place_order(order)

        return IroriOrderResponse(order_id=oid)
    
    def short_close_stop_market_order(self, stop_loss : OrderCommand):

        positions = self.get_positions()
        for stock in positions.stockList:
            if stock.ticker == stop_loss.ticker and stock.quantity > 0:
                err_msg = f"Cannot short {stop_loss.ticker} because there are existing holdings."
                return IroriOrderResponse(error_message=err_msg)
            
        contract = stock_contract(symbol=str(stop_loss.ticker), currency=str(stop_loss.market))
        order = stop_order(account=self.client_config.account, contract=contract, action='BUY', aux_price=round(stop_loss.aux_price,2), quantity=stop_loss.quantity)
        oid = self.trade_client. place_order(order)
        return IroriOrderResponse(order_id=oid)
    
    def short_open_stop_limit_order(self, stop_loss : irori_common.OrderCommand):

        positions = self.get_positions()
        for stock in positions.stockList:
            if stock.ticker == stop_loss.ticker and stock.quantity > 0:
                err_msg = f"Cannot short {stop_loss.ticker} because there are existing holdings."
                return IroriOrderResponse(error_message=err_msg)
            
        # generate stock contracts
        contract = stock_contract(symbol=str(stop_loss.ticker), currency=str(stop_loss.market))
        # generate order object
        order = stop_limit_order(account=self.client_config.account, contract=contract, action='SELL', limit_price=round(stop_loss.price,2), aux_price=round(stop_loss.aux_price,2), quantity=stop_loss.quantity)
        # order
        oid = self.trade_client.place_order(order)
        return IroriOrderResponse(order_id=oid)
    
    def short_close_stop_limit_order(self, stop_loss : irori_common.OrderCommand):

        positions = self.get_positions()
        for stock in positions.stockList:
            if stock.ticker == stop_loss.ticker and stock.quantity > 0:
                err_msg = f"Cannot short {stop_loss.ticker} because there are existing holdings."
                return IroriOrderResponse(error_message=err_msg)
            
        # generate stock contracts
        contract = stock_contract(symbol=str(stop_loss.ticker), currency=str(stop_loss.market))
        # generate order object
        order = stop_limit_order(account=self.client_config.account, contract=contract, action='BUY', limit_price=round(stop_loss.price,2), aux_price=round(stop_loss.aux_price,2), quantity=stop_loss.quantity)
        # order
        oid = self.trade_client.place_order(order)
        return IroriOrderResponse(order_id=oid)

    def buy_market_order(self, buy_command : OrderCommand):
        print("buying market order in tiger")
        if(self.trade_client == None):
            print("trade client emptuy")

        result_order_id = self.place_market_order(buy_command.ticker, 'BUY', buy_command.quantity)

        return IroriOrderResponse(order_id=result_order_id)

    def sell_market_order(self, sell_command: OrderCommand):
        result_order_id = self.place_market_order(sell_command.ticker, 'SELL', sell_command.quantity)

        return IroriOrderResponse(order_id=result_order_id)

    # ------------------------------------------------------------------------------

    def cancel_order(self, cancel_order_command: CancelOrderCommand):
        try:
            is_cancelled = self.trade_client.cancel_order(id=cancel_order_command.orderID)
            if is_cancelled:
                print(f"Order {cancel_order_command.orderID} cancelled successfully.")
                return IroriOrderResponse(-1, '', f'Successfully cancelled order {cancel_order_command.orderID}')
            else:
                print(f"Failed to cancel order {cancel_order_command.orderID}.")
                return IroriOrderResponse(-1, f'Failed to cancel order with id {cancel_order_command.orderID}', '', IroriOrderStatusCode.ERROR)
        except ApiException as e:
            print(f"Failed to cancel order. Code: {e.code}, Reason: {e.msg}")
            return IroriOrderResponse(-1, f'{e.msg}', f'Failed to cancel order with id {cancel_order_command.orderID}', IroriOrderStatusCode.ERROR)

    def clear_existing_orders(self, clear_order : ClearExistingOrderCommand):
        orders = self.trade_client.get_open_orders(sec_type=SecurityType.STK, market=clear_order.market, symbol=clear_order.ticker)
        print(f'{clear_order.ticker} Found {len(orders)} orders to cancel')
        
        if (len(orders) == 0):
            return

        orders_failed_to_cancel = []
        for order in orders:
            try:
                self.trade_client.cancel_order(id=order.id)
            except ApiException as e:
                print(f'Cancel order {order.id} failed. code: {e.code} msg: {e.msg}')
                # logger.error(f'Cancel order {order.id} failed. code: {e.code} msg: {e.msg}')
                orders_failed_to_cancel.append(order.id)
                continue
        
        err_msg = ''
        if len(orders_failed_to_cancel) != 0:
            err_msg = f'Failed to cancel orders {orders_failed_to_cancel}\n'
            # logger.error(f'Failed to cancel orders {orders_failed_to_cancel}')
        
        remarks = f'{clear_order.ticker} Cancelled {len(orders) - len(orders_failed_to_cancel)} orders successfully'

        return IroriOrderResponse(error_message=err_msg, remarks=remarks)
        # logger.info(f'{self.ticker} Cancelled {len(orders) - len(orders_failed_to_cancel)} orders successfully')

    def sell_all_existing_stocks(self, ticker, targetedProfit):
        positions = self.trade_client.get_positions(sec_type=SecurityType.STK, currency=Currency.ALL, symbol=ticker, market=Market.ALL)

        sell_orders_placed_successfully = 0

        for p in positions:
            print(f'Holding cost {p.average_cost}. Average cost {p.average_cost_by_average}')
            # logger.info(f'Holding cost {p.average_cost}. Average cost {p.average_cost_by_average}')
            sell_price = round(p.average_cost_by_average + targetedProfit, 2)
                
            # order_id = self.place_limit_order(trade_client=self.trade_client, account=self.client_config.account, symbol=ticker, action='SELL', quantity=p.quantity, price=sell_price)
            order_id = self.place_market_order()
            if order_id != -1:
                sell_orders_placed_successfully += 1
        
        if sell_orders_placed_successfully == len(positions):
            print(f'{ticker} Successfully placed sell orders for all existing stock {ticker}')
        elif sell_orders_placed_successfully == 0:
            print(f'{ticker} Unable to place any sell order for held stocks')
        else:
            print(f'{ticker} Partial success placed sell order for {sell_orders_placed_successfully}/{len(positions)} held stocks')

    def exit_all_positions_immediately(self, clear_order : ClearExistingOrderCommand):
        self.clear_existing_orders(self.trade_client, clear_order)
        self.sell_all_existing_stocks(clear_order.ticker)
    
    def stop(self):
        try:
            self.push_client.unsubscribe_tick(self.tickerList)
            self.push_client.disconnect()
        except Exception as e:
            print(f'Error cleaning up push client')
            # logger.error(f'Error cleaning up push client')
        super().stop()


    def place_limit_order(self, symbol, action, quantity, price):
        # make sure to round the price to 2 decimal places
        print(f'Placing {action} limit order for {symbol} qty {quantity} at {price} USD')

        contract = stock_contract(symbol=symbol, currency='USD')
        order = limit_order(account=self.client_config.account, contract=contract, action=action, limit_price=round(price, 2), quantity=quantity)
        
        if (self.paperaccount!=True):
            order.time_in_force = "GTC"

        if(self.trade_client == None):
            print("Trade client is not initialised")
            return IroriOrderResponse(-1, f'Trade client is not initialised', f'Failed to place {action} market order of qty {quantity}', IroriOrderStatusCode.ERROR)
        
        try:
            order_id = self.trade_client.place_order(order)
            #print(f'Limit Order placed successfully order {order}')
            print(f'Limit Order placed successfully order {order}')
            return IroriOrderResponse(order_id, '', 'Limit Order placed successfully')
        except ApiException as e:
            #print(f'Failed to create Limit Order. Code {e.code} Reason {e.msg}')
            print(f'Failed to create Limit Order. Code {e.code} Reason {e.msg}')
            return IroriOrderResponse(-1, f'{e.msg}', f'Failed to place {action} limit order of qty {quantity} price {price}', IroriOrderStatusCode.ERROR)

    def place_market_order(self, symbol, action, quantity):
        print(f'Placing market order for {symbol} qty {quantity}')

        contract = stock_contract(symbol=symbol, currency='USD')
        order = market_order(account=self.client_config.account, contract=contract, action=action, quantity=quantity)

        if(self.trade_client == None):
            print("Trade client is not initialised")
            return IroriOrderResponse(-1, f'Trade client is not initialised', f'Failed to place {action} market order of qty {quantity}', IroriOrderStatusCode.ERROR)

        try:
            order_id = self.trade_client.place_order(order)
            print(f'Market Order placed successfully order {order}')
            return IroriOrderResponse(order_id, '', f'{action} Market Order placed successfully of qty {quantity}')
        except ApiException as e:
            print(f'Failed to create Market Order. Code {e.code} Reason {e.msg}')
            return IroriOrderResponse(-1, f'{e.msg}', f'Failed to place {action} market order of qty {quantity}', IroriOrderStatusCode.ERROR)
        
    async def emergency_stop_option(self, order_offset:float):
        open_orders:list[TigerOrder]  = self.mediator.tiger_obj.trade_client.get_open_orders(sec_type=SecurityType.OPT, market=Market.ALL)

        for order in open_orders:
            self.trade_client.cancel_order(order.id)

        positions:list[TigerPosition] = self.trade_client.get_positions(sec_type=SecurityType.OPT, currency=Currency.ALL, market=Market.ALL)
        print(f'Exposed positions:')
        for position in positions:
            print(f'{position.contract} {position.quantity}')