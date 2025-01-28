
import unittest
from irori.BrokerBase import BrokerBase
from irori.Broker_YFinance import *
import pandas as pd

class YFinanceBrokerTests(unittest.TestCase):

    def setUp(self):
        self.broker = YFinanceBroker()
        self.broker.working_currency = 1000
        self.ticker = 'x'
        self.ticker2 = 'y'

        data = [['2024-01-02', 100, 120, 80, 90, 100, 500000]]
        self.df: pd.DataFrame = pd.DataFrame(data, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'])

        data2 = [['2024-01-02', 10, 12, 8, 9, 10, 500000]]
        self.df2: pd.DataFrame = pd.DataFrame(data2, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'])

        self.broker.new_day(datetime.now(), self.ticker, self.df.iloc[0])
        self.broker.new_day(datetime.now(), self.ticker2, self.df2.iloc[0])

    def test_place_buy_order_adds_to_buy_order_list(self):
        # Arrange
        quantity_to_buy = 1
        order = OrderCommand(self.ticker, quantity=quantity_to_buy)
        order2 = OrderCommand(self.ticker2, quantity=quantity_to_buy)

        # Act
        self.broker.buy_market_order(order)
        self.broker.buy_market_order(order2)

        # Assert
        self.assertEqual(len(self.broker.buy_order_list), 2)
        self.assertEqual(self.broker.buy_order_list[0].limit_price, self.df.iloc[0]['Open'])
        self.assertEqual(self.broker.buy_order_list[0].num_shares, quantity_to_buy)

        self.assertEqual(self.broker.buy_order_list[1].limit_price, self.df2.iloc[0]['Open'])
        self.assertEqual(self.broker.buy_order_list[1].num_shares, quantity_to_buy)

    def test_place_buy_order_fill_adds_to_owned_stock(self):
        # Arrange
        quantity_to_buy = 1
        order = OrderCommand(self.ticker, quantity=quantity_to_buy)
        order2 = OrderCommand(self.ticker2, quantity=quantity_to_buy)

        # Act
        self.broker.buy_market_order(order)
        self.broker.buy_market_order(order2)

        self.broker.process_day_start()

        # Assert
        self.assertEqual(len(self.broker.buy_order_list), 0)
        self.assertEqual(len(self.broker.shares_owned_list), 2)

        ticker1_owned_stock = self.broker.get_owned_stock(self.ticker)
        ticker2_owned_stock = self.broker.get_owned_stock(self.ticker2)

        self.assertEqual(ticker1_owned_stock.avg_price, self.df.iloc[0]['Open'])
        self.assertEqual(ticker1_owned_stock.num_shares, quantity_to_buy)

        self.assertEqual(ticker2_owned_stock.avg_price, self.df2.iloc[0]['Open'])
        self.assertEqual(ticker2_owned_stock.num_shares, quantity_to_buy)

    def test_place_multiple_buy_orders_adds_to_owned_stock_quantity(self):
        """
        Buy ticker 1 twice
        """
        # Arrange
        quantity_to_buy = 1
        order = OrderCommand(self.ticker, quantity=quantity_to_buy)

        # Act
        self.broker.buy_market_order(order)
        self.broker.buy_market_order(order)

        self.broker.process_day_start()

        # Assert
        self.assertEqual(self.broker.get_owned_stock(self.ticker).num_shares, 2)

    def test_buy_limit_order_price_not_met_will_not_fill_order(self):
        """
        Opening price for ticker 1 is 100, we buy at 90
        """
        # Arrange
        quantity_to_buy = 1
        order = OrderCommand(self.ticker, quantity=quantity_to_buy, price=90)

        # Act
        self.broker.buy_limit_order(order)

        self.broker.process_day_start()

        # Assert
        self.assertEqual(self.broker.get_owned_stock(self.ticker).num_shares, 0)
        self.assertEqual(len(self.broker.buy_order_list), 1)

    def test_buy_limit_order_fulfilled_will_fill_order_at_best_price(self):
        """
        Opening price for ticker 1 is 100, we buy at 150
        We should buy at 100
        """
        # Arrange
        quantity_to_buy = 1
        order = OrderCommand(self.ticker, quantity=quantity_to_buy, price=150)

        # Act
        self.broker.buy_limit_order(order)

        self.broker.process_day_start()

        # Assert
        self.assertEqual(self.broker.get_owned_stock(self.ticker).num_shares, 1)
        self.assertEqual(self.broker.get_owned_stock(self.ticker).avg_price, 100)
        self.assertEqual(self.broker.working_currency, 900)

    def test_buy_limit_order_fulfilled_during_day_will_fill_order_at_limit_price(self):
        """
        Opening 100
        Lowest 80
        Closing 90
        If we buy limit order at 85, it should fulfill somewhere during the day because lowest went to 80
        Note: This is processed at day end
        """
        # Arrange
        quantity_to_buy = 1
        order = OrderCommand(self.ticker, quantity=quantity_to_buy, price=85)

        # Act
        self.broker.buy_limit_order(order)
        self.broker.process_day_start()

        self.broker.process_day_end()

        # Assert
        self.assertEqual(self.broker.get_owned_stock(self.ticker).num_shares, 1)
        self.assertEqual(self.broker.get_owned_stock(self.ticker).avg_price, 85)
        self.assertEqual(self.broker.working_currency, 915)

    def test_sell_limit_order_placed_will_add_to_order_list(self):
        # Arrange
        quantity_to_sell = 1
        buy_order = OrderCommand(self.ticker, quantity=1)
        sell_order = OrderCommand(self.ticker, quantity=quantity_to_sell, price=101)

        # Act
        self.broker.buy_market_order(buy_order)
        self.broker.process_intraday_start()

        order_id = self.broker.sell_limit_order(sell_order)
        sell_order = self.broker.get_order(order_id)

        # Assert
        self.assertEqual(len(self.broker.sell_order_list), 1)
        self.assertEqual(sell_order.num_shares, quantity_to_sell)
        self.assertEqual(sell_order.limit_price, 101)

    def test_sell_limit_order_filled_during_daystart_dayend(self):
        """
        Buy @ Open, $100
        Sell at 101, fail
        In between dayend and daystart, high is 120
        When processing day end, it will see that the price is hit as high is larger than limit order price,
        fill at limit order price $101
        Final working currency $1000-$100+$101 = $1001
        """
        # Arrange
        quantity_to_sell = 1
        buy_order = OrderCommand(self.ticker, quantity=1)
        sell_order = OrderCommand(self.ticker, quantity=quantity_to_sell, price=101)

        # Act
        self.broker.buy_market_order(buy_order)
        self.broker.process_intraday_start()

        order_id = self.broker.sell_limit_order(sell_order)
        sell_order = self.broker.get_order(order_id)

        self.broker.process_day_start()
        self.broker.process_day_end()

        # Assert
        self.assertEqual(len(self.broker.sell_order_list), 0)
        owned_stock = self.broker.get_owned_stock(self.ticker)
        self.assertEqual(owned_stock.num_shares, 0)
        self.assertEqual(self.broker.working_currency, 1001)

    def test_expired_orders_should_be_cancelled_at_end_of_day(self):
        # Arrange
        buy_order = OrderCommand(self.ticker, quantity=1, price=1, time_in_force=TimeInForce.DAY)

        # Act
        self.broker.buy_limit_order(buy_order)
        self.broker.process_intraday_start()

        self.broker.process_day_start()
        self.broker.process_day_end()

        # Assert
        self.assertEqual(len(self.broker.buy_order_list), 0)
        self.assertEqual(len(self.broker.shares_owned_list), 0)
        

if __name__ == '__main__':
    unittest.main()