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
from supabase import create_client, Client
from jproperties import Properties
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.trade.trade_client import TradeClient
import logging
import math
from datetime import datetime
import uuid

# DO NOT MODIFY ANY FUNCTIONS IN THIS FILE

# Load properties from the Authentication.properties file
configs = Properties()
with open('Authentication.properties', 'rb') as config_file:
    configs.load(config_file)

# Retrieve the properties
url = configs.get("supabase_url").data
key = configs.get("supabase_key").data

# Initialize the Supabase client
supabase: Client = create_client(url, key)
tiger_client:TigerOpenClientConfig = None
trade_client:TradeClient = None

logging.getLogger("httpx").setLevel(logging.WARNING)

def get_trade_client() -> TradeClient:
    global tiger_client, trade_client
    if tiger_client is None:
        tiger_client = TigerOpenClientConfig(sandbox_debug=False)
        tiger_client.private_key = configs.get("private_key_pk1").data
        tiger_client.account = configs.get("account").data
        tiger_client.tiger_id = configs.get("tiger_id").data
        trade_client = TradeClient(tiger_client)

    return trade_client

def get_row_by_id(row_id: int):
    response = supabase.table("shareholders").select("*").eq("id", row_id).execute()
    if response.data:
        return response.data
    else:
        print("No user found with the provided ID.")
        return None
    
def get_id_by_email(email: str):
    response = supabase.table("shareholders").select("id").eq("email", email).execute()
    if response.data:
        return response.data[0]['id']
    else:
        print("No user found with the provided email.")
        return None
        
def get_id_by_phone_no(phone_no: str):
    response = supabase.table("shareholders").select("id").eq("phone_no", phone_no).execute()

    if response.data:
        return response.data[0]['id']
    else:
        print("No user found with the provided phone number.")
        return None
    
def register_user(name, phone_no:str, email, address, discord, remark = ""):
    # Check if email or phone number already exists
    email_response = supabase.table("shareholders").select("id").eq("email", email).execute()
    if email_response.data:
        print(f"User with email {email} already exists with ID: {email_response.data[0]['id']}")
        exit()
    
    # Check if phone number already exists
    phone_response = supabase.table("shareholders").select("id").eq("phone_no", phone_no).execute()
    if phone_response.data:
        print(f"User with phone number {phone_no} already exists with ID: {phone_response.data[0]['id']}")
        exit()

    if not phone_no.startswith("+"):
        raise ValueError("Phone number must start with '+'")
    
    # If both email and phone number are unique, insert new user
    data = {
        "name": name,
        "role": "Client",
        "phone_no": phone_no,
        "email": email,
        "address": address,
        "discord_id": discord,
        "shares": 0,
        "total_investment" : 0,
        "remark": remark
    }

    response = supabase.table("shareholders").insert(data).execute()
    if response.data:
        user_id = response.data[0]['id']  # Extract the ID from the response
        return user_id
    else:
        raise Exception(f"Error inserting data: {response}")
    
def edit_entry(user_id: int, name: str = None, phone_no: str = None, email: str = None, address: str = None, remark: str = None, role: str = None):
    # Prepare the data dictionary with only the provided values
    data = {}
    if name is not None:
        data["name"] = name
    if phone_no is not None:
        data["phone_no"] = phone_no
    if email is not None:
        data["email"] = email
    if address is not None:
        data["address"] = address
    if remark is not None:
        data["remark"] = remark
    if role is not None:
        data["role"] = role

    if not data:
        print("No data provided to update.")
        return
    
    # Update the entry in the table
    response = supabase.table("shareholders").update(data).eq("id", user_id).execute()
    
    if response.data != []:
        print("Entry updated successfully.")
    else:
        print("Error: no user found")

def get_total_shares():
    response = supabase.rpc("get_total_shares", {}).execute()
    
    if response.data:
        return response.data[0]['sum']
    else:
        print("Error retrieving total shares:", response.error)
        return 0

def get_share_price():
    return get_portfolio_gross_value()/get_total_shares()

