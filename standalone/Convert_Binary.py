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
import os
import pandas as pd

def convert_dataframe(dataFrame:pd.DataFrame)->pd.DataFrame:
        # Initialize the output DataFrame with the same time column and an empty price column
        result_df = pd.DataFrame({
            'Datetime': dataFrame['Date'],
            'Price': 0.0
        })

        # Initialize previous prices for comparison
        previous_bidPrice = None
        previous_askPrice = None

        for index, row in dataFrame.iterrows():
            bidPrice = float(row['Bid Price'])
            askPrice = float(row['Ask Price'])

            if previous_bidPrice is None and previous_askPrice is None:
                # This is the first iteration, both are considered changed
                price = (bidPrice + askPrice) / 2
            else:
                bid_changed = bidPrice != previous_bidPrice
                ask_changed = askPrice != previous_askPrice

                if bid_changed and not ask_changed:
                    # Only bidPrice changed
                    price = bidPrice
                elif ask_changed and not bid_changed:
                    # Only askPrice changed
                    price = askPrice
                else:
                    # Both changed or none changed
                    price = (bidPrice + askPrice) / 2

            # Update the price in the result DataFrame
            result_df.at[index, 'Price'] = price

            # Update previous prices for the next iteration
            previous_bidPrice = bidPrice
            previous_askPrice = askPrice

        return result_df

def convert_excel_to_pickle(root_folder):
    # Walk through all subdirectories and files in the root folder
    for subdir, _, files in os.walk(root_folder):
        for file in files:
            # Check if the file is an Excel file
            if file.endswith(('.xlsx', '.xls')):
                print(f"Converting {file}...")
                file_path = os.path.join(subdir, file)
                
                # Read the Excel file into a DataFrame
                try:
                    #df = pd.read_excel(file_path)
                    df = pd.read_excel(file_path, engine='openpyxl')
                    df = convert_dataframe(df)
                    
                    # Generate the output pickle file path
                    pickle_file_path = os.path.splitext(file_path)[0] + '.parquet'
                    
                    # # Save the DataFrame as a Pickle file
                    # with open(pickle_file_path, 'wb') as f:
                    #     pickle.dump(df, f)
                    df.to_parquet(pickle_file_path)

                    os.remove(file_path)
                    print(f"Converted {file_path} to {pickle_file_path}")

                except Exception as e:
                    print(f"Failed to convert {file_path}: {e}")

file_dir = os.path.dirname(os.path.realpath(__file__))
dataLocation = ((file_dir) + r"\BacktestData\\")
convert_excel_to_pickle(dataLocation)
