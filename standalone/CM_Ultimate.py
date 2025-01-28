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
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import sqrt

# Fetch data
data = yf.download('NVDA', start='2023-03-01', end='2024-05-02')

# Calculate moving averages
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def wma(series, period):
    weights = [i for i in range(1, period + 1)]
    return series.rolling(period).apply(lambda x: sum(x * weights) / sum(weights), raw=True)

def sma(series, period):
    return series.rolling(period).mean()

def hull_ma(series, period):
    return wma(2 * wma(series, period // 2) - wma(series, period), int(sqrt(period)))

def rma(series, period):
    return series.ewm(alpha=1/period, adjust=False).mean()

def tilson_t3(series, period, volume_factor=0.7):
    vfact = volume_factor * 0.1

    def gd(x):
        ema1 = ema(x, period)
        ema2 = ema(ema1, period)
        return ema1 * (1 + vfact) - ema2 * vfact

    first = gd(series)
    second = gd(first)
    third = gd(second)
    return third

# data = pd.concat([data, data])
# data = pd.concat([data, data])
# data = pd.concat([data, data, data])

print(data)
import time
start_time = time.time()
# Sample moving average calculation
data['SMA'] = sma(data['Close'], 5)
data['EMA'] = ema(data['Close'], 5)
data['WMA'] = wma(data['Close'], 5)
data['HMA'] = hull_ma(data['Close'], 5)
data['RMA'] = rma(data['Close'], 5)
data['TilsonT3'] = tilson_t3(data['Close'], 5, 7)
end_time = time.time()
print(end_time - start_time)
# Debugging: print first few non-NaN rows
#print(data[['Close', 'SMA', 'EMA', 'WMA', 'HMA', 'TilsonT3']].dropna().head())

print(data['HMA'])

# Plotting
plt.figure(figsize=(14, 7))
plt.plot(data['Close'], label='Close Price', color='gray')
plt.plot(data['SMA'], label='SMA 5', color='red')
plt.plot(data['EMA'], label='EMA 5', color='green')
plt.plot(data['WMA'], label='WMA 5', color='blue')
plt.plot(data['HMA'], label='HMA 5', color='purple')
plt.plot(data['RMA'], label='RMA 5', color='orange')
plt.plot(data['TilsonT3'], label='Tilson T3', color='pink')
plt.title('NVDA Stock Prices and Moving Averages')
plt.legend()
plt.show()