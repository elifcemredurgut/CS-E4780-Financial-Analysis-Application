import os
import asyncpg
from typing import Optional

DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"

conn_pool: Optional[asyncpg.Pool] = None

async def init_timescale() -> None:
    global conn_pool
    try:
       # conn_pool = await asyncpg.create_pool(
       #     dsn=os.getenv(DATABASE_URL), min_size=1, max_size=10
        #)
        conn_pool = await asyncpg.create_pool(
                dsn=DATABASE_URL, min_size=1, max_size=10
        )
    except Exception as e:
        print("Connection error")
        raise

async def get_timescale() -> asyncpg.Pool:
    global conn_pool
    if conn_pool is None:
        print("No connection pool");
        raise ConnectionError("No connection pool")
    try:
        return conn_pool
    except Exception as e:
        print("Connection failure")
        raise

async def close_timescale() -> None:
    global conn_pool 
    if conn_pool is not None:
        try:
            await conn_pool.close()
            print("Timescale closed")
        except Exception as e:
            print("Could not close")
            raise
    else:
        print("No connection pool")


