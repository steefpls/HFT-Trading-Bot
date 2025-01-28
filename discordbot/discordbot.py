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
import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands

from datetime import datetime, timedelta,timezone,date
import random
import os
import asyncio
import time
import yfinance as yf
from supabase import create_client, Client
from jproperties import Properties
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.trade.trade_client import TradeClient
import logging
import math
import asyncio
from datetime import datetime
import uuid
from discord import app_commands
import threading
import pytz
import pandas_market_calendars as mcal

class UserGroupUpdateView(View):
    def __init__(self, users, numnewshares, userlist=[]):
        super().__init__()
        self.numnewshares = numnewshares
        self.userlist = userlist
        if (self.userlist == []):
            for user_id, username in users:
                self.userlist.append((user_id,username,False))
        for user_id, username,isSelected in userlist:
            self.add_item(UserSelectButton(user_id, username,isSelected))
        self.add_item(GroupUpdateConfirmButton())
        self.add_item(CancelButton())

class UserStatsView(View):
    def __init__(self, users):
        super().__init__()
        for user_id, username in users:
            self.add_item(UserStatsButton(user_id, username))
        self.add_item(CancelButton())

class UserUpdateView(View):
    def __init__(self, users,numnewshares):
        super().__init__()
        self.numnewshares = numnewshares
        for user_id, username in users:
            self.add_item(UserUpdateButton(user_id, username))
        self.add_item(CancelButton())

class UserDepositView(View):
    def __init__(self, users,numnewshares):
        super().__init__()
        self.numnewshares = numnewshares
        for user_id, username in users:
            self.add_item(UserDepositButton(user_id, username))
        self.add_item(CancelButton())


# DO NOT MODIFY ANY FUNCTIONS IN THIS FILE
class UserSetSelectView(View):
    def __init__(self, users, amount):
        super().__init__()
        self.amount = amount
        for user_id, username in users:
            self.add_item(UserSetSharesButton(user_id, username))
        self.add_item(CancelButton())

class UserAddSelectView(View):
    def __init__(self, users, amount):
        super().__init__()
        self.amount = amount
        for user_id, username in users:
            self.add_item(UserAddSharesButton(user_id, username))
        self.add_item(CancelButton())

class UserSubSelectView(View):
    def __init__(self, users, amount):
        super().__init__()
        self.amount = amount
        for user_id, username in users:
            self.add_item(UserSubSharesButton(user_id, username))
        self.add_item(CancelButton())

class UserAddInvestmentView(View):
    def __init__(self, users, amount):
        super().__init__()
        self.amount = amount
        for user_id, username in users:
            self.add_item(UserAddInvestmentButton(user_id, username))
        self.add_item(CancelButton())

class UserSetInvestmentView(View):
    def __init__(self, users, amount):
        super().__init__()
        self.amount = amount
        for user_id, username in users:
            self.add_item(UserSetInvestmentButton(user_id, username))
        self.add_item(CancelButton())

class UserStatsButton(Button):
    def __init__(self, user_id, username):
        super().__init__(label=username, style=discord.ButtonStyle.primary)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        user_id = self.user_id
        num_shares = get_row_by_id(user_id)[0]['shares']
        totalshares = get_total_shares()
        if totalshares == 0:
            await interaction.response.send_message("No shares in the fund.")
            return
        offset = get_offset_by_discord_id(user_id)
        totalinvestment = get_row_by_id(user_id)[0]['total_investment']
        totalinvestment+=offset
        # Your current net worth
        networth = num_shares/totalshares*get_checkpoint_price()
        networth += offset
        temptext = ""
        nameofuser = get_row_by_id(user_id)[0]['name']
        #get live USD TO SGD exchange rate with yahoo finance
        USDtoSGD = yf.Ticker("USDSGD=X")
        exchange_rate = USDtoSGD.history(period='1d')['Close'].iloc[-1]
        if networth > totalinvestment:
            temptext = (f"\n{nameofuser} is in a profit of {round(((networth/totalinvestment)-1)*100,2)}%, USD ${round(networth-totalinvestment,2)}, SGD ${round((networth-totalinvestment)*exchange_rate,2)}")
        elif networth < totalinvestment:
            temptext = (f"\n{nameofuser} is in a loss of {round(((networth/totalinvestment)-1)*100,2)}%, USD ${round(networth-totalinvestment,2)}, SGD ${round((networth-totalinvestment)*exchange_rate,2)}")    
        await interaction.response.edit_message(
                content=f"Total investment: {round(totalinvestment,2)}\nCurrent net worth\n(USD): {round(networth,2)}\n(SGD estimated): {round(networth*exchange_rate,2)}\nExchange rate: {round(exchange_rate,4)}\n"+temptext+f"\nShares: {num_shares}",
                view=None
            )

