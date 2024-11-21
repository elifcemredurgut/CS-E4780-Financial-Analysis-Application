import csv
from collections import defaultdict
from datetime import datetime

def analyze_csv_by_interval(file_name, output_file):
    # Dictionary to store counts of each stock per 5-minute interval
    interval_stock_counts = defaultdict(lambda: defaultdict(int))

    with open(file_name, mode='r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header row

        for row in reader:
            stock_symbol = row[0] 
            trading_time_str = row[23] 

            # Parse trading time and round to the nearest 5-minute interval
            trading_time = datetime.strptime(trading_time_str, "%H:%M:%S.%f")
            rounded_time = trading_time.replace(minute=(trading_time.minute // 5) * 5, second=0, microsecond=0)
            interval_key = rounded_time.strftime("%H:%M")

            # Increment the count for the stock in this interval
            interval_stock_counts[interval_key][stock_symbol] += 1

    with open(output_file, mode='w') as output:
        output.write("Stock Counts by 5-Minute Interval:\n")
        for interval, stocks in sorted(interval_stock_counts.items()):
            output.write(f"Interval {interval}:\n")
            for stock, count in sorted(stocks.items()):
                output.write(f"  {stock}: {count}\n")

if __name__ == "__main__":
    analyze_csv_by_interval('realistic_time_ordered_data.csv', 'stats.txt')
