FROM timescale/timescaledb-ha:pg16
ENV POSTGRES_DB=stocksdb
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=password
COPY create_tables.sql /docker-entrypoint-initdb.d/

