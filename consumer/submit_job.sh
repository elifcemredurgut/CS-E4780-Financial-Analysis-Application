#!/bin/bash

# Submit the Flink job
echo "Submitting Flink job..."
/opt/flink/bin/flink run -d -m jobmanager:8081 -py /opt/flink_job_ema.py
/opt/flink/bin/flink run -d -m jobmanager:8081 -py /opt/flink_job_price.py

