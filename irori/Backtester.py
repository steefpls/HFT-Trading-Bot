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
from irori.common import *
import irori.Data_Visualisation as dv
from datetime import datetime
import os
import time
from datetime import datetime,timedelta
from findatapy.market import Market, MarketDataRequest, MarketDataGenerator
from irori.stats import StrategyStats, DailyStockStat
from irori.strategyBase import StrategyBase
from typing import Union
import numpy as np
import yfinance as yf
import pandas as pd
import gc
from irori.Options_Backtester_Polygon import getParquetList
from irori.Index_Downloader_ThetaData import getDFThetaData
import pytz
#from memory_profiler import profile

class Backtester:
    def setup_strategy(self, strategy:StrategyBase, globalConfig:dict):
        self.strategy = strategy
        self.global_config = globalConfig
        self.strategy.init()

    def start(self):
        input_ticker,input_startdate,input_finishdate = self.get_backtest_input()
        backtest_master:Backtest_MasterData = self.init(input_ticker, input_startdate, input_finishdate)
        is_yfin_broker = self.strategy.mediator.selected_broker == Broker.BT_DAY

        if not is_yfin_broker:
            self.verify_data(backtest_master)
        self.main(backtest_master)

    def init(self, tickers:list[str], startdate1, finishdate1):
        self.file_dir = os.path.dirname(os.path.realpath(__file__))
        print(f"Retrieving trading days between {startdate1} to {finishdate1} (exlusive) from NYSE...")

        #error handling if dates are invalid
        try:
            start_day, start_month, start_year = startdate1.split()
            finish_day, finish_month, finish_year = finishdate1.split()
        except ValueError:
            print("Incorrect data format, should be DD Month YYYY (1 feb 2024). Exiting...")
            exit()
        
        start_day, start_month, start_year = startdate1.split()
        finish_day, finish_month, finish_year = finishdate1.split()

        #month to number
        start_month = datetime.strptime(start_month, "%b").month
        finish_month = datetime.strptime(finish_month, "%b").month

        #Date Format: 2024-02-01
        startdate = f'{start_year}-{start_month}-{start_day}'
        finishdate = f'{finish_year}-{finish_month}-{finish_day}'

        #get num of days between start and finish date
        start = datetime.strptime(startdate, "%Y-%m-%d")
        finish = datetime.strptime(finishdate, "%Y-%m-%d")

        self.dataLocation = ((self.file_dir) + r"\BacktestData")
        #create folder if it doesn't exist
        if not os.path.exists(self.dataLocation):
            print(f"No {ticker} folder exists. Creating folder at {self.dataLocation}")
            os.makedirs(self.dataLocation)

        # Delete old sessions if enabled
        if self.global_config["DeleteOldSessions"].data == 'true':
            session_path = f"{self.file_dir}\\Session"
            print(f"Deleting old sessions in {session_path}....")
            for entry in os.listdir(session_path):
                entry_path = os.path.join(session_path, entry)
                import shutil
                if os.path.isdir(entry_path):  # Check if it's a directory
                    try:
                        shutil.rmtree(entry_path)
                    except PermissionError as e:
                        print(f"Could not delete {entry_path}: {e}")
                    except Exception as e:
                        print(f"Error deleting {entry_path}: {e}")
                elif os.path.isfile(entry_path):
                    try:
                        os.remove(entry_path)
                    except PermissionError as e:
                        print(f"Could not delete {entry_path}: {e}")
                    except Exception as e:
                        print(f"Error deleting {entry_path}: {e}")

        self.tick_resolution = int(self.global_config["TickResolution"].data)
        self.load_time = time.time()
        backtest_master:Backtest_MasterData = Backtest_MasterData()
        all_data:dict[str, pd.DataFrame] = {}
        day_list:list[datetime] =[]

        is_yfin_broker = self.strategy.mediator.selected_broker == Broker.BT_DAY

        # Download the entire range data for each ticker once
        for ticker in tickers:
            backtest_ticker = backtest_master.add_ticker(ticker)
            data:pd.DataFrame = yf.download(backtest_master.tickers[ticker].yfinance_ticker, start=startdate, end=finishdate, progress=False, auto_adjust=False)
            if not data.empty:
                all_data[ticker] = data
                if is_yfin_broker and backtest_ticker is not None:
                    backtest_ticker.yfinance_tick_data_df = data

        # Check for non-empty data for each date
        current_date = start
        current_date = current_date.replace(tzinfo=pytz.UTC)
        finish = finish.replace(tzinfo=pytz.UTC)
        while current_date <= finish:
            for ticker in tickers:
                if ticker in all_data:
                    data = all_data[ticker]
                    if current_date in data.index:
                        day_list.append(current_date)
                        break

            current_date += timedelta(1)

        # Fill in stock split data
        for ticker in backtest_master.tickers.keys():
            backtest_master.tickers[ticker].split_date = yf.Ticker(backtest_master.tickers[ticker].yfinance_ticker).splits

        # Fill in date
        for i in range(len(day_list)):
            backtest_master.add_date(day_list[i])

        del all_data
        gc.collect()
        time_taken = time.time() - self.load_time
        print(f"Found {len(day_list)} trading days. Time taken: {round(time_taken, 2)} seconds.")
        
        return backtest_master
    
    def verify_data(self, masterdata:Backtest_MasterData):
        self.dataLocation = ((self.file_dir) + r"\BacktestData\\")
        if not os.path.exists(self.dataLocation):
            print(f"No backtest folder exists. Creating folder at {self.dataLocation}")

        print("Verifying data...")
        market = Market(market_data_generator=MarketDataGenerator())
        # Suppress logging
        import logging
        logging.getLogger('findatapy.market.datavendorweb').setLevel(logging.ERROR)
        logging.getLogger('findatapy.market.marketdatagenerator').setLevel(logging.ERROR)
        logging.getLogger('findatapy.market.ioengine').setLevel(logging.ERROR)

        for date in masterdata.date_list:
            formatted_date = date.strftime("%Y-%m-%d")
            for ticker in masterdata.tickers.keys():
                if not os.path.exists(self.dataLocation + ticker + f'\{ticker}-{formatted_date}.parquet'):
                    if (ticker == 'SPX'):
                        # self.download_polygon_spx_data(formatted_date, self.file_dir)
                        self.download_thetadata_spx_data(formatted_date, self.file_dir)
                    else:
                        self.DownloadFile(ticker, self.file_dir, date, formatted_date, market)
        
        time_taken = time.time() - self.load_time
        print(f"Data prepared. Time taken: {round(time_taken, 2)} seconds.")
    
    def DownloadFile(self, ticker:str, file_dir:str, date_obj:datetime, formatted_date:str, market:Market)->bool:
        startdate = date_obj.strftime("%d %b %Y")
        finishdate = (date_obj + timedelta(days=1)).strftime("%d %b %Y")
        print(f"Downloading {ticker} data for {startdate}...")
        #check if ticker has IDX
        appendText = 'US'
        original_ticker = ticker
        if (ticker[-3:] == 'IDX'):
            ticker = ticker[:-3]
            appendText = 'IDXUSD'
        elif (ticker[-3:] == 'DKK'):
            ticker = ticker[:-3]
            appendText = 'DKDKK'
        elif (ticker[-3:] == 'SGD'):
            ticker = ticker[:-3]
            appendText = 'SGD'
        else:
            appendText = 'USUSD'
        #check if market is open
        md_request = MarketDataRequest(start_date= startdate,
                                finish_date=finishdate,
                                #get bid, ask data
                                fields=['bid', 'ask'],
                                vendor_fields=['bid', 'ask'],
                                freq='tick', data_source='dukascopy',
                                tickers=[ticker],
                                vendor_tickers=[(ticker+appendText)])
        df:pd.DataFrame = market.fetch_market(md_request)
        if df is None:
            empty_df = pd.DataFrame(columns=['Datetime', 'Price'])
            parquet_file_path = os.path.join(self.dataLocation, original_ticker, f'{original_ticker}-{startdate}.parquet')
            os.makedirs(os.path.dirname(parquet_file_path), exist_ok=True)
            empty_df.to_parquet(parquet_file_path)
            print(f"No {original_ticker} file for {startdate} by Dukascopy. Empty file saved to {parquet_file_path}")
            return False
        df = df/1000
        df.columns = ['Bid Price', 'Ask Price']
        df.index = df.index.astype(str)

        # Initialize previous prices for comparison
        previous_bidPrice = None
        previous_askPrice = None

        for index, row in df.iterrows():
            bidPrice = float(row['Bid Price'])
            askPrice = float(row['Ask Price'])

            if previous_bidPrice is None and previous_askPrice is None:
                # This is the first iteration, both are considered changed
                price = (bidPrice + askPrice) * 0.5
            else:
                bid_changed = bidPrice != previous_bidPrice
                ask_changed = askPrice != previous_askPrice

                if bid_changed and not ask_changed:
                    # Only bidPrice changed
                    price = bidPrice
                elif ask_changed and not bid_changed:
                    # Only askPrice changed
                    price = askPrice
                else:
                    # Both changed or none changed
                    price = (bidPrice + askPrice) * 0.5

            # Update the price in the result DataFrame
            df.at[index, 'Price'] = price

            # Update previous prices for the next iteration
            previous_bidPrice = bidPrice
            previous_askPrice = askPrice

        df = df.drop(columns=['Bid Price', 'Ask Price'])
        df.index.name = 'Datetime'  
        df = df.reset_index()  

        date_obj = datetime.strptime(startdate, "%d %b %Y")
        formatted_date = date_obj.strftime("%Y-%m-%d")

        # Save the DataFrame as a Pickle file
        parquet_file_path = os.path.join(file_dir, 'BacktestData', original_ticker, f'{original_ticker}-{formatted_date}.parquet')
        os.makedirs(os.path.dirname(parquet_file_path), exist_ok=True)
        df.to_parquet(parquet_file_path)

        print(f"File saved to {parquet_file_path}")
        return True
    
    def download_polygon_spx_data(self, formatted_date:str, file_dir:str)->bool:
        data_list:list = getParquetList("SPX", formatted_date)
        df = pd.DataFrame(data_list, columns=["Datetime", "Price"])
        parquet_file_path = os.path.join(file_dir, 'BacktestData', 'SPX', f'SPX-{formatted_date}.parquet')
        os.makedirs(os.path.dirname(parquet_file_path), exist_ok=True)
        df.to_parquet(parquet_file_path)

        return True
    
    def download_thetadata_spx_data(self, formatted_date:str, file_dir:str)->bool:
        df:pd.DataFrame = getDFThetaData("SPX", formatted_date)
        parquet_file_path = os.path.join(file_dir, 'BacktestData', 'SPX', f'SPX-{formatted_date}.parquet')
        os.makedirs(os.path.dirname(parquet_file_path), exist_ok=True)
        df.to_parquet(parquet_file_path)

        return True
        
    def get_backtest_input(self):
        ticker:str = self.global_config["Tickers"].data.upper()
        ticker_list = ticker.split(" ") #split by comma
        startdate1 = self.global_config["StartDate"].data
        finishdate1 = self.global_config["FinishDate"].data
        return (ticker_list, startdate1, finishdate1)
    #@profile
    def main(self, masterdata:Backtest_MasterData)->None:
        print(f"\n=== Starting Simulation for {len(masterdata.date_list)} Trading Days ===\n")
        self.strategy.set_backtest()
        self.strategy.init_datetime(masterdata.date_list[0])
        self.strategy.start()
        start_time = time.time()
        strategy_stats:StrategyStats = StrategyStats(self.strategy.mediator.get_account_information().gross_position_value)
        intraday_stat_list =[]
        dayNo:int = 0

        epoch = int(time.time())

        if self.strategy.mediator.selected_broker == Broker.BACKTEST:
            for date in masterdata.date_list:
                formatted_date = date.strftime("%Y-%m-%d")
                all_df:list[pd.DataFrame] = []
                for ticker, ticker_obj in masterdata.tickers.items():
                    df = pd.read_parquet(f"{self.dataLocation}\\{ticker}\\{ticker}-{formatted_date}.parquet", engine='pyarrow')
                    if not df.empty:
                        # Apply stock split
                        adjusted_df = masterdata.adjust_for_splits(ticker, df)
                        adjusted_df['Ticker'] = ticker
                        all_df.append(adjusted_df)
                        from irori.stats import DailyStockStat
                        ticker_obj.stock_stat_list.append(DailyStockStat(ticker, adjusted_df.iloc[0]['Price'], adjusted_df.iloc[-1]['Price'], adjusted_df['Price'].max(), adjusted_df['Price'].min()))
                    else:
                        ticker_obj.stock_stat_list.append(None)
                    
                # Combine and sort all dataframes for the date
                if len(all_df) == 0:
                    print(f"No data for {formatted_date}. Skipping...")
                    dayNo += 1
                    continue

                if self.tick_resolution > 1:
                    for i in range(len(all_df)):
                        df = all_df[i]
                        # Select every nth row based on tickResolution, keep first and last
                        trimmed_df = df.iloc[::self.tick_resolution, :]
                        if df.iloc[0].name != trimmed_df.iloc[0].name:  
                            trimmed_df = pd.concat([df.iloc[[0]], trimmed_df])
                        # Ensure the last row is included
                        if df.iloc[-1].name != trimmed_df.iloc[-1].name:  
                            trimmed_df = pd.concat([trimmed_df, df.iloc[[-1]]])
                        all_df[i] = trimmed_df.sort_index()

                combined_df = pd.concat(all_df)
                combined_df.sort_values(by='Datetime', inplace=True)

                # Process the day
                self.ProcessDay(dayNo, combined_df, masterdata, formatted_date, epoch, intraday_stat_list)
                dayNo += 1
        else:
            for date in masterdata.date_list:
                #print(f"Processing {date}...")
                self.ProcessDay_yFinance(dayNo, date, epoch, intraday_stat_list, masterdata)
                dayNo += 1
                # for ticker, ticker_obj in masterdata.tickers.items():
                #     ticker_day_data = ticker_obj.yfinance_tick_data_df.iloc[dayNo]
                #     self.ProcessDay_yFinance(dayNo, date, epoch, intraday_stat_list, ticker, ticker_day_data, ticker_obj)
                # dayNo += 1

        print("\nCrunching numbers...")
        for item in intraday_stat_list:
            strategy_stats.recorded_days.append(item)

        strategy_stats.calculate_stats(self.strategy.mediator.get_positions(), self.strategy.mediator.get_account_information().gross_position_value, self.strategy.mediator.returns if self.strategy.mediator.valid_sharpe else [])
        #print(strategy_stats)
        self.strategy.mediator.print_account_info()
        
        save_location = f"{self.file_dir}\\Session\\{epoch}-{self.global_config['StrategyName'].data}"
        print(f"Generating performance report...")
        dv.master_graph(intraday_stat_list, save_location, masterdata, strategy_stats.recorded_days[0].starting_gross_value, self.global_config['StrategyName'].data)
        dv.master_graph_log(intraday_stat_list, save_location, masterdata, strategy_stats.recorded_days[0].starting_gross_value, self.global_config['StrategyName'].data)
        strategy_stats.write_to_excel(save_location, epoch)
        
        print("================ End of Simulation ================")
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(elapsed_time, 60)
        print(f"Simulation time: {int(minutes)} min {round(seconds, 2)} sec")
        elapsed_time = time.time() - self.load_time
        minutes, seconds = divmod(elapsed_time, 60)
        print(f"Total time:      {int(minutes)} min {round(seconds, 2)} sec")
        print(f"Current time: {datetime.now().strftime('%I:%M:%S %p')}")

    def ProcessDay(self, dayNo: int, combined_df:pd.DataFrame, masterdata:Backtest_MasterData, currentDate, sessionID: int, intraday_stat_list: list) -> None:
        # if is_parallel:
        #     strategy: StrategyBase = copy.deepcopy(self.strategy)
        # else:
        strategy: StrategyBase = self.strategy

        strategy.init_datetime(parse_datetime(combined_df['Datetime'].iloc[0]))
        strategy.mediator.start_stats(strategy.datetime_utc)
        last_tick_time = parse_datetime(combined_df['Datetime'].iloc[-1])
        rowList: list[list[Union[str, float]]] = combined_df.values.tolist()

        def process_row_list(rowList, p: int, strategy: StrategyBase):
            tickTimeStr = str(rowList[p][0])
            tickTime = datetime.fromisoformat(tickTimeStr)
            price = float(rowList[p][1])
            tick: TickChangeData = TickChangeData(rowList[p][-1], tickTime, price)
            strategy.mediator.backtest_obj.trigger_tick_callback(tick)
            if strategy.is_backtest_skipped:
                return True
            
            return False
        
        ticker_price_closes = {}

        for ticker_name, ticker_obj in masterdata.tickers.items():
            # First Tick
            first_row_index = np.where(combined_df['Ticker'] == ticker_name)[0][0]
            tickTimeStr = str(rowList[first_row_index][0])
            tickTime = datetime.fromisoformat(tickTimeStr)
            price = float(rowList[first_row_index][1])
            tick: TickChangeData = TickChangeData(rowList[first_row_index][-1], tickTime, price)
            strategy.mediator.backtest_obj.setup_first_tick(tick)

            #0 = open, 1 = close, 2 = high, 4 = low
            ticker_price_closes[ticker_name] = ticker_obj.stock_stat_list[dayNo].close
            #strategy.mediator.backtest_obj.specific_prices[ticker_name] = [ticker_obj.stock_stat_list[dayNo].open, ticker_obj.stock_stat_list[dayNo].close, ticker_obj.stock_stat_list[dayNo].high, ticker_obj.stock_stat_list[dayNo].low]

        print(f"\nDay {dayNo} {strategy.datetime_utc.strftime('%Y-%m-%d')}\nLength of rowList: {len(rowList)}")
        strategy.intraday_start()
        strategy.day_start()

        for p in range(1, len(rowList)):
            is_backtest_skipped = process_row_list(rowList, p, strategy)
            if is_backtest_skipped:
                break
        
        if strategy.is_backtest_skipped:
            strategy.ticker_price_closes = ticker_price_closes

        strategy.day_end()

        for ticker_name, ticker_obj in masterdata.tickers.items():
            last_row_indices = np.where(combined_df['Ticker'] == ticker_name)[0]
            if len(last_row_indices) > 0:
                last_row_index = last_row_indices[-1]
                process_row_list(rowList, last_row_index, strategy)

        # if is_parallel and strategy.mediator.backtest_obj.sell_all_positions():
        #     print(f"Alert: Forcefully sold all shares due to end of day for {currentDate}")

        print(f"End gross value: {strategy.mediator.get_account_information().gross_position_value:.2f}")

        if self.global_config['SaveImage'].data == 'true':
            for ticker_name, ticker_obj in masterdata.tickers.items():
                if ticker_obj.stock_stat_list:
                    ticker_obj.stock_stat_list[-1].dv_image = dv.data_visualisation(self.global_config, combined_df[combined_df['Ticker'].str.contains(ticker_name, na=False)], self.dataLocation, ticker_name, currentDate, sessionID, strategy.mediator.stats)

        stock_stat_list = []
        for ticker_name, ticker_obj in masterdata.tickers.items():
            stock_stat_list.append(ticker_obj.stock_stat_list[-1])

        strategy.mediator.stats.daily_stock_stat_list = stock_stat_list
        strategy.mediator.calculate_stats(last_tick_time)
        intraday_stat_list.append(strategy.mediator.stats)

        strategy.stop()

    def ProcessDay_yFinance(self, dayNo:int, currentDate: datetime, sessionID:int, intraday_stat_list:list, masterdata: Backtest_MasterData)->None:
        strategy:StrategyBase = self.strategy

        # Init broker
        yfinance_broker = strategy.mediator.bt_day_obj
        if not yfinance_broker:
            return
        yfinance_broker.init(masterdata.tickers.keys())

        yfinance_broker = strategy.mediator.bt_day_obj
        if not yfinance_broker:
            return

        # Init strategy
        strategy.init_datetime(currentDate)
        strategy.mediator.start_stats(currentDate)

        # Process
        strategy.start() # Also runs broker start

        for ticker, ticker_obj in masterdata.tickers.items():
            ticker_day_data = ticker_obj.yfinance_tick_data_df.iloc[dayNo]
            yfinance_broker.set_ticker_day_data(ticker, ticker_day_data)
            current_day_data = yfinance_broker.get_current_day_data(ticker)
            ticker_obj.stock_stat_list.append(DailyStockStat(ticker, current_day_data['Open'].iloc[0], current_day_data['Close'].iloc[0], current_day_data['High'].iloc[0], current_day_data['Low'].iloc[0]))

        yfinance_broker.new_day(currentDate)

        strategy.intraday_start()
        yfinance_broker.process_intraday_start()
        strategy.day_start()
        yfinance_broker.process_day_start()
        strategy.day_end()
        yfinance_broker.process_day_end()

        stock_stat_list:list[DailyStockStat] = [] 
        for ticker, ticker_obj in masterdata.tickers.items():
            stock_stat_list.append(ticker_obj.stock_stat_list[-1])

        self.strategy.mediator.stats.daily_stock_stat_list = stock_stat_list
        self.strategy.mediator.calculate_stats(currentDate+timedelta(minutes=1))
        intraday_stat_list.append(self.strategy.mediator.stats)

        strategy.stop()