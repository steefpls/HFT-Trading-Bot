from irori.common import *
from irori import strategyBase
from irori.stats import *

class Template(strategyBase.StrategyBase):
    
    # Date time is not initialized here. Use this to set up any custom objects or variables
    # Super class init method should be called to initialize the ticker and mediator class
    def init(self):
        super().init()

        # mandatory call to assign ticker list
        self.tickers.tickerList = ["NVDA"]

    # Calls when strategy is ready to be used
    # Super class start method should be called to set up the broker within mediator
    # This is called once after init with essential variables have been set up
    def start(self):
        super().start()
        pass

    # Calls 5 minutes before market opens
    def intraday_start(self):
        pass

    # Calls when market opens
    def day_start(self):
        pass

    # Calls when market closes
    def day_end(self):
        pass

    # Calls when tick is sent
    def on_tick_changed(self, frame: TickChangeData):
        pass

    # Calls when any order is updated
    def on_order_changed(self, frame: strategyBase.OrderChangeData):
        pass

    # Skips the remaining day for backtesting
    def skip(self):
        pass

    # Calls when strategy is stopped
    def stop(self):
        pass