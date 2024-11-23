import logging
import json
import psycopg2
from pyflink.datastream import StreamExecutionEnvironment, TimeCharacteristic
from pyflink.datastream.functions import ProcessWindowFunction
from pyflink.datastream.window import TumblingProcessingTimeWindows, TumblingEventTimeWindows
from pyflink.common import Time, Types, Row, WatermarkStrategy, Duration
from pyflink.datastream.connectors import FlinkKafkaConsumer
from pyflink.datastream.connectors.jdbc import JdbcSink, JdbcConnectionOptions, JdbcExecutionOptions
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.watermark_strategy import TimestampAssigner
from typing import Tuple, Iterable, Dict
from datetime import datetime
from pyflink.common.typeinfo import RowTypeInfo
from pyflink.datastream.output_tag import OutputTag
from collections import defaultdict

# Set up logging to write to the TaskManager log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FlinkTaskManagerLog")

class EmaCalculator:
    def __init__(self, smoothing_factor):
        self.previous_ema = {}
    def calculate_ema(self, last_price, symbol, smoothing_factor):
        last_price = float(last_price)
        last_ema = self.previous_ema.get(symbol, 0)
        alpha = 2 / (1 + smoothing_factor)
        current_ema = (last_price * alpha) + (last_ema * (1 - alpha))
        self.previous_ema[symbol] = current_ema
        return current_ema

class MyProcessWindowFunction(ProcessWindowFunction):
    def __init__(self):
        super().__init__()
        self.ema_calculator_38 = EmaCalculator(38)
        self.ema_calculator_100 = EmaCalculator(100)
        self.symbol_id_map = self.load_symbol_id_map()
        self.side_output_tag = OutputTag('raw-stock-price', Types.ROW([Types.INT(), Types.SQL_TIMESTAMP(), Types.DOUBLE()]))
    def load_symbol_id_map(self) -> Dict[str, int]:
        try:
            conn = psycopg2.connect(
                dbname="stocksdb",
                user="postgres",
                password="password",
                host="timescaledb",
                port="5432"
            )
            cursor = conn.cursor()
            cursor.execute("SELECT symbol, id FROM stock;")
            symbol_id_map = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            logger.info("Loaded symbol-ID map from the database.")
            return symbol_id_map
        except psycopg2.Error as e:
            logger.error(f"Error loading symbol-ID map: {e}")
            return {}

    def process(self, key: str, context: ProcessWindowFunction.Context,
                elements: Iterable[Tuple[str, int]]) -> Iterable[str]:
        try:
            #1st Part - Finding Avg value for the stocks with the same timestamps
            price_map = defaultdict(list)
            for element in elements:
                symbol = element['ID']
                price = float(element['Last'])
                dt = datetime.strptime(f"{element['trading_date']} {element['Trading time']}", "%d-%m-%Y %H:%M:%S.%f")
                price_map[(symbol, dt)].append(price)
            
            for (symbol, dt), prices in price_map.items():
                avg_price = sum(prices) / len(prices)
                
                stock_id = self.symbol_id_map.get(symbol)
                row_price = Row(
                    f0=stock_id,
                    f1=dt,
                    f2=avg_price
                )
                #logger.info(f"raw price: {symbol} {dt} {avg_price}/n ")
                yield self.side_output_tag, row_price
            #2nd Part - Calculating EMA's for the last data in the window
            #get the last element in the current window
            element = max(elements, key=lambda element: datetime.strptime(
                f"{element['trading_date']} {element['Trading time']}",
                "%d-%m-%Y %H:%M:%S.%f"
            ))
            
            symbol = element['ID']
            dt = datetime.strptime(f"{element['trading_date']} {element['Trading time']}", "%d-%m-%Y %H:%M:%S.%f")
            #take the avg price for the latest trading time
            last_price = sum(price_map[(symbol, dt)]) / len(price_map[(symbol, dt)])
            #get stock ID from the cached dictionary
            stock_id = self.symbol_id_map.get(symbol)
            if stock_id is not None:
                # Calculate EMA for the symbol
                prev_ema_38 = self.ema_calculator_38.previous_ema.get(symbol, 0)
                prev_ema_100 = self.ema_calculator_100.previous_ema.get(symbol, 0)
                ema_value_38 = self.ema_calculator_38.calculate_ema(last_price, symbol, 38)
                ema_value_100 = self.ema_calculator_100.calculate_ema(last_price, symbol, 100)
                dt = datetime.strptime(f"{element['trading_date']} {element['Trading time']}", "%d-%m-%Y %H:%M:%S.%f")
                starting_dt = datetime.strptime(f"{element['current_date']} {element['current_time']}", "%d/%m/%Y %H:%M:%S.%f")
                logger.info(f"{stock_id} {symbol} {dt} {starting_dt} {ema_value_38} ")
                row = Row(
                    stock_id,
                    dt,
                    prev_ema_38,
                    prev_ema_100,
                    ema_value_38,
                    ema_value_100,
                    starting_dt
                )
                # Log the type and content of the row for verification
                #logger.info(f" {last_price}, {symbol} {dt} /n")
                # Yield the row directly
                yield row
            else:
                logger.warning(f"Stock ID for symbol {symbol} not found in cache.")
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error processing record: {e}")