def get_portfolio_gross_value() -> float:
    portfolio_account = get_trade_client().get_prime_assets(base_currency="USD")
    return portfolio_account.segments['S'].equity_with_loan

def add_transaction_log_entry(user_id: uuid.UUID, initial_value: float, last_known_value: float, action: str, status: str):
    data = {
        "user_id": user_id,
        "transaction_datetime": datetime.now().isoformat(),
        "inital_value": initial_value,
        "last_known_value": last_known_value,
        "royalties": 0.0,
        "action": action,
        "status": status
    }

    response = supabase.table("transaction_log").insert(data).execute()
    if response.data:
        return response.data[0]
    else:
        raise Exception(f"Error inserting transaction log entry: {response}")

def get_transaction_log_entry_by_id(transaction_id: uuid.UUID):
    response = supabase.table("transaction_log").select("*").eq("transaction_id", transaction_id).execute()
    if response.data:
        return response.data[0]
    else:
        print("No transaction log entry found with the provided ID.")
        return None

def get_transaction_log_entries_by_user_id(user_id: uuid.UUID):
    response = supabase.table("transaction_log").select("*").eq("user_id", user_id).execute()
    if response.data:
        return response.data
    else:
        print("No transaction log entries found for the provided user ID.")
        return []

def update_transaction_log_entry(transaction_id: uuid.UUID, last_known_value: float, status: str):
    data = {
        "last_known_value": last_known_value,
        "status": status
    }

    response = supabase.table("transaction_log").update(data).eq("transaction_id", transaction_id).execute()
    if response.data:
        print("Transaction log entry updated successfully.")
        return response.data[0]
    else:
        print("Error: no transaction log entry found or failed to update.")
        return None
    
def complete_deposit(transaction_id: str, total_investment: float):
    # Get transaction log entry
    transaction = get_transaction_log_entry_by_id(uuid.UUID(transaction_id))
    if not transaction:
        print("Transaction not found.")
        return None
    
    user_id = transaction['user_id']
    last_known_value = transaction['last_known_value']

    # Get the current share price
    share_price = get_share_price()
    shares_added = last_known_value / share_price

    # Update the user's total_investment and shares
    response = supabase.table("shareholders").select("total_investment", "shares").eq("id", user_id).execute()
    if response.data:
        current_investment = response.data[0]['total_investment']
        current_shares = response.data[0]['shares']

        new_investment = current_investment + last_known_value
        new_shares = current_shares + shares_added

        update_data = {
            "total_investment": new_investment,
            "shares": new_shares
        }

        update_response = supabase.table("shareholders").update(update_data).eq("id", user_id).execute()
        if update_response.data:
            print("Shareholder's investment and shares updated successfully.")
        else:
            print("Failed to update shareholder's investment and shares.")
    else:
        print("User not found.")
        return None

    # Update the transaction log entry status
    updated_entry = update_transaction_log_entry(uuid.UUID(transaction_id), last_known_value, 'Completed')
    return updated_entry