class UserDepositButton(Button):
    def __init__(self, user_id, username):
        super().__init__(label=username, style=discord.ButtonStyle.primary)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        view: UserUpdateView = self.view
        value = get_portfolio_gross_value()
        prev = get_checkpoint_price()-get_debt()
        diff = value-prev

        currentshares = get_row_by_id(self.user_id)[0]['shares']
        totalinvestment = get_row_by_id(self.user_id)[0]['total_investment']

        shareprice = get_share_price()
        newShareprice = get_true_share_price()

        result1 = update_investment(self.user_id, totalinvestment+diff)
        result2 = update_shares(self.user_id, currentshares+view.numnewshares)
        
        set_checkpoint_price(value)
        
        tempword = ""
        if diff > 0:
            tempword = "Added"
        elif diff < 0:
            tempword = "Subtracted"
        if result1 and result2:
            await interaction.response.edit_message(
                content=f"Checkpoint set!\nDifference in portfolio value: {round(diff,2)}\n{tempword} {view.numnewshares} shares @ user {self.label} (ID: {self.user_id}).\n New total shares: {currentshares+view.numnewshares}\n Previous total shares: {currentshares}\n New total investment: {totalinvestment+diff}\n Previous total investment: {totalinvestment}",   
                view=None
            )
        else:
            set_checkpoint_price(prev)
            await interaction.response.edit_message(
                content=f"Failed to update for user {self.label} (ID: {self.user_id}).",
                view=None
            )

class UserUpdateButton(Button):
    def __init__(self, user_id, username):
        super().__init__(label=username, style=discord.ButtonStyle.primary)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        view: UserUpdateView = self.view
        value = get_portfolio_gross_value()
        prev = get_checkpoint_price()-get_debt()
        diff = value-prev

        currentshares = get_row_by_id(self.user_id)[0]['shares']

        shareprice = get_share_price()
        newShareprice = get_true_share_price()

        result2 = update_shares(self.user_id, currentshares+view.numnewshares)
        
        set_checkpoint_price(value)
        tempword = ""
        if diff > 0:
            tempword = "Added"
        elif diff < 0:
            tempword = "Subtracted"
        if result2:
            await interaction.response.edit_message(
                content=f"Checkpoint set!\nDifference in portfolio value: {round(diff,2)}\n{tempword} {view.numnewshares} shares to user {self.label} (ID: {self.user_id}).\n New total shares: {currentshares+view.numnewshares}\n Previous total shares: {currentshares}",
                view=None
            )
        else:
            set_checkpoint_price(prev)
            await interaction.response.edit_message(
                content=f"Failed to update for user {self.label} (ID: {self.user_id}).",
                view=None
            )

class UserSetInvestmentButton(Button):
    def __init__(self, user_id, username):
        super().__init__(label=username, style=discord.ButtonStyle.primary)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        view: UserSetInvestmentView = self.view
        currentinvestment = get_row_by_id(self.user_id)[0]['total_investment']
        result = update_investment(self.user_id, view.amount)

        if result:
            await interaction.response.edit_message(
                content=f"Total investment for user {self.label} (ID: {self.user_id}) have been set to {view.amount}, previously {currentinvestment}.",
                view=None
            )
        else:
            await interaction.response.edit_message(
                content=f"Failed to update total investment for user {self.label} (ID: {self.user_id}).",
                view=None
            )

