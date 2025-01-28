# import unittest

# from irori import strategyBase
# import irori.common as irori_common
# from irori.Broker_Moomoo import *
# from irori.mediator import *

# class MooMooBrokerTests(unittest.TestCase):
#     @classmethod
#     def setUpClass(cls):
#         cls.tickers = Tickers()
#         cls.tickers.tickerList = ["NVDA"]
#         cls.markets = ["US"]
#         cls.mediator = Mediator()
#         cls.mediator.init(Broker.MOOMOO)
#         cls.mediator.start()
#         cls.order_change_data = []
#         cls.ticker_symbol = cls.markets[0] + "." + cls.tickers.tickerList[0]

#     def on_order_change_data_callback(self, frame: strategyBase.OrderChangeData):
#         self.order_change_data.append(frame)

#     # Make sure our irori order returned is same as moomoo order
#     def test_get_order_should_return_corresponding_irori_order_object(self):
#         # Arrange
#         self.mediator.setup_callbacks(tick_event=None, order_event=self.on_order_change_data_callback, broker=Broker.MOOMOO, tickers=self.tickers)
#         limit_price = 1
#         buy_qty = 5
#         ticker = self.tickers.tickerList[0]

#         buy_limit_order_command = OrderCommand(ticker=ticker, quantity=buy_qty, price=limit_price)

#         # Act
#         order_id = self.mediator.buy_limit_order(buy_limit_order_command)

#         moomoo_order = self.mediator.get_raw_order(id=order_id)
#         self.assertIsNotNone(moomoo_order)

#         irori_order_data : irori_common.Order = self.mediator.get_order(id=order_id)

#         self.assertNotEqual(len(self.order_change_data), 0, "Order change data should be called")

#         # Assert
#         self.assertEqual(irori_order_data.total_quantity, moomoo_order['qty'][0], "Get Order qty should be same as buy commmand")
#         self.assertEqual(irori_order_data.ticker, moomoo_order['code'][0], "Get Order ticker should be same as buy command")
#         self.assertEqual(irori_order_data.action, 'BUY', "Get order action should be BUY action")
#         self.assertEqual(irori_order_data.order_id, moomoo_order['order_id'][0], "Get order id should have same id as moomoo order id")
#         self.assertEqual(irori_order_data.order_type, irori_common.OrderType.LIMIT, "Get order ordertype should have limit order type")
#         self.assertEqual(moomoo_order['order_type'][0], OrderType.NORMAL, "Get order ordertype should have limit order type")
#         self.assertEqual(moomoo_order['trd_side'][0], TrdSide.BUY, "Get order ordertype should have limit order type")

#     def test_buy_market_order_should_correspond_with_broker(self):
#         # Arrange
#         self.mediator.setup_callbacks(tick_event=None, order_event=self.on_order_change_data_callback, broker=Broker.MOOMOO, tickers=self.tickers)
#         buy_qty = 5
#         ticker = self.tickers.tickerList[0]
#         buy_market_order_command = OrderCommand(ticker=ticker, quantity=buy_qty)

#         # Act
#         order_id = self.mediator.buy_market_order(buy_market_order_command)

#         moomoo_order = self.mediator.get_raw_order(id=order_id)
#         self.assertIsNotNone(moomoo_order)

#         irori_order_data : irori_common.Order = self.mediator.get_order(id=order_id)

#         self.assertNotEqual(len(self.order_change_data), 0, "Order change data should be called")

#         # Assert
#         self.assertEqual(irori_order_data.total_quantity, moomoo_order['qty'][0], "Get Order qty should be same as buy commmand")
#         self.assertEqual(irori_order_data.ticker, moomoo_order['code'][0], "Get Order ticker should be same as buy command")
#         self.assertEqual(irori_order_data.action, 'BUY', "Get order action should be BUY action")
#         self.assertEqual(irori_order_data.order_id, moomoo_order['order_id'][0], "Get order id should have same id as moomoo order id")
#         self.assertEqual(irori_order_data.order_type, irori_common.OrderType.MARKET, "Get order ordertype should have limit order type")
#         self.assertEqual(moomoo_order['order_type'][0], OrderType.MARKET, "Get order ordertype should have limit order type")
#         self.assertEqual(moomoo_order['trd_side'][0], TrdSide.BUY, "Get order ordertype should have limit order type")

