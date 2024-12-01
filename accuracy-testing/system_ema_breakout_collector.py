import psycopg2
import numpy as np
import os

BREAKOUT_HEADERS = ["stock_id,dt,breakout_type"]
EMA_HEADERS=["stock_id,dt,prev_ema38,prev_ema100,ema38,ema100"]

BREAKOUT_PATH = "./system/breakout.csv"
EMA_PATH = "./system/ema.csv"

os.makedirs(os.path.dirname(BREAKOUT_PATH), exist_ok=True)
os.makedirs(os.path.dirname(EMA_PATH), exist_ok=True)

# Connection parameters
conn = psycopg2.connect(
    dbname="stocksdb",
    user="postgres",
    password="password",
    host="localhost",
    port="5433"
)

# Create a cursor object
cursor = conn.cursor()

# Execute a query
cursor.execute("SELECT * from ema;")
emas = [f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]}" for row in cursor.fetchall()]

cursor.execute("SELECT * from breakouts;")
breakouts = [f"{row[1]},{row[2]},{row[3]}" for row in cursor.fetchall()]

np.savetxt("./system/ema.csv", emas, delimiter=",", fmt='%s', header=",".join(EMA_HEADERS), comments="")
np.savetxt("./system/breakout.csv", breakouts, delimiter=",", fmt='%s', header=",".join(BREAKOUT_HEADERS), comments="")
# Close the connection
cursor.close()
conn.close()