class UserAddInvestmentButton(Button):
    def __init__(self, user_id, username):
        super().__init__(label=username, style=discord.ButtonStyle.primary)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        view: UserAddInvestmentView = self.view
        currentinvestment = get_row_by_id(self.user_id)[0]['total_investment']
        result = update_investment(self.user_id, currentinvestment+view.amount)

        if result:
            await interaction.response.edit_message(
                content=f"Total investment for user {self.label} (ID: {self.user_id}) have been set to {currentinvestment+view.amount}, previously {currentinvestment}.",
                view=None
            )
        else:
            await interaction.response.edit_message(
                content=f"Failed to update total investment for user {self.label} (ID: {self.user_id}).",
                view=None
            )

class UserSetSharesButton(Button):
    def __init__(self, user_id, username):
        super().__init__(label=username, style=discord.ButtonStyle.primary)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        view: UserSetSelectView = self.view
        currentshares = get_row_by_id(self.user_id)[0]['shares']
        result = update_shares(self.user_id, view.amount)

        if result:
            await interaction.response.edit_message(
                content=f"Shares for user {self.label} (ID: {self.user_id}) have been set to {view.amount}, previously {currentshares}.",
                view=None
            )
        else:
            await interaction.response.edit_message(
                content=f"Failed to update shares for user {self.label} (ID: {self.user_id}).",
                view=None
            )

class UserAddSharesButton(Button):
    def __init__(self, user_id, username):
        super().__init__(label=username, style=discord.ButtonStyle.primary)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        view: UserAddSelectView = self.view
        currentshares = get_row_by_id(self.user_id)[0]['shares']
        result = update_shares(self.user_id, currentshares+view.amount)

        if result:
            await interaction.response.edit_message(
                content=f"Shares for user {self.label} (ID: {self.user_id}) have been set to {currentshares+view.amount}, previously {currentshares}.",
                view=None
            )
        else:
            await interaction.response.edit_message(
                content=f"Failed to update shares for user {self.label} (ID: {self.user_id}).",
                view=None
            )

class UserSubSharesButton(Button):
    def __init__(self, user_id, username):
        super().__init__(label=username, style=discord.ButtonStyle.primary)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        view: UserSubSelectView = self.view
        currentshares = get_row_by_id(self.user_id)[0]['shares']
        result = update_shares(self.user_id, currentshares-view.amount)

        if result:
            await interaction.response.edit_message(
                content=f"Shares for user {self.label} (ID: {self.user_id}) have been set to {currentshares-view.amount}, previously {currentshares}.",
                view=None
            )
        else:
            await interaction.response.edit_message(
                content=f"Failed to update shares for user {self.label} (ID: {self.user_id}).",
                view=None
            )
class UserSelectButton(Button):
    def __init__(self, user_id, username, isSelected):
        if isSelected:
            super().__init__(label=username, style=discord.ButtonStyle.success)
        else:
            super().__init__(label=username, style=discord.ButtonStyle.primary)
        self.user_id = user_id
    async def callback(self, interaction: discord.Interaction):
        self.style = discord.ButtonStyle.success if self.style == discord.ButtonStyle.primary else discord.ButtonStyle.primary
        await interaction.response.edit_message(view=self.view)

class CancelButton(Button):
    def __init__(self):
        super().__init__(label="Cancel", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="Cancelled.", view=None)

def setcheckpointloop():
        while(True):
            lastupdatestring = get_checkpoint_last_update()
            if (get_checkpoint_last_update() == None):
                set_checkpoint_last_update(str(datetime.now()))
                
            now = datetime.now()
            datetime_object = datetime.strptime(lastupdatestring, '%Y-%m-%d %H:%M:%S.%f')
            isrighttime = (datetime.now().hour<21 and datetime.now().hour>5)
            if(now-datetime_object).seconds>43200 and isrighttime:
                print("Checkpoint last set over 12 hours ago. Updating now.")
            else:
                # Calculate the time until 46 PM the next day, update at 4pm
                target_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
                if now >= target_time:
                    target_time += timedelta(days=1)
                print(f"Checkpoint updater sleeping for {(target_time - now).total_seconds()} seconds, until {target_time}")
                time.sleep((target_time - now).total_seconds())  # Wait until time

            if is_nyse_open_today():
                prev = get_checkpoint_price()
                debt = get_debt()
                value = get_portfolio_gross_value()
                valuewithdebt = value+debt
                message = ""
                #positive day
                if prev<valuewithdebt:
                    message += f"Day is positive. Setting new checkpoint, recalculating debt.\n"
                    comission = 0.075
                    profit = valuewithdebt-prev
                    newdebt = debt-profit*comission
                    set_debt(newdebt)
                    message += f"Nom nom, took {comission*100}% of ${round(profit,2)} as repayment for debt.\n Debt reduced from ${round(debt,2)}, to ${round(newdebt,2)}.\n"
                    set_checkpoint_price(value)
                    message +=f"Checkpoint automatically set to {valuewithdebt}, from {prev}."
                elif valuewithdebt<prev:
                    message += f"Change is Negative. Setting new checkpoint, no debt reduction :(\n"
                    set_checkpoint_price(value)
                    message +=f"Checkpoint automatically set to {valuewithdebt}, from {prev}"
                else:
                    message +=f"Value is the same since last checkpoint. No new checkpoint set."
                set_checkpoint_last_update(str(datetime.now()))
                add_share_price_timestamp()
                print(message)
            else:
                set_checkpoint_last_update(str(datetime.now()))
                print("Skipping share price updating today, market not open today.")


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

