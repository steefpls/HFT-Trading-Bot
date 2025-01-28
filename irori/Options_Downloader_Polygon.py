import requests
from concurrent.futures import ThreadPoolExecutor
import ujson as json
import os
import calendar, datetime, time
import jproperties
from jproperties import Properties
import yfinance as yf
import pandas as pd
import math
class OptionsSymbol:
    def __init__(self, ticker,exp_date,option_type,strike_price):
        self.ticker = ticker.upper()
        self.exp_date = exp_date
        self.option_type = option_type.upper()
        self.strike_price = strike_price
    def getString(self):
        # Strike price needs to be formatted without decimals, padded to 8 digits
        strike_price_str = f"{int(self.strike_price * 1000):08d}"
        return f"{self.ticker}{self.exp_date}{self.option_type}{strike_price_str}"
    def getDateString(self):
        year = self.exp_date[:2]
        month = self.exp_date[2:4]
        date = self.exp_date[4:6]
        return f"20{year}-{month}-{date}"
    
# Define the request function
def fetch_options_data(symbol: OptionsSymbol, key:str):
    symbolstring = symbol.getString()
    datestring = symbol.getDateString()
    url = f"https://api.polygon.io/v2/aggs/ticker/O:{symbolstring}/range/1/second/{datestring}/{datestring}?adjusted=true&sort=asc&limit=50000&apiKey={key}"
    headers = {
        "accept": "application/json",
    }
    response = requests.get(url, headers=headers)
    if (int(response.status_code) == 200):
        print("Options data download success!")
    else:
        print(f"Options data download error, status code: {response.status_code}")
    return response.json()

def fetch_indices_data(symbol:str,date:str,key:str):
    symbolstring = symbol.getString()
    datestring = symbol.getDateString()
    url = f"https://api.polygon.io/v2/aggs/ticker/I:{symbol}/range/1/second/{date}/{date}?sort=asc&lomit=50000&apiKey={key}"
    headers = {
        "accept": "application/json",
    }
    response = requests.get(url, headers=headers)
    if (int(response.status_code) == 200):
        print("Options data download success!")
    else:
        print(f"Options data download error, status code: {response.status_code}")
    return response.json()

def read_options_data(symbol: OptionsSymbol):
    #check if the file for the Symbol already exists.
    if not os.path.exists("./backtest/"):
        os.mkdir("./backtest/")
        os.mkdir("./backtest/OptionsBacktest")
        print("Directory doesnt exist. Making Directory.")
        return False
        #check if the file for the Symbol already exists.
    if not os.path.exists("./backtest/OptionsBacktest"):
        os.mkdir("./backtest/OptionsBacktest")
        print("Directory doesnt exist. Making Directory.")
        return False
    if not os.path.exists(f"./backtest/OptionsBacktest/{symbol.getString()}.json"):
        return False
    return True

import irori_constants as irori_constants
tigerAccPropertiesFile = irori_constants.BROKER_AUTH_PROPERTIES_FILE
jPropertyConfigs = Properties()
with open(tigerAccPropertiesFile, "rb") as config_file:
    jPropertyConfigs.load(config_file)


key = jPropertyConfigs.get("polygon_key").data

async def load_options_data(symbol: OptionsSymbol):
    #If Data doesnt exist,fetch the results from alpaca and save them to a file. Returns None if symbol has no data (Holiday or weekend)
    global keyid
    if not (read_options_data(symbol)):
        
        current_key = key

        # Fetch results using the current key
        datastring = fetch_options_data(symbol, current_key)

        # Check if there's an error in the data
        if not 'error' in datastring:
            # If successful, convert data into JSON format
            jsonstring = json.dumps(datastring, indent=4)

            # Save the results to a file named after the symbol
            with open(f"./backtest/OptionsBacktest/{symbol.getString()}.json", "w") as f:
                f.write(jsonstring)
        else:
            print("Error writing datastring")

    else:
        #print(f"Data exists locally for {symbol.getString()}.")
        pass


