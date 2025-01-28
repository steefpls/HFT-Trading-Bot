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

class BacktestbrokerTests(unittest.TestCase):

    def setUp(self):
        self.broker = BacktestBroker()
        self.ticker_mock = 'asd'
        self.broker.ticker_list = [[self.ticker_mock, 0]]
        self.tick_price = 100
        self.broker.set_current_price(self.ticker_mock, self.tick_price)
        self.starting_currency = 1000
        self.broker.working_currency = self.starting_currency
        self.broker.shortToggle = False

    # ----------------- Helper functions -------------------------- #

    # ----------------------------------------------------------------- #

    # ----------------- Market & Limit Tests -------------------------- #

    # Buys
    def test_buy_market_order_should_update_buy_list(self):
        buy_qty = 1
        command = OrderCommand(ticker=self.ticker_mock, quantity=buy_qty)

        buy_qty2 = 3
        command2 = OrderCommand(ticker=self.ticker_mock, quantity=buy_qty2)

        self.broker.buy_market_order(command)

        self.assertEqual(len(self.broker.buy_order_list), 1, "buy_order_list not updating after placing buy order")
        self.assertEqual(self.broker.buy_order_list[0].limit_price, self.tick_price, "buy_order_list should contain buy order with correct price")
        self.assertEqual(self.broker.buy_order_list[0].num_shares, buy_qty, "buy_order_list should contain buy order with correct number of shares")
        self.assertEqual(self.broker.buy_order_list[0].block_id, 1, "buy_order_list should contain buy order with correct block id")

        self.broker.buy_market_order(command2)
        self.assertEqual(len(self.broker.buy_order_list), 2, "buy_order_list should be 2 after buying twice")
        self.assertEqual(self.broker.buy_order_list[1].limit_price, self.tick_price, "buy_order_list should contain buy order with correct price")
        self.assertEqual(self.broker.buy_order_list[1].num_shares, buy_qty2, "buy_order_list should contain buy order with correct number of shares")
        self.assertEqual(self.broker.buy_order_list[1].block_id, 2, "buy_order_list should contain buy order with correct block id")

    def test_fill_market_order_successful_should_update_information(self):
        buy_qty = 1
        self.broker.buy_market_order(OrderCommand(ticker=self.ticker_mock, quantity=buy_qty))
        self.broker.fill_orders()

        self.assertLess(self.broker.working_currency, 1000, "working_currency should decrease after buying")
        self.assertEqual(len(self.broker.shares_owned_list), 1, "shares_owned_list should increase after filling buy order")
        self.assertEqual(self.broker.shares_owned_list[0].block_id, 1, "owned stock price should be same as buy order")
        self.assertEqual(self.broker.shares_owned_list[0].avg_price, self.tick_price)
        self.assertEqual(self.broker.shares_owned_list[0].num_shares, buy_qty)

        self.assertEqual(len(self.broker.transaction_list), 1, "transaction_list should update after filling buy order")
        self.assertEqual(self.broker.transaction_list[0].block_id, 1, "owned stock price should be same as buy order")
        self.assertEqual(self.broker.transaction_list[0].price, self.tick_price)
        self.assertEqual(self.broker.transaction_list[0].num_shares, buy_qty)

    def test_buy_orders_should_trigger_order_change_callback(self):
        global called
        called = False
        def order_callback(frame):
            global called
            called = True

        self.broker.setup_callbacks(None, order_callback, None)

        buy_qty = 1
        command = OrderCommand(ticker=self.ticker_mock, quantity=buy_qty)

        self.broker.buy_market_order(command)

        self.assertTrue(called, "order changed callback should be called")

    def test_buy_market_order_order_change_callback_should_be_correct(self):
        global order_change_data
        order_change_data = OrderChangeData()
        def order_callback(frame):
            global order_change_data
            order_change_data = frame

        self.broker.setup_callbacks(None, order_callback, None)

        buy_qty = 1
        command = OrderCommand(ticker=self.ticker_mock, quantity=buy_qty)

        self.broker.buy_market_order(command)

        self.assertEqual(order_change_data.order_type, OrderType.MARKET, "Order type should be market")
        self.assertEqual(order_change_data.order_status, OrderStatus.NEW, "Order status should be new")
        self.assertEqual(order_change_data.orderID, 1, "Order id should be 1")
        self.assertEqual(order_change_data.action, OrderAction.BUY, "action should be buy")
        self.assertEqual(order_change_data.limit_price, self.broker.get_current_price(self.ticker_mock), "Order change data limit price should be bought at broker current price")
        self.assertEqual(order_change_data.total_quantity, command.quantity, "Order change qty should be same as command's qty")

    def test_buy_limit_order_meet_conditions_should_be_filled(self):
        # Arrange
        buy_qty = 1
        limprice = 101
        command = OrderCommand(ticker=self.ticker_mock, price=limprice, quantity=buy_qty)

        # Act
        self.broker.buy_limit_order(command)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(len(self.broker.buy_order_list), 0, "Limit order should not be fulfilled as limit price did not hit current price")
        self.assertEqual(len(self.broker.shares_owned_list), 1, "Limit order should not be fulfilled as limit price did not hit current price")

    def test_buy_limit_order_does_not_meet_price_should_not_fill(self):
        # Arrange
        buy_qty = 1
        limprice = 99
        command = OrderCommand(ticker=self.ticker_mock, price=limprice, quantity=buy_qty)

        # Act
        self.broker.buy_limit_order(command)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(len(self.broker.buy_order_list), 1, "Limit order should not be fulfilled as limit price did not hit current price")
        self.assertEqual(len(self.broker.shares_owned_list), 0, "Limit order should not be fulfilled as limit price did not hit current price")

    def test_buy_limit_order_order_change_callback_should_be_correct(self):
        # Arrange
        global order_change_data
        order_change_data = OrderChangeData()
        def order_callback(frame):
            global order_change_data
            order_change_data = frame

        self.broker.setup_callbacks(None, order_callback, None)

        buy_qty = 1
        limprice = 101
        command = OrderCommand(ticker='', price=limprice, quantity=buy_qty)

        # Act
        self.broker.buy_limit_order(command)

        # Assert
        self.assertEqual(order_change_data.order_type, OrderType.LIMIT, "Order type should be market")
        self.assertEqual(order_change_data.order_status, OrderStatus.NEW, "Order status should be new")
        self.assertEqual(order_change_data.orderID, 1, "Order id should be 1")
        self.assertEqual(order_change_data.action, OrderAction.BUY, "action should be buy")
        self.assertEqual(order_change_data.limit_price, command.price, "Order change data limit price should be bought at broker current price")
        self.assertEqual(order_change_data.total_quantity, command.quantity, "Order change qty should be same as command's qty")

        # Act
        self.broker.fill_orders()

        # Assert
        self.assertEqual(order_change_data.order_status, OrderStatus.FILLED, "Order status should be filled")

    def test_buy_market_with_insufficient_currency_should_fail(self):
        # Arrange
        self.broker.toggle_margin = False
        self.broker.set_current_price(self.ticker_mock, 9999)
        self.broker.working_currency = 1000

        buy_qty = 1
        command = OrderCommand(ticker=self.ticker_mock, quantity=buy_qty)

        # Act
        self.broker.buy_market_order(command)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(self.broker.working_currency, self.starting_currency, "Currency should be the same as buying failed")
        self.assertEqual(len(self.broker.shares_owned_list), 0, "shares owned should not increase as nothing was filled")
        self.assertEqual(len(self.broker.buy_order_list), 0, "buy market order should not be placed with insufficient currency")

    # Sells
    def test_sell_market_order_when_insufficient_shares_owned_should_fail(self):
        # Arrange
        self.broker.shares_owned_list.append(OwnedStock(block_id=1, ticker=self.ticker_mock, price=100, num_shares=4))
        self.broker.order_id_tracker = 1

        sell_qty = 5
        sell_command = OrderCommand(ticker='', quantity=sell_qty)

        global orderChangeData
        orderChangeData = OrderChangeData()
        def order_change_callback(frame):
            global orderChangeData
            orderChangeData = frame

        # Act
        self.broker.setup_callbacks(None, order_change_callback, None)
        self.broker.sell_market_order(sell_command)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(len(self.broker.sell_order_list), 0, "Sell order list should not even add a sell order")
        self.assertEqual(self.broker.working_currency, self.starting_currency, "Working currency should remain same since nothing was sold")
        self.assertNotEqual(orderChangeData.order_status, OrderStatus.FILLED, "Order change data should not be filled")

    def test_sell_market_order_filled_successful_should_update_information(self):
        # Arrange
        self.broker.shares_owned_list.append(OwnedStock(block_id=0, ticker=self.ticker_mock, price=100, num_shares=5))
        self.broker.order_id_tracker = 1
        
        sell_qty = 5
        sell_command = OrderCommand(ticker=self.ticker_mock, quantity=sell_qty)

        global orderChangeData
        orderChangeData = OrderChangeData()
        def order_change_callback(frame):
            global orderChangeData
            orderChangeData = frame

        # Act
        self.broker.setup_callbacks(None, order_change_callback, None)
        self.broker.sell_market_order(sell_command)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(len(self.broker.sell_order_list), 0, "Sell order list should be empty because sell is fulfilled")
        self.assertEqual(len(self.broker.shares_owned_list), 0, "shares owned list should be empty after selling")
        self.assertGreater(self.broker.working_currency, self.starting_currency, "Working currency should increase since we sold")
        self.assertEqual(orderChangeData.order_status, OrderStatus.FILLED, "Sell Market Order change data should be filled")

    def test_sell_limit_order_price_not_met_should_not_sell(self):
        # Arrange
        self.broker.shares_owned_list.append(OwnedStock(block_id=1, ticker=self.ticker_mock, price=100, num_shares=5))
        self.broker.order_id_tracker = 2
        
        sell_qty = 5
        sell_command = OrderCommand(ticker=self.ticker_mock, price=101, quantity=sell_qty)

        global orderChangeData
        orderChangeData = OrderChangeData()
        def order_change_callback(frame):
            global orderChangeData
            orderChangeData = frame

        # Act
        self.broker.setup_callbacks(None, order_change_callback, None)
        self.broker.sell_limit_order(sell_command)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(len(self.broker.sell_order_list), 1, "Sell order list should be 1 because sell is not fulfilled")
        self.assertNotEqual(len(self.broker.shares_owned_list), 0, "shares owned list should not be empty because nothing was sold")
        self.assertEqual(self.broker.working_currency, self.starting_currency, "Working currency remain unchanged")
        self.assertNotEqual(orderChangeData.order_status, OrderStatus.FILLED, "Sell Limit Order change data should not be filled")

    def test_sell_limit_order_filled_should_update_information(self):
        # Arrange
        self.broker.shares_owned_list.append(OwnedStock(block_id=0, ticker=self.ticker_mock, price=100, num_shares=5))
        self.broker.order_id_tracker = 1
        
        sell_qty = 5
        sell_command = OrderCommand(ticker=self.ticker_mock, price=99, quantity=sell_qty)

        global orderChangeData
        orderChangeData = OrderChangeData()
        def order_change_callback(frame):
            global orderChangeData
            orderChangeData = frame

        # Act
        self.broker.setup_callbacks(None, order_change_callback, None)
        self.broker.sell_limit_order(sell_command)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(len(self.broker.sell_order_list), 0, "Sell order list should be empty after selling")
        self.assertEqual(len(self.broker.shares_owned_list), 0, "shares owned list be empty")
        self.assertGreater(self.broker.working_currency, self.starting_currency, "Working currency should increase after selling")
        self.assertEqual(orderChangeData.order_status, OrderStatus.FILLED, "Sell Limit Order change data should be filled")

    def test_sell_more_than_owned_quantity_should_not_sell(self):
        """
        We have 5 qty and we try to sell 6
        It should fail
        """
        # Arrange
        self.broker.shares_owned_list.append(OwnedStock(block_id=0, ticker=self.ticker_mock, price=100, num_shares=5))
        self.broker.order_id_tracker = 1
        
        sell_qty = 6
        sell_command = OrderCommand(ticker=self.ticker_mock, quantity=sell_qty)

        # Act
        self.broker.sell_market_order(sell_command)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(len(self.broker.sell_order_list), 0, "Sell order should not even be placed")
        self.assertEqual(self.broker.shares_owned_list[0].num_shares, 5)
        self.assertEqual(self.broker.working_currency, self.starting_currency)

    # ------------------------ END MARKET & LIMIT TESTS ----------------------- #

    def test_working_currency(self):
        # Arrange
        self.broker.working_currency = 100
        self.broker.toggle_fees = False
        self.broker.set_current_price(self.ticker_mock, 10)
        buy_order = OrderCommand(ticker = self.ticker_mock, price = 10, quantity=10)

        # Act
        self.broker.buy_market_order(buy_order)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(self.broker.working_currency, 0)

    def test_buy_leverage_order(self):
        """
        We have $100
        Buy 50 qty @ 10 (Total $500)
        Asset size should be $100, money owed to broker $400
        """
        # Arrange
        self.broker.working_currency = 100
        self.broker.toggle_margin = True
        self.broker.toggle_fees = False
        self.broker.set_current_price(self.ticker_mock, 10)
        buy_order = OrderCommand(ticker = self.ticker_mock, price = 10, quantity=50)

        # Act
        self.broker.buy_market_order(buy_order)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(self.broker.get_ticker_asset_value(self.ticker_mock), 500)
        self.assertEqual(self.broker.money_owed_to_broker, 400.0)

    def test_buy_multiple_leverage_orders(self):
        """
        We have $100
        Buy 20x$10, cost $200
        Buy 15x$10, cost $150
        We should owe $250
        """
        # Arrange
        self.broker.working_currency = 100
        self.broker.toggle_fees = False
        self.broker.toggle_margin = True
        self.broker.set_current_price(self.ticker_mock, 10)
        buy_order = OrderCommand(ticker = self.ticker_mock, quantity=20)
        buy_order2 = OrderCommand(ticker = self.ticker_mock, quantity=15)

        # Act
        self.broker.buy_market_order(buy_order)
        self.broker.buy_market_order(buy_order2)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(self.broker.get_ticker_asset_value(self.ticker_mock), 350)
        self.assertEqual(self.broker.money_owed_to_broker, 250)

    def test_sell_leverage_order(self):
        """
        We have $100, buy 20x$10 at 200, we owe $100
        We sell 20x$14, that's 280, but we should only receive 180 as we payback $100 to broker
        """
        # Arrange
        self.broker.working_currency = 100
        self.broker.toggle_margin = True
        self.broker.toggle_fees = False
        self.broker.set_current_price(self.ticker_mock, 10)
        buy_order = OrderCommand(ticker = self.ticker_mock, price = 10, quantity=20)
        sell_order = OrderCommand(ticker = self.ticker_mock, quantity=20)

        # Act
        self.broker.buy_market_order(buy_order)
        self.broker.fill_orders()

        self.broker.set_current_price(self.ticker_mock, 14)
        self.broker.sell_market_order(sell_order)
        self.broker.fill_orders()

        # Assert
        self.assertEqual(self.broker.working_currency, 180)
        self.assertEqual(self.broker.money_owed_to_broker, 0)

    def test_average_price_of_owned_stock_is_correct(self):
        """
        buy 5 qty @100, then buy 3 qty @150
        average price of the stock should be 118.75
        """
        #Arrange
        self.broker.working_currency = 10000
        self.broker.toggle_fees = False
        
        first_buy = OrderCommand(ticker=self.ticker_mock, price=100,quantity=5)
        second_buy = OrderCommand(ticker=self.ticker_mock, price=150, quantity=3)

        #Act
        self.broker.set_current_price(self.ticker_mock, 100)
        self.broker.buy_market_order(first_buy)
        self.broker.fill_orders()
        self.broker.set_current_price(self.ticker_mock, 150)
        self.broker.buy_market_order(second_buy)
        self.broker.fill_orders()

        #Assert
        self.assertEqual(self.broker.shares_owned_list[0].num_shares, 8)
        self.assertEqual(self.broker.shares_owned_list[0].avg_price, 118.75)

    def test_force_liquidate(self):
        """
        We have $50
        Buy 50 qty @ 10 (Total $500) @ 10x Leverage
        Asset size should be $500, money owed to broker $450
        Price drops to $9, position size = 50 qty * $9 = $450, and we owe broker $450, force liquidate

        """
        # Arrange
        self.broker.working_currency = 50
        self.broker.toggle_fees = False
        self.broker.toggle_margin = True
        self.broker.set_current_price(self.ticker_mock, 10)
        buy_order = OrderCommand(ticker = self.ticker_mock, quantity=50)

        # Act
        self.broker.buy_market_order(buy_order)
        self.broker.fill_orders()

        self.broker.set_current_price(ticker=self.ticker_mock, price=9.1)
        self.broker.check_force_liquidate()

        self.assertEqual(self.broker.money_owed_to_broker, 450)

        self.broker.set_current_price(ticker=self.ticker_mock, price=9.0)
        self.broker.check_force_liquidate()

        # Assert
        self.assertEqual(self.broker.working_currency, 0)
        self.assertEqual(self.broker.money_owed_to_broker, 0)

if __name__ == '__main__':
    unittest.main()