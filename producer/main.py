import os
import glob
import datetime
import json
from confluent_kafka import Producer, KafkaError

conf = {
    'bootstrap.servers': "kafka:9092"
}

# Create the Producer instance
producer = Producer(conf)


path = os.getcwd()
csv_files = glob.glob(os.path.join(path, "data", "*.csv"))

try:

    for csv_file in csv_files:
        with open(csv_file, 'r') as file:
            is_first_line = True
            for line in file:
                if line[0] == "#":
                    print("Comment line skipped.")
                    continue
                
                if is_first_line:
                    is_first_line = False
                    continue
                
                values = line.strip().split(",")  # Strip whitespace and split by comma

                stock_id = values[0]
                sec_type = values[1]
                last = values[21]
                trading_time = values[23]
                trading_date = values[26]

                # Prepare value based on validation
                if stock_id == '':
                    value = f"{datetime.datetime.now()}: ID cannot be null"
                    producer.produce("error", key=stock_id, value=value.encode("utf-8"))  # Send to error topic
                elif sec_type == '':
                    value = f"{datetime.datetime.now()}: SecType cannot be null"
                    producer.produce("error", key=stock_id, value=value.encode("utf-8"))  # Send to error topic
                elif last == '':
                    value = f"{datetime.datetime.now()}: Last cannot be null"
                    producer.produce("error", key=stock_id, value=value.encode("utf-8"))  # Send to error topic
                elif trading_time == '':
                    value = f"{datetime.datetime.now()}: Trading time cannot be null"
                    producer.produce("error", key=stock_id, value=value.encode("utf-8"))  # Send to error topic
                elif trading_date == '':
                    value = f"{datetime.datetime.now()}: Trading date cannot be null"
                    producer.produce("error", key=stock_id, value=value.encode("utf-8"))  # Send to error topic
                else:
                    # Valid data, produce to stocks topic
                    value = {"ID": stock_id, "SecType": sec_type, "Last": last, "Trading time": trading_time, "trading_date": trading_date}
                    producer.produce("stocks", key=stock_id, value=json.dumps(value).encode('utf-8'))
                producer.flush() 


except KafkaError as e:
    print(f"Kafka error: {e}")

    print("Transaction aborted due to Kafka error.")
except Exception as e:
    print(f"General error: {e}")
    print("Transaction aborted due to general error.")
