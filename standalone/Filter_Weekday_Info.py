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
import datetime as dt

def get_stock_data(ticker, start_date, end_date):
    # Convert the start_date to a datetime object
    start_date_obj = dt.datetime.strptime(start_date, '%Y-%m-%d')
    # Subtract 3 days from the start_date
    adjusted_start_date = start_date_obj - dt.timedelta(days=3)
    # Convert the adjusted date back to a string
    adjusted_start_date_str = adjusted_start_date.strftime('%Y-%m-%d')
    
    stock_data = yf.download(ticker, start=adjusted_start_date_str, end=end_date)
    if stock_data.empty:
        raise ValueError("No data fetched for the given ticker and date range.")
    return stock_data

def calculate_returns(stock_data):
    # Regular exit
    # if 'Close' not in stock_data.columns:
    #     raise ValueError("The fetched data does not contain 'Close' prices.")
    
    # stock_data['Return'] = stock_data['Close'].pct_change()
    # stock_data.dropna(inplace=True)
    # return stock_data


    # Exit only if close is higher than buy in day's high
    # if 'Close' not in stock_data.columns or 'High' not in stock_data.columns:
    #     raise ValueError("The fetched data does not contain 'Close' or 'High' prices.")
    
    # stock_data['Return'] = None  # Initialize the 'Return' column with None

    # for i in range(len(stock_data) - 1):
    #     today_high = stock_data['High'].iloc[i]
    #     for j in range(i + 1, len(stock_data)):
    #         if stock_data['Close'].iloc[j] > stock_data['High'].iloc[i]:
    #             stock_data.loc[stock_data.index[i], 'Return'] = (stock_data['Close'].iloc[j] - today_high) / today_high
    #             break
    
    # stock_data.dropna(subset=['Return'], inplace=True)  # Remove rows where 'Return' is still None
    # return stock_data

    # TT exit
    if 'Close' not in stock_data.columns or 'High' not in stock_data.columns:
        raise ValueError("The fetched data does not contain 'Close' or 'High' prices.")
    
    stock_data['Return'] = None  # Initialize the 'Return' column with None

    # simulated_returns = 1.0
    # for i in range(len(stock_data) - 1):
    #     today_close = stock_data['Close'].iloc[i]
    #     today_day_name = stock_data.index[i].day_name()
    #     for j in range(i + 1, len(stock_data)):
    #         if stock_data['Close'].iloc[j] > stock_data['High'].iloc[j-1]:
    #             stock_data.loc[stock_data.index[i], 'Return'] = (stock_data['Close'].iloc[j] - today_close) / today_close
    #             if (today_day_name == 'Monday' or today_day_name == 'Tuesday'):
    #                 simulated_returns *= (1 + stock_data['Return'].iloc[i])
    #             break

    import pandas as pd
    from itertools import permutations
    def calculate_simulated_returns(stock_data, day_pair):
        simulated_returns = 1.0
        for i in range(len(stock_data) - 1):
            today_close = stock_data['Close'].iloc[i]
            today_day_name = stock_data.index[i].day_name()
            for j in range(i + 1, len(stock_data)):
                if stock_data['Close'].iloc[j] > stock_data['High'].iloc[j-1]:
                    stock_data.loc[stock_data.index[i], 'Return'] = (stock_data['Close'].iloc[j] - today_close) / today_close
                    if today_day_name in day_pair:
                        simulated_returns *= (1 + stock_data['Return'].iloc[i])
                    break
        return simulated_returns

    # List of all weekdays
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    # Generate all permutations of weekday pairs
    weekday_pairs = permutations(weekdays, 2)

    # Calculate and print simulated returns for each pair
    results = []
    for pair in weekday_pairs:
        simulated_return = calculate_simulated_returns(stock_data, pair)
        results.append((pair, simulated_return))

    # Print results
    for pair, simulated_return in results:
        print(f"Weekday pair: {pair}, Cumulative return: {(simulated_return*100):.2f}%")
    
    stock_data.dropna(subset=['Return'], inplace=True)  # Remove rows where 'Return' is still None
    return stock_data

def classify_and_summarize_returns(stock_data):
    stock_data['Weekday'] = stock_data.index.day_name()

    valid_days = []
    for i in range(2, len(stock_data)):
        if stock_data['Close'].iloc[i-2] > stock_data['Close'].iloc[i-1] > stock_data['Close'].iloc[i]:
            valid_days.append(stock_data.index[i])
    
    valid_stock_data = stock_data.loc[valid_days]
    
    summary = {}
    
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        day_data = valid_stock_data[valid_stock_data['Weekday'] == day]
        positive_returns = day_data[day_data['Return'] > 0]
        non_positive_returns = day_data[day_data['Return'] <= 0]

        simulated_returns = 100.0
        if not day_data.empty:
        # Iterate through the rows of day_data
            for i in range(len(day_data)):
                simulated_returns *= (1 + float(day_data['Return'].iloc[i]))
        
        total_days_positive = len(positive_returns)
        total_days_non_positive = len(non_positive_returns)
        total_return_percent = day_data['Return'].sum() * 100

        if not day_data.empty:
            lowest_return = day_data['Return'].min() * 100
            highest_return = day_data['Return'].max() * 100
        else:
            lowest_return = None
            highest_return = None
        
        summary[day] = {
            'Total Trading Days': total_days_positive + total_days_non_positive,
            'Total Positive Days': total_days_positive,
            'Total Non-Positive Days': total_days_non_positive,
            'Total Return (%)': total_return_percent,
            'Lowest Return (%)': lowest_return,
            'Highest Return (%)': highest_return,
            'Simulated Return (%)': simulated_returns
        }
    
    return summary

def main():
    ticker = input("Enter the stock ticker: ")
    
    while True:
        start_date = input("Enter the start date (YYYY-MM-DD): ")
        end_date = input("Enter the end date (YYYY-MM-DD): ")
        try:
            pd.to_datetime(start_date, format='%Y-%m-%d')
            pd.to_datetime(end_date, format='%Y-%m-%d')
            break
        except ValueError:
            print("Incorrect date format. Please enter the date in YYYY-MM-DD format.")
    
    try:
        stock_data = get_stock_data(ticker, start_date, end_date)
        stock_data = calculate_returns(stock_data)
        
        summary = classify_and_summarize_returns(stock_data)
        
        # for day, values in summary.items():
        #     print(f"{day}:")
        #     print(f"  Total trading days: {values['Total Trading Days']}")
        #     print(f"  Total Positive Days: {values['Total Positive Days']}")
        #     print(f"  Total Non-Positive Days: {values['Total Non-Positive Days']}")
        #     print(f"  Total Return (%): {values['Total Return (%)']:.2f}%\n")
        #     print(f"  Lowest Return (%): {values['Lowest Return (%)']:.2f}%")
        #     print(f"  Highest Return (%): {values['Highest Return (%)']:.2f}%")
        #     print(f"  Simulated Return (%): {values['Simulated Return (%)']:.2f}%")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
