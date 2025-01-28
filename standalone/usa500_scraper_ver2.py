import requests
import re
import json
import time

url = 'https://freeserv.dukascopy.com/2.0/index.php?path=chart%2Fjson3&instrument=E_SandP-500&offer_side=B&interval=TICK&last_update=1729078498583&splits=true&stocks=true&jsonp=_callbacks____dm2bspccx'

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:131.0) Gecko/20100101 Firefox/131.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Referer': 'https://freeserv.dukascopy.com/2.0/?path=chart/index&lang=en&showUI=true&showTabs=true&showParameterToolbar=true&showOfferSide=true&allowInstrumentChange=true&allowPeriodChange=true&allowOfferSideChange=true&showAdditionalToolbar=true&showDetachButton=true&presentationType=candle&axisX=true&axisY=true&legend=true&timeline=true&showDateSeparators=true&showZoom=true&showScrollButtons=true&showAutoShiftButton=true&crosshair=true&borders=false&theme=Pastelle&uiColor=%23000&availableInstruments=l%3A&instrument=EUR/USD&period=7&offerSide=BID&timezone=0&live=true&panLock=false&width=100%25&height=600&adv=popup',
    'Cookie': 'XSRF-TOKEN=eyJpdiI6IldsSnhuczF3N01iQ1dTeDE2SlwvSjd3PT0iLCJ2YWx1ZSI6InVOOHFMQzZXOFFRUGVLcWJpb0VVMmRKYWkwamJOV25RWU5IcUFub2dhMVBPckhGS3JjYjQxYXNmd1E5VUs4QWwiLCJtYWMiOiJmODAyMmRhMTFkNTM3NDA5NDJiNTIzZGY4NGVlYTdkMjk2NTZhMjA2NjA2NmM1YmZkZDJmOWY0OGJkMzYxOTM1In0%3D; dukascopy_trading_tools_session=eyJpdiI6ImJNSkN5eUdLTFgyNHlTQzJ0NHBmYmc9PSIsInZhbHVlIjoiRUhpd1ZWKzY4a0VRZkhoSWUzVHRvN2xPbVlFbHlNNEc4NVg1V3hGTWFMMENuaHFSa2l1NFM5WUR3OGpFK2dCViIsIm1hYyI6Ijg4NDNjZThmN2MyYWQ5MzUyZDZkYjQ3ODZhNWFjNWNmNzk3NGY2MTg1ODM0ODI1MDAzZTViMTU1NmM5ODM1ZWEifQ%3D%3D; _gcl_au=1.1.156895716.1729078362; _ga_K7YWEJ4FF5=GS1.1.1729078362.1.1.1729078416.0.0.0; _ga=GA1.1.844077706.1729078362; _ga_E5V67SH0LM=GS1.1.1729078362.1.1.1729078416.6.0.0; _ga=GA1.3.844077706.1729078362; _gid=GA1.3.1150689721.1729078365; _ga_SS02W783FB=GS1.3.1729078364.1.1.1729078418.6.0.0',
    'Sec-Fetch-Dest': 'script',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'same-origin'
}

def fetch_latest_data():
    """Fetch and return the latest data from the response."""
    response = requests.get(url, headers=headers)
    
    # Extract the JSON data from the response
    data_str = re.search(r'\(\[(.*)\]\);', response.text).group(1)

    # Convert the extracted string into a valid Python list
    data_list = json.loads(f'[{data_str}]')
    
    # Return the last element
    return data_list[-1]

def save_to_file(data):
    """Save the formatted data to a text file."""
    timestamp, bid, ask, *_ = data
    mid = (bid + ask) / 2  # Calculate the middle value (mid)
    
    # Prepare the formatted string
    formatted_data = f'{{time: {timestamp}, bid: {bid}, ask: {ask}, mid: {mid:.6f}}}\n'
    # Get the current time as a Unix timestamp
    current_time = time.time()

    # Calculate the difference
    time_difference = current_time - (timestamp/1000)

    # Print the result
    print(f"Time difference: {time_difference} seconds")
        
    # Append the formatted string to a file
    with open('data_log.txt', 'a') as file:
        file.write(formatted_data)

# Initialize with None to store the previous value
previous_data = None

# Continuously check for changes every second
while True:
    try:
        # Fetch the latest data
        latest_data = fetch_latest_data()

        # Check if the data has changed
        if latest_data != previous_data:
            print("New data:", latest_data)
            save_to_file(latest_data)  # Save the new data to the file
            previous_data = latest_data  # Update the previous data to the latest
    except Exception as e:
        print(f"Error occurred: {e}")
        break