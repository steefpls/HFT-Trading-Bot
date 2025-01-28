
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
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mattticker
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import numpy as np
import pandas as pd
import os
from irori.stats import *
from irori.common import Backtest_MasterData, parse_datetime

extra_tickers = ["USA500IDX", "TQQQ"]

def compute_rsi(data, window=14):
    diff = np.diff(data)
    gain = np.maximum(diff, 0)
    loss = np.abs(np.minimum(diff, 0))

    avg_gain = np.convolve(gain, np.ones(window) / window, mode='valid')
    avg_loss = np.convolve(loss, np.ones(window) / window, mode='valid') + 1e-10  # to avoid division by zero

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Initialize full-length RSI array with NaNs
    rsi_full = np.full_like(data, np.nan, dtype=np.float64)
    # Fill RSI values starting after the first `window` data points
    rsi_full[window:] = rsi  # Adjust to start filling at the correct index

    return rsi_full

def data_visualisation(global_config:dict, dataFrame:pd.DataFrame, dataLocation:str, ticker:str, currentDate:str, epoch:int, stats:IntradayStats) -> str:
    #plot the graph
    fig: Figure
    ax: Axes
    ax2: Axes
    fig, (ax, ax2) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1]})

    # Convert 'Date' column to datetime and set as index
    dataFrame['Datetime'] = pd.to_datetime(dataFrame['Datetime'], format='ISO8601')
    dataFrame.set_index('Datetime', inplace=True)
    
    # Price
    price = dataFrame['Price'].rolling(window=60, min_periods=1).mean()
    ax.plot(dataFrame.index, price, label='Simulated Price (1 min)', color='black', linewidth=0.5)

    # SMA 1
    if (global_config['SMA1'].data != '0'):
        sma1 = dataFrame['Price'].rolling(window=int(global_config['SMA1'].data), min_periods=1).mean()
        ax.plot(dataFrame.index, sma1, label='SMA1', color=global_config['SMA1Color'].data, linewidth=0.5)

    # SMA 2
    if (global_config['SMA2'].data != '0'):
        sma2 = dataFrame['Price'].rolling(window=int(global_config['SMA2'].data), min_periods=1).mean()
        ax.plot(dataFrame.index, sma2, label='SMA2', color=global_config['SMA2Color'].data, linewidth=0.5)

    ax.set_title(f'{ticker} Price Graph, date: {currentDate}')
    ax.legend()
    ax.xaxis.set_major_locator(mattticker.MultipleLocator(1000))
    ax.xaxis.set_major_formatter('')

    # Trades
    for trade in stats.trades:
        if trade.ticker != ticker:
            continue
        if trade.buy_sell == 'BUY':
            ax.plot(trade.date_time, trade.price, '^', color='green')
        elif trade.buy_sell == 'SELL':
            ax.plot(trade.date_time, trade.price, 'v', color='red')
        elif trade.buy_sell == 'SHORT_OPEN':
            ax.plot(trade.date_time, trade.price, 'v', color='blue')
        elif trade.buy_sell == 'SHORT_CLOSE':
            ax.plot(trade.date_time, trade.price, '^', color='orange')

    # RSI
    if (global_config['RSI'].data != '0'):
        resampled_prices = dataFrame['Price'].resample(global_config['RSI'].data).mean()
        rsi_values = compute_rsi(resampled_prices.dropna().values, window=14)

        rsi_index = resampled_prices.index[len(resampled_prices.index) - len(rsi_values):]
        rsi_series = pd.Series(rsi_values, index=rsi_index)

        ax2.plot(rsi_series.index, rsi_series, color=global_config['RSIColor'].data, label='RSI', linewidth=0.5)
        ax2.set_title(f"Relative Strength Index | Overbought ({global_config['RSIOverbought'].data} ) | Oversold ({global_config['RSIOversold'].data})")
        ax2.legend()
        ax2.set_ylim(0, 100)
        ax2.axhline(int(global_config['RSIOverbought'].data), color='red', linestyle='--', linewidth=1)
        ax2.axhline(int(global_config['RSIOversold'].data), color='green', linestyle='--', linewidth=1)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

        ax2.legend(loc='upper left')  # Adjust legend location to avoid overlap
    
    #change subplot params
    fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

    #Set Figure Size
    fig.set_size_inches(8, 6)

    # #Increase resolution of saved graph
    plt.rcParams['savefig.dpi'] = 150
    # if (global_config['DisplayGraph'].data == 'true'):
    #     plt.get_current_fig_manager().full_screen_toggle()
    #     plt.show()

    #Create folder if it does not exist
    strategyname = global_config['StrategyName'].data
    session_dir = os.path.join(dataLocation.rstrip("\\"), "Session")
    strategy_dir = os.path.join(session_dir, f"{epoch}-{strategyname}")

    # Create session directory if it doesn't exist
    if not os.path.exists(strategy_dir):
        os.makedirs(strategy_dir)

    file_path = os.path.join(strategy_dir, f"{ticker}-{currentDate}.png")

    # Save the figure
    fig.savefig(file_path)
    plt.close(fig)

    return file_path

