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
from datetime import datetime
import os
import time
from datetime import datetime,timedelta
import pandas_market_calendars as mcal
import multiprocessing
from findatapy.market import Market, MarketDataRequest, MarketDataGenerator
import pandas as pd

class Backtester:
    dataLocation:str = None

    def start(self):
        input_ticker,input_startdate,input_finishdate = self.get_backtest_input()
        self.init(input_ticker, input_startdate, input_finishdate)

    def releaseList(self, list):
        del list[:]
        del list
    
    def market_is_open(self, date):
        result = mcal.get_calendar("NYSE").schedule(start_date=date, end_date=date)
        return result.empty == False

    def init(self, ticker, startdate1, finishdate1):
        file_dir = os.path.dirname(os.path.realpath(__file__))
        market = Market(market_data_generator=MarketDataGenerator())

        #error handling if dates are invalid
        try:
            start_day, start_month, start_year = startdate1.split()
            finish_day, finish_month, finish_year = finishdate1.split()
        except ValueError:
            print("Incorrect data format, should be DD Month YYYY (1 feb 2024). Please try again.")
            return (-1,-1,-1,-1)
        
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
        numDays = (finish - start).days
        cacheS = datetime.strptime(startdate, "%Y-%m-%d")+ timedelta(days=1)
        cacheF = datetime.strptime(finishdate, "%Y-%m-%d")+ timedelta(days=1)

        dataLocation = ((file_dir) + r"\BacktestData\\"+ ticker)
        dataFrameList = []
        processList = []
        manager = multiprocessing.Manager()
        return_List = manager.list()
        #create folder if it doesn't exist
        dataLocation = ((file_dir) + r"\BacktestData\\"+ ticker)
        if not os.path.exists(dataLocation):
            print(f"No {ticker} folder exists. Creating folder at {dataLocation}")
            os.makedirs(dataLocation)
        LoadFileDateList = []
        DownloadFileDateListStart = []
        DownloadFileDateListFinish = []
        #loop through the days
        for i in range(numDays):
            startdate = start.strftime("%d %b %Y")
            finishdate = (start + timedelta(days=1)).strftime("%d %b %Y") 
            if os.path.exists(dataLocation + f'\{ticker}-{startdate}.xlsx'):
                print(f"Date {startdate} exists. ")
                LoadFileDateList.append(startdate)
                #LoadFile(dataLocation,ticker,startdate,dataFrameList)
            else:
                if not self.market_is_open(start):
                    print(f"Date {startdate} is not a trading day")
                else:
                    print(f"Date {startdate} needs to be downloaded.")
                    DownloadFileDateListStart.append(startdate)
                    DownloadFileDateListFinish.append(finishdate)
                #DownloadFile(ticker,start,finish,file_dir,startdate,finishdate,market,dataFrameList)
            start = start + timedelta(days=1)
            finish = finish + timedelta(days=1)
        #start global timer to measure time taken
        global start_time
        start_time = time.time()
            
        downloaderProcess = multiprocessing.Process(target=self.DownloadAllFiles, args=(ticker,file_dir,DownloadFileDateListStart,DownloadFileDateListFinish,market,return_List))
        downloaderProcess.start()

        #split ProcessList into lists of size multiprocessing.cpu_count()-2 to prevent overloading. 1 thread is reserved for downloaderProcess, 1 for using your pc.
        processorCount = multiprocessing.cpu_count()-2
        totalProcesses = len(processList)
        processList = [processList[i:i + processorCount] for i in range(0, len(processList), processorCount)]
        #start and join each process
        for i in range(len(processList)):
            if ((i+1)*processorCount-1)>totalProcesses:
                print(f"Loading days {i*processorCount} to {totalProcesses} out of {totalProcesses}...")
            else:
                print(f"Loading days {i*processorCount} to {(i+1)*processorCount-1} out of {totalProcesses}...")
            for x in range(len(processList[i])):
                processList[i][x].start()
            for x in range(len(processList[i])):
                processList[i][x].join()
        downloaderProcess.join()

    def DownloadAllFiles(self,ticker,file_dir,startdateList,finishdateList,market,dataFrameList)->None:
        for i in range(len(startdateList)):
            print(f"\nFile {ticker}-{startdateList[i]}.xlsx does not exist. Downloading file number {i+1} of {len(startdateList)}...")
            self.DownloadFile(ticker,file_dir,startdateList[i],finishdateList[i],market,dataFrameList)

    def DownloadFile(self, ticker:str,file_dir,startdate,finishdate,market:Market,dataFrameList:list)->None:
        #check if ticker has IDX
        appendText = 'US'
        original_ticker = ticker
        if (ticker[-3:] == 'IDX'):
            ticker = ticker[:-3]
            appendText = 'IDXUSD'
        elif (ticker[-3:] == 'DKK'):
            ticker = ticker[:-3]
            appendText = 'DKDKK'
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
            print(f"ERROR! No data for {startdate}!")
            return
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
                price = (bidPrice + askPrice) / 2
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
                    price = (bidPrice + askPrice) / 2

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

        df.to_excel(file_dir + f'\BacktestData\{original_ticker}\{original_ticker}-{formatted_date}.xlsx',engine='xlsxwriter')
        print(f"File saved to {file_dir}\BacktestData\{original_ticker} as {original_ticker}-{formatted_date}.xlsx")

        # Append the DataFrame to the dataFrameList
        dataFrameList.append(df)
        
    def get_backtest_input(self):
        input_ticker = input("Enter the ticker you want to backtest: ")
        input_startdate = input("Enter the start date (DD Month YYYY): ")
        input_finishdate = input("Enter the finish date (DD Month YYYY): ")
        return input_ticker.upper(), input_startdate, input_finishdate

if __name__ == '__main__':
    Backtester().start()