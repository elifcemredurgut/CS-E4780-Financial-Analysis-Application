import csv
import random
from datetime import datetime, timedelta

input_file = '../python-db-helper/stocks.csv'
output_file = 'realistic_time_ordered_data.csv'
rows=100000
frequent_stock_count=500

stocks = []
with open(input_file, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        stocks.append((row['ID'], row['SecType']))

# Generate weights for long-tail distribution
weights = [1 / (i + 1) for i in range(len(stocks))]
total_weight = sum(weights)
probabilities = [w / total_weight for w in weights]

frequent_stocks = random.choices(stocks, probabilities, k=5)

stock_prices = {stock[0]: round(random.uniform(10, 1000), 2) for stock in stocks}
start_time = datetime.strptime("2021-01-01 10:00:00", "%Y-%m-%d %H:%M:%S")
end_time = datetime.strptime("2021-01-01 11:00:00", "%Y-%m-%d %H:%M:%S")

# Calculate time increment per row
total_seconds = (end_time - start_time).total_seconds()
time_increment = timedelta(seconds=total_seconds / rows)

current_time = start_time
rows_data = []

for _ in range(rows):
    stock, sec_type = random.choices(
        frequent_stocks + stocks,
        weights=[10] * len(frequent_stocks) + probabilities,
        k=1
    )[0]
    # calculate the price
    last_price = stock_prices[stock]
    price_change = random.uniform(-0.02, 0.02)  # Change between -2% and +2%
    new_price = max(1, round(last_price * (1 + price_change), 2))
    stock_prices[stock] = new_price

    trading_time = current_time.strftime("%H:%M:%S.%f")[:-3]  
    trading_date = current_time.strftime("%d-%m-%Y")

    row = [""] * 27
    row[0] = stock  
    row[1] = sec_type  
    row[21] = new_price  
    row[23] = trading_time 
    row[26] = trading_date  

    rows_data.append(row)

    current_time += time_increment

with open(output_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow([""] * 27)  
    writer.writerows(rows_data)

