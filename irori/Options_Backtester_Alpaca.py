import requests
from concurrent.futures import ThreadPoolExecutor
import ujson as json
import os
import calendar, datetime, time

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
    
class Symbol:
    def __init__(self, ticker,date):
        self.ticker = ticker
        self.date = date
    def getString(self):
        return str(self.ticker)
    def getDateString(self):
        year = self.date[:2]
        month = self.date[2:4]
        date = self.date[4:6]
        return f"20{year}-{month}-{date}"
    def getNameString(self):
        return str(self.getString()+self.getDateString())

def fetch_stock_data(symbol: Symbol):
    symbolstring = symbol.getString()
    datestring = symbol.getDateString()
    url = f"https://data.alpaca.markets/v2/stocks/bars?symbols={symbolstring}&timeframe=1Min&start={datestring}T00%3A00%3A00Z&end={datestring}T23%3A59%3A59Z&limit=10000&adjustment=split&feed=sip&sort=asc"
    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": "AKTMELPPU1B00ZWJYPR2",
        "APCA-API-SECRET-KEY": "PbQ3OaCAplW2rV0WWQXF0GAu0P2IbK5zCNxbJ98G"
    }
    response = requests.get(url, headers=headers)
    return response.json()

# Define the request function
def fetch_options_data(symbol: OptionsSymbol):
    symbolstring = symbol.getString()
    datestring = symbol.getDateString()
    url = f"https://data.alpaca.markets/v1beta1/options/bars?symbols={symbolstring}&timeframe=1Min&start={datestring}T00%3A00%3A00Z&end={datestring}T23%3A59%3A59Z&limit=10000&sort=asc"
    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": "AKTMELPPU1B00ZWJYPR2",
        "APCA-API-SECRET-KEY": "PbQ3OaCAplW2rV0WWQXF0GAu0P2IbK5zCNxbJ98G"
    }
    response = requests.get(url, headers=headers)
    return response.json()

def read_stock_data(symbol: Symbol):
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
    if not os.path.exists(f"./backtest/OptionsBacktest/{symbol.getNameString()}.json"):
        return False
    return True

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

def load_options_data(symbol: OptionsSymbol):
    #If Data doesnt exist,fetch the results from alpaca and save them to a file. Returns None if symbol has no data (Holiday or weekend)
    if not (read_options_data(symbol)):
    #Fetch Ressults
        result = fetch_options_data(symbol)
        datastring = result["bars"]
        #print(datastring)
        #change header name
        print(f"{datastring}")
        datastring['results'] = datastring.pop(symbol.getString())
        #change to epoch time
        for result in datastring['results']:
            result['t'] = convertToEpochTime(result['t'])
        #Convert data into JSON format
        jsonstring = json.dumps(datastring, indent=4)

        #Save the results to a file named after the symbol in the directory
        with open(f"./backtest/OptionsBacktest/{symbol.getString()}.json", "w") as f:
            f.write(jsonstring)
    else:
        #print(f"Data exists locally for {symbol.getString()}. Loading data.")
        pass
    #load data into datalist
    with open(f"./backtest/OptionsBacktest/{symbol.getString()}.json", "r") as f:
    #load data into datalist
        datalist = json.loads(f.read())
        #check if datalist has data.
        if datalist:
            #print(f"Data loaded for {symbol.getString()}.")
            return datalist
        else:
            print(f"Data loaded but no values for {symbol.getString()}.")
            return None

def load_stock_data(symbol: Symbol):
    #If Data doesnt exist,fetch the results from alpaca and save them to a file. Returns None if symbol has no data (Holiday or weekend)
    if not (read_stock_data(symbol)):
    #Fetch Ressults
        result = fetch_stock_data(symbol)
        datastring = result["bars"]
        #Convert data into JSON format
        jsonstring = json.dumps(datastring, indent=4)
        print(f"Data downloading for {symbol.getNameString()}. Loading data.")
        #Save the results to a file named after the symbol in the directory
        with open(f"./backtest/OptionsBacktest/{symbol.getNameString()}.json", "w") as f:
            f.write(jsonstring)
    else:
        print(f"Data exists locally for {symbol.getNameString()}. Loading data.")
    #load data into datalist
    with open(f"./backtest/OptionsBacktest/{symbol.getNameString()}.json", "r") as f:
    #load data into datalist
        datalist = json.loads(f.read())
        #check if datalist has data.
        if datalist:
            print(f"Data loaded for {symbol.getNameString()}.")
            return datalist
        else:
            print(f"Data loaded but no values for {symbol.getNameString()}.")
            return None
#Test Code - makes a symbol and loads the data into datalist. Downloads data if data is not present
"""
Format:
{
    'c': 2.09,             # Closing price of the option for that minute
    'h': 2.15,             # Highest price during the minute
    'l': 1.91,             # Lowest price during the minute
    'n': 135,              # Number of trades (transactions) that occurred during the minute
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
    timestamp = timestamp[0:10]+"T"+timestamp[11:17]+"00Z"
    timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:00Z')
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
            return dataList[mid]
        elif target_timestamp < current_timestamp:
            high = mid - 1
        else:
            low = mid + 1
    print(f"Timestamp not found in dataList. Returning closest earlier value.") # timestamp not found
    return dataList[low] 

def convertUTCTimestamp(timestamp: str):
    return str(timestamp[2:4]+timestamp[5:7]+timestamp[8:10])

#
def getOptionPrice(utcTimestamp: str, ticker: str, option_type: str, strike_price: float):
    tempSymbol = OptionsSymbol(ticker,convertUTCTimestamp(utcTimestamp),option_type, strike_price)
    dataList = load_options_data(tempSymbol)['results']
    return find_in_dataList(utcTimestamp,dataList)


# #Load Options Data
# tempSymbol = OptionsSymbol("SPY","240201","C", 480.00)
# dataList = load_options_data(tempSymbol)['results']
# for i in range(len(dataList)):
#     print(f"{i} - {dataList[i]}")
'''
tempSymbol2 = OptionsSymbol("SPY","240904","P", 549.00)
dataList2 = load_options_data(tempSymbol2)[tempSymbol2.getString()]

tempSymbol3 = Symbol('SPY',"240904")
datalist3 = load_stock_data(tempSymbol3)[tempSymbol3.getString()]


#iterate through dataList and print the values of each key in that dictionary to console.
for i in range(len(datalist3)):
    print(f"{i} - {datalist3[i]}")
'''