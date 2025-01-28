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

def get_stock_data(ticker, start_date, end_date):
    stock_data = yf.download(ticker, start=start_date, end=end_date)
    if stock_data.empty:
        raise ValueError("No data fetched for the given ticker and date range.")
    return stock_data

def calculate_returns(stock_data):
    if 'Close' not in stock_data.columns:
        raise ValueError("The fetched data does not contain 'Close' prices.")
    
    stock_data['Return'] = stock_data['Close'].pct_change()
    stock_data.dropna(inplace=True)
    return stock_data

def classify_and_summarize_returns(stock_data):
    stock_data['Weekday'] = stock_data.index.day_name()
    
    summary = {}
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        day_data = stock_data[stock_data['Weekday'] == day]
        positive_returns = day_data[day_data['Return'] > 0]
        non_positive_returns = day_data[day_data['Return'] <= 0]
        
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
            'Highest Return (%)': highest_return
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
        
        for day, values in summary.items():
            print(f"{day}:")
            print(f"  Total trading days: {values['Total Trading Days']}")
            print(f"  Total Positive Days: {values['Total Positive Days']}")
            print(f"  Total Non-Positive Days: {values['Total Non-Positive Days']}")
            print(f"  Total Return (%): {values['Total Return (%)']:.2f}%\n")
            print(f"  Lowest Return (%): {values['Lowest Return (%)']:.2f}%")
            print(f"  Highest Return (%): {values['Highest Return (%)']:.2f}%\n")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
