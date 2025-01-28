import irori
import irori.Indicator_Realtime
from irori.common import *
from irori import strategyBase

class StrategyTimeBased(strategyBase.StrategyBase):

    def init(self):
        super().init()

        # config = common.open_config_file(irori_constants.STRATEGY_EXAMPLE)
        self.tickers.tickerList = ["NVDA"]

        self.is_initialized_successfully = True

        self.bought = False
        self.sold = False
        self.opening_price = 0.0
        self.closing_price = 0.0
        self.last_tick_date : datetime = datetime.now()
        self.buy_strategy = True

        print("Time strat init")

    def start(self):
        super().start()
        print("Time strat start")

    def stop(self):
        super().stop()
        print("Time strat stop")

    def day_start(self):
        """
        1 tick will be processed before day_start should be called
        """
        super().day_start()
        print("Time strat day start")

        self.tick_count = 0

        self.day_started = True
        self.bought = False
        self.sold = False
        self.opening_price = 0.0
        self.closing_price = 0.0
        self.sell_time = self.last_tick_date + timedelta(minutes=30)
        self.gradient = 0.0

        # self.mediator.backtest_obj.working_currency = 100000
        # self.mediator.stats.starting_funds = self.mediator.backtest_obj.working_currency

        # 1 tick will be processed before day start, so self.last_tick_date will be the backtest data's date
        # print(f'Last tick date {self.last_tick_date}')
        self.ri = irori.Indicator_Realtime.Indicator_Realtime("NVDA", False, self.last_tick_date)
        self.closing_price = self.ri.previous_day.get_close()

    def day_end(self):
        super().day_end()
        self.day_started = False

    def is_positive_gradient(self, price):
        opening_price = price
        self.gradient = opening_price - self.closing_price
        # print(f"Closing {self.closing_price} Opening {self.opening_price} Diff {self.gradient}")
        return self.gradient > 0

    def on_tick_changed(self, frame: TickChangeData):
        tick_time : datetime = frame.time
        self.last_tick_date = tick_time

        if not self.is_backtest_skipped or not self.day_started:
            return
        
        if not self.bought:
            up = self.is_positive_gradient(frame.price)
            if up:
                self.buy_strategy = False
            else:
                self.buy_strategy = True

            buy_order_command = OrderCommand(ticker = self.tickers.tickerList[0], quantity=50)
            if self.buy_strategy:
                # self.mediator.buy_market_order(buy_market_order_command=buy_order_command)
                self.mediator.buy_market_order(buy_order_command)
            else:
                """
                Else short strategy
                """
                self.mediator.short_buy_market_order(buy_order_command)

            self.bought_time = tick_time
            self.sell_time = tick_time + timedelta(minutes=30)
            self.bought = True

        if self.bought and not self.sold and self.sell_time < tick_time:
            sell_command = OrderCommand(ticker = self.tickers.tickerList[0], quantity=50)
            if self.buy_strategy:
                # self.mediator.sell_market_order(sell_command)
                self.mediator.sell_market_order(sell_command)
            else:
                self.mediator.short_sell_market_order(sell_command)

            self.sold = True
            self.stop()

    def on_order_changed(self, frame: strategyBase.OrderChangeData):
        print(f'Order change data {frame.orderID} {frame.action} {frame.order_status}')

        # # End after we buy back after 30min
        # if frame.action == 'BUY' and frame.order_status == OrderStatus.FILLED and frame.is_short:
        #     print("Terminating strategy as it is done")
        #     # print(f"End monies {self.mediator.query_account_information(AccountQuery(broker=self.mediator.selected_broker))}")
            




        