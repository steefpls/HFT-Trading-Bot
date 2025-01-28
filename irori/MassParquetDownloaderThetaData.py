import Index_Downloader_ThetaData as dl
import os
import pandas as pd
import pandas_market_calendars as mcal
from datetime import datetime

def download_thetadata_spx_data(formatted_date: str) -> bool:
    # Define the file path
    parquet_file_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), 
        'BacktestData', 'SPX', f'SPX-{formatted_date}.parquet'
    )
    
    # Check if the file already exists
    if os.path.exists(parquet_file_path):
        print(f"File for {formatted_date} already exists. Skipping download.")
        return False

    # If the file does not exist, download the data
    print(f"Downloading data for {formatted_date}...")
    df: pd.DataFrame = dl.getDFThetaData("SPX", formatted_date)
    os.makedirs(os.path.dirname(parquet_file_path), exist_ok=True)
    df.to_parquet(parquet_file_path)
    print(f"File saved: {parquet_file_path}")
    return True

# Get NYSE calendar
nyse = mcal.get_calendar('NYSE')

# Define the date range
start_date = datetime(2020, 1, 1)
end_date = datetime.today()

# Generate all NYSE trading days in the date range
schedule = nyse.schedule(start_date=start_date, end_date=end_date)
trading_days = schedule.index

# Iterate through trading days and run the download function
for trading_day in trading_days:
    formatted_date = trading_day.strftime('%Y-%m-%d')
    try:
        download_thetadata_spx_data(formatted_date)
    except Exception as e:
        print(f"Error processing {formatted_date}: {e}")