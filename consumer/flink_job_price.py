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
from pyflink.datastream.window import Trigger
from pyflink.datastream.window import TriggerResult

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

        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error processing record: {e}")

class CustomTimestampAssigner(TimestampAssigner):
    def extract_timestamp(self, element, record_timestamp):
        # Convert 'trading_date' and 'Trading time' into a single timestamp in milliseconds
        dt = datetime.strptime(f"{element['trading_date']} {element['Trading time']}", "%d-%m-%Y %H:%M:%S.%f")
        #logger.info(f"{dt}")
        return int(dt.timestamp() * 1000)  # Convert to milliseconds

class PurgeTrigger(Trigger):
    def on_element(self, element, timestamp, window, ctx):
        # Continue collecting elements until the window ends
        return TriggerResult.CONTINUE

    def on_processing_time(self, time, window, ctx):
        # No action on processing time
        return TriggerResult.CONTINUE

    def on_event_time(self, time, window, ctx):
        # When the event time reaches the end of the window
        if time == window.max_timestamp():
            # Fire the computation and purge the window's contents
            return TriggerResult.FIRE_AND_PURGE
        return TriggerResult.CONTINUE

    def on_merge(self, window, ctx):
        # Tumbling windows don't merge; do nothing
        pass

    def clear(self, window, ctx):
        # Clean up resources if needed (optional, e.g., timers)
        pass

def process_kafka_stream():
    # Set up Flink environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(3)
    env.set_stream_time_characteristic(TimeCharacteristic.EventTime)
    
    properties = {
        'bootstrap.servers': 'kafka2:9092',
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
        .window(TumblingEventTimeWindows.of(Time.seconds(5))) \
        .trigger(PurgeTrigger()) \
        .process(MyProcessWindowFunction())
    # Get the side output for raw stock prices
    raw_stock_prices = processed_stream.get_side_output(MyProcessWindowFunction().side_output_tag)

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
    env.execute("Python Flink Kafka Stream Processing with Price Inserting")
if __name__ == '__main__':
    process_kafka_stream()