def query_withdraw_details(user_id: uuid.UUID, shares: float, interval_in_years:float = 1, projected_share_value: float = 0.0):
    def calculate_royalties(x):
        if x <= 1000000:
            y = 2 - (x / 1000000)
        else:
            y = 1 / math.log10(x - 999999)
        return y
    # Get the current share price
    share_price = get_share_price()

    # Calculate the amount to be withdrawn
    amount_withdrawn = shares * share_price

    # Retrieve the user's total investment from the shareholders table
    response = supabase.table("shareholders").select("total_investment", "shares").eq("id", user_id).execute()
    
    if response.data:
        total_investment = response.data[0]['total_investment']
        total_shares = response.data[0]['shares']
        
        # Calculate initial investment per share
        initial_investment_per_share = total_investment / total_shares if total_shares != 0 else 0
        
        # Calculate profit percentage per share
        profit_percentage_per_share = 0
        if (projected_share_value > 0):
            profit_percentage_per_share = ((projected_share_value - initial_investment_per_share) / initial_investment_per_share) * 100 if initial_investment_per_share != 0 else 0
        else:
            profit_percentage_per_share = ((share_price - initial_investment_per_share) / initial_investment_per_share) * 100 if initial_investment_per_share != 0 else 0

        # Calculate royalties
        royalty_rate = calculate_royalties(get_portfolio_gross_value())
        royalties = 0
        if initial_investment_per_share * (1 + royalty_rate/100) > share_price:
            royalties = royalty_rate

        # Calculate recommended commission
        recommended_commission = profit_percentage_per_share - royalties - (((1.2 ** interval_in_years) - 1) * 100)
        
        print(f"Amount to be withdrawn: ${amount_withdrawn:.2f}")
        print(f"Total investment: ${total_investment:.2f}")
        print(f"Total shares: {total_shares:.2f}")
        print(f"Profit percentage per share: {profit_percentage_per_share:.2f}%")
        print(f"Total investment after withdraw: {total_investment * (1 - profit_percentage_per_share * 0.01):.2f}")
        if (royalties > 0):
            print(f"Royalties: {royalties:.2f}%")
        else:
            print("No royalties due to loss")

        if (recommended_commission > 0):
            print(f"Recommended max commission: {recommended_commission:.2f}% of withdrawn amount")
        else:
            print("No commission recommended as client will be in loss")
    else:
        print("User not found.")

#------------------------------------------------ Admin ------------------------------------------------
# Create new account
# user_id = register_user(name="Jedidiah Wong Sai Hong", phone_no="+6597238725", email="", address="", discord="305205895434993666")
# print(f"New user ID: {user_id}")

# Get ID by email
# email = "hydrater@gmail.com"
# user_id_by_email = get_id_by_email(email)
# print(f"User ID by email: {user_id_by_email}")

# Get ID by phone number
# phone_no = "+6582864834"
# user_id_by_phone_no = get_id_by_phone_no(phone_no)
# print(f"User ID by phone number: {user_id_by_phone_no}")

# Edit entry
# user_id = "284cbb3b-bfe7-4737-af5c-09e4d7828adc"
# edit_entry(user_id, name="Hyde", phone_no="+6582864834", email="hydrater@gmail.com", address="418868")

#------------------------------------------------ Core ------------------------------------------------
# Get total shares
# total_shares = get_total_shares()
# print(f"Total number of shares: {total_shares}")

# Get value per share
# share_price = get_share_price()

#------------------------------------------------ Transaction ------------------------------------------------
# Enums:
# action VARCHAR(10) CHECK (action IN ('Withdraw', 'Deposit')) NOT NULL,
# status VARCHAR(15) CHECK (status IN ('Transferring', 'Converting', 'Completed', 'Cancelled')) NOT NULL

# Add new transaction log entry
# new_entry = add_transaction_log_entry("284cbb3b-bfe7-4737-af5c-09e4d7828adc", 100.0, 100.0, 'Deposit', 'Transferring')
# print("New transaction log entry added:", new_entry)

# Get entry by transaction_id
# transaction = get_transaction_log_entry_by_id("3b0417ba-c0dd-4b30-8cb2-71490c47dea4")
# print("Transaction log entry by ID:", transaction)

# Get list of entries by user_id
# user_transactions = get_transaction_log_entries_by_user_id("284cbb3b-bfe7-4737-af5c-09e4d7828adc")
# print("Transaction log entries by user ID:", user_transactions)

# Edit an entry
# updated_entry = update_transaction_log_entry("3b0417ba-c0dd-4b30-8cb2-71490c47dea4", 150.0, 'Completed')
# print("Updated transaction log entry:", updated_entry)

# Complete deposit (Add last_known_value to shareholder's table user's total_investment and shares)
#result = updated_entry = complete_deposit("bbadd9e8-3e02-4f22-97cc-10afc0073cb5", 150.0)

# ------------------------------------------------ Others ------------------------------------------------
# Query withdraw details:
# query_withdraw_details("284cbb3b-bfe7-4737-af5c-09e4d7828adc", 5)
def get_debt():
    response = supabase.table('main').select('debt').eq('main_id', '0').execute()
    if response.data:
        return response.data[0]['debt']
    else:
        return None  # Return None if no data found
    
print(get_debt())