class CustomTimestampAssigner(TimestampAssigner):
    def extract_timestamp(self, element, record_timestamp):
        # Convert 'trading_date' and 'Trading time' into a single timestamp in milliseconds
        dt = datetime.strptime(f"{element['trading_date']} {element['Trading time']}", "%d-%m-%Y %H:%M:%S.%f")
        #logger.info(f"{dt}")
        return int(dt.timestamp() * 1000)  # Convert to milliseconds

def process_kafka_stream():
    # Set up Flink environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    env.set_stream_time_characteristic(TimeCharacteristic.EventTime)
    
    properties = {
        'bootstrap.servers': 'kafka1:9092',
        'group.id': 'flink-consumer'
    }
    kafka_consumer = FlinkKafkaConsumer(
        topics='stocks',
        deserialization_schema=SimpleStringSchema(),
        properties=properties
    )
    # Add Kafka source to the environment and assign timestamps and watermarks
    stream = env.add_source(kafka_consumer).map(lambda msg: json.loads(msg))
    stream = stream.assign_timestamps_and_watermarks(
        WatermarkStrategy
        .for_bounded_out_of_orderness(Duration.of_seconds(10))
        .with_timestamp_assigner(CustomTimestampAssigner())
    )
    # Apply event time window processing
    processed_stream = stream \
        .key_by(lambda msg: msg['ID']) \
        .window(TumblingEventTimeWindows.of(Time.minutes(5))) \
        .process(MyProcessWindowFunction())
    # Get the side output for raw stock prices
    raw_stock_prices = processed_stream.get_side_output(MyProcessWindowFunction().side_output_tag)
    
    # Set up JDBC sink for writing processed data to TimescaleDB
    type_name = ['stock_id', 'dt', 'prev_ema38', 'prev_ema100', 'ema38', 'ema100', 'latency_start']
    type_schema = [Types.INT(), Types.SQL_TIMESTAMP(), Types.DOUBLE(), Types.DOUBLE(), Types.DOUBLE(), Types.DOUBLE(), Types.SQL_TIMESTAMP()]
    type_info = RowTypeInfo(type_schema, type_name)
    processed_stream = processed_stream.map(lambda r: r, output_type=type_info)

    processed_stream.add_sink(
        JdbcSink.sink(
            "INSERT INTO ema (stock_id, dt, prev_ema38, prev_ema100, ema38, ema100, latency_start) VALUES (?::int, ?::timestamp, ?::double precision, ?::double precision, ?::double precision, ?::double precision, ?::timestamp)",
            type_info,
            JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                .with_url("jdbc:postgresql://timescaledb:5432/stocksdb")
                .with_driver_name("org.postgresql.Driver")
                .with_user_name("postgres")
                .with_password("password")
                .build(),
            JdbcExecutionOptions.builder()
                .with_batch_interval_ms(200)
                .with_batch_size(1000)
                .build()
        )
    )
    
    type_name_price = ['f0', 'f1', 'f2']
    type_schema_price = [Types.INT(), Types.SQL_TIMESTAMP(), Types.DOUBLE()]
    type_info_price = RowTypeInfo(type_schema_price, type_name_price)
    raw_stock_prices = raw_stock_prices.map(lambda r: r, output_type=type_info_price)
    raw_stock_prices.add_sink(
        JdbcSink.sink(
            "INSERT INTO stock_price (stock_id, dt, price) VALUES (?, ?, ?)",
            type_info_price,
            JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                .with_url("jdbc:postgresql://timescaledb:5432/stocksdb")
                .with_driver_name("org.postgresql.Driver")
                .with_user_name("postgres")
                .with_password("password")
                .build(),
            JdbcExecutionOptions.builder()
                .with_batch_interval_ms(200)
                .with_batch_size(1000)
                .build()
        )
    )
    # Execute the Flink job
    env.execute("Python Flink Kafka Stream Processing with EMA Calculation")
if __name__ == '__main__':
    process_kafka_stream()