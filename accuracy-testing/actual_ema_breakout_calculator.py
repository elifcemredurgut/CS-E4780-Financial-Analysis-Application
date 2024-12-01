from datetime import datetime, timedelta
import glob
import os
import psycopg2

def load_symbol_id_map():
    conn = psycopg2.connect(
       dbname="stocksdb",
        user="postgres",
        password="password",
        host="localhost",
        port="5433"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, id FROM stock;")
    symbol_id_map = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return symbol_id_map

def round_up_to_next_five_minutes(dt):
    total_seconds = dt.minute * 60 + dt.second + (dt.microsecond > 0)
    if total_seconds % (5 * 60) != 0: 
        dt += timedelta(minutes=(5 - (dt.minute % 5)), seconds=-dt.second, microseconds=-dt.microsecond)
    return dt.replace(second=0, microsecond=0)

symbols = load_symbol_id_map()
BREAKOUT_PATH = "./actual/breakout.csv"
EMA_PATH = "./actual/ema.csv"


class EMA():
    def __init__ (self, symbol, price, dt, prev_ema38=0, prev_ema100=0):
        self.prev_ema38 = prev_ema38
        self.prev_ema100 = prev_ema100
        self.price = price
        self.ema38 = self.calculate_ema(38)
        self.ema100 = self.calculate_ema(100)
        self.dt = dt
        self.stock_id = symbols[symbol]
        self.breakout_type = None
    def calculate_ema(self, factor):
        prev_ema = None
        if factor == 38:
            prev_ema = self.prev_ema38
        else:
            prev_ema = self.prev_ema100
        return (float(self.price)*(2/(1+factor))) + (prev_ema*(1-(2/(1+factor))))
    def is_breakout(self):
        if self.ema38 > self.ema100 and self.prev_ema38 <= self.prev_ema100:
            self.breakout_type = "bull"
            return True
        elif self.ema38 < self.ema100 and self.prev_ema38 >= self.prev_ema100:
            self.breakout_type = "bear"
            return True
        else:
            return False
    def ema_to_csv(self):
        with open (EMA_PATH, "a") as file:
            file.writelines(f"{self.stock_id},{self.dt},{self.prev_ema38},{self.prev_ema100},{self.ema38},{self.ema100}\n")
    
    def breakouts_to_csv(self):
        if self.is_breakout():
            with open (BREAKOUT_PATH, "a") as file:
                file.writelines(f"{self.stock_id},{self.dt},{self.breakout_type}\n")

class Price():
    def __init__(self, price, symbol, dt):
        self.price = price
        self.symbol = symbol
        self.dt = dt


window_start = datetime.strptime("08-11-2021 00:00:00.000", "%d-%m-%Y %H:%M:%S.%f")
window_end = datetime.strptime("08-11-2021 00:05:00.000", "%d-%m-%Y %H:%M:%S.%f")

prev_emas = {}
emas = {}
prices = {}

os.makedirs(os.path.dirname(BREAKOUT_PATH), exist_ok=True)
os.makedirs(os.path.dirname(EMA_PATH), exist_ok=True)


with open (EMA_PATH, "w") as file:
    file.writelines("stock_id,dt,prev_ema38,prev_ema100,ema38,ema100\n")
with open (BREAKOUT_PATH, "w") as file:
    file.writelines("stock_id,dt,breakout_type\n")


path = "../producer"
csv_files = sorted(glob.glob(os.path.join(path, "data", "*.csv")))

for csv_file in csv_files:
    with open (csv_file, "r") as file:
        is_first_line = True
        for line in file.readlines():
            if line[0] == "#":
                print("Comment line skipped.")
                continue
            if(is_first_line):
                is_first_line = False
                continue
            values = line.strip().split(",")  # Strip whitespace and split by comma
            
            symbol = values[0]
            sec_type = values[1]
            temp_time = values[3]
            price = values[21]
            trading_time = values[23]
            trading_date = values[26]

            if symbol == '':
                continue
            elif sec_type == '':
                continue
            elif price == '':
                continue
            elif trading_time == '':
                if temp_time == '':
                    continue
                else:
                    trading_time = temp_time
            elif trading_date == '':
                continue

            trading_full_date = datetime.strptime(trading_date.strip()+" "+trading_time.strip(), "%d-%m-%Y %H:%M:%S.%f")
            if trading_full_date >= window_start and trading_full_date < window_end:
                new_price = Price(price=price, symbol=symbol, dt=trading_full_date.strftime("%Y-%m-%d").strip()+" "+trading_time.strip()+"000")
                prices[symbol] = new_price
            elif trading_full_date >= window_end:
                #window_end += timedelta(minutes=5)
                window_end = round_up_to_next_five_minutes(trading_full_date)
                windows_start = window_end - timedelta(minutes=5)
                for symbol, price_object in prices.items():   
                    if symbol in prev_emas:
                        prev_ema = prev_emas[symbol]
                        new_ema = EMA(price=price_object.price, dt=price_object.dt, symbol=price_object.symbol, prev_ema38=prev_ema.ema38, prev_ema100=prev_ema.ema100)
                        new_ema.ema_to_csv()
                        new_ema.breakouts_to_csv()
                        emas[symbol] = new_ema
                    else:
                        new_ema = EMA(price=price_object.price, dt=price_object.dt, symbol=price_object.symbol)
                        new_ema.ema_to_csv()
                        new_ema.breakouts_to_csv()
                        emas[symbol] = new_ema
                
                for symbol, prev_ema in prev_emas.items():
                    if symbol not in emas:
                        emas[symbol] = prev_ema 
                prev_emas = emas.copy()
                emas = {}
                
                prices = {}
                new_price = Price(price=price, symbol=symbol, dt=trading_full_date.strftime("%Y-%m-%d").strip()+" "+trading_time.strip()+"000")
                prices[symbol] = new_price