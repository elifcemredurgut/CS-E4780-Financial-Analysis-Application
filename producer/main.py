import os
import glob
import datetime
import json
from confluent_kafka import Producer, KafkaError

conf = {
    'bootstrap.servers': "kafka1:9092,kafka2:9092,kafka3:9092,kafka4:9092,kafka5:9092",
    'linger.ms': 0,  # Immediate send
    'batch.size': 16384,
    'acks': '1'
}

def parse_time(time_str):
    hours, minutes, seconds, milliseconds, microseconds = map(int, time_str.split(":"))
    return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds, microseconds=microseconds)

def calculate_arrival_time(current_time, processing_time):
    # Convert to timedelta objects
    current_time_delta = parse_time(current_time)
    processing_time_delta = parse_time(processing_time)

    # Sum the two timedelta objects
    result_time_delta = current_time_delta + processing_time_delta

    # Extract the resulting hours, minutes, seconds, milliseconds, and microseconds
    total_seconds = int(result_time_delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    milliseconds = result_time_delta.microseconds // 1000
    microseconds = result_time_delta.microseconds % 1000

    # Format the result as a string
    result_time_str = f"{hours:02}:{minutes:02}:{seconds:02}:{milliseconds:02}:{microseconds:03}"
    return result_time_str


# Create the Producer instance
producer = Producer(conf)


path = os.getcwd()
csv_files = glob.glob(os.path.join(path, "data", "*.csv"))

try:
    for csv_file in csv_files:
        prev_trading_time = None
        current_hour = 0
        with open(csv_file, 'r') as file:
            is_first_line = True
            for line in file:
                start_time = datetime.datetime.now()
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
                    minutes, seconds, miliseconds = trading_time.split(":")
                    miliseconds, microseconds = miliseconds.split(".")
                    if prev_trading_time != None and int(trading_time[0]) < int(prev_trading_time[0]):
                        current_hour += 1
                    current_time = f"{current_hour:02}:{minutes}:{seconds}:{miliseconds}:{microseconds}"
                    prev_trading_time = trading_time
                    end_time = datetime.datetime.now()

                    processing_time = end_time - start_time
                    seconds = processing_time.seconds % 60
                    milliseconds = processing_time.microseconds // 1000
                    formatted_processing_time = f"00:00:{seconds:02}:{milliseconds:02}:{processing_time.microseconds:03}"
                    arrival_time = calculate_arrival_time(current_time, formatted_processing_time)

                    value = {"ID": stock_id, "SecType": sec_type, "Last": last, "Trading time": trading_time, "trading_date": trading_date, "current_time":current_time, "arrival_time":arrival_time}
                    producer.produce("stocks", key=stock_id, value=json.dumps(value).encode('utf-8'))
                producer.flush() 


except KafkaError as e:
    print(f"Kafka error: {e}")

    print("Transaction aborted due to Kafka error.")
except Exception as e:
    print(f"General error: {e}")
    print("Transaction aborted due to general error.")