def get_checkpoint_price():
    response = supabase.table('main').select('last_portfolio_value', 'debt').eq('main_id', '0').execute()
    if response.data:
        return response.data[0]['last_portfolio_value'] + response.data[0]['debt']
    else:
        return None  # Return None if no data found

def get_debt():
    response = supabase.table('main').select('debt').eq('main_id', '0').execute()
    if response.data:
        return response.data[0]['debt']
    else:

        return None  # Return None if no data found
def set_debt(price: float):
    response = supabase.table('main').update({'debt': price}).eq('main_id', '0').execute()

def get_checkpoint_last_update():
    response = supabase.table('main').select('checkpoint_last_update').eq('main_id', '0').execute()
    if response.data:
        return response.data[0]['checkpoint_last_update']
    else:

        return None  # Return None if no data found
def set_checkpoint_last_update(time: str):
    response = supabase.table('main').update({'checkpoint_last_update': time}).eq('main_id', '0').execute()


def set_checkpoint_price(price: float):
    response = supabase.table('main').update({'last_portfolio_value': price}).eq('main_id', '0').execute()

def add_share_price_timestamp():
    # Fetch the current share price
    share_price = get_share_price()

    # Generate the current timestampUpdate discordbot.py
    current_timestamp = datetime.now(pytz.timezone('Asia/Singapore')).isoformat()  # Ensure UTC for consistency

    # Insert into the Supabase table
    response = supabase.table('share_price').insert({
        'Date': current_timestamp,
        'Price': share_price
    }).execute()
    print(response)

def get_share_price_timestamps():
    response = supabase.table('share_price').select("*").execute()
    return response

def get_current_account_assets():
    response = supabase.table('main').select('last_portfolio_value').eq('main_id', '0').execute()
    return response.data[0]['last_portfolio_value']

def get_all_rows():
    response = supabase.table("shareholders").select("*").execute()
    if response.data:
        return response.data
    else:
        print("No users found.")
        return None
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
    
def get_id_by_discord_id(discord_id: str):
    response = supabase.table("shareholders").select("id").eq("discord_id", discord_id).execute()

    if response.data:
        return response.data[0]['id']
    else:
        print("No user found with the provided discord id.")
        return None

def get_offset_by_discord_id(discord_id: str):
    data = get_row_by_id(discord_id)[0]
    return data['offset'] 

def update_shares(user_id: str, new_shares: float):
    response = supabase.table("shareholders").update({"shares": new_shares}).eq("id", user_id).execute()
    if response.data[0]['shares'] == new_shares:
        print(f"Shares updated successfully for user id {user_id}.")
        return True
    else:
        print(f"Failed to update shares for user id {user_id}: {response.get('error')}")
        return False

def update_investment(user_id: str, new_investment: float):
    response = supabase.table("shareholders").update({"total_investment": new_investment}).eq("id", user_id).execute()
    if response.data[0]['total_investment'] == new_investment:
        print(f"Investment updated successfully for user id {user_id}.")
        return True
    else:
        print(f"Failed to update investment for user id {user_id}: {response.get('error')}")
        return False

def update_shares_by_discord_id(discord_id: str, new_shares: float):
    user_id = get_id_by_discord_id(discord_id)
    if user_id:
        return update_shares(user_id, new_shares)
    else:
        print("No user found with the provided discord id.")
        return False

def register_user(name, phone_no:str, email, address, discord, remark = ""):
    # Check if email or phone number already exists
    email_response = supabase.table("shareholders").select("id").eq("email", email).execute()
    if email_response.data:
        print(f"User with email {email} already exists with ID: {email_response.data[0]['id']}")
        return 0 # Return 0 if email already exists
    
    # Check if phone number already exists
    phone_response = supabase.table("shareholders").select("id").eq("phone_no", phone_no).execute()
    if phone_response.data:
        print(f"User with phone number {phone_no} already exists with ID: {phone_response.data[0]['id']}")
        return 1 # Return 1 if phone number already exists

    if not phone_no.startswith("+"):
        raise ValueError("Phone number must start with '+'")
        return 2 # Return 2 if phone number does not start with '+'
    
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
        "remark": remark,
    }

    response = supabase.table("shareholders").insert(data).execute()
    if response.data:
        user_id = response.data[0]['id']  # Extract the ID from the response
        return user_id # Return the ID of the new user
    else:
        raise Exception(f"Error inserting data: {response}")
        return 3 # Return 3 if error inserting data
    
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
        return -1

def get_share_price():
    return get_checkpoint_price()/get_total_shares()

def get_adjusted_share_price(adjustment: float):
    return (get_checkpoint_price()+adjustment)/get_total_shares()

def get_true_share_price():
    return get_portfolio_gross_value()/get_total_shares()

def get_portfolio_gross_value() -> float:
    portfolio_account = get_trade_client().get_prime_assets(base_currency="USD")
    return portfolio_account.segments['S'].cash_available_for_trade

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
        royalty_rate = calculate_royalties(get_checkpoint_price())
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

def is_nyse_open_today():
    # Get today's date
    today = date.today()
    # Get NYSE market calendar
    nyse = mcal.get_calendar("NYSE")

    # Get the schedule for today
    schedule = nyse.schedule(start_date=today, end_date=today)

    # Check if the schedule is not empty
    if not schedule.empty:
        market_open = schedule.iloc[0]['market_open'].to_pydatetime()
        market_close = schedule.iloc[0]['market_close'].to_pydatetime()

        # Get current time in the same timezone as market_open and market_close
        now = datetime.now(pytz.timezone('America/New_York'))

        # Check if the current time is within market hours
        return True
    else:
        return False


class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

