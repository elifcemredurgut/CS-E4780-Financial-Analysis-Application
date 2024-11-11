import logging
import json
from pyflink.datastream import StreamExecutionEnvironment, TimeCharacteristic
from pyflink.datastream.functions import ProcessWindowFunction
from pyflink.datastream.window import TumblingProcessingTimeWindows
from pyflink.common import Time
from pyflink.datastream.connectors import FlinkKafkaConsumer
from pyflink.common.serialization import SimpleStringSchema
from typing import Tuple, Iterable
# Set up logging to write to the TaskManager log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FlinkTaskManagerLog")
class EmaCalculator:
    def __init__(self, smoothing_factor=38):
        self.previous_ema = {}
    def calculate_ema(self, last_price, symbol, smoothing_factor=38):
        last_price = float(last_price)
        last_ema = self.previous_ema.get(symbol, 0)
        alpha = 2 / (1 + smoothing_factor)
        current_ema = (last_price * alpha) + (last_ema * (1 - alpha))
        self.previous_ema[symbol] = current_ema
        return current_ema
class MyProcessWindowFunction(ProcessWindowFunction):
    def __init__(self):
        super().__init__()
        self.ema_calculator = EmaCalculator()
        
    def process(self, key: str, context: ProcessWindowFunction.Context,
                elements: Iterable[Tuple[str, int]]) -> Iterable[str]:
        result={}
        for element in elements:
            try:
                symbol = element['ID']
                last_price = element['Last']
                trading_time = element['Trading time']
                trading_date = element['trading_date']
                # Calculate EMA for the symbol
                ema_value_38 = self.ema_calculator.calculate_ema(last_price, symbol, 38)
                ema_value_100 = self.ema_calculator.calculate_ema(last_price, symbol, 100)
                result = {
                    'Symbol': symbol,
                    'EMA38': ema_value_38,
                    'EMA100': ema_value_100,
                    'Last Price': last_price,
                    'Time': f"{trading_time} {trading_date}"
                }
                
            except (KeyError, ValueError, json.JSONDecodeError) as e:
                logger.error(f"Error processing record: {e}")
        # Log and collect the result
        logger.info(f"{result}")
        yield "Window: {} result: {}".format(context.window(), result)
        #logger.info(f"Countt: {count}, key: {key}")

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
    stream.map(lambda msg: json.loads(msg)) \
        .key_by(lambda msg: msg['ID']) \
        .window(TumblingProcessingTimeWindows.of(Time.minutes(5))) \
        .process(MyProcessWindowFunction())
    # Execute the Flink job
    env.execute("Python Flink Kafka Stream Processing with EMA Calculation")
if __name__ == '__main__':
    process_kafka_stream()
