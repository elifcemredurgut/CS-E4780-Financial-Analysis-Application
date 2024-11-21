CREATE EXTENSION IF NOT EXISTS timescaledb;
SET datestyle = 'ISO, DMY';

CREATE TABLE stock (
	id SERIAL PRIMARY KEY,
	symbol TEXT NOT NULL,
	security_type TEXT NOT NULL
);

CREATE TABLE ema (
	stock_id INTEGER NOT NULL,
	dt TIMESTAMP NOT NULL,
	prev_ema38 DOUBLE PRECISION,
	prev_ema100 DOUBLE PRECISION,
	ema38 DOUBLE PRECISION,
	ema100 DOUBLE PRECISION,
	latency_start TIMESTAMP NOT NULL,
	PRIMARY KEY (stock_id, dt),
	CONSTRAINT fk_stock FOREIGN KEY (stock_id) REFERENCES stock (id)
);

CREATE TABLE stock_price (
	stock_id INTEGER NOT NULL,
	dt TIMESTAMP NOT NULL,
	price DOUBLE PRECISION NOT NULL,
	PRIMARY KEY (stock_id, dt),
	CONSTRAINT fk_stock FOREIGN KEY (stock_id) REFERENCES stock (id)
);

CREATE TABLE breakouts (
	id SERIAL,
	stock_id INTEGER NOT NULL,
	dt TIMESTAMP NOT NULL,
	breakout_type TEXT NOT NULL,
	latency_start TIMESTAMP NOT NULL,
	latency_end TIMESTAMP NOT NULL,
	PRIMARY KEY (stock_id, dt),
	CONSTRAINT fk_stock FOREIGN KEY (stock_id) REFERENCES stock (id)
);

CREATE UNIQUE INDEX ON ema (stock_id, dt);
CREATE INDEX ON breakouts(stock_id, dt);
CREATE UNIQUE INDEX ON stock_price (stock_id, dt);

SELECT create_hypertable('stock_price', 'dt');
SELECT create_hypertable('ema', 'dt');
SELECT create_hypertable('breakouts', 'dt');
SELECT set_chunk_time_interval('ema', INTERVAL '1 day');
SELECT add_retention_policy('ema', INTERVAL '7 days');
SELECT add_retention_policy('stock_price', INTERVAL '7 days');

-- TRIGGERS HERE
CREATE OR REPLACE FUNCTION record_bull_breakout()
	RETURNS trigger AS $record_bull_breakout$
DECLARE
        breakout_time TIMESTAMP := NOW();
BEGIN
	IF NEW.ema38 > NEW.ema100 AND NEW.prev_ema38 <= NEW.prev_ema100 THEN
		INSERT INTO breakouts (stock_id, dt, breakout_type, latency_start, latency_end)
			VALUES(NEW.stock_id, NEW.dt, 'bull', NEW.latency_start, breakout_time)
			ON CONFLICT DO NOTHING;
	END IF;
	RETURN NEW;
END;
$record_bull_breakout$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION record_bear_breakout()
	RETURNS trigger AS $record_bear_breakout$
DECLARE
        breakout_time TIMESTAMP := NOW();
BEGIN
        IF NEW.ema38 < NEW.ema100 AND NEW.prev_ema38 >= NEW.prev_ema100 THEN
		INSERT INTO breakouts (stock_id, dt, breakout_type, latency_start, latency_end)
                        VALUES(NEW.stock_id, NEW.dt, 'bear', NEW.latency_start, breakout_time)
			ON CONFLICT DO NOTHING;
        END IF;
        RETURN NEW;
END;
$record_bear_breakout$ LANGUAGE plpgsql;

CREATE TRIGGER record_bull_breakout
	BEFORE INSERT ON ema
	FOR EACH ROW
	EXECUTE PROCEDURE record_bull_breakout();

CREATE TRIGGER record_bear_breakout
        BEFORE INSERT ON ema
        FOR EACH ROW
        EXECUTE PROCEDURE record_bear_breakout();

-- View for breakouts, can be updated as needed FIXME
/*DROP MATERIALIZED VIEW IF EXISTS breakout_summary;
CREATE MATERIALIZED VIEW breakout_summary
    WITH (timescaledb.continuous) AS
    SELECT time_bucket('5 minutes', dt) AS bucket,
           stock_id,
           COUNT(*) FILTER (WHERE breakout_type = 'bull') AS bull_breakouts,
           COUNT(*) FILTER (WHERE breakout_type = 'bear') AS bear_breakouts
    FROM breakouts
    GROUP BY bucket, stock_id;
SELECT add_continuous_aggregate_policy('breakout_summary', start_offset => INTERVAL '5 minutes');*/