def master_graph(recorded_days:List[IntradayStats], data_location:str, masterdata:Backtest_MasterData, starting_capital:float, strategy_name:str):
    # Extract dates and end_gross_values from the recorded days
    dates = [stat.start_date_time for stat in recorded_days]
    end_gross_values = [stat.end_gross_value for stat in recorded_days]
    colors = plt.cm.get_cmap('tab10', round((len(masterdata.tickers) + len(extra_tickers))))

    # Calculate peak and trough
    peak = max(end_gross_values)
    trough = min(end_gross_values)

    # Plot the changes in end gross value
    plt.figure(figsize=(10, 6))
    plt.plot(dates, end_gross_values, linestyle='-', color='black', label='Strategy')
    plt.xlabel('Date')
    if len(dates) < 32:
        date_format = mdates.DateFormatter('%Y-%m-%d')
    else:
        date_format = mdates.DateFormatter('%Y-%m')
    plt.gca().xaxis.set_major_formatter(date_format)
    from matplotlib import ticker as mticker
    plt.gca().xaxis.set_major_locator(mticker.MaxNLocator(nbins=10))
    plt.ylabel('Portfolio value (Closed price)')
    plt.title(f'Performance Report ({strategy_name})')

    # Highlight peak and trough points
    peak_index = end_gross_values.index(peak)
    trough_index = end_gross_values.index(trough)

    plt.scatter(dates[peak_index], peak, color='green', zorder=5)
    plt.scatter(dates[trough_index], trough, color='red', zorder=5)

    plt.text(dates[peak_index], peak, f'{peak:.2f}', color='green', ha='right', va='bottom', fontsize=9)
    plt.text(dates[trough_index], trough, f'{trough:.2f}', color='red', ha='right', va='top', fontsize=9)

    i = 0
    for ticker_name, ticker_obj in masterdata.tickers.items():
        dates = []
        close_prices = []

        # Check if the DataFrame is not empty and has at least one row
        first_price = next((item for item in ticker_obj.stock_stat_list if item is not None), None).open
        quantity_multiplier = starting_capital / first_price

        last_known_price = 0
        index = 0
        for stock_stat in ticker_obj.stock_stat_list:
            dates.append(masterdata.date_list[index])
            if (stock_stat is not None):
                last_known_price = stock_stat.close
            close_prices.append(last_known_price * quantity_multiplier)
            index += 1
        
        plt.plot(dates, close_prices, linestyle='--', color=colors(i), label=ticker_name)
        i+=1

    for ticker in extra_tickers:
        from irori.common import convert_yfin_ticker
        ticker_data = yf.Ticker(convert_yfin_ticker(ticker))
        hist = ticker_data.history(start=min(masterdata.date_list), end=max(masterdata.date_list))
        
        hist.index = pd.to_datetime(hist.index).strftime('%Y-%m-%d')
        ticker_dates = [date.strftime('%Y-%m-%d') for date in masterdata.date_list]
        close_prices = []
        
        if hist.empty or hist['Close'].empty:
            continue
        first_price = hist['Close'].iloc[0]
        quantity_multiplier = starting_capital / first_price

        for date in ticker_dates:
            if date in hist.index:
                close_price = hist.loc[date, 'Close']
                new_price = close_price * quantity_multiplier
            else:
                if (len(close_prices) > 0):
                    new_price = close_prices[-1]
                else:
                    new_price = first_price * quantity_multiplier
            close_prices.append(new_price)
        
        plt.plot(dates, close_prices, linestyle='--', color=colors(i), label=ticker)
        i += 1
    
    plt.legend(loc='upper left')
    
     # Create session directory if it doesn't exist
    if not os.path.exists(data_location):
        os.makedirs(data_location)

    plt.savefig(os.path.join(data_location, 'master_graph.png'))
    plt.close()

