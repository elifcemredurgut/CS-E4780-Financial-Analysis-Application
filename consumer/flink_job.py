import logging
import json
import psycopg2
from pyflink.datastream import StreamExecutionEnvironment, TimeCharacteristic
from pyflink.datastream.functions import ProcessWindowFunction
from pyflink.datastream.window import TumblingProcessingTimeWindows
from pyflink.common import Time, Types, Row
from pyflink.datastream.connectors import FlinkKafkaConsumer
from pyflink.datastream.connectors.jdbc import JdbcSink, JdbcConnectionOptions, JdbcExecutionOptions
from pyflink.common.serialization import SimpleStringSchema
from typing import Tuple, Iterable, Dict
from datetime import datetime
from pyflink.common.typeinfo import RowTypeInfo

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

    def load_symbol_id_map(self) -> Dict[str, int]:
        """Loads the symbol-ID mapping from the database into a dictionary."""
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
        element = max(elements, key=lambda element: datetime.strptime(
            f"{element['trading_date']} {element['Trading time']}",
            "%d-%m-%Y %H:%M:%S.%f"
        ))
        try:
            symbol = element['ID']
            last_price = element['Last']
            trading_time = element['Trading time']
            trading_date = element['trading_date']
            # Get stock ID from the cached dictionary
            stock_id = self.symbol_id_map.get(symbol)

            if stock_id is not None:
                # Calculate EMA for the symbol
                prev_ema_38 = self.ema_calculator_38.previous_ema.get(symbol, 0)
                prev_ema_100 = self.ema_calculator_100.previous_ema.get(symbol, 0)
                ema_value_38 = self.ema_calculator_38.calculate_ema(last_price, symbol, 38)
                ema_value_100 = self.ema_calculator_100.calculate_ema(last_price, symbol, 100)

                row = Row(
                    stock_id,
                    prev_ema_38,
                    prev_ema_100,
                    ema_value_38,
                    ema_value_100
                )

                # Log the type and content of the row for verification
                logger.info(f"{row}, {last_price}, {symbol}")

                # Yield the row directly
                yield row
            else:
                logger.warning(f"Stock ID for symbol {symbol} not found in cache.")
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error processing record: {e}")

def process_kafka_stream():
    # Set up Flink environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    env.set_stream_time_characteristic(TimeCharacteristic.ProcessingTime)

    # Configure Kafka consumer
    properties = {
        'bootstrap.servers': 'kafka:9092',
        'group.id': 'flink-consumer'
    }
    kafka_consumer = FlinkKafkaConsumer(
        topics='stocks',
        deserialization_schema=SimpleStringSchema(),
        properties=properties
    )

    # Add Kafka source to the environment
    stream = env.add_source(kafka_consumer)

    # Apply window processing with EMA calculations
    processed_stream = stream.map(lambda msg: json.loads(msg)) \
        .key_by(lambda msg: msg['ID']) \
        .window(TumblingProcessingTimeWindows.of(Time.minutes(1))) \
        .process(MyProcessWindowFunction())

    # Set up JDBC sink for writing processed data to TimescaleDB
    type_name = ['stock_id', 'prev_ema38', 'prev_ema100', 'ema38', 'ema100']
    type_schema = [Types.INT(), Types.DOUBLE(), Types.DOUBLE(), Types.DOUBLE(), Types.DOUBLE()]
    type_info = RowTypeInfo(type_schema, type_name)
    processed_stream = processed_stream.map(lambda r: r, output_type=type_info)
    processed_stream.add_sink(
        JdbcSink.sink(
            "INSERT INTO ema (stock_id, dt, prev_ema38, prev_ema100, ema38, ema100) VALUES (?, '2024-01-01 00:00:00', ?, ?, ?, ?)",
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

    # Execute the Flink job
    env.execute("Python Flink Kafka Stream Processing with EMA Calculation")

if __name__ == '__main__':
    process_kafka_stream()
