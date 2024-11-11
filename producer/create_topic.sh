#!/bin/bash

# Create the topic with the desired number of partitions and replication factor
kafka-topics --bootstrap-server kafka1:9092 --create --topic stocks --partitions 10 --replication-factor 2
kafka-topics --bootstrap-server kafka1:9092 --create --topic error --partitions 1 --replication-factor 1
