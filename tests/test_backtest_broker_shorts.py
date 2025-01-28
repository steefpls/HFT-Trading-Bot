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
import unittest

from irori.Broker_Backtest import *
from irori.common import *

class BacktestBrokerShortTests(unittest.TestCase):
    def setUp(self):
        self.broker = BacktestBroker()
        self.broker.ticker_list = [["ticker", 0]]
        self.tick_price = 100
        self.starting_currency = 0
        self.ticker = "ticker"
        self.broker.set_current_price(self.ticker, self.tick_price)
        self.broker.working_currency = self.starting_currency
        self.broker.shortToggle = True
        self.broker.toggle_fees = False
        self.frame: OrderChangeData = None

    def test_short_open_order_successful_should_increase_working_currency(self):
        # Arrange
        order = OrderCommand(ticker=self.ticker, quantity=10)

        # Act
        self.broker.short_open_market_order(order)
        self.broker.fill_orders()

        # Assert
        self.assertNotEqual(self.broker.working_currency, self.starting_currency, "Money should increase after shorting")
        self.assertEqual(self.broker.working_currency, 1000)
        self.assertEqual(len(self.broker.shorts_owned_list), 1, "Shorts owned list should not be empty")

    def test_multiple_short_open_order_successful_should_update_shorts_owned(self):
        # Arrange
        order = OrderCommand(ticker=self.ticker, quantity=6)
        order2 = OrderCommand(ticker=self.ticker, quantity=9)

        # Act
        self.broker.short_open_market_order(order)
        self.broker.short_open_market_order(order2)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(len(self.broker.shorts_owned_list), 1)
        self.assertEqual(self.broker.shorts_owned_list[0].num_shares, 15)

    def test_multiple_short_open_order_successful_should_update_avg_price(self):
        """
        Buy 10 @ $10
        Buy 5 @ 5
        Total: 15 Qty, Avg price should be ($100 + $25) / 15 = ~$8.33333
        """
        # Arrange
        order = OrderCommand(ticker=self.ticker, quantity=10)
        order2 = OrderCommand(ticker=self.ticker, quantity=5)

        # Act
        self.broker.set_current_price(self.ticker, 10)
        self.broker.short_open_market_order(order)
        self.broker.fill_orders()

        self.broker.set_current_price(self.ticker, 5)
        self.broker.short_open_market_order(order2)
        self.broker.fill_orders()

        # Assert
        self.assertAlmostEqual(self.broker.shorts_owned_list[0].avg_price, 8.33333, 2)

    def test_short_open_order_successful_should_store_in_shorts_owned(self):
        # Arrange
        num_shares_to_short = 10
        order = OrderCommand(ticker=self.ticker, quantity=num_shares_to_short)

        # Act
        self.broker.short_open_market_order(order)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(len(self.broker.shorts_owned_list), 1, "Shorts owned list should not be empty")
        self.assertEqual(self.broker.shorts_owned_list[0].ticker, self.ticker)
        self.assertEqual(self.broker.shorts_owned_list[0].num_shares, num_shares_to_short)
        self.assertEqual(self.broker.shorts_owned_list[0].avg_price, self.tick_price)

    def test_short_open_order_successful_should_trigger_order_change(self):
        # Arrange
        num_shares_to_short = 10
        order = OrderCommand(ticker=self.ticker, quantity=num_shares_to_short)

        global order_change_data
        order_change_data = OrderChangeData()
        def on_order_change(frame: OrderChangeData):
            global order_change_data
            order_change_data = frame

        self.broker.setup_callbacks(None, on_order_change, None)

        # Act
        self.broker.short_open_market_order(order)
        self.assertEqual(OrderStatus.NEW, order_change_data.order_status)
        self.assertEqual(self.tick_price, order_change_data.limit_price)

        self.broker.fill_orders()

        # Assert
        self.assertIsNotNone(order_change_data)
        self.assertEqual(OrderStatus.FILLED, order_change_data.order_status)
        self.assertEqual(True, order_change_data.is_short)
        self.assertEqual(num_shares_to_short, order_change_data.total_quantity)
        self.assertEqual(self.ticker, order_change_data.ticker)

    def test_short_close_order_successful_should_decrease_working_currency(self):
        # Arrange
        num_shares_to_close = 10
        self.broker.working_currency = 1000
        short_open_order = OrderCommand(ticker=self.ticker, quantity=num_shares_to_close)
        self.broker.short_open_market_order(short_open_order)
        self.broker.fill_orders()

        short_close_order = OrderCommand(ticker=self.ticker, quantity=num_shares_to_close)

        # Act
        self.broker.short_close_market_order(short_close_order)
        self.broker.fill_orders()

        # Assert
        self.assertNotEqual(self.broker.working_currency, 0)
        self.assertEqual(len(self.broker.shorts_owned_list), 0)
        self.assertEqual(len(self.broker.short_close_list), 0)

    def test_short_close_order_fail_should_not_place_short_close_order(self):
        """
        Fail due to trying to sell more quantity than held
        """
        # Arrange
        num_shares_to_close = 10
        short_open_order = OrderCommand(ticker=self.ticker, quantity=num_shares_to_close)
        self.broker.short_open_market_order(short_open_order)
        self.broker.fill_orders()

        short_close_order = OrderCommand(ticker=self.ticker, quantity=num_shares_to_close + 1)

        # Act
        self.broker.short_close_market_order(short_close_order)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(len(self.broker.short_open_list), 0)
        self.assertEqual(self.broker.working_currency, 1000)
        self.assertEqual(len(self.broker.shorts_owned_list), 1) 

    def test_short_limit_close_order_price_not_met_should_not_fill_order(self):
        """
        Not filling order due to price not being met
        """
        # Arrange
        num_shares_to_close = 10
        short_open_order = OrderCommand(ticker=self.ticker, quantity=num_shares_to_close)
        self.broker.short_open_market_order(short_open_order)
        self.broker.fill_orders()

        short_close_order = OrderCommand(ticker=self.ticker, quantity=num_shares_to_close)

        # Act
        self.broker.short_close_limit_order(short_close_order)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(len(self.broker.short_close_list), 1)
        self.assertEqual(self.broker.working_currency, 1000)

    def test_close_all_shorts_should_place_orders(self):
        # Arrange
        self.broker.working_currency = 0
        num_shares_to_close = 10
        short_open_order = OrderCommand(ticker=self.ticker, quantity=num_shares_to_close)
        short_open_order2 = OrderCommand(ticker=self.ticker, quantity=num_shares_to_close + 5)
        self.broker.short_open_market_order(short_open_order)
        self.broker.short_open_market_order(short_open_order2)
        self.broker.fill_orders()

        # Act
        has_shorts = self.broker.close_all_shorts()

        # Assert
        self.assertEqual(has_shorts, True)
        self.assertEqual(len(self.broker.short_close_list), 1)
        self.assertEqual(self.broker.short_close_list[0].num_shares, num_shares_to_close * 2 + 5)
        self.assertEqual(self.broker.working_currency, 2500)

    def test_close_all_shorts_should_close_all(self):
        # Arrange
        self.broker.working_currency = 0
        num_shares_to_close = 10
        short_open_order = OrderCommand(ticker=self.ticker, quantity=num_shares_to_close)
        short_open_order2 = OrderCommand(ticker=self.ticker, quantity=num_shares_to_close + 5)
        self.broker.short_open_market_order(short_open_order)
        self.broker.short_open_market_order(short_open_order2)
        self.broker.fill_orders()

        # Act
        has_shorts = self.broker.close_all_shorts()
        self.broker.fill_orders()

        # Assert
        self.assertEqual(has_shorts, True)
        self.assertEqual(len(self.broker.short_open_list), 0)
        self.assertEqual(self.broker.working_currency, 0)

