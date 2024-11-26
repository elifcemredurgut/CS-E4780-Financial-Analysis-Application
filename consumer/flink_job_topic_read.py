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

# Set up logging to write to the TaskManager log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FlinkTaskManagerLog")
"""
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
        for element in elements:
            symbol = element['ID']
            price = float(element['Last'])
            dt = datetime.strptime(f"{element['trading_date']} {element['Trading time']}", "%d-%m-%Y %H:%M:%S.%f")

            # Get stock ID from the symbol ID map
            stock_id = self.symbol_id_map.get(symbol)

            if stock_id is not None:
                # Output raw stock prices to the side output
                logger.info(f"raw price: {symbol} {stock_id} {price} {dt}/n ")
                yield stock_id

  

class CustomTimestampAssigner(TimestampAssigner):
    def extract_timestamp(self, element, record_timestamp):
        # Convert 'trading_date' and 'Trading time' into a single timestamp in milliseconds
        dt = datetime.strptime(f"{element['trading_date']} {element['Trading time']}", "%d-%m-%Y %H:%M:%S.%f")
        #logger.info(f"{dt}")
        return int(dt.timestamp() * 1000)  # Convert to milliseconds
"""
def process_kafka_stream():
    # Set up Flink environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    env.set_stream_time_characteristic(TimeCharacteristic.EventTime)

    # Configure Kafka consumer
    properties = {
        'bootstrap.servers': 'kafka3:9092',
        'group.id': 'flink-consumer'
    }
    kafka_consumer = FlinkKafkaConsumer(
        topics='stocks',
        deserialization_schema=SimpleStringSchema(),
        properties=properties
    )
    stream = env.add_source(kafka_consumer)
    # Process the data and log it to TaskManager
    stream.map(lambda msg: json.loads(msg)) \
         .map(lambda msg: logger.info(f"Received message: {msg}")) \
         .print()
    """
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
    """
    # Execute the Flink job
    env.execute("Python Flink Kafka Stream Processing with EMA Calculation")

if __name__ == '__main__':
    process_kafka_stream()