import pandas as pd
# read by default 1st sheet of an excel file
dataframe1 = pd.read_excel("testdata.xlsx", sheet_name=1)

multiplierlist = []
prev1 = False #True for positive
prev2 = False
prev3 = False
# To print the date along with other row information

win = [0,0,0,0,0]
loses = [0,0,0,0,0]
no_data = [0,0,0,0,0]

for index, row in dataframe1.iterrows():
    
    newindex = 0
    for item in row:
        if (index > 1 and newindex > 0):
        #check if prev1 and prev2 are not both positive
            if(row[newindex]!= "No Data"):
                #print(f"col: {newindex} row: {index} item: {row[newindex]}")
                val = float(row[newindex].strip('%'))
                if (val>0):
                    win[newindex-1]+=1
                elif (val<0):
                    loses[newindex-1]+=1
            else:
                no_data[newindex-1]+=1

            # if ((prev1 and prev2 and prev3 ) is not True):
            #     print(f"Trading today. Result: {row[newindex]}")
            #     multiplierlist.append(row[newindex])
                
            # else:
            #     print(f"2 in a row previous 2 days, not trading today. Potential result: {row[newindex]}")
            #     #Commented out to prevent adding every day
            #     #multiplierlist.append(row[newindex])
            # prev3 = prev2
            # prev2 = prev1
            # 
            #     if (row[newindex] < 0):
            #         loses[newindex]+=1
            #     elif (row[newindex]>0):
            #         win[newindex]+=1

        newindex+=1

    prevrow = row
percentage = [0,0,0,0,0]
for i in range(5):
    percentage[i] = win[i]/(win[i]+loses[i])
print("Wins: "+str(win))
print("Loses: "+str(loses))
print("Percentage: "+str(percentage))
print("No Data: "+str(no_data))

# startingmulti = 1
# highest = 1
# lowest = 1
# biggestdrawdown=0
# numpos = 0
# numneg = 0
# for num in multiplierlist:
#     startingmulti = startingmulti*(1+float(num))
#     if (startingmulti>=highest):
#         highest = startingmulti
#     else:
#         diff = highest-startingmulti
#         diffpercent = diff/highest
#         if (diffpercent>biggestdrawdown):
#             biggestdrawdown = diffpercent
#     if num>0:
#         numpos+=1
#     else:
#         numneg+=1



# print("Final Multiplier: "+str(startingmulti))
# print("Num days traded: "+ str(len(multiplierlist)))
# print("Max drawdown %: "+ str(biggestdrawdown))
# print("Winrate: "+str(numpos/len(multiplierlist)))