# # ------------------------- START STOP LOSS TESTS ------------------------- #
    # def test_stop_loss_buy(self):
    #     #arrange
    #     buy_qty = 1
    #     price = 100
    #     command = StopMarketBuyOrderCommand(ticker='', quantity=buy_qty,aux_price=price, broker=Broker.BACKTEST)

    #     buy_qty2 = 3
    #     price2 = 75
    #     command2 = StopMarketBuyOrderCommand(ticker='', quantity=buy_qty2,aux_price=price2, broker=Broker.BACKTEST)

    #     #assert
    #     self.broker.stop_market_buy_order(command)
    #     self.assertEqual(len(self.broker.stop_buy_list), 1, "short_stop_loss_list not updating after placing stop loss order")
    #     self.assertEqual(self.broker.stop_buy_list[0].stop_price, price, "short_stop_loss_list should contain buy order with correct price")
    #     self.assertEqual(self.broker.stop_buy_list[0].num_shares, buy_qty, "short_stop_loss_list should contain buy order with correct number of shares")
    #     self.assertEqual(self.broker.stop_buy_list[0].block_id, 1, "short_stop_loss_list should contain buy order with correct block id")

    #     self.broker.stop_market_buy_order(command2)
    #     self.assertEqual(len(self.broker.stop_buy_list), 2, "short_stop_loss_list should be 2 after buying twice")
    #     self.assertEqual(self.broker.stop_buy_list[1].stop_price, price2, "short_stop_loss_list should contain buy order with correct price")
    #     self.assertEqual(self.broker.stop_buy_list[1].num_shares, buy_qty2, "short_stop_loss_list should contain buy order with correct number of shares")
    #     self.assertEqual(self.broker.stop_buy_list[1].block_id, 2, "short_stop_loss_list should contain buy order with correct block id")
    
    # def test_fill_stop_loss_buy_successful_should_update_information(self):
    #     buy_qty = 1
    #     price = 100
    #     self.broker.stop_market_buy_order(StopMarketBuyOrderCommand(ticker='', quantity=buy_qty,aux_price=price, broker=Broker.BACKTEST))
    #     self.broker.fill_orders(0)

    #     self.assertLess(self.broker.working_currency, 1000, "working_currency should decrease after buying")
    #     self.assertEqual(len(self.broker.shares_owned_list), 1, "shares_owned_list should increase after filling buy order")
    #     self.assertEqual(self.broker.shares_owned_list[0].block_id, 1, "owned stock block id should be same as buy order")
    #     self.assertEqual(self.broker.shares_owned_list[0].price, self.tick_price, "owned stock price should be same as buy order")
    #     self.assertEqual(self.broker.shares_owned_list[0].num_shares, buy_qty)

    #     self.assertEqual(len(self.broker.transaction_list), 1, "transaction_list should update after filling buy order")
    #     self.assertEqual(self.broker.transaction_list[0].block_id, 1, "transaction block id should be same as buy order")
    #     self.assertEqual(self.broker.transaction_list[0].price, self.tick_price, "transaction price should be same as buy order")
    #     self.assertEqual(self.broker.transaction_list[0].num_shares, buy_qty)

    # def test_stop_loss_buy_orders_should_trigger_order_change_callback(self):
    #     global called
    #     called = False
    #     def order_callback(frame):
    #         global called
    #         called = True

    #     self.broker.setup_callbacks(None, order_callback, None)

    #     buy_qty = 1
    #     price = 100
    #     command = StopMarketBuyOrderCommand(ticker='', quantity=buy_qty, aux_price = price, broker=Broker.BACKTEST)

    #     self.broker.stop_market_buy_order(command)

    #     self.assertTrue(called, "order changed callback should be called")

    # def test_stop_loss_buy_order_order_change_callback_should_be_correct(self):
    #     global order_change_data
    #     order_change_data = OrderChangeData()
    #     def order_callback(frame):
    #         global order_change_data
    #         order_change_data = frame

    #     self.broker.setup_callbacks(None, order_callback, None)

    #     buy_qty = 1
    #     price = 100
    #     command = StopMarketBuyOrderCommand(ticker='', quantity=buy_qty,aux_price=price, broker=Broker.BACKTEST)

    #     self.broker.stop_market_buy_order(command)

    #     self.assertEqual(order_change_data.orderType, OrderType.STOP, "Order type should be market")
    #     self.assertEqual(order_change_data.status, OrderStatus.NEW, "Order status should be new")
    #     self.assertEqual(order_change_data.orderID, 1, "Order id should be 1")
    #     self.assertEqual(order_change_data.action, "BUY", "action should be buy")
    #     self.assertEqual(order_change_data.avg_fill_price, price, "Order change data limit price should be bought at broker current price")
    #     self.assertEqual(order_change_data.total_quantity, command.quantity, "Order change qty should be same as command's qty")

    # def test_stop_loss_buy_order_meet_conditions_should_be_filled(self):
    #     # Arrange
    #     buy_qty = 1
    #     price = 99
    #     command = StopMarketBuyOrderCommand(ticker='', aux_price=price, quantity=buy_qty, broker=Broker.BACKTEST)

    #     # Act
    #     self.broker.stop_market_buy_order(command)
    #     self.broker.fill_orders(0)

    #     # Assert
    #     self.assertEqual(len(self.broker.shares_owned_list), 1, "order should be fulfilled as stop price hit current price")

    # def test_stop_loss_buy_order_does_not_meet_price_should_not_fill(self):
    #     # Arrange
    #     buy_qty = 1
    #     price = 101
    #     command = StopMarketBuyOrderCommand(ticker='', aux_price=price, quantity=buy_qty, broker=Broker.BACKTEST)

    #     # Act
    #     self.broker.stop_market_buy_order(command)
    #     self.broker.fill_orders(0)

    #     # Assert
    #     self.assertEqual(len(self.broker.stop_buy_list), 1, "order should not be fulfilled as stop price did not hit current price")
    #     self.assertEqual(len(self.broker.shares_owned_list), 0, "order should not be fulfilled as stop price did not hit current price")        

    # # ----------------- Shorts Market & Limit Tests -------------------------- #       
    # # Buys
    # # Markets
    # def test_buy_short_market_order_should_update_short_list(self):
    #     short_qty = 1
    #     command = ShortMarketOrderCommand(ticker='', quantity=short_qty, broker=Broker.BACKTEST)
    #     self.broker.short_market_order(command)

    #     # self.assertEqual(len(self.broker.buy_order_list), 1, "short_order_list not updating after placing buy order")
    #     self.assertEqual(len(self.broker.short_buy_list), 1, "short_order_list not updating after placing buy order")
    #     self.assertEqual(self.broker.short_buy_list[0].limit_price, self.tick_price, "short_order_list should contain buy order with correct price")
    #     self.assertEqual(self.broker.short_buy_list[0].num_shares, short_qty, "short_order_list should contain buy order with correct number of shares")
    #     self.assertEqual(self.broker.short_buy_list[0].block_id, 1, "short_order_list should contain buy order with correct block id")

    # def test_fill_short_market_order_successful_should_update_information(self):
    #     short_qty = 1
    #     self.broker.short_market_order(ShortMarketOrderCommand('', short_qty, Broker.BACKTEST))
    #     self.broker.fill_orders(0)

    #     # self.assertGreater(self.broker.working_currency, 1000, "working_currency should increase after buying")
    #     self.assertGreater(self.broker.working_currency, 1000, "working_currency should increase after buying")
    #     self.assertEqual(len(self.broker.shorts_owned_list), 1, "shorts_owned_list should increase after filling buy short order")
    #     self.assertEqual(self.broker.shorts_owned_list[0].block_id, 1, "owned shorts price should be same as buy order")
    #     self.assertEqual(self.broker.shorts_owned_list[0].price, self.tick_price)
    #     self.assertEqual(self.broker.shorts_owned_list[0].num_shares, short_qty)

    #     self.assertEqual(len(self.broker.transaction_list), 1, "transaction_list should update after filling buy order")
    #     self.assertEqual(self.broker.transaction_list[0].block_id, 1, "owned stock price should be same as buy order")
    #     self.assertEqual(self.broker.transaction_list[0].price, self.tick_price)
    #     self.assertEqual(self.broker.transaction_list[0].num_shares, short_qty)

    # def test_short_buy_market_orders_should_trigger_order_change_callback(self):
    #     global called
    #     called = False
    #     def order_callback(frame):
    #         global called
    #         called = True

    #     self.broker.setup_callbacks(None, order_callback, None)

    #     short_qty = 1
    #     command = ShortMarketOrderCommand('', short_qty, Broker.BACKTEST)

    #     self.broker.short_market_order(command)

    #     self.assertTrue(called, "order changed callback should be called")

    # def test_short_buy_market_order_order_change_callback_should_be_correct(self):
    #     global order_change_data
    #     order_change_data = OrderChangeData()
    #     def order_callback(frame):
    #         global order_change_data
    #         order_change_data = frame

    #     self.broker.setup_callbacks(None, order_callback, None)

    #     short_qty = 1
    #     command = ShortMarketOrderCommand('', short_qty, Broker.BACKTEST)

    #     self.broker.short_market_order(command)

    #     self.assertEqual(order_change_data.orderType, OrderType.MARKET, "Order type should be market")
    #     self.assertEqual(order_change_data.status, OrderStatus.NEW, "Order status should be new")
    #     self.assertEqual(order_change_data.orderID, 1, "Order id should be 1")
    #     self.assertEqual(order_change_data.action, "SELL", "action should be sell")
    #     self.assertEqual(order_change_data.limit_price, self.broker.current_price, "Order change data limit price should be bought at broker current price")
    #     self.assertEqual(order_change_data.total_quantity, command.quantity, "Order change qty should be same as command's qty")

    # # Limits
    # def test_buy_short_limit_order_should_update_short_list(self):
    #     short_qty = 1
    #     command = ShortLimitOrderCommand(ticker='', price=100, quantity=short_qty, broker=Broker.BACKTEST)
    #     self.broker.short_limit_order(command)

    #     # self.assertEqual(len(self.broker.buy_order_list), 1, "short_order_list not updating after placing buy order")
    #     self.assertEqual(len(self.broker.short_buy_list), 1, "short_order_list not updating after placing buy order")
    #     self.assertEqual(self.broker.short_buy_list[0].limit_price, self.tick_price, "short_order_list should contain buy order with correct price")
    #     self.assertEqual(self.broker.short_buy_list[0].num_shares, short_qty, "short_order_list should contain buy order with correct number of shares")
    #     self.assertEqual(self.broker.short_buy_list[0].block_id, 1, "short_order_list should contain buy order with correct block id")

    # def test_fill_short_limit_order_successful_should_update_information(self):
    #     short_qty = 1
    #     self.broker.short_limit_order(ShortLimitOrderCommand('', 99, short_qty, Broker.BACKTEST))
    #     self.broker.fill_orders(0)

    #     # self.assertGreater(self.broker.working_currency, 1000, "working_currency should increase after buying")
    #     self.assertGreater(self.broker.working_currency, 1000, "working_currency should increase after buying")
    #     self.assertEqual(len(self.broker.shorts_owned_list), 1, "shorts_owned_list should increase after filling buy short order")
    #     self.assertEqual(self.broker.shorts_owned_list[0].block_id, 1, "owned shorts price should be same as buy order")
    #     self.assertEqual(self.broker.shorts_owned_list[0].price, self.tick_price)
    #     self.assertEqual(self.broker.shorts_owned_list[0].num_shares, short_qty)

    #     self.assertEqual(len(self.broker.transaction_list), 1, "transaction_list should update after filling buy order")
    #     self.assertEqual(self.broker.transaction_list[0].block_id, 1, "owned stock price should be same as buy order")
    #     self.assertEqual(self.broker.transaction_list[0].price, self.tick_price)
    #     self.assertEqual(self.broker.transaction_list[0].num_shares, short_qty)

    # def test_short_buy_limit_orders_should_trigger_order_change_callback(self):
    #     global called
    #     called = False
    #     def order_callback(frame):
    #         global called
    #         called = True

    #     self.broker.setup_callbacks(None, order_callback, None)

    #     short_qty = 1
    #     command = ShortLimitOrderCommand('', 100, short_qty, Broker.BACKTEST)

    #     self.broker.short_limit_order(command)

    #     self.assertTrue(called, "order changed callback should be called")

    # def test_short_buy_limit_order_order_change_callback_should_be_correct(self):
    #     global order_change_data
    #     order_change_data = OrderChangeData()
    #     def order_callback(frame):
    #         global order_change_data
    #         order_change_data = frame

    #     self.broker.setup_callbacks(None, order_callback, None)

    #     short_qty = 1
    #     command = ShortLimitOrderCommand('', 100, short_qty, Broker.BACKTEST)

    #     self.broker.short_limit_order(command)

    #     self.assertEqual(order_change_data.orderType, OrderType.LIMIT, "Order type should be market")
    #     self.assertEqual(order_change_data.status, OrderStatus.NEW, "Order status should be new")
    #     self.assertEqual(order_change_data.orderID, 1, "Order id should be 1")
    #     self.assertEqual(order_change_data.action, "SELL", "action should be sell")
    #     self.assertEqual(order_change_data.limit_price, self.broker.current_price, "Order change data limit price should be bought at broker current price")
    #     self.assertEqual(order_change_data.total_quantity, command.quantity, "Order change qty should be same as command's qty")

    # def test_short_buy_limit_order_meet_conditions_should_be_filled(self):
    #     # Arrange
    #     short_qty = 1
    #     limprice = 99
    #     command = ShortLimitOrderCommand(ticker='', price=limprice, quantity=short_qty, broker=Broker.BACKTEST)

    #     # Act
    #     self.broker.short_limit_order(command)
    #     self.broker.fill_orders(0)

    #     # Assert
    #     self.assertEqual(len(self.broker.short_buy_list), 0, "Short limit order should be fulfilled as limit price less than current price")
    #     self.assertEqual(len(self.broker.shorts_owned_list), 1, "Short limit order should be fulfilled as limit price less than current price")

    # def test_short_buy_limit_order_does_not_meet_price_should_not_fill(self):
    #     # Arrange
    #     short_qty = 1
    #     limprice = 101
    #     command = ShortLimitOrderCommand(ticker='', price=limprice, quantity=short_qty, broker=Broker.BACKTEST)

    #     # Act
    #     self.broker.short_limit_order(command)
    #     self.broker.fill_orders(0)

    #     # Assert
    #     self.assertEqual(len(self.broker.short_buy_list), 1, "Short limit order should not be fulfilled as limit price did not hit current price")
    #     self.assertEqual(len(self.broker.shorts_owned_list), 0, "Short limit order should not be fulfilled as limit price did not hit current price")

    # # Sells
    # # Market
    # def test_sell_short_market_order_should_update_short_list(self):
    #     short_qty = 1
    #     command = ShortSellMarketOrderCommand('', short_qty, Broker.BACKTEST)
    #     self.broker.shorts_owned_list.append(SellShortOrder(lim_price=100,\
    #                                                        num_shares=1,\
    #                                                         block_id = 1))
    #     self.broker.short_sell_market_order(command)

    #     # self.assertEqual(len(self.broker.buy_order_list), 1, "short_order_list not updating after placing buy order")
    #     self.assertEqual(len(self.broker.short_sell_list), 1, "short_sell_list not updating after placing sell order")
    #     self.assertEqual(self.broker.short_sell_list[0].limit_price, self.tick_price, "short_sell_list should contain buy order with correct price")
    #     self.assertEqual(self.broker.short_sell_list[0].num_shares, short_qty, "short_sell_list should contain buy order with correct number of shares")
    #     self.assertEqual(self.broker.short_sell_list[0].block_id, 1, "short_sell_list should contain buy order with correct block id")

    # def test_short_sell_market_when_no_shares_owned_should_fail(self):
    #     # Arrange
    #     sell_qty = 1
    #     sell_command = ShortSellMarketOrderCommand('', sell_qty, Broker.BACKTEST)

    #     global orderChangeData
    #     orderChangeData = OrderChangeData()
    #     def order_change_callback(frame):
    #         global orderChangeData
    #         orderChangeData = frame

    #     # Act
    #     self.broker.setup_callbacks(None, order_change_callback, None)
    #     self.broker.short_sell_market_order(sell_command)
    #     self.broker.fill_orders(0)

    #     # Assert
    #     self.assertEqual(len(self.broker.short_sell_list), 0, "Sell order list should be empty since no shares owned")
    #     self.assertEqual(self.broker.working_currency, self.starting_currency, "Working currency should remain same since nothing was sold")
    #     self.assertNotEqual(orderChangeData.status, OrderStatus.FILLED, "Order change data should not be filled")

    # def test_short_sell_market_when_shares_owned_should_pass(self):
    #     # Arrange
    #     sell_qty = 1
    #     sell_command = ShortSellMarketOrderCommand('', sell_qty, Broker.BACKTEST)

    #     self.broker.shortToggle = True

    #     self.broker.shares_owned_list.append(ShortOrder(lim_price=100,\
    #                                                        num_shares=1,\
    #                                                         block_id = 1))

    #     global orderChangeData
    #     orderChangeData = OrderChangeData()
    #     def order_change_callback(frame):
    #         global orderChangeData
    #         orderChangeData = frame

    #     # Act
    #     self.broker.setup_callbacks(None, order_change_callback, None)
    #     self.broker.short_sell_market_order(sell_command)
    #     self.broker.fill_orders(0)

    #     # Assert
    #     self.assertLess(self.broker.working_currency, 1000, "working_currency should decrease after selling")
    #     self.assertEqual(len(self.broker.shorts_owned_list), 0, "shorts_owned_list should decrease after filling sell short order")

    #     self.assertEqual(len(self.broker.transaction_list), 1, "transaction_list should update after filling sell order")
    #     self.assertEqual(self.broker.transaction_list[0].block_id, 1, "owned stock price should be same as sell order")
    #     self.assertEqual(self.broker.transaction_list[0].price, self.tick_price)
    #     self.assertEqual(self.broker.transaction_list[0].num_shares, sell_qty)

    # # Limit
    # def test_sell_short_limit_order_should_update_short_list(self):
    #     short_qty = 1
    #     command = ShortSellLimitOrderCommand('', 100, short_qty, Broker.BACKTEST)
    #     self.broker.shorts_owned_list.append(SellShortOrder(lim_price=100,\
    #                                                        num_shares=1,\
    #                                                         block_id = 1))
    #     self.broker.short_sell_market_order(command)

    #     # self.assertEqual(len(self.broker.buy_order_list), 1, "short_order_list not updating after placing buy order")
    #     self.assertEqual(len(self.broker.short_sell_list), 1, "short_sell_list not updating after placing sell order")
    #     self.assertEqual(self.broker.short_sell_list[0].limit_price, self.tick_price, "short_sell_list should contain buy order with correct price")
    #     self.assertEqual(self.broker.short_sell_list[0].num_shares, short_qty, "short_sell_list should contain buy order with correct number of shares")
    #     self.assertEqual(self.broker.short_sell_list[0].block_id, 1, "short_sell_list should contain buy order with correct block id")

    # def test_sell_limit_when_no_shares_owned_should_fail(self):
    #     # Arrange
    #     sell_qty = 5
    #     sell_command = ShortLimitOrderCommand('', 100, sell_qty, Broker.BACKTEST)

    #     global orderChangeData
    #     orderChangeData = OrderChangeData()
    #     def order_change_callback(frame):
    #         global orderChangeData
    #         orderChangeData = frame

    #     # Act
    #     self.broker.setup_callbacks(None, order_change_callback, None)
    #     self.broker.short_sell_limit_order(sell_command)
    #     self.broker.fill_orders(0)

    #     # Assert
    #     self.assertEqual(len(self.broker.short_sell_list), 0, "Sell order list should not decrease since it is not fulfilled")
    #     self.assertEqual(self.broker.working_currency, self.starting_currency, "Working currency should remain same since nothing was sold")
    #     self.assertNotEqual(orderChangeData.status, OrderStatus.FILLED, "Order change data should not be filled")
    

    # # ------------------------ END SHORTS MARKET & LIMIT TESTS ----------------------- #


if __name__ == '__main__':
    unittest.main()