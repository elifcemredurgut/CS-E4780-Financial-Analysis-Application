from datetime import datetime, timedelta
import random
import csv
import os

NUM_OF_ROWS = 10000000
SYMBOLS = ["A0HN5C.ETR", "SGFI.FR", "NRP.NL", "840400.ETR", "519000.ETR", "543900.ETR", "620440.ETR", "872087.ETR", "750000.ETR", "SGO.FR"]
EQUTIES = ["E", "I"]
HEADERS = []
DATA_PATH = "./data/example.csv"

os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)

data = []
current_time = datetime(2022, 5, 17)
price = round(random.uniform(3000, 5000), 4)

headers = [""] * 27
headers[0] = "ID"  
headers[1] = "SecType"
headers[21] = "Last"
headers[23] = "Trading time"
headers[26] = "Trading date"
data = [headers]

for i in range(NUM_OF_ROWS): 
    current_time += timedelta(milliseconds=random.randint(10,100)) 
    trading_date = current_time.strftime("%d-%m-%Y")
    trading_time = current_time.strftime("%H:%M:%S") + f".{current_time.microsecond // 1000:03d}"

    price += random.uniform(-100, 100)
    equity = random.choice(EQUTIES)
    symbol = random.choice(SYMBOLS)

    new_stock = [symbol, equity] + ["empty"]*19 + [price] + ["empty"] + [trading_time] + [""]*2 + [trading_date]
    data.append(new_stock)
    
with open(DATA_PATH, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(data)