#     # def test_buy_limit_order_should_correspond_with_broker(self):
#     #     self.mediator.setup_callbacks(tick_event=None, order_event=self.on_order_change_data_callback, broker=Broker.MOOMOO, tickers=self.tickers, markets=self.markets)
#     #     limit_price = 1
#     #     buy_qty = 5
#     #     ticker = self.tickers.tickerList[0]

#     #     buy_limit_order_command = OrderCommand(ticker=ticker, broker=Broker.MOOMOO, quantity=buy_qty, price=limit_price)

#     #     order_id = self.mediator.buy_limit_order(buy_limit_order_command)

#     #     order_data : irori_common.Order = self.mediator.get_order(id=order_id, broker=Broker.MOOMOO)

#     #     self.assertNotEqual(len(self.order_change_data), 0, "Order change data should be called")
#     #     self.assertEqual(order_data.quantity, buy_qty, "Order placed qty should be same as buy commmand")
#     #     self.assertEqual(order_data.price, limit_price, "Order limit price placed should be same as buy command")
#     #     self.assertEqual(order_data.ticker, self.ticker_symbol, "Order placed ticker should be same as buy command")

#     # def test_sell_market_order_should_correspond_with_broker(self):
#     #     self.mediator.setup_callbacks(tick_event=None, order_event=self.on_order_change_data_callback, broker=Broker.MOOMOO, tickers=self.tickers, markets=self.markets)
#     #     buy_qty = 5
#     #     ticker = self.tickers.tickerList[0]
#     #     buy_market_order_command = OrderCommand(ticker=ticker, broker=Broker.MOOMOO, quantity=buy_qty)

#     #     order_id = self.mediator.sell_market_order(buy_market_order_command)

#     #     order_data : irori_common.Order = self.mediator.get_order(id=order_id, broker=Broker.MOOMOO)

#     #     self.assertNotEqual(len(self.order_change_data), 0, "Order change data should be called")
#     #     self.assertEqual(order_data.quantity, buy_qty, "Order placed qty should be same as buy commmand")
#     #     self.assertEqual(order_data.ticker, self.ticker_symbol, "Order placed ticker should be same as buy command")

#     def tearDown(self) -> None:
#         self.__class__.order_change_data = []
#         return super().tearDown()

#     @classmethod
#     def tearDownClass(cls) -> None:
#         cls.mediator.stop()
#         return super().tearDownClass()

# if __name__ == '__main__':
#     unittest.main()


import unittest
from irori import strategyBase
import irori.common as irori_common
from irori.Broker_Tiger import TigerBroker  # Assuming your TigerBroker class is in Broker_Tiger module
from irori.mediator import Mediator
from irori.common import OrderCommand, CancelOrderCommand, Tickers, Broker

class TigerBrokerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tickers = Tickers()
        cls.tickers.tickerList = ["NVDA"]
        cls.markets = ["US"]
        cls.mediator = Mediator()
        cls.mediator.init(Broker.TIGER)
        cls.mediator.start()
        cls.order_change_data = []
        cls.ticker_symbol = cls.markets[0] + "." + cls.tickers.tickerList[0]

    def on_order_change_data_callback(self, frame: strategyBase.OrderChangeData):
        self.order_change_data.append(frame)

    def test_cancel_order_should_return_success(self):
        # Arrange
        self.mediator.setup_callbacks(tick_event=None, order_event=self.on_order_change_data_callback, broker=Broker.TIGER, tickers=self.tickers)
        limit_price = 1
        buy_qty = 5
        ticker = self.tickers.tickerList[0]

        buy_limit_order_command = OrderCommand(ticker=ticker, quantity=buy_qty, price=limit_price)
        order_id = self.mediator.buy_limit_order(buy_limit_order_command)

        cancel_order_command = CancelOrderCommand(orderID=order_id)

        # Act
        is_cancelled = self.mediator.cancel_order(cancel_order_command)

        # Assert
        self.assertTrue(is_cancelled, "Order should be cancelled successfully")

        tiger_order = self.mediator.get_raw_order(id=order_id)
        self.assertIsNone(tiger_order, "Cancelled order should not be retrievable")

    def tearDown(self) -> None:
        self.__class__.order_change_data = []
        return super().tearDown()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mediator.stop()
        return super().tearDownClass()

if __name__ == '__main__':
    unittest.main()

