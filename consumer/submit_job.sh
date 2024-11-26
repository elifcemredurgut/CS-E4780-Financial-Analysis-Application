#!/bin/bash

echo "Submitting Flink job..."
/opt/flink/bin/flink run -d -m jobmanager:8081 -py /opt/flink_job_same_window.py
#/opt/flink/bin/flink run -d -m jobmanager:8081 -py /opt/flink_job_topic_read.py
#/opt/flink/bin/flink run -d -m jobmanager:8081 -py /opt/flink_job_ema.py
#/opt/flink/bin/flink run -d -m jobmanager:8081 -py /opt/flink_job_price.py

