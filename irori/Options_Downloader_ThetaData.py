import httpx  # install via pip install httpx
import pandas as pd
import json
import os
import datetime
import pytz
import pandas_market_calendars as mcal
import yfinance as yf
BASE_URL = "http://127.0.0.1:25510/v2"  # all endpoints use this URL base

def get_spx_high_low(startdate,enddate):
    # Fetch SPX data for the specific date
    ticker = "^GSPC"  # S&P 500 index ticker on Yahoo Finance
    data = yf.download(ticker, start = startdate, end = enddate, interval="1d")
    if not data.empty:
        return data
    else:
        raise ValueError(f"No SPX data available for {startdate}")
    
def getoptionsprice(ticker:str, date:str,callput:str ,strike: float):
    ticker = ticker.upper()
    callput = callput.upper()
    year = int(date[0:4])
    
    month = int(date[4:6])
    day = int(date[6:8])
    yearshorthand = date[2:4]
    monthshorthand = date[4:6]
    dayshorthand = date[6:8]
    # File path based on parameters
    file_path = f"./backtest/OptionsBacktest/{ticker}{yearshorthand}{monthshorthand}{dayshorthand}{callput}0{strike}000.json"

    if read_options_data(ticker, date, callput, strike):
        # Read data from the existing file
        print(f"{ticker}{yearshorthand}{monthshorthand}{dayshorthand}{callput}0{strike}000.json exists. Skipping download.")
    else:
        print(f"{ticker}{yearshorthand}{monthshorthand}{dayshorthand}{callput}0{strike}000.json does not exist, downloading file...")
        # Prepare URL for API request
        datestring = f"{year}-{month:02d}-{day:02d}"
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

        mspertick = "1000"  # milliseconds per tick
        url = BASE_URL + f"/hist/option/ohlc?root={ticker}&exp={date}&strike={strike}000&right={callput}&start_date={date}&end_date={date}&ivl={mspertick}"
        
        # Make the request
        response = httpx.get(url)
        if response.status_code !=200:
            print(f"Download failed for {ticker}{yearshorthand}{monthshorthand}{dayshorthand}{callput}0{strike}000.json")  # Ensure the request worked
            return False
        data = response.json()
        if "response" in data:
            data["results"] = data.pop("response")
            transformed_results = []
            
            for item in data["results"]:
                if(item[1] +item[2]+item[3]+item[4] == 0):
                    continue
                transformed_results.append({
                "o": item[1],  # Assuming the first value represents open price
                "c": item[4],  # Assuming open and close are the same
                "h": item[2],  # Assuming high price is the same as open
                "l": item[3],  # Assuming low price is the same as open
                "t": item[0]+epoch_time*1000  # WIP TIME TRANSFORMATION
            })
                data["results"] = transformed_results
            
        # Save the fetched data to a file
            with open(file_path, "w") as file:
                json.dump(data, file)
                print("File saved.")
                return True

    
        
    


def read_options_data(ticker: str, date: str, callput: str, strike: float):
    # Check if the file directory exists, create if not
    if not os.path.exists("./backtest/"):
        os.mkdir("./backtest/")
    if not os.path.exists("./backtest/OptionsBacktest"):
        os.mkdir("./backtest/OptionsBacktest")
    yearshorthand = date[2:4]
    monthshorthand = date[4:6]
    dayshorthand = date[6:8]
    # Check if the specific file exists
    file_path = f"./backtest/OptionsBacktest/{ticker}{yearshorthand}{monthshorthand}{dayshorthand}{callput}0{strike}000.json"
    return os.path.exists(file_path)



"""Code needs to: 
- Check if trading day
- Check SPX price range for that day
- Download all Call and put options prices, within the days range + 20 below the minimum, 20 below the maximum. (Strike prices are in intervals of 5)
"""

def mass_download():
    # Set start and end dates
    start_date = datetime.date(2016, 1, 1)
    end_date = datetime.date.today()
    
    # Get the SPX high and low data for the date range
    spxhighlow = get_spx_high_low(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    
    # Convert spxhighlow index to date format to match trading_days
    spxhighlow.index = spxhighlow.index.date  # Ensure the index is in date format
    
    # Get the market calendar for trading days
    nyse = mcal.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=start_date, end_date=end_date)
    trading_days = schedule.index.date  # Extract trading dates as date objects
    
    # Iterate through each trading day
    for current_date in trading_days:
        # Check if SPX high/low data exists for the current day
        if current_date in spxhighlow.index:
            spx_day_data = spxhighlow.loc[current_date]
            spx_high = spx_day_data.loc['High'].values[0]
            spx_low = spx_day_data.loc['Low'].values[0]
            
            print(f"Fetching options data for {current_date} with SPX High: \n{spx_high}\n and Low: \n{spx_low}\n")
            
            # Calculate the strike range (±30 from SPX high/low, with 5 strike intervals)
            min_strike = int((spx_low - 30)//5 * 5)  # Avoid negative strike prices
            max_strike = int((spx_high + 30)//5 * 5)

            print(f"Adjusted min strike: {min_strike}, Adjusted max strike: {max_strike}")
            
            # Download call options data for all strikes within the range
            for strike in range(min_strike, max_strike + 1, 5):
                # Download call options (right='C')
                if (getoptionsprice("SPXW", current_date.strftime('%Y%m%d'), "C", strike) == False):
                    print("Options data doesnt exist for this day. skipping.")
                    break
                # Download put options (right='P')
                if (getoptionsprice("SPXW", current_date.strftime('%Y%m%d'), "P", strike) == False):
                    break
        else:
            print(f"No SPX data available for {current_date}")

mass_download()