"""
Format:
{
    'c': 2.09,             # Closing price of the option for that minute
    'h': 2.15,             # Highest price during the minute
    'l': 1.91,             # Lowest price during the minute
    'n': 135,              # Number of trades (transactions) that occurred during the second
    'o': 2.02,             # Opening price for that minute
    't': '2024-09-04T13:30:00Z', # Timestamp indicating the time the data corresponds to, in UTC
    'v': 1141,             # Volume of contracts traded during the minute (number of option contracts)
    vw': 2.072857         # Volume-weighted average price (VWAP) for the minute
}

"""
class dataChunk():
    def __init__(self,close,high,low,num,open,time,vol,vwap):
        self.close = close
        self.high = high
        self.low = low
        self.num = num
        self.open = open
        self.time = time
        self.vol = vol
        self.vwap = vwap

def getDateTimeStamp(timestamp: str):
    #get first 10 values
    intvalues = timestamp[:4]+timestamp[5:7]+timestamp[8:10]
    return int(intvalues)

def getTimeTimeStamp(timestamp: str):
    intvalues = int(str(timestamp)[11:13]+str(timestamp)[14:16])*100
    return int(intvalues)

#converts from utc to epoch
def convertToEpochTime(timestamp):
    timestamp = timestamp[0:10]+"T"+timestamp[11:19]+"Z"
    timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
    epoch = calendar.timegm(timestamp.utctimetuple())
    return int(epoch)*1000

def find_in_dataList(timestamp: str, dataList: list):
    # Use binary search to find the index of the timestamp in dataList. Returns -1 if timestamp is not present
    if len(dataList) <1:
        print(f"ERROR: Data List is length 0.")
        return -1

    low = 0
    high = len(dataList) - 1

    while low <= high:
        mid = (low + high) // 2
        current_timestamp = int(dataList[mid]['t'])
        target_timestamp = convertToEpochTime(timestamp)

        if target_timestamp == current_timestamp:
            ## Return the data corresponding to that timestamp in dataList
            # print(f"Timestanp found.")
            return dataList[mid]
        elif target_timestamp < current_timestamp:
            high = mid - 1
        else:
            low = mid + 1
    print(f"Timestamp not found in dataList. Returning closest earlier value.") # timestamp not found
    if (low>high):
        low = high
    return dataList[low] 

def convertUTCTimestamp(timestamp: str):
    return str(timestamp[2:4]+timestamp[5:7]+timestamp[8:10])
import asyncio
async def main():
    # Load SPX data
    yfinanceTicker = "^SPX"
    polygonOptionTicker = "SPXW"
    stepsize = 5

    spx = yf.Ticker(yfinanceTicker)
    dayhist = spx.history(period="2y")

    # If the Date is the index, reset it to make it a column
    dayhist.reset_index(inplace=True)

    threads = 16
    tasklist = []
    for i in range(threads):
        tasklist.append("")
        
    indicator = 0
    # To print the date along with other row information
    for index, row in dayhist.iterrows():
        if index == 0:
            continue
        date = str(row['Date'])
        high = row['High']
        low = row['Low']
        newdate = f"{date[2:4]}{date[5:7]}{date[8:10]}"
        newlow = math.floor(low/stepsize)*stepsize-(stepsize*10)
        newhigh = math.ceil(high/stepsize)*stepsize+(stepsize*10)
        print(f"Downloading data for {date}")
        while newlow<=newhigh:
            tempSymbol = OptionsSymbol(polygonOptionTicker,newdate,"C", newlow)
            tempSymbol2 = OptionsSymbol(polygonOptionTicker,newdate,"P", newlow)
            
            tasklist[indicator] = load_options_data(tempSymbol)
            indicator +=1
            tasklist[indicator] = load_options_data(tempSymbol2)
            indicator +=1
            if (indicator >=16):
                indicator = 0
                print("Gathering tasks...")
                await asyncio.gather(tasklist[0],tasklist[1],tasklist[2],tasklist[3],tasklist[4],tasklist[5],tasklist[6],tasklist[7],tasklist[8],tasklist[9],tasklist[10],tasklist[11],tasklist[12],tasklist[13],tasklist[14],tasklist[15])

            newlow+=5

if __name__ == "__main__":
    asyncio.run(main())