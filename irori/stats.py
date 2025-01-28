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
from __future__ import division
import datetime
from typing import List
import numpy as np
import xlsxwriter
import os
from irori.common import PositionsResponse
import pandas as pd
import yfinance as yf

class ExposureTracker:
    def __init__(self, positions:PositionsResponse, date_time:datetime):
        self.last_updated:datetime = date_time
        self.elapsed_time:datetime.timedelta = datetime.timedelta(0)
        if (len(positions.stockList) == 0):
            self.is_tracking:bool = False
        else:
            self.is_tracking:bool = True

    def update_expoure_time(self, positions:PositionsResponse, date_time:datetime):
        if self.is_tracking:
            if not positions.stockList:
                self.elapsed_time += date_time - self.last_updated
                self.is_tracking = False
        else:
            if positions.stockList:
                self.is_tracking = True
    
    def day_end(self, date_time:datetime):
        if self.is_tracking:
            self.elapsed_time += date_time - self.last_updated

class DailyStockStat():
    def __init__(self, ticker: str, open:float = 0.0, close:float = 0.0, high:float = 0.0, low:float = 0.0):
        self.ticker: str = ticker
        self.open: float = open
        self.close: float = close
        self.high: float = high
        self.low: float = low
        self.dv_image:str = ""
        self.trend_type:str = 'Skipped'
        self.is_high_amplitude:str = 'Skipped'

        percentage_difference = ((self.close - self.open) / self.open) * 100
        abs_percentage = abs(percentage_difference)

        def get_is_high_amplitude(open:float, highest_price:float, lowest_price:float, threshold:float) -> bool:
            if abs(highest_price - open) / open > threshold or abs(lowest_price - open) / open > threshold:
                return True
            return False

        if abs_percentage < 2.5:
            self.trend_type = 'Neutral'
            self.is_high_amplitude = get_is_high_amplitude(self.open, float(self.high), float(self.low), 0.03)
        elif abs_percentage < 5:
            if percentage_difference > 0:
                self.trend_type = 'Bullish'
            else:
                self.trend_type = 'Bearish'
            self.is_high_amplitude = get_is_high_amplitude(self.open, float(self.high), float(self.low), 0.05)
        elif abs_percentage >= 5:
            if percentage_difference > 0:
                self.trend_type = 'Very Bullish'
            else:
                self.trend_type = 'Very Bearish'
            self.is_high_amplitude = get_is_high_amplitude(self.open, float(self.high), float(self.low), 0.08)

    def __str__(self) -> str:
        return f"{self.ticker} - Open: {self.open}, Close: {self.close}, High: {self.high}, Low: {self.low}"

class Trade:
    def __init__(self):
        self.date_time:datetime
        self.ticker:str
        self.price:float
        self.quantity:int
        self.fees:float
        self.net_returns:float
        self.buy_sell:str
        self.remarks = ""

class IntradayStats:
    def __init__(self, date_time:datetime, starting_funds:float, gross_value:float, positions:PositionsResponse):
        self.start_date_time:datetime = date_time
        self.trades:List[Trade] = []
        self.starting_funds:float = starting_funds
        self.starting_gross_value:float = gross_value
        self.end_gross_value:float = 0
        self.daily_returns_gross_p:float = 0.0
        self.daily_returns_gross_flat:float = 0.0
        self.total_fees:float = 0
        self.comments:str = ""
        
        self.exposure_time:float = 0
        self.exposure_tracker:ExposureTracker = ExposureTracker(positions, date_time)
        from irori.Backtester import DailyStockStat as DSS
        self.daily_stock_stat_list:list[DSS] = None
    
    def calculate_end(self, end_funds:float, last_tick_time:datetime):
        self.end_gross_value = end_funds
        self.total_fees = sum(trade.fees for trade in self.trades)
        self.daily_returns_gross_flat = self.end_gross_value - self.starting_gross_value
        if (self.starting_gross_value == 0):
            self.daily_returns_gross_p = 0
        else:
            self.daily_returns_gross_p = self.daily_returns_gross_flat / self.starting_gross_value
        self.exposure_tracker.day_end(last_tick_time)
        total_time:datetime.timedelta = last_tick_time - self.start_date_time
        self.exposure_time = self.exposure_tracker.elapsed_time.total_seconds() / total_time.total_seconds()

