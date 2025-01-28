import unittest

from irori.Broker_Backtest import BacktestBroker
from irori.stats import IntradayStats, StrategyStats


class StatsTests(unittest.TestCase):
    
    def test_stats_accuracy(self):
        # avg_daily_return = 0.0011
        # sd = 0.0022
        sharp_ratio_result = 0.286

        recorded_days = []
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.002))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.001))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=-0.003))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.004))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.001))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=-0.002))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.003))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=-0.001))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.002))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.001))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.003))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=-0.001))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.002))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.001))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=-0.004))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.002))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.003))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=-0.002))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.001))
        recorded_days.append(IntradayStats(starting_funds=100, daily_returns=0.002))

        ss = StrategyStats(100)
        ss.recorded_days = recorded_days
        ss.calculate_stats()

        self.assertAlmostEqual(ss.sharpe_ratio, sharp_ratio_result, 2, "Sharpe ratio should be similar")

    def test_broker_fees(self):
        broker = BacktestBroker()
        broker.shortToggle = True

        stock_price = 600
        num_shares = 50
        short_open_fees = broker.calculate_fees_moomoo(stock_price, num_shares, False)
        buy_fees = broker.calculate_fees_moomoo(stock_price, num_shares, True)

        stock_price = 599
        short_close_fees = broker.calculate_fees_moomoo(stock_price, num_shares, True)
        sell_fees = broker.calculate_fees_moomoo(stock_price, num_shares, False)

        self.assertNotEqual(buy_fees + sell_fees, short_open_fees + short_close_fees, "Fees should not be equal")
        self.assertAlmostEqual(buy_fees + sell_fees, short_open_fees + short_close_fees, 2, "Fees should be near equal")
        self.assertGreaterEqual(short_open_fees + short_close_fees, buy_fees + sell_fees, "Short fees should be higher")

if __name__ == '__main__':
    unittest.main()