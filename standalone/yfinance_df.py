import yfinance as yf
import pandas as pd

# Define the ticker symbol and the date range
ticker_symbol = 'QQQ'
start_date = '2024-01-01'
end_date = '2024-01-30'

# Fetch the data using yfinance
# data = yf.download(ticker_symbol, start=start_date, end=end_date)

# # Print the dataframe
# print(data)

def get_yfinance_df(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)

    # Print the dataframe
    # print(data)
    return data

data: pd.DataFrame = get_yfinance_df(ticker_symbol, start_date, end_date)
print(data.head())
print(data.iloc[0])

# test = [1,2,3]

# test2 = list(filter(lambda x: x == 1, test))

# print(test)
# print(test2)