def master_graph_log(recorded_days: List[IntradayStats], data_location: str, masterdata: Backtest_MasterData, starting_capital: float, strategy_name: str):
    # Extract dates and end_gross_values from the recorded days
    dates = [stat.start_date_time for stat in recorded_days]
    end_gross_values = [stat.end_gross_value for stat in recorded_days]
    colors = plt.cm.get_cmap('tab10', round((len(masterdata.tickers) + len(extra_tickers))))
    plt.figure(figsize=(10, 6))

    # Plot the changes in end gross value
    log_end_gross_values = np.log2(end_gross_values)

    # Calculate peak and trough
    peak = max(log_end_gross_values)
    trough = min(log_end_gross_values)

    plt.plot(dates, log_end_gross_values, linestyle='-', color='black', label='Strategy')
    plt.xlabel('Date')
    if len(dates) < 32:
        date_format = mdates.DateFormatter('%Y-%m-%d')
    else:
        date_format = mdates.DateFormatter('%Y-%m')
    plt.gca().xaxis.set_major_formatter(date_format)
    from matplotlib import ticker as mticker
    plt.gca().xaxis.set_major_locator(mticker.MaxNLocator(nbins=10))
    plt.ylabel('Portfolio value (Log2)')
    plt.title(f'Logarithmic Scale Report ({strategy_name})')
    plt.yscale('log')

    # Highlight peak and trough points
    peak_index = log_end_gross_values.tolist().index(peak)
    trough_index = log_end_gross_values.tolist().index(trough)

    plt.scatter(dates[peak_index], peak, color='green', zorder=5)
    plt.scatter(dates[trough_index], trough, color='red', zorder=5)

    plt.text(dates[peak_index], peak, f'{pow(2,peak):.2f}', color='green', ha='right', va='bottom', fontsize=9)
    plt.text(dates[trough_index], trough, f'{pow(2,trough):.2f}', color='red', ha='right', va='top', fontsize=9)

    i = 0
    for ticker_name, ticker_obj in masterdata.tickers.items():
        dates = []
        close_prices = []

        # Check if the DataFrame is not empty and has at least one row
        first_price = next((item for item in ticker_obj.stock_stat_list if item is not None), None).open
        quantity_multiplier = starting_capital / first_price

        last_known_price = 0
        index = 0
        for stock_stat in ticker_obj.stock_stat_list:
            dates.append(masterdata.date_list[index])
            if stock_stat is not None:
                last_known_price = stock_stat.close
            close_prices.append(last_known_price * quantity_multiplier)
            index += 1
        
        log_close_prices = np.log2(close_prices)
        plt.plot(dates, log_close_prices, linestyle='--', color=colors(i), label=ticker_name)
        i += 1
    
    for ticker in extra_tickers:
        from irori.common import convert_yfin_ticker
        ticker_data = yf.Ticker(convert_yfin_ticker(ticker))
        hist = ticker_data.history(start=min(masterdata.date_list), end=max(masterdata.date_list))
        
        hist.index = pd.to_datetime(hist.index).strftime('%Y-%m-%d')
        ticker_dates = [date.strftime('%Y-%m-%d') for date in masterdata.date_list]
        close_prices = []

        if hist.empty or hist['Close'].empty:
            continue
        first_price = hist['Close'].iloc[0]
        quantity_multiplier = starting_capital / first_price

        for date in ticker_dates:
            if date in hist.index:
                close_price = hist.loc[date, 'Close']
                new_price = close_price * quantity_multiplier
            else:
                if (len(close_prices) > 0):
                    new_price = close_prices[-1]
                else:
                    new_price = first_price * quantity_multiplier
            close_prices.append(new_price)
        
        log_close_prices = np.log2(close_prices)
        plt.plot(dates, log_close_prices, linestyle='--', color=colors(i), label=ticker)
        i += 1

    plt.legend(loc='upper left')
    
    # Create session directory if it doesn't exist
    if not os.path.exists(data_location):
        os.makedirs(data_location)

    plt.savefig(os.path.join(data_location, 'master_graph_log.png'))
    plt.close()
