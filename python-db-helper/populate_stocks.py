import config
import psycopg2
import psycopg2.extras
import pandas as pd
import time

for _ in range(5):
    try:
        connection = psycopg2.connect(host=config.DB_HOST, port=config.DB_PORT, database=config.DB_NAME, user=config.DB_USER, password=config.DB_PASS)
        break
    except psycopg2.OperationalError as e:
        print("Database connection failure, retrying")
        time.sleep(5)

cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

stocks_data = pd.read_csv('stocks.csv')

for _, row in stocks_data.iterrows():
    cursor.execute("""
            INSERT INTO stock (symbol, security_type)
            VALUES (%s, %s)
            """, (row['ID'], row['SecType']))

connection.commit()
connection.close()