def start_bot():
    client = MyClient()

    @client.event
    async def on_ready():
        print(f'Logged in as {client.user} (ID: {client.user.id})')
        print('------')

    @client.tree.command(name="price", description="Gets the current price of a stock.")
    async def price(interaction: discord.Interaction, stock: str):
        if not stock:
            await interaction.response.send_message("Please enter a valid stock symbol.")
            return
        
        stock = stock.upper()
        stock_info = yf.Ticker(stock)
        if stock_info.history(period="1d").empty:
            await interaction.response.send_message(f"Stock {stock} does not exist.")
        else:
            stockprice = float(stock_info.history(period="1d")["Close"].iloc[-1])
            stockprice = round(stockprice, 2)
            await interaction.response.send_message(f"Price of {stock} is {stockprice}")

    @client.tree.command(name="register", description="Register a new user. Use postal code for address and +65 for phone number.")
    async def register(interaction: discord.Interaction, name: str, phone_no: str, email: str, address: str, remark: str =""):
        user_id = register_user(name, phone_no, email, address, interaction.user.id, remark)
        match user_id:
            case 0:
                await interaction.response.send_message(f"User with email {email} already exists.")
            case 1:
                await interaction.response.send_message(f"User with phone number {phone_no} already exists.")
            case 2:
                await interaction.response.send_message("Phone number must start with '+'")
            case 3:
                await interaction.response.send_message("Error inserting data.")
            case _:
                await interaction.response.send_message(f"User registered with ID: {user_id}")

    @client.tree.command(name="checkfund", description="Get the total value of the portfolio (Steef and Hyde Only)")
    async def checkfund(interaction: discord.Interaction):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        value = get_checkpoint_price()
        await interaction.response.send_message(f"Portfolio gross value: {value}")

    @client.tree.command(name="totalshares", description="Get the total number of shares comprising the Irori Fund (Steef and Hyde Only)")
    async def totalshares(interaction: discord.Interaction):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        value = get_total_shares()
        await interaction.response.send_message(f"Total shares: {value}")

    @client.tree.command(name="getmystats", description="Get your shares via DM")
    async def getmystats(interaction: discord.Interaction):
        try:
            id = get_id_by_discord_id(interaction.user.id)
            if (id == None):
                await interaction.response.send_message("You are not registered in the system.")
                return
            num_shares = get_row_by_id(id)[0]['shares']
            totalshares = get_total_shares()
            if totalshares == 0:
                await interaction.response.send_message("No shares in the fund.")
                return
                
            offset = get_offset_by_discord_id(id)
            totalinvestment = get_row_by_id(id)[0]['total_investment']
            totalinvestment+=offset
            # Your current net worth
            networth = num_shares/totalshares*get_checkpoint_price()
            temptext = ""
            #get live USD TO SGD exchange rate with yahoo finance
            USDtoSGD = yf.Ticker("USDSGD=X")
            exchange_rate = USDtoSGD.history(period='1d')['Close'].iloc[-1]
            
            networth += offset
            if networth > totalinvestment:
                temptext = (f"You are in a profit of {round(((networth/totalinvestment)-1)*100,2)}%, USD ${round(networth-totalinvestment,2)}, SGD(Estimated) ${round((networth-totalinvestment)*exchange_rate,2)}, Exchange rate: {round(exchange_rate,4)}\nNote that profits are calculated based on investment in USD not SGD")
            elif networth < totalinvestment:
                temptext = (f"You are in a loss of {round(((networth/totalinvestment)-1)*100,2)}%, USD ${round(totalinvestment-networth,2)} SGD(Estimated) ${round((totalinvestment-networth)*exchange_rate,2)}, Exchange rate: {round(exchange_rate,4)}\nNote that profits are calculated based on investment in USD not SGD")
            await interaction.user.send(f"Total investment: {round(totalinvestment,2)}\nCurrent net worth\n(USD): {round(networth,2)}\n(SGD estimated): {round(networth*exchange_rate,2)}\nExchange rate: {round(exchange_rate,4)}\n"+temptext)#+f"\nShares: {num_shares}")
            await interaction.response.send_message("I've sent you a DM!")
        except discord.Forbidden:
            await interaction.response.send_message("I couldn't send you a DM. You might have DMs disabled or have blocked me.")

    #get someone else's stats (Steef and Hyde only)
    @client.tree.command(name="getstats", description="Get someone else's shares via DM (Steef and Hyde Only)")
    async def getstats(interaction: discord.Interaction):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        allusers = []
        # Fetch users from your database
        users = get_all_rows()
        for(user) in users:
            allusers.append((user['id'], user['name']))
        view = UserStatsView(allusers)
        await interaction.response.send_message("Select a user to get stats for:", view=view)
        

    @client.tree.command(name="setshares", description="Set the number of shares for a user (Steef and Hyde Only)")
    @app_commands.describe(amount="The number of shares to set")
    async def setshares(interaction: discord.Interaction, amount: float):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        allusers = []
        # Fetch users from your database
        users = get_all_rows()
        for(user) in users:
            allusers.append((user['id'], user['name']))

        view = UserSetSelectView(allusers, amount)
        await interaction.response.send_message("Select a user to set shares for:", view=view)

    #add Shares now
    @client.tree.command(name="addshares", description="Add the number of shares for a user (Steef and Hyde Only)")
    @app_commands.describe(amount="The number of shares to add")
    async def addshares(interaction: discord.Interaction, amount: float):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        allusers = []
        # Fetch users from your database
        users = get_all_rows()
        for(user) in users:
            allusers.append((user['id'], user['name']))

        view = UserAddSelectView(allusers, amount)
        await interaction.response.send_message("Select a user to add shares for:", view=view)

    #subtract Shares now
    @client.tree.command(name="subtractshares", description="Subtract the number of shares for a user (Steef and Hyde Only)")
    @app_commands.describe(amount="The number of shares to subtract")
    async def subtractshares(interaction: discord.Interaction, amount: float):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        allusers = []
        # Fetch users from your database
        users = get_all_rows()
        for(user) in users:
            allusers.append((user['id'], user['name']))

        view = UserSubSelectView(allusers, amount)
        await interaction.response.send_message("Select a user to subtract shares for:", view=view)

    # command to set initial investment
    @client.tree.command(name="settotalinvestment", description="Set the total investment for a user (Steef and Hyde Only)")
    @app_commands.describe(amount="The total investment to set to")
    async def settotalinvestment(interaction: discord.Interaction, amount: float):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        allusers = []
        # Fetch users from your database
        users = get_all_rows()
        for(user) in users:
            allusers.append((user['id'], user['name']))

        view = UserSetInvestmentView(allusers, amount)
        await interaction.response.send_message("Select a user to set total investment for:", view=view)

    #command to add to initial investment
    @client.tree.command(name="addtotalinvestment", description="Add to the total investment for a user (Steef and Hyde Only)")
    @app_commands.describe(amount="The total investment to add")
    async def addtotalinvestment(interaction: discord.Interaction, amount: float):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        allusers = []
        # Fetch users from your database
        users = get_all_rows()
        for(user) in users:
            allusers.append((user['id'], user['name']))

        view = UserAddInvestmentView(allusers, amount)
        await interaction.response.send_message("Select a user to add to total investment for:", view=view)

    #command to show all users and their shares, total investment
    @client.tree.command(name="showall", description="Show all users and their shares, total investment (Steef and Hyde Only)")
    async def showall(interaction: discord.Interaction):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        allusers = []
        # Fetch users from your database
        users = get_all_rows()
        for(user) in users:
            allusers.append((user['id'], user['name'], user['shares'], user['total_investment']))
        allusersString = ""
        totalshares = get_total_shares()
        for user in allusers:
            sharepercent = user[2]/totalshares*100
            allusersString += f"{user[1]}: Shares - {round(user[2],2)}, Total Investment - {round(user[3],2)}, Share Percent - {round(sharepercent,2)}%\n"
        await interaction.response.send_message(f"Users and their shares, total investment: \n{allusersString}")

    @client.tree.command(name="getshareprice", description="Get the price of each share")
    async def getshareprice(interaction: discord.Interaction):
        shareprice = get_share_price()
        await interaction.response.send_message(f"Price of each share: {shareprice}")

    #update command, for admins to update a single user's shares, after money has changed in the fund if other investments are made
    @client.tree.command(name="update", description="Updates a user's shares, based on portfolio difference (Steef and Hyde Only)")
    async def update(interaction: discord.Interaction):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        # Fetch users from your database
        users = get_all_rows()
        allusers = []
        for(user) in users:
            allusers.append((user['id'], user['name']))
            
        diff = get_checkpoint_price() - get_portfolio_gross_value() - get_debt()

        numnewshares = 0
        if diff == 0:
            await interaction.response.send_message("Checkpoint is already up to date, no need to use update function.")
            
        else:
            numnewshares = diff / get_share_price()
            view = UserUpdateView(allusers, numnewshares)
            #Display Current Total Shares, Current fund net value, adjusted share price assuming money is already in the fund
            await interaction.response.send_message(f"Price difference: {round(diff,2)}\nNumber of new shares to be added: {numnewshares}\nSelect a user to deposit for:", view=view)

    #deposit command, for admins to deposit money into the fund, and update the user's shares and total investment
    @client.tree.command(name="deposit", description="Deposit money for a user. Similar to update, also modifies initial investment (Steef and Hyde Only)")
    async def deposit(interaction: discord.Interaction):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        # Fetch users from your database
        users = get_all_rows()
        allusers = []
        for(user) in users:
            allusers.append((user['id'], user['name']))

        diff = (get_portfolio_gross_value() + get_debt()) - get_checkpoint_price()
        print("get_checkpoint_price: "+str(get_checkpoint_price()))
        print("get_portfolio_gross_value: "+str(get_portfolio_gross_value()))
        print("get_debt: "+str(get_debt()))
        
        numnewshares = 0
        if diff == 0:
            await interaction.response.send_message("Latest money amount (checkpoint) is already up to date, no need to use update function. If this is incorrect, please check the checkpoint value, and manually update shares if needed.")
            
        else:
            numnewshares = diff / get_share_price()
            view = UserDepositView(allusers, numnewshares)
            #Display Current Total Shares, Current fund net value, adjusted share price assuming money is already in the fund
            await interaction.response.send_message(f"Price difference: {round(diff,2)}\nNumber of new shares to be added: {numnewshares}\nSelect a user to deposit for:", view=view)
        

    @client.tree.command(name="setcheckpoint", description="Set portfolio value checkpoint automatically (Steef and Hyde Only)")

    async def setcheckpoint(interaction: discord.Interaction):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        prev = get_checkpoint_price()
        debt = get_debt()
        value = get_portfolio_gross_value()
        valuewithdebt = value+debt
        message = ""
        #positive day
        if prev<valuewithdebt:
            message += f"Day is positive. Setting new checkpoint, recalculating debt.\n"
            comission = 0.08
            profit = valuewithdebt-prev
            newdebt = debt-profit*comission
            set_debt(newdebt)
            message += f"Nom nom, took {comission*100}% of ${round(profit,2)} as repayment for debt.\n Debt reduced from ${round(debt,2)}, to ${round(newdebt,2)}.\n"
            set_checkpoint_price(value)
            message +=f"Checkpoint automatically set to {valuewithdebt}, from {prev}."
        elif valuewithdebt<prev:
            message += f"Change is Negative. Setting new checkpoint, no debt reduction :(\n"
            set_checkpoint_price(value)
            message +=f"Checkpoint automatically set to {valuewithdebt}, from {prev}"
        else:
            message +=f"Value is the same since last checkpoint. No new checkpoint set."
            
        await interaction.response.send_message(message)

    @client.tree.command(name="setcustomcheckpoint", description="Set portfolio value checkpoint manually(Steef and Hyde Only)")
    @app_commands.describe(amount="The checkpoint to set")
    async def setcustomcheckpoint(interaction: discord.Interaction, amount: float):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        set_checkpoint_price(amount)
        await interaction.response.send_message(f"Checkpoint manually set to {amount}")

    @client.tree.command(name="setdebt", description="Set portfolio debt manually(Steef and Hyde Only)")
    @app_commands.describe(amount="The debt to set")
    async def setcustomcheckpoint(interaction: discord.Interaction, amount: float):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        debt = get_debt()
        set_debt(amount)
        await interaction.response.send_message(f"Debt manually set to {amount}, from {debt}")

    @client.tree.command(name="getcheckpoint", description="Get stock price checkpoint (Steef and Hyde Only)")
    async def getcheckpoint(interaction: discord.Interaction):
        allowed_ids = [224437447059177472, 134499528660221961]
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("You are not authorized to use this command.")
            return
        checkpoint = get_checkpoint_price()
        debt = get_debt()
        gross = get_current_account_assets()
        await interaction.response.send_message(f"Checkpoint is {checkpoint}. \nCurrent monetary value of the fund: {gross}\nTotal Debt: {debt}")

    @client.tree.command(name="getsharepricehistory", description="Get a historical chart of the share price.")
    async def getsharepricehistory(interaction: discord.Interaction):
        # Fetch the share price timestamps
        data = get_share_price_timestamps()

        # Handle cases where data is not available or the query failed
        if not data:
            await interaction.response.send_message("No data available or an error occurred.")
            return

        # Build the display text
        displaytext = "Share Price History:\n"
        counter = 0
        for datapoint in data:
            if counter == 0:
                dictlist= datapoint[1]
                for dict in dictlist:
                    displaytext += f"Date: {dict['Date']} \tPrice: {float(dict['Price']):.4f}\n"
            counter +=1
        # Send the response
        await interaction.response.send_message(displaytext)
    #start the bot
    token = ""
    with open('.env', 'r') as f:
        token = f.readline().strip()
    token = token.split("=")[1]
    client.run(token)

if __name__ == "__main__":
    checkpointer_thread = threading.Thread(target=setcheckpointloop)

    checkpointer_thread.start()
    start_bot()
    