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
import irori.strategyBase as strategyBase
import time

from irori.common import *
from irori.mediator import Mediator as Medy

class macwing(strategyBase.StrategyBase):
    masterMacd = []
    masterSignal = []
    masterHistogram = []
    masterHistogramGradient = []
    masterModeSignal = []
    
    def init(self):

        pass

    def start(self):

        pass

    def day_start(self):
        pass

    def day_end(self):
        pass

    def stop(self):
        pass

    # def on_order_changed(frame: OrderStatusData):
    #     print(f'order changed: {frame}')

    def on_tick_changed(frame: TickChangeData):
        df = pd.DataFrame(frame)
        #erase column data
        df.columns = ['Price']
        #erase all previous ewm data before calculating new ewm
        df['12EMA'] = 0
        df['26EMA'] = 0
        df['MACD'] = 0
        df['Signal'] = 0
        df['Histogram'] = 0

        #calculate MACD, timed
        t = time.time()
        df['12EMA'] = df['Price'].ewm(span=12000, adjust=False).mean()
        df['26EMA'] = df['Price'].ewm(span=26000, adjust=False).mean()

        #multiply by 910/currentstockprice to increase sensitivity
        df['MACD'] = df['12EMA'] - df['26EMA']
        df['Signal'] = df['MACD'].ewm(span=9000, adjust=False).mean()
        df['Histogram'] = df['MACD'] - df['Signal']
        momentum = df['Histogram'].tolist()[-1]

        #calculate momentum gradient based on last 200 momentum values
        if (len(df['Histogram'].tolist())>6000):
            gradient = np.gradient(df['Histogram'].tolist()[-6000:])
            masterHistogramGradient.append(gradient[-1]*1000)
        elif (len(df['Histogram'].tolist())>1):
            gradient = np.gradient(df['Histogram'].tolist())
            masterHistogramGradient.append(gradient[-1]*1000)
        else:
            masterHistogramGradient.append(0)

        #add to momentum signal list
            #combine momentum and gradient values
        masterModeSignal.append(momentum+masterHistogramGradient[-1]*stock_config.momentumSensitivity)
        currentDayTick = currentDayTick+1
        #check if new day, set new open price if new day
        
        #immendiate sell all shares
        if (stock_config.sellExistingStocks):
            listlen = len(sharesOwned)-1
            while listlen>=0:
                i = listlen
                workingCurrency = workingCurrency + (prevPrice*sharesOwned[i].numShares)- calculateFeeTiger(prevPrice,sharesOwned[i].numShares,False)
                listlen = listlen-1
            print("Sold all shares")
            sharesOwned = []
            buyOrderList = []
            sellOrderList = []

        #========================= Trading Logic =========================
        
        tempMomentum = 0
        tradingMode = stock_config.tradingMode[0]
        match int(tradingMode):
            case 0:
                tempMomentum = momentum
            case 1:
                tempMomentum = masterModeSignal[-1]
            case 2:
                tempMomentum = masterHistogramGradient[-1]
        if (currentDayTick%1000==0):
            #print MACD
            print(f"DAY: {currentDayNumber} | TICK NUMBER: {currentDayTick}/{len(dataFrame)} | Momentum: {tempMomentum}")
        
        # trading modes
        # 0 = StartOfDay, 1 = Buy Mode, 2 = Short Mode, 3 = EOD/Not Trading
        if (endDay or (tempMomentum<=momentumCap and tempMomentum>=-momentumCap)): #End of Day
            if (endDay):
                    lowMomentum = True
                    tempMode = 3
            if (not lowMomentum):
                if (secondsSinceDayStart-previousSwitchTime>300):
                #print("Momentum is neutral. Entering Close Mode.==================================================================")
                    lowMomentum = True
                    tempMode = 3
        
        elif (tempMomentum > momentumCap): #Buy Mode
            if (lowMomentum):
                #check if it's been at least 300 seconds since last trade mode switch
                    if (secondsSinceDayStart-previousSwitchTime>300):
                        #print("Positive momentum detected. Entering Buy Mode.=================================================================")
                        #add Indicator
                        lowMomentum = False
                        tempMode = 1
        elif (tempMomentum < -momentumCap): #Short Mode
            if (lowMomentum):
                #check if it's been at least 300 seconds since last trade mode switch
                    if (secondsSinceDayStart-previousSwitchTime>300):
                        #print("Negative momentum detected. Entering Short Mode.================================================================")
                        lowMomentum = False
                        tempMode = 2
        elif (secondsSinceDayStart<1800):
            tempMode = 0
        else:
            tempMode = previousMode

        match tempMode:
            case 0: #Start of Day
                lowMomentum = True
            case 1: #Buy Mode
                if (previousMode!=1):
                    previousMode = 1
                    previousSwitchTime = secondsSinceDayStart
                    calculateThresholds(stock_config.currentPrice,stock_config)
                    buyOrderList = []
                    transactionList.append(transaction(stock_config.currentPrice,stock_config.bulkSize,3,True,True,tickCounter))
                    #add transaction indicator
                    
                    #add Indicator
                    indicatorList.append(indicator(1,tickCounter))
                #If current price is higher than upper threshold, recalculate thresholds
                if (stock_config.currentPrice>stock_config.upperThreshold or lowMomentum):
                    calculateThresholds(stock_config.currentPrice,stock_config)
                    transactionList.append(transaction(stock_config.currentPrice,stock_config.bulkSize,3,True,True,tickCounter))
                    #cancel all buy orders
                    buyOrderList = []
                    #make new buy orders for the lower thresholds
                #if buy is successful and stocks are owned
                    #cycle through lower thresholds
                for i in range(len(lowerThresholdList)):
                    if (lowerThresholdList[i]<workingCurrency):
                        buyShares(lowerThresholdList[i],stock_config.bulkSize,i,buyOrderList,sharesOwned)
                            
                #if stocks owned, make sell orders
                if(len(sharesOwned)>0):
                    for i in range(len(sharesOwned)):
                        #check if sell order exists
                        for x in range(len(sellOrderList)):
                            if (sharesOwned[i].blockID == sellOrderList[x].blockID):
                                break
                        sellingPrice = sharesOwned[i].price+(stock_config.targetedProfit/100*lastSale)
                        tempfee = calculateFeeTiger(sellingPrice,sharesOwned[i].numShares,True)
                        tempfee = tempfee + calculateFeeTiger(sellingPrice,sharesOwned[i].numShares,False)
                        tempfee = tempfee/sharesOwned[i].numShares
                        sellShares(sharesOwned[i].blockID,sellingPrice+tempfee,sharesOwned,sellOrderList)
            case 2: #Short Mode
                if (previousMode!=2):
                    previousMode = 2
                    previousSwitchTime = secondsSinceDayStart
                    calculateShortThresholds(stock_config.currentPrice,stock_config)
                    transactionList.append(transaction(stock_config.currentPrice,stock_config.bulkSize,3,True,True,tickCounter))
                    shortBuyList = []
                    #add Indicator
                    indicatorList.append(indicator(2,tickCounter))
                if (stock_config.currentPrice<lowerThreshold or lowMomentum):
                    stock_config.currentPrice<lowerThreshold
                    calculateShortThresholds(stock_config.currentPrice,stock_config)
                    shortBuyList = []
                    #add trasnaction indicator
                    transactionList.append(transaction(stock_config.currentPrice,stock_config.bulkSize,3,True,True,tickCounter))
                    
                    
                '''if (tickCounter%1000==0):
                    print("\n\n=== Shorts Owned ===")
                    for i in range(len(shortsOwned)):
                        print(f"Block ID: {shortsOwned[i].blockID}\nBuy Price: {shortsOwned[i].price} | Num Shares: {shortsOwned[i].numShares}")
                    print("=== Short Buy Orders ===")
                    for i in range(len(shortBuyList)):
                        print(f"Block ID: {shortBuyList[i].blockID}\nBuy Price: {shortBuyList[i].limitPrice} | Num Shares: {shortBuyList[i].numShares}")
                    print("=== Short Sell Orders ===")
                    for i in range(len(shortSellList)):
                        print(f"Block ID: {shortSellList[i].blockID}\nSell Price: {shortSellList[i].limitPrice} | Num Shares: {shortSellList[i].numShares}")'''
                
                #make new short buy orders for the upper thresholds
                #cycle through upper thresholds
                for i in range(len(upperThresholdList)):
                    shortShares(upperThresholdList[i],stock_config.bulkSize,i,shortBuyList,shortsOwned)

                #if shorts owned, make short sell orders
                if(len(shortsOwned)>0):
                    for i in range(len(shortsOwned)):
                        #check if short sell order exists
                        for x in range(len(shortSellList)):
                            if (shortsOwned[i].blockID == shortSellList[x].blockID):
                                break
                        buyingPrice = shortsOwned[i].price-(stock_config.targetedProfit/100*lastSale)
                        tempfee = calculateFeeTiger(shortsOwned[i].price,shortsOwned[i].numShares,False)
                        tempfee = tempfee + calculateFeeTiger(buyingPrice,shortsOwned[i].numShares,True)
                        tempfee = tempfee/shortsOwned[i].numShares
                        shortSellShares(shortsOwned[i].blockID,buyingPrice-tempfee,shortsOwned,shortSellList)
            case 3:#End of Day
                if (previousMode!=0):
                    previousMode = 0
                    previousSwitchTime = secondsSinceDayStart
                    #add Indicator
                    indicatorList.append(indicator(0,tickCounter))
                #sell all shares
                listlen = len(sharesOwned)-1
                if (listlen>=0):
                    if (endDay):
                        print("End of Day, closed all positions.")
                    else:
                        print("Momentum is neutral, closed all positions.")
                while listlen>=0:
                    i = listlen
                    workingCurrency = workingCurrency + (lastSale*sharesOwned[i].numShares)- calculateFeeTiger(lastSale,sharesOwned[i].numShares,False)
                    listlen = listlen-1
                    totalFees = totalFees + calculateFeeTiger(lastSale,sharesOwned[i].numShares,False)
                    transactionList.append(transaction(lastSale,sharesOwned[i].numShares,sharesOwned[i].blockID,False,False,tickCounter))
                if (not lowMomentum):
                    lowMomentum = True
                    #add Indicator
                    indicatorList.append(indicator(0,tickCounter))
                #close all shorts
                listlen = len(shortsOwned)-1
                if (listlen>=0):
                    if (endDay):
                        print("End of Day, closed all short positions.")
                    else:
                        print("Momentum is neutral, closed all short positions.")
                while listlen>=0:
                    i = listlen
                    workingCurrency = workingCurrency - (lastSale*shortsOwned[i].numShares)- calculateFeeTiger(lastSale,shortsOwned[i].numShares,True)
                    listlen = listlen-1
                    totalFees = totalFees + calculateFeeTiger(lastSale,shortsOwned[i].numShares,True)
                    transactionList.append(transaction(lastSale,shortsOwned[i].numShares,shortsOwned[i].blockID,True,False,tickCounter))
                sharesOwned = []
                buyOrderList = []
                sellOrderList = []
                shortsOwned = []
                shortBuyList = []
                shortSellList = []

    # def on_transaction_changed(frame: OrderTransactionData):
    #     # logger.info(f'transaction changed: {frame}')
    #     print(f'transaction changed: {frame}')
    
    def get_stock_names():
        pass

    def ReceiveTickData(tick_data):
        pass