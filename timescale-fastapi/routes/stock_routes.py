from fastapi import HTTPException, Path, Body, APIRouter, Depends
from database.timescale import get_timescale
from database.redisclient import get_redis
from typing import Union, List
from asyncpg import Pool
from redis.asyncio import Redis, ConnectionPool
import json
from models.stock_models import (
    Stock,
    StockPrice,
    Breakout,
    BreakoutBatch,
)

stock_router = APIRouter()

@stock_router.get("/")
def read_root():
    return {"message": "Hello World"}

@stock_router.get("/breakouts/recent", response_model=List[Breakout])
async def get_recent_breakouts(
        db: Pool = Depends(get_timescale),
        redis_conn_pool: ConnectionPool = Depends(get_redis)
):
    #Redis Jail
    redis_client = Redis(connection_pool=redis_conn_pool)
    async with db.acquire() as conn:
        recent_row = await conn.fetch("SELECT id FROM breakouts ORDER BY latency_end DESC LIMIT 1")
    if recent_row:
        breakout_id = recent_row[0]['id']
        exists = await redis_client.hexists(f"breakouts", breakout_id)
        if exists:
            recent_breakouts = []
            recent_breakout_ids = await redis_client.hkeys("breakouts") 
            print(recent_breakout_ids)
            for breakout_id in recent_breakout_ids:
                breakout_data = await redis_client.hget("breakouts", breakout_id.decode("utf-8"))
                if breakout_data:
                    recent_breakouts.append(json.loads(breakout_data.decode("utf-8")))
            print("yay cache")
            return recent_breakouts 

   # breakouts = await redis_client.lrange("recent", 0, 19)
   # cached_breakout_ids = [json.loads(breakout.decode("utf-8")).get("id") for breakout in breakouts]
   # breakouts_dict = [json.loads(breakout.decode("utf-8")) for breakout in breakouts]
   # if breakouts and all(breakout_id in cached_breakout_ids for breakout_id in recent_breakout_ids):
    #    print("YAY REDIS")
    #    return breakouts_dict

    #DB stuff
    query = """
        SELECT breakouts.id, breakouts.stock_id, stock.symbol, breakouts.dt, breakouts.breakout_type, stock_price.price FROM breakouts INNER JOIN stock ON stock.id = breakouts.stock_id LEFT JOIN LATERAL (SELECT stock_price.price FROM stock_price WHERE stock_price.stock_id = breakouts.stock_id ORDER BY ABS(EXTRACT(EPOCH FROM (stock_price.dt - breakouts.dt))) LIMIT 1) stock_price ON true ORDER BY breakouts.dt DESC LIMIT 20;
        """
    async with db.acquire() as conn:
        rows = await conn.fetch(query)
    if not rows:
        raise HTTPException(status_code=404, detail="No breakouts found")
    breakouts = [
        Breakout(
            breakout_id = row["id"],
            stock_symbol = row["symbol"],
            timestamp = row["dt"],
            breakout_type = row['breakout_type'],
            price = row["price"],
        )
        for row in rows
    ]

    breakouts_dict = [breakout.dict() for breakout in breakouts]
    for breakout in breakouts_dict:
        breakout_id = breakout["breakout_id"]
        await redis_client.hset("breakouts", breakout_id, json.dumps(breakout, default=str))
    await redis_client.expire("breakouts", 600)
    return breakouts  

@stock_router.get("/breakouts/{stock_symbol}", response_model=List[Breakout])
async def get_stock_breakouts(
    stock_symbol: str = Path(..., description="Symbol of desired stock"),
    db: Pool = Depends(get_timescale),
):
    query = """
        SELECT breakouts.id, breakouts.stock_id, stock.symbol, breakouts.dt, breakouts.breakout_type, stock_price.price FROM breakouts INNER JOIN stock_price ON stock_price.stock_id=breakouts.stock_id INNER JOIN stock ON stock.id = breakouts.stock_id WHERE stock.symbol = $1 ORDER BY breakouts.dt DESC;
    """
    async with db.acquire() as conn:
        rows = await conn.fetch(query, stock_symbol)
    if not rows:
        raise HTTPException(status_code=404, detail="No breakouts found")
    return [
        Breakout(
            breakout_id = row['id'],
            stock_symbol = row["symbol"],
            timestamp = row["dt"],
            breakout_type = row["breakout_type"],
            price = row["price"],
        )
        for row in rows
    ]