class StrategyStats:
    def __init__(self, starting_funds:float):
        self.recorded_days:List[IntradayStats] = []
        self.starting_funds:float = starting_funds
        self.end_funds:float = 0
        self.risk = 0
        self.total_profit:float = 0
        self.total_profit_percentage:float = 0
        self.no_of_profitable_days:int = 0
        self.no_of_loss_days:int = 0
        self.total_trades:int = 0
        self.total_fees:float = 0
        self.total_fees_percentage:float = 0
        self.sharpe_ratio:float = 0
        self.average_r_multiple:float = 0
        self.total_exposure_time:float = 0
        self.most_profitable_day:str = None
        self.most_profitable_day_return:float = 0
        self.most_profitable_day_return_percentage:float = 0
        self.least_profitable_day:str = None
        self.least_profitable_day_return:float = 0
        self.least_profitable_day_return_percentage:float = 0
        self.most_profitable_day_p:str = None
        self.most_profitable_day_p_flat:float = 0
        self.most_profitable_day_p_percentage:float = 0
        self.least_profitable_day_p:str = None
        self.least_profitable_day_p_flat:float = 0
        self.least_profitable_day_p_percentage:float = 0
        self.max_drawdown:float = 0
        self.max_drawdown_percentage:float = 0
        self.winrate:str = ''

    def __str__(self):
        details = [
                "\n-------------------- Details --------------------\n"
                f"Total returns: {self.total_profit:,.2f}\n"
                f"Total fees: {self.total_fees:,.2f}\n"
                f"Fees % of starting funds: {self.total_fees_percentage:.2%}\n"
                f"Total trades: {self.total_trades}\n"
                f"Winning pair trades: {self.winning_trades}\n"
                f"Losing pair trades: {self.losing_trades}\n"
                f"Trading win rate: {self.winrate}\n"
                f"Peak: {self.peak:,.2f}\n"
                f"Trough: {self.trough:,.2f}\n"
                f"Max Drawdown: {self.max_drawdown:,.2f}\n"
                f"Max Drawdown(%): {self.max_drawdown_percentage:.2%}\n"
                f"-------------------- Day data --------------------\n"
                f"Total days: {len(self.recorded_days)}\n"
                f"Start Date: {self.recorded_days[0].start_date_time.strftime('%Y-%m-%d')}\n"
                f"End Date: {self.recorded_days[-1].start_date_time.strftime('%Y-%m-%d')}\n"
                f"No of inactive days: {self.inactive_days}\n"
                f"No of trading days: {self.total_trading_days}\n"
                f"No of profitable days: {self.no_of_profitable_days}\n"
                f"Average profitable day profits: {self.profitable_day_profits_avg:.2%}\n"
                f"No of unprofitable days: {self.no_of_loss_days}\n"
                f"Average loss day losses: {self.loss_day_losses_avg:.2%}\n"
                f"Day WR: {0 if self.no_of_profitable_days == 0 else self.no_of_profitable_days / self.total_trading_days:.2%}\n"
                "-------------------- Best daily returns --------------------\n"
                f"Date: {self.most_profitable_day}\n"
                f"Returns: {self.most_profitable_day_return:.2f}\n"
                f"Returns(%): {self.most_profitable_day_return_percentage:.2%}\n"
                "-------------------- Worst daily returns --------------------\n"
                f"Date: {self.least_profitable_day}\n"
                f"Returns: {self.least_profitable_day_return:.2f}\n"
                f"Returns(%): {self.least_profitable_day_return_percentage:.2%}\n"
                 "-------------------- Best daily returns (%) --------------------\n"
                f"Date: {self.most_profitable_day_p}\n"
                f"Returns: {self.most_profitable_day_p_flat:.2f}\n"
                f"Returns(%): {self.most_profitable_day_p_percentage:.2%}\n"
                "-------------------- Worst daily returns (%) --------------------\n"
                f"Date: {self.least_profitable_day_p}\n"
                f"Returns: {self.least_profitable_day_p_flat:.2f}\n"
                f"Returns(%): {self.least_profitable_day_p_percentage:.2%}\n"
                f"-------------------- Strategy Stats --------------------\n"
                f"Total days: {len(self.recorded_days)}\n"
                f"Starting funds: {self.starting_funds:,.2f}\n"
                f"End funds: {self.end_funds:,.2f}\n"
                f"Sharpe ratio ({self.risk_free_rate:.2%} annual): {self.sharpe_ratio if isinstance(self.sharpe_ratio, str) else f'{self.sharpe_ratio:.5f}'}\n"
                #f"R multiple average (Capital as R): {self.average_r_multiple:.5f}\n"
                f"R multiple average: {'Not available'}\n"
                f"Total exposure time: {self.total_exposure_time:.2%}\n"
                f"TWR % (Time-weighted returns): {self.time_weighted_returns:.2%}\n"
                f"Annualized returns: {self.annual_returns:.2%}\n"
                f"Beta (Against QQQ): {self.beta}\n"
                f"Simulated returns: {self.total_profit_percentage:.2%}\n"
                f"-------------------- Benchmark (yfinance)--------------------\n"
                f"SPX Growth: {self.spx_growth}%\n"
                f"QQQ Growth: {self.qqq_growth}%\n"
                f"-------------------- Benchmark (Simulated) --------------------"
        ]

        for i in range(len(self.recorded_days[0].daily_stock_stat_list)):
            ticker = self.recorded_days[0].daily_stock_stat_list[i].ticker
            start = self.recorded_days[0].daily_stock_stat_list[i].open
            end = self.recorded_days[-1].daily_stock_stat_list[i].close

            growth = (end - start) / start * 100
            details.append(f"{ticker} Growth: {growth:.2f}%")

        return "\n".join(details)

    def calculate_stats(self, positions:PositionsResponse, end_funds:float = 0, returns:List[float] = []):
        self.positions = positions
        if (end_funds == 0):
            self.end_funds = self.starting_funds + sum(day.end_gross_value - day.starting_gross_value for day in self.recorded_days)
        else:
            self.end_funds = end_funds
        self.total_profit = self.end_funds - self.starting_funds
        self.total_profit_percentage = self.total_profit / self.starting_funds
        self.total_trades = sum(len(day.trades) for day in self.recorded_days)
        self.no_of_profitable_days = sum(1 for day in self.recorded_days if day.end_gross_value > day.starting_gross_value)
        self.no_of_loss_days = sum(1 for day in self.recorded_days if day.end_gross_value < day.starting_gross_value)
        self.total_fees = sum(sum(trade.fees for trade in day.trades) for day in self.recorded_days)
        self.total_fees_percentage = self.total_fees / self.starting_funds if self.total_profit != 0 else 0

        end_gross_values = [stat.end_gross_value for stat in self.recorded_days]
        self.peak = max(end_gross_values)
        self.trough = min(end_gross_values)

        cumulative_returns = [stat.end_gross_value for stat in self.recorded_days]
        peak_value = cumulative_returns[0]
        max_drawdown = 0

        for value in cumulative_returns:
            if value > peak_value:
                peak_value = value
            drawdown = (peak_value - value) / peak_value
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        self.max_drawdown = max_drawdown * self.starting_funds
        self.max_drawdown_percentage = max_drawdown

        if self.recorded_days:
            daily_profits = [(day.daily_returns_gross_flat) for day in self.recorded_days]

            if daily_profits:  # Check if daily_profits is not empty
                max_profit = max(daily_profits)
                min_profit = min(daily_profits)
                max_profit_index = daily_profits.index(max_profit)
                min_profit_index = daily_profits.index(min_profit)

                # Check if there are any trades on the most profitable and least profitable days
                self.most_profitable_day = (self.recorded_days[max_profit_index].start_date_time).strftime('%Y-%m-%d')
                self.most_profitable_day_return = max_profit
                self.most_profitable_day_return_percentage = self.recorded_days[max_profit_index].daily_returns_gross_p
                self.least_profitable_day = (self.recorded_days[min_profit_index].start_date_time).strftime('%Y-%m-%d')
                self.least_profitable_day_return = min_profit
                self.least_profitable_day_return_percentage = self.recorded_days[min_profit_index].daily_returns_gross_p

            daily_profits_percentage = [(day.daily_returns_gross_p) for day in self.recorded_days]

            if daily_profits_percentage:  # Check if daily_profits is not empty
                max_profit_percentage = max(daily_profits_percentage)
                min_profit_percentage = min(daily_profits_percentage)
                max_profit_index = daily_profits_percentage.index(max_profit_percentage)
                min_profit_index = daily_profits_percentage.index(min_profit_percentage)

                # Check if there are any trades on the most profitable and least profitable days
                self.most_profitable_day_p = (self.recorded_days[max_profit_index].start_date_time).strftime('%Y-%m-%d')
                self.most_profitable_day_p_flat = self.recorded_days[max_profit_index].daily_returns_gross_flat
                self.most_profitable_day_p_percentage = max_profit_percentage
                self.least_profitable_day_p = (self.recorded_days[min_profit_index].start_date_time).strftime('%Y-%m-%d')
                self.least_profitable_day_p_flat = self.recorded_days[min_profit_index].daily_returns_gross_flat
                self.least_profitable_day_p_percentage = min_profit_percentage

        self.total_trading_days = self.no_of_profitable_days + self.no_of_loss_days
        self.inactive_days = len(self.recorded_days) - self.total_trading_days

        profitable_day_profits = 0
        loss_day_losses = 0

        total_exposure_time:float = 0
        for day in self.recorded_days:
            total_exposure_time += day.exposure_time
            if (day.daily_returns_gross_p > 0):
                profitable_day_profits += day.daily_returns_gross_p
            elif (day.daily_returns_gross_p < 0):
                loss_day_losses += day.daily_returns_gross_p

        self.profitable_day_profits_avg = profitable_day_profits/self.no_of_profitable_days if self.no_of_profitable_days != 0 else 0
        self.loss_day_losses_avg = loss_day_losses/self.no_of_loss_days if self.no_of_loss_days != 0 else 0
        self.total_exposure_time = total_exposure_time / len(self.recorded_days)

        self.annual_returns = ((self.end_funds / self.starting_funds) ** (252 / len(self.recorded_days))) - 1
        if (self.total_exposure_time != 0):
            self.time_weighted_returns = self.total_profit_percentage / self.total_exposure_time
        else:
            self.time_weighted_returns = 0

        self.average_r_multiple = self.calculate_average_r_multiple()
        bond_ticker = yf.Ticker("^IRX")
        history = bond_ticker.history(period="1d")

        if not history.empty:
            latest_yield = history['Close'].iloc[-1]
        else:
            # Handle the case where there is no data
            latest_yield = 1
        
        self.risk_free_rate = latest_yield / 100
        self.sharpe_ratio = self.calculate_sharpe_ratio(returns=returns)
        self.winning_trades = sum(1 for trade in returns if trade > 0)
        self.losing_trades = sum(1 for trade in returns if trade < 0)
        if (len(returns) == 0):
            self.winning_trades = 'Not available'
            self.losing_trades = 'Not available'
            self.winrate = 'Not available'
        elif isinstance(self.winning_trades, int) and isinstance(self.losing_trades, int) and self.winning_trades + self.losing_trades > 0:
            self.winrate = f"{self.winning_trades / (self.winning_trades + self.losing_trades):.2%}"
        else:
            self.winrate = 'Not available'

        start_date = self.recorded_days[0].start_date_time.strftime('%Y-%m-%d')
        end_date = self.recorded_days[-1].start_date_time.strftime('%Y-%m-%d')

        tickers = ["^GSPC", "QQQ"]

        # Download the stock data
        data = yf.download(tickers, start=start_date, end=end_date, progress=False)

        if data['Open']['^GSPC'].empty:
            self.beta = 'Not available'
            self.spx_growth = 'Not available'
            self.qqq_growth = 'Not available'
            return

        # Calculate the growth
        spx_open_start = data['Open']['^GSPC'].iloc[0]
        spx_close_end = data['Close']['^GSPC'].iloc[-1]
        qqq_open_start = data['Open']['QQQ'].iloc[0]
        qqq_close_end = data['Close']['QQQ'].iloc[-1]

        self.spx_growth = f"{(spx_close_end - spx_open_start) / spx_open_start * 100:.2f}"
        self.qqq_growth = f"{(qqq_close_end - qqq_open_start) / qqq_open_start * 100:.2f}"

        # Resample the returns to different frequencies and calculate the mean
        returns = data.pct_change()
        weekly_returns = returns.resample('W').mean()
        monthly_returns = returns.resample('ME').mean()
        annual_returns = returns.resample('YE').mean()

        # Calculate the average returns for each frequency
        average_weekly_return_spx = weekly_returns[('Adj Close', '^GSPC')].mean() * 100
        average_monthly_return_spx = monthly_returns[('Adj Close', '^GSPC')].mean() * 100
        average_annual_return_spx = annual_returns[('Adj Close', '^GSPC')].mean() * 100

        average_weekly_return_qqq = weekly_returns[('Adj Close', 'QQQ')].mean() * 100
        average_monthly_return_qqq = monthly_returns[('Adj Close', 'QQQ')].mean() * 100
        average_annual_return_qqq = annual_returns[('Adj Close', 'QQQ')].mean() * 100

        monthly_returns = (1 + self.annual_returns) ** (1/12) - 1

        # Calculate daily returns (assuming 252 trading days in a year)
        weekly_returns = (1 + self.annual_returns) ** (1/63) - 1

        # print(f"SPX annual Growth: {average_annual_return_spx:.2%}")
        # print(f"QQQ annual Growth: {average_annual_return_qqq:.2%}")
        # print(f"Strategy annual Growth: {self.annual_returns:.2%}")
        # print(f"Annual beta against SPX: {self.annual_returns/average_annual_return_spx:.5f}")
        # print(f"Annual beta against QQQ: {self.annual_returns/average_annual_return_qqq:.5f}")

        # print(f"SPX monthly Growth: {average_monthly_return_spx:.2%}")
        # print(f"QQQ monthly Growth: {average_monthly_return_qqq:.2%}")
        # print(f"Strategy monthly Growth: {monthly_returns:.2%}")
        # print(f"Monthly beta against SPX: {monthly_returns/average_monthly_return_spx:.5f}")
        # print(f"Monthly beta against QQQ: {monthly_returns/average_monthly_return_qqq:.5f}")

        # print(f"SPX weekly Growth: {average_weekly_return_spx:.2%}")
        # print(f"QQQ weekly Growth: {average_weekly_return_qqq:.2%}")
        # print(f"Strategy weekly Growth: {weekly_returns:.2%}")
        # print(f"Weekly beta against SPX: {weekly_returns/average_weekly_return_spx:.5f}")
        # print(f"Weekly beta against QQQ: {weekly_returns/average_weekly_return_qqq:.5f}")

        self.beta = f"{self.annual_returns/average_annual_return_qqq:.5f}"

    def calculate_average_r_multiple(self):
        daily_returns = np.array([(day.end_gross_value - day.starting_gross_value) / self.starting_funds for day in self.recorded_days if day.daily_returns_gross_p != 0])
        if len(daily_returns) == 0:
            return np.nan
        return np.mean(daily_returns) / 100 + 1

    def calculate_sharpe_ratio(self, returns:List[float] = []):
        if len(returns) == 0:
            return 'Not available'
        
        daily_rfr = (1 + self.risk_free_rate) ** (1 / 252) - 1
        
        excess_returns = [r - daily_rfr for r in returns]

        # Calculate the average excess return
        average_excess_return = sum(excess_returns) / len(excess_returns)

        # Calculate the standard deviation of the investment returns
        mean_return = sum(returns) / len(returns)
        std_dev = (sum((r - mean_return) ** 2 for r in returns) / len(returns)) ** 0.5

        if std_dev == 0:
            return 'Not available'
        else:
            # Calculate the Sharpe Ratio
            sharpe_ratio = average_excess_return / std_dev
            return sharpe_ratio
    
    def write_to_excel(self, data_location: str, session_id: str):
        def rgb2hex(r,g,b):
            red = int(r)
            green = int(g)
            blue = int(b)
            finalhex = f'#{red:02x}{green:02x}{blue:02x}'
            return finalhex
        
        if not os.path.exists(data_location):
                os.makedirs(data_location)
        # Create a workbook and add a worksheet
        workbook = xlsxwriter.Workbook(data_location+f"\\_Summary_{session_id}.xlsx")

        center_format = workbook.add_format({'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'align': 'center'})
        num_format = workbook.add_format({'align': 'center', 'num_format': '#,##0.00'})
        int_format = workbook.add_format({'align': 'center', 'num_format': '#,##0'})
        summary_header_format = workbook.add_format({'font_size': 13,'bold': True,'align': 'center'})

        # Add a main worksheet for dates
        main_worksheet = workbook.add_worksheet('Dates')
        headers = ['Date', 'Day', 'Start Gross Value', 'End Gross Value', 'Daily Returns(%)', 'Comments']
        for col, header in enumerate(headers):
            main_worksheet.write(0, col, header, header_format)
        main_worksheet.set_column('A:A', 9.5, header_format)
        main_worksheet.set_column('B:B', 10.5, center_format)
        main_worksheet.set_column('C:C', 15, num_format)
        main_worksheet.set_column('D:D', 15, num_format)
        main_worksheet.set_column('E:E', 15, num_format)
        main_worksheet.set_column('F:F', 30)
        # higher priority summary info
        main_worksheet.set_column('G:G', 40)    #this was originally used for the attr and values headers
        main_worksheet.set_column('H:H', 18)
        # lower priority summary info
        main_worksheet.set_column('I:I', 40)     
        main_worksheet.set_column('J:J', 18)
        main_worksheet.insert_image(0, 10, data_location+f"\\master_graph.png")
        main_worksheet.insert_image(29, 10, data_location+f"\\master_graph_log.png")
        # loop + var's responsible for writing in excel
        if (len(self.positions.stockList) > 0):
            positions_info = (f"-------------------- Positions Information --------------------, "
                              f"Ticker: Quantity, "
                              f"{str(self.positions)}"
                              ).split(', ')

            summary_info = str(self).split('\n') + positions_info
        else:
            summary_info = str(self).split('\n')
        low_prio = 0
        high_prio = 0
        # col I and J for low priority. high prio col num is assigned in the elif section of the for loop
        attibute_col = 8    
        value_col = 9       
        for line in summary_info:       
            if ':' in line:  # check for lines with attribute : value
                part_label, part_value = line.split(':', 1)  # Split at the first colon
                if attibute_col == 6:   # col G "high priority stuff"
                    # checking specifically for the line "Quantity: Ticker" declared in positions_info
                    if line.lower().strip() == "ticker: quantity":
                        main_worksheet.write(high_prio, attibute_col, part_label.strip(), summary_header_format)
                        main_worksheet.write(high_prio, value_col, part_value.strip(), summary_header_format)
                    else:
                        main_worksheet.write(high_prio, attibute_col, part_label.strip())
                        main_worksheet.write(high_prio, value_col, part_value.strip(), num_format)
                    high_prio +=1
                elif attibute_col== 8:  # "low priority stuff"
                    main_worksheet.write(low_prio, attibute_col, part_label.strip())
                    main_worksheet.write(low_prio, value_col, part_value.strip(), num_format)
                    low_prio += 1
            
            elif line !='':   #only process if lines are not blank     
                if 'Strategy Stats' in line:     #only change col Num on new headers
                    attibute_col = 6
                    value_col = 7

                # merge header cells based on which column we're printing in
                # .merge_range(first_row, first_col, last_row, last_col, DATA, FORMAT)
                if attibute_col == 6:   #"high priorty"
                    main_worksheet.merge_range(high_prio, attibute_col, high_prio, value_col, line, summary_header_format)
                    high_prio +=1
                elif attibute_col== 8:  #"low priority"
                    main_worksheet.merge_range(low_prio, attibute_col, low_prio, value_col, line, summary_header_format)
                    low_prio += 1
        
        # Add a worksheet for a daily heatmap
        daily_heatmap = workbook.add_worksheet('Daily Heatmap')
        daily_heatmap.set_column('A:A', 10, header_format)
        daily_heatmap.set_column('B:B', 10, header_format)
        daily_heatmap.set_column('C:C', 10, header_format)
        daily_heatmap.set_column('D:D', 10, header_format)
        daily_heatmap.set_column('E:E', 10, header_format)
        daily_heatmap.set_column('F:F', 10, header_format)
        daily_heatmap.set_column('G:G', 10, header_format)
        daily_heatmap.set_column('H:H', 10, header_format)
        daily_heatmap.set_column('I:I', 10, header_format)

        #find number of total days in between the first and last recorded day
        total_days = (self.recorded_days[-1].start_date_time - self.recorded_days[0].start_date_time).days + 1

        #find which day of the week the first recorded day is
        first_day_of_week = self.recorded_days[0].start_date_time.weekday()

        #Fill in B1 to I1 with the days of the week
        daily_heatmap.write(0, 1, 'Monday', header_format)
        daily_heatmap.write(0, 2, 'Tuesday', header_format)
        daily_heatmap.write(0, 3, 'Wednesday', header_format)
        daily_heatmap.write(0, 4, 'Thursday', header_format)
        daily_heatmap.write(0, 5, 'Friday', header_format)

        #get start day of strategy: 1 = Monday, 2 = Tuesday, 3 = Wednesday, 4 = Thursday, 5 = Friday
        row = 1
        start_day = self.recorded_days[0].start_date_time.weekday()
        current_day = start_day
        prev_day = start_day
        recorded_days = []
        recorded_data = []
        for day in self.recorded_days:
            current_day = day.start_date_time.weekday()
            if current_day<prev_day:
                row += 1
            daily_heatmap.write(row, current_day+1, f"{day.daily_returns_gross_p:.2%}", num_format)
            recorded_days.append((row, current_day+1))
            recorded_data.append(day.daily_returns_gross_p)
            prev_day = current_day

        #Set column A to width 25
        daily_heatmap.set_column('A:A', 25, header_format)
        
        #print the week ranges on the first column
        for i in range(row):
            if i == 0:
                firstDay = self.recorded_days[0].start_date_time
                if first_day_of_week != 0:
                    #get first theoritical monday, by getting the number of days before the first day of the week if its not a monday
                    daysbefore = start_day
                    #get the monday of the first week by subtracting it from firstDay
                    firstDay = firstDay - datetime.timedelta(days=daysbefore)

            #print for the left side of each row, the date range of the week.
            daily_heatmap.write(i+1, 0, f"{(firstDay+ datetime.timedelta(days=i*7)).strftime('%Y-%m-%d')} - {(firstDay + datetime.timedelta(days=4+i*7)).strftime('%Y-%m-%d')}", header_format)

        #iterate through all the days that are not filled in and fill in the rest of the days with "Market not opened"
        for i in range(row*5):
            row = i //5 + 1
            col = i % 5 + 1
            if (row, col) not in recorded_days:
                daily_heatmap.write(row, col, "No Data", num_format)
                #color the cell blue
                daily_heatmap.conditional_format(row, col, row, col, {'type': 'cell', 'criteria': '==', 'value': '"No Data"', 'format': workbook.add_format({'bg_color': '#ffffff'})})
            else:
                #get the index of the recorded day
                index = recorded_days.index((row, col))
                #get the daily returns of the recorded day
                daily_returns = recorded_data[index]
                color = ""
                #Determine Colour, via rgb to hex conversion
                #if >5%,(104, 255, 87), if 0%, (255,255,255) if <-5%, (255, 77, 64)
                if (self.least_profitable_day_p_percentage > self.most_profitable_day_p_percentage):
                    limit = self.least_profitable_day_p_percentage
                else:
                    limit = self.most_profitable_day_p_percentage

                limit *= 0.8
                if daily_returns > limit:
                    color = rgb2hex(104, 255, 87)

                elif daily_returns > 0:
                    #get lerped color
                    color = rgb2hex(104 + (255-104) * (1-(daily_returns / limit)), 255, 87+ (255-87) * (1-(daily_returns / limit)))

                elif daily_returns == 0:
                    color = rgb2hex(255, 255, 255)

                elif daily_returns > -limit:
                    color = rgb2hex(255, 77 + (255-77) * (1-(daily_returns / -limit)), 64+ (255-64) * (1-(daily_returns / -limit)))

                else:
                    color = rgb2hex(255, 77, 64)
                #color the cell based on the daily returns the cell white
                daily_heatmap.conditional_format(row, col, row, col, {'type': 'cell', 'criteria': '!=', 'value': '"No Data"', 'format': workbook.add_format({'bg_color': color})})

        # Loop through recorded days and create a worksheet for each date
        row = 1
        for intraday_stat in self.recorded_days:
            date_str = intraday_stat.start_date_time.strftime('%Y-%m-%d')
            day = intraday_stat.start_date_time.strftime('%A')
            worksheet = workbook.add_worksheet(date_str)     
            worksheet.set_column('A:A', 10, num_format)
            worksheet.set_column('B:B', 10, num_format)
            worksheet.set_column('C:C', 10, num_format)
            worksheet.set_column('D:D', 10, int_format)
            worksheet.set_column('E:E', 10, num_format)
            worksheet.set_column('F:F', 14, num_format)
            worksheet.set_column('G:G', 10, num_format)
            worksheet.set_column('I:I', 20, header_format)
            worksheet.set_column('J:J', 14, num_format)
            worksheet.set_column('L:L', 20, header_format)
            worksheet.set_column('M:M', 14, num_format)

            # Add hyperlink on the summary sheet to the new worksheet
            main_worksheet.write_url(row, 0, f"internal:'{date_str}'!A1", string=date_str)
            main_worksheet.write(row, 1, day)
            main_worksheet.write(row, 2, intraday_stat.starting_gross_value, num_format)
            main_worksheet.write(row, 3, intraday_stat.end_gross_value, num_format)
            main_worksheet.write(row, 4, f"{intraday_stat.daily_returns_gross_p:.2%}", num_format)
            main_worksheet.write(row, 5, intraday_stat.comments)

            # Image
            for i in range(len(intraday_stat.daily_stock_stat_list)):
                if intraday_stat.daily_stock_stat_list[i].dv_image != "":
                    worksheet.insert_image(i * 30, 13, intraday_stat.daily_stock_stat_list[i].dv_image)

            # Writing headers for the trades
            headers = ['Time', 'Ticker', 'Price', 'Quantity', 'Fees', 'Net Returns', 'Order Type', 'Remarks', 'Attributes', 'Values']
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            # Write trade details in the worksheet
            trade_row = 1
            for trade in intraday_stat.trades:
                worksheet.write(trade_row, 0, trade.date_time.strftime('%H:%M:%S'), center_format)
                worksheet.write(trade_row, 1, trade.ticker)
                worksheet.write(trade_row, 2, trade.price)
                worksheet.write(trade_row, 3, trade.quantity)
                worksheet.write(trade_row, 4, trade.fees)
                worksheet.write(trade_row, 5, trade.net_returns)
                worksheet.write(trade_row, 6, trade.buy_sell)
                worksheet.write(trade_row, 7, trade.remarks, center_format)
                trade_row += 1
            row += 1
            # Write the attributes of each intraday_stat
            attributes = [
                ('Day', day),
                ('Starting Funds', intraday_stat.starting_funds),
                ('Starting Gross Value', intraday_stat.starting_gross_value),
                ('End Gross Value', intraday_stat.end_gross_value),
                ('Daily Returns Gross', f"{intraday_stat.daily_returns_gross_p:.2%}"),
                ('Exposure time', f"{(intraday_stat.exposure_time):.2%}"),
                ('Total Fees', intraday_stat.total_fees),
            ]
            for i, (label, value) in enumerate(attributes, 2):
                worksheet.write(f'I{i}', label)
                worksheet.write(f'J{i}', value)
            worksheet.write_url(i+1, 9, "internal:'Dates'!A1", string="Back to Summary")

            sectionid:int = 0
            for dss in intraday_stat.daily_stock_stat_list:
                dss: 'DailyStockStat'
                worksheet.write(sectionid, 11, 'Ticker')
                worksheet.write(sectionid, 12, dss.ticker)
                worksheet.write(sectionid + 1, 11, 'Open')
                worksheet.write(sectionid + 1, 12, dss.open)
                worksheet.write(sectionid + 2, 11, 'Close')
                worksheet.write(sectionid + 2, 12, dss.close)
                worksheet.write(sectionid + 3, 11, 'Highest Price')
                worksheet.write(sectionid + 3, 12, dss.high)
                worksheet.write(sectionid + 4, 11, 'Lowest Price')
                worksheet.write(sectionid + 4, 12, dss.low)
                worksheet.write(sectionid + 5, 11, 'Trend Type')
                worksheet.write(sectionid + 5, 12, dss.trend_type)
                worksheet.write(sectionid + 6, 11, 'Is High Amplitude')
                worksheet.write(sectionid + 6, 12, dss.is_high_amplitude)
                sectionid += 30
        workbook.close()
        for intraday_stat in self.recorded_days:
            intraday_stat: 'IntradayStats'
            img_list = [intraday_stat.daily_stock_stat_list[i].dv_image for i in range(len(intraday_stat.daily_stock_stat_list))]
            for img_path in img_list:
                if img_path != "":
                    os.remove(img_path)
        if os.path.exists(data_location+f"\\master_graph.png"):
            os.remove(data_location+f"\\master_graph.png")
        if os.path.exists(data_location+f"\\master_graph_log.png"):
            os.remove(data_location+f"\\master_graph_log.png")
       
        print(f"Performance report saved to {data_location}\\_Summary_{session_id}.xlsx")