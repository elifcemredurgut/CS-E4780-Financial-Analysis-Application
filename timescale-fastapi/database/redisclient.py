import os
import redis.asyncio as redis
from typing import Optional

REDIS_URL = f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379"

redis_pool: None

async def init_redis() -> None:
    global redis_pool
    try:
        redis_pool = redis.ConnectionPool.from_url(REDIS_URL, max_connections=10)
    except Exception as e:
        print("!!REDIS CONNECTION ERROR!!: Redis connection error")
        raise

async def get_redis() -> redis.ConnectionPool:
    global redis_pool
    if redis_pool is None:
        print("No connection pool");
        raise ConnectionError("No connection pool")
    try:
        return redis_pool
    except Exception as e:
        print("!!!REDIS CONNECTION FAILURE!!!")
        raise

async def close_redis() -> None:
    if redis_pool is not None:
        try:
            await redis_pool.aclose()
            print("Redis closed")
        except Exception as e:
            print("Could not close Redis")
            raise
    else:
        print("No connection pool")



