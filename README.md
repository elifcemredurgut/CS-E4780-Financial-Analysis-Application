WELCOME TO THE CS-E4780 FINANCIAL ANALYSIS APPLICATION PROJECT!

2024-2025 - Fall Semester

----------------------------------------------------------------

CONTRIBUTORS (A to Z):

- Elif Cemre Durgut (@elifcemredurgut)
- Metehan Koç (@DatAmstrongest)
- Tori Simon (@torisimon2)

----------------------------------------------------------------

HOW TO RUN THE PROJECT?

1) Place the .csv files in /producer/data

2) Run the project using the command below:
```
docker-compose up --build
```

3) Access the Grafana UI via the link below:

http://localhost:3000/

4) Enter the credentials:
```
username: admin

password: admin
```

5)  Click on "Financial Data Analysis" in the "Recently accessed dashbords" bar

6) Select one or more stock symbol(s) to view their price graph and breakouts

7) You can adjust the time range based on the data you have run.

8) The default refresh time is set to 5 seconds, but you can turn it on/off from the top-right corner.

9) For additional details regarding Apache Flink, the UI and logs are available here:

http://localhost:8081/

----------------------------------------------------------------

HOW TO TEST THE PROJECT?

1) Accuracy Test

1.1) Run the following file to calculate breakouts
```
cd /accuracy-testing
python3 actual_ema_breakout_collector.py
```

1.2) Run the following file to get the breakouts from the system
```
python3 system_ema_breakout_collector.py
```

1.3) Run the following file to compare actual and system breakouts
```
python3 accuracy_checker.py
```

2) Latency Test

2.1) Connect TimescaleDB container
```
psql -U postgres -d stocksdb
```

2.2) Run the following SQL statement:
```
select AVG(latency_end - latency_start)  from breakouts;
```

----------------------------------------------------------------

PROJECT DOCUMENTS

The project requirements link given by the course instructor:

TO BE ADDED

The project report link:

TO BE ADDED