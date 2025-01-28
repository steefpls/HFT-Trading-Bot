import httpx  # install via pip install httpx
import pandas as pd
import json
import os
import datetime
import pytz
BASE_URL = "http://127.0.0.1:25510/v2"  # all endpoints use this URL base

def getindexprice(ticker:str, date:str):
    ticker = ticker.upper()
    year = int(date[0:4])
    month = int(date[4:6])
    day = int(date[6:8])

    datestring = f"{year}-{month}-{day}"
    market_open_time = "00:00"
    market_timezone = "America/New_York"  # Timezone of the market
    # Combine date and time
    dt_string = f"{datestring} {market_open_time}"
    dt_format = "%Y-%m-%d %H:%M"
    # Parse into a naive datetime object
    naive_dt = datetime.datetime.strptime(dt_string, dt_format)

    # Localize to the market's timezone
    local_tz = pytz.timezone(market_timezone)
    localized_dt = local_tz.localize(naive_dt)
    
    # Convert to UTC and get epoch time
    epoch_time = int(localized_dt.astimezone(pytz.utc).timestamp())

    mspertick = "1000" #miliseconds per tick

    url = BASE_URL + f'/hist/index/price?root={ticker}&start_date={date}&end_date={date}&ivl={mspertick}'

    if url is not None:
        response = httpx.get(url)  # make the request
        response.raise_for_status()  # make sure the request worked

    data = response.json()

    # manipulate data here
    # Rename "response" to "results"
    if "response" in data:
        data["results"] = data.pop("response")
        transformed_results = []
        for item in data["results"]:
            transformed_results.append({
            "o": item[1],  # Assuming the first value represents open price
            "c": item[1],  # Assuming open and close are the same
            "h": item[1],  # Assuming high price is the same as open
            "l": item[1],  # Assuming low price is the same as open
            "t": item[0]+epoch_time*1000  # WIP TIME TRANSFORMATION
        })
            
    data["results"] = transformed_results[1:]
    return data

#save
# data = getindexprice("spx","20240507")
# with open('data.json', 'w', encoding='utf-8') as f:
#     json.dump(data, f, ensure_ascii=False, indent=4)

# # Extract relevant data from the JSON
# results = data["results"]

# # Convert to DataFrame
# df = pd.DataFrame(results)

# # Convert timestamp to the desired format
# df['Datetime'] = pd.to_datetime(df['t'], unit='ms').dt.strftime('%Y-%m-%d %H:%M:%S.%f+00:00')

# # Select and rename columns
# df = df[['Datetime', 'o']].rename(columns={'o': 'Price'})

# # Display the resulting DataFrame
# print(df)

def getDFThetaData(ticker:str,date:str):
    data:pd.DataFrame = load_indices_data(ticker,date)
    if data.empty:
        print(f"No data for date: {date}.\n{data}")
        return None
    
    return data

def read_indices_data(symbol:str,date:str):
    #check if the file for the Symbol already exists.
    symbol = symbol.upper()
    if not os.path.exists("./backtest/"):
        os.mkdir("./backtest/")
        os.mkdir("./backtest/TTIndices")
        print("Directory doesnt exist. Making Directory.")
        return False
        #check if the file for the Symbol already exists.
    if not os.path.exists("./backtest/TTIndices"):
        os.mkdir("./backtest/TTIndices")
        print("Directory doesnt exist. Making Directory.")
        return False
    if not os.path.exists(f"./backtest/TTIndices/{symbol}-{date}.json"):
        return False
    return True

def load_indices_data(symbol:str,date:str):
    #If Data doesnt exist,fetch the results and save them to a file. Returns None if symbol has no data (Holiday or weekend)
    symbol = symbol.upper()
    if not (read_indices_data(symbol,date)):
        print("Data not found, attempting download from ThetaData...")
        data = getindexprice(symbol, date.replace("-", ""))

        # Extract relevant data from the JSON
        results = data["results"]

        # Convert to DataFrame
        df = pd.DataFrame(results)

        # Convert timestamp to the desired format
        df['Datetime'] = pd.to_datetime(df['t'], unit='ms').dt.strftime('%Y-%m-%d %H:%M:%S.%f+00:00')

        # Select and rename columns
        df = df[['Datetime', 'o']].rename(columns={'o': 'Price'})
        print("Download success.")
        return df

    else:
    #     #print(f"Data exists locally for {symbol.getString()}. Loading data.")
    #     pass
    # #load data into datalist
    # with open(f"./backtest/TTIndices/{symbol}-{date}.json", "r") as f:
    # #load data into datalist
    #     datalist = json.loads(f.read())
    #     #check if datalist has data.
    #     if datalist:
    #         #print(f"Data loaded for {symbol.getString()}.")
    #         return datalist
    #     else:
    #         print(f"Data loaded but no values for {symbol}.")
    #         return None
        return None
    