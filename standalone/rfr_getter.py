import yfinance as yf

# Fetch the data for the 3-month Treasury Bill (^IRX) and Get the latest yield
latest_yield = yf.Ticker("^IRX").history(period="1d")['Close'].iloc[-1]
risk_free_rate = latest_yield / 100  # Convert from percentage to decimal

print(f'Current 3-month Treasury Bill Yield (Risk-Free Rate): {risk_free_rate}')