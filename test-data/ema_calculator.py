import pandas as pd
import json
from datetime import datetime
from collections import defaultdict

class EmaCalculator:
    def __init__(self, smoothing_factor):
        self.smoothing_factor = smoothing_factor
        self.previous_ema = {}

    def calculate_ema(self, last_price, symbol):
        last_price = float(last_price) 
        last_ema = self.previous_ema.get(symbol, 0) 
        alpha = 2 / (1 + self.smoothing_factor)  
        current_ema = (last_price * alpha) + (last_ema * (1 - alpha)) 
        self.previous_ema[symbol] = current_ema 
        return current_ema

def load_symbol_id_map():
    file_path = 'id-map.txt'
    symbol_id_map = {}
    
    with open(file_path, 'r') as file:
        for line in file:
            # Split the line into components based on the '|' separator
            parts = line.strip().split('|')
            stock_id = int(parts[0].strip())
            symbol = parts[1].strip()
            symbol_id_map[symbol] = stock_id
    print("Loaded symbol-id map.")
    return symbol_id_map

def process_csv_file(file_path, output_file):
    df = pd.read_csv(file_path, header=None)

    df.columns = ['stock_symbol', 'sec_type', 'field1', 'field2', 'field3', 'field4', 'field5', 'field6', 
                  'field7', 'field8', 'field9', 'field10', 'field11', 'field12', 'field13', 'field14', 
                  'field15', 'field16', 'field17', 'field18', 'field19', 'price', 'field21', 'timestamp', 
                  'field23', 'field24', 'date']

    df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['timestamp'], format='%d-%m-%Y %H:%M:%S.%f')

    df.set_index('timestamp', inplace=True)

    symbol_id_map = load_symbol_id_map()
    ema_calculator_38 = EmaCalculator(38)
    ema_calculator_100 = EmaCalculator(100)

    results = []

    windowed_groups = df.groupby(pd.Grouper(freq='5min'))

    for window, group in windowed_groups:
        for stock_symbol, stock_group in group.groupby('stock_symbol'):
            latest_record = stock_group.iloc[-1]  # Select the last record for this stock in the window

            last_price = latest_record['price']
            timestamp = latest_record.name 
            stock_id = symbol_id_map.get(stock_symbol)

            # Calculate the EMA for this record
            prev_ema_38 = ema_calculator_38.previous_ema.get(stock_symbol, 0)
            prev_ema_100 = ema_calculator_100.previous_ema.get(stock_symbol, 0)
            ema_value_38 = ema_calculator_38.calculate_ema(last_price, stock_symbol)
            ema_value_100 = ema_calculator_100.calculate_ema(last_price, stock_symbol)

            result = {
                "stock_id": stock_id,
                "timestamp": timestamp.isoformat(),
                "price": last_price,
                "prev_ema_38": prev_ema_38,
                "prev_ema_100": prev_ema_100,
                "ema_38": ema_value_38,
                "ema_100": ema_value_100
            }

            results.append(result)

    with open(output_file, mode='w') as file:
        for result in results:
            file.write(json.dumps(result) + "\n")
    print(f"Processed data written to {output_file}")

if __name__ == '__main__':
    file_path = '../producer/data/realistic_time_ordered_data.csv' 
    output_file = "ema_results.txt"  
    process_csv_file(file_path, output_file)
