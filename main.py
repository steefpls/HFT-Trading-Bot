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

import irori.irori_constants as irori_constants
from irori.common import *
from irori.Backtester import Backtester
from irori.Strategy_Library import *
from irori.strategyBase import *
import threading
import logging
import io

if __name__ == '__main__':
    log_stream = io.StringIO()

    # Configure the root logger or specific logger
    logging.basicConfig(
        level=logging.ERROR,
        stream=log_stream,  # Redirect logs to the stream
        format='%(levelname)s:%(name)s:%(message)s'  # Format similar to your output
    )

    # This is the function that will be run every 1 second
    async def repeat_task(stop_event:threading.Event, strategy: StrategyBase):
        while not stop_event.is_set():
            await strategy.async_task()
            await asyncio.sleep(1)  # Wait 1 seconds before the next run
            log_contents = log_stream.getvalue()
            if ("kick out" in log_contents):
                raise_error()

    # This function will start the event loop in a separate thread
    def run_event_loop(stop_event:threading.Event, strategy: StrategyBase):
        asyncio.run(repeat_task(stop_event, strategy))

    try:
        jPropertyConfigs : Properties = open_config_file(irori_constants.GLOBAL_CONFIG_FILE)
        broker = str_to_enum(Broker, jPropertyConfigs.get("BrokerName").data.upper())
        strategy = get_strategy(jPropertyConfigs.get("StrategyName").data.lower())
        
        init_time(jPropertyConfigs)
        stop_event = threading.Event()  # Create a stop event

        utc_date_now = datetime.now(timezone.utc)
        if (broker != Broker.BACKTEST and broker != Broker.BT_DAY):
            strategy.init()
            strategy.mediator.init(broker)
            strategy.mediator.set_up_discord(jPropertyConfigs.get("Discord_Notify").data.lower() == "true")
            strategy.mediator.setup_callbacks(strategy.on_tick_changed, strategy.on_order_changed, broker, strategy.tickers)
            strategy.init_datetime(utc_date_now)
            strategy.start()
            
            # Live trading
            while True:
                print(f"sgtime: {datetime.now().strftime('%m-%d %I:%M %p')}")
                market_open = is_market_open()
                utc_date_now = datetime.now(timezone.utc)
                strategy.init_datetime(utc_date_now)

                if not market_open:
                    time_until_open = time_until_market_open()

                    # Intraday start is called 30mins before market open, If market open withins 30mins, call intraday_start
                    # Else, sleep until 30mins before market open and call intraday_start by restarting
                    # 1800 seconds, 30mins
                    if (time_until_open < 1799):
                        print(f"Intraday start {datetime.now().strftime('%m-%d %I:%M %p')}")
                        strategy.intraday_start()
                    else:
                        sleep_irori_bot(time_until_open - 1800)
                        raise TypeError("Irori restarting to set up callbacks")

                    # Sleep until market opens
                    time_until_open = time_until_market_open()
                    sleep_irori_bot(time_until_open)

                    print(f"Day start {datetime.now().strftime('%m-%d %I:%M %p')}")
                    strategy.day_start()
                
                loop_thread = threading.Thread(target=run_event_loop, args=(stop_event, strategy))
                loop_thread.start()

                print(f"Irori is live {datetime.now().strftime('%m-%d %I:%M %p')}")
                time_until_market_closes = time_until_market_close()
                print(f"Time until market closes: {time_until_market_closes}")

                sleep_irori_bot(time_until_market_closes)

                print(f"Day end at time {datetime.now().strftime('%m-%d %I:%M %p')}")
                strategy.day_end()

                # Post sleep because if we continue the while loop immediately, time_until_open will be negative 
                # because time now is same as market closing time
                print("Irori bot sleep for cleanup")
                stop_event.set()
                loop_thread.join()
                sleep_irori_bot(46800)
        else:
            backtester:Backtester = Backtester()
            global_config = properties_to_dict(jPropertyConfigs)
            backtester.setup_strategy(strategy, global_config)

            brokerForFees = str_to_enum(Broker, jPropertyConfigs.get("BrokerForFees").data.upper())

            backtester.strategy.mediator.init(broker)
            backtester.strategy.mediator.set_working_currency(float(global_config["Funds"].data))

            strategy.mediator.setup_callbacks(strategy.on_tick_changed, strategy.on_order_changed, broker, strategy.tickers)
            backtester.strategy.mediator.setup_backtest_broker(brokerForFees)
            
            backtester.start()
    except Exception as e:
        if (not strategy.is_running_on_backtesting):
            stop_event.set()
            strategy.on_exit()
            if str(e) != "Irori restarting to set up callbacks":
                if str(e) != "Error raised, Sleep Interrupted":
                    strategy.mediator.discord_notify("Error", str(e))
                else:
                    strategy.mediator.discord_notify("Restarting", "Low priority error, restarting", 1414354, False)
        raise_error()
        raise e