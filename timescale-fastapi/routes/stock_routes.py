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
from datetime import datetime

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
        recent_row = await conn.fetch("SELECT id FROM breakouts ORDER BY id DESC LIMIT 1")
    if recent_row:
        breakout_id = recent_row[0]['id']
        exists = await redis_client.hexists(f"breakouts", breakout_id)
        if exists:
            recent_breakouts = []
            recent_breakout_ids = await redis_client.hkeys("breakouts")
            for breakout_id in recent_breakout_ids:
                breakout_data = await redis_client.hget("breakouts", breakout_id.decode("utf-8"))
                if breakout_data:
                    recent_breakouts.append(json.loads(breakout_data.decode("utf-8")))
            return recent_breakouts 

    #DB stuff
    query = """
        SELECT breakouts.id, breakouts.stock_id, stock.symbol, breakouts.dt, breakouts.breakout_type, stock_price.price, breakouts.latency_start, breakouts.latency_end FROM breakouts INNER JOIN stock ON stock.id = breakouts.stock_id LEFT JOIN LATERAL (SELECT stock_price.price FROM stock_price WHERE stock_price.stock_id = breakouts.stock_id ORDER BY ABS(EXTRACT(EPOCH FROM (stock_price.dt - breakouts.dt))) LIMIT 1) stock_price ON true ORDER BY breakouts.dt DESC LIMIT 20;
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
            latency = (row["latency_end"] - row["latency_start"]).total_seconds(),
        )
        for row in rows
    ]

    await redis_client.delete("breakouts")
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
    redis_conn_pool: ConnectionPool = Depends(get_redis)
):
    redis_client = Redis(connection_pool=redis_conn_pool)
    exists = await redis_client.hexists(f"stocks", stock_symbol)
    if exists:
        async with db.acquire() as conn:
            recent_breakouts = await conn.fetch("SELECT id, stock_id FROM breakouts ORDER BY id DESC")
            stock_id = await conn.fetch("SELECT id FROM stock WHERE symbol = '"+ stock_symbol + "';")
        search_data = await redis_client.hget("stocks", stock_symbol)
        search_data = json.loads(search_data.decode('utf-8'))
        found = False
        for recent in recent_breakouts:
            if stock_id[0]['id'] == recent['stock_id']:
                found = False
                for search in search_data:
                    if recent['id'] == search["breakout_id"]:
                        found = True
                        break
                if not found:
                    break
        if found:
            return search_data

    #db stuff
    query = """
        SELECT breakouts.id, breakouts.stock_id, stock.symbol, breakouts.dt, breakouts.breakout_type, stock_price.price, breakouts.latency_start, breakouts.latency_end FROM breakouts INNER JOIN stock ON stock.id = breakouts.stock_id LEFT JOIN LATERAL (SELECT stock_price.price FROM stock_price WHERE stock_price.stock_id = breakouts.stock_id ORDER BY ABS(EXTRACT(EPOCH FROM (stock_price.dt - breakouts.dt))) LIMIT 1) stock_price ON true WHERE stock.symbol = $1 ORDER BY breakouts.dt DESC;
    """
    async with db.acquire() as conn:
        rows = await conn.fetch(query, stock_symbol)
    if not rows:
        raise HTTPException(status_code=404, detail="No breakouts found")
    dt_format = "%Y-%m-%d %H:%M:%S.%f"
    breakouts =  [
        Breakout(
            breakout_id = row['id'],
            stock_symbol = row["symbol"],
            timestamp = row["dt"],
            breakout_type = row["breakout_type"],
            price = row["price"],
            latency =  (row["latency_end"] - row["latency_start"]).total_seconds(),
        )
        for row in rows
    ]

    #store he search
    await redis_client.hdel("stocks", stock_symbol)
    breakouts_dict = [breakout.dict() for breakout in breakouts]
    await redis_client.hset("stocks", stock_symbol, json.dumps(breakouts_dict, default=str))
    await redis_client.expire(f"stocks:{stock_symbol}", 3600)
    return breakouts

@stock_router.get("/stocks", response_model=List[Stock])
async def get_stocks(
    db: Pool = Depends(get_timescale),
):
    query = "SELECT * FROM stock;"
    async with db.acquire() as conn:
        rows = await conn.fetch(query)
    if not rows:
        raise HTTPException(status_code=404, detail="No stocks found")
    stocks = [
            Stock(
                stock_id = row['id'],
                symbol = row['symbol'],
                security_type = row['security_type'],
            )
            for row in rows
        ]
    return stocks

@stock_router.get("/stocks/{stock_symbol}", response_model=List[StockPrice])
async def get_stock_from_symbol(
    stock_symbol: str = Path(..., description="Symbol of desired stock"),
    db: Pool = Depends(get_timescale),
):
    query = "SELECT stock.symbol, stock_price.dt, stock_price.price FROM stock INNER JOIN stock_price ON stock.id = stock_price.stock_id WHERE stock.symbol = $1;"
    async with db.acquire() as conn:
        rows = await conn.fetch(query, stock_symbol)
    if not rows:
        raise HTTPException(status_code=404, detail="No stocks found")
    stocks = [
            StockPrice(
                stock_symbol = row['symbol'],
                timestamp = row['dt'],
                price = row['price'],
            )
            for row in rows
        ]
    return stocks
