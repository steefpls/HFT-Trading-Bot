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
TIGER_ACCOUNT_PROPERTIES_FILE="./Authentication.properties"
TIGER_PRIVATE_KEY_PROPERTY="private_key_pk1"
TIGER_ID_PROPERTY="tiger_id"
TIGER_ACCOUNT_PROPERTY="account"

# 1-Year Treasury: 5.14%
# assuming yearly (252 days) bond rate is 5.14%
# root 252 (1.0514) = 1.0001989190254
# 1.000203968253968^252
ANNUAL_RISK_FREE_RATE=0.0514
RISK_FREE_RATE=0.0001989190254

#GST
GST = 0.09
ALLOW_MARGIN_TRADING = True

BROKER_AUTH_PROPERTIES_FILE="./Authentication.properties"
GLOBAL_CONFIG_FILE="global.config"

# Users
HYDE_DIRECTORY_PATH=r'C:\Users\liqui\OneDrive\Documents\GitHub\Irori-bot'
JED_DIRECTORY_PATH=r'E:\Work\Irori-bot'
NARH_DIRECTORY_PATH=r'e:\Projects\Irori-bot'
AOYUN_DIRECTORY_PATH=r'C:\Users\aoyun\Documents\Irori-bot'
STEEF_DIRECTORY_PATH=""

# Discord
MB_DISCORD_MAIN_CHANNEL='https://discord.com/api/webhooks/1210877934739390545/8HD2n__okWvSMMp81Z5qg36Xsla_JN5ppA_LwVFwBOfPXzTo6yBteGM-9lqcZndhKX4w'
MB_DISCORD_ERROR_CHANNEL='https://discord.com/api/webhooks/1210893936747352084/mBS3dgGZl7TKCM8ER63fAIRdnLWyVGhw45ZXdBZgtG2gUtcJcnuVV9dRerOnL6iiAOlR'
MB_DISCORD_DAILY_CHANNEL='https://discord.com/api/webhooks/1210941867827396628/nsDx5ukSiGygBa9DKWgOxa7GP4DMVnfsc-l0ApuJ9J064dK-jA9OPQVqUgpQpEmAaEr7'
MB_DISCORD_TRADE_CHANNEL='https://discord.com/api/webhooks/1210941884260679690/51dcXrYlyxF2o9JS2Whu4xJFc2JHlP7sCpuSY_SvnPG2C08YdZ02kxUFeZUX-t2R9Yu1'
