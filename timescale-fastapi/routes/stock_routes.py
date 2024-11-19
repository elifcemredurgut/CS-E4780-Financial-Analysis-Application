from fastapi import HTTPException, Path, Body, APIRouter, Depends
from database.timescale import get_timescale
from typing import Union, List
from asyncpg import Pool
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
        db: Pool = Depends(get_timescale)
):
    query = """
        SELECT breakouts.stock_id, stock.symbol, breakouts.dt, breakouts.breakout_type, stock_price.price FROM breakouts INNER JOIN stock_price ON stock_price.stock_id=breakouts.stock_id INNER JOIN stock ON stock.id = breakouts.stock_id ORDER BY breakouts.dt DESC LIMIT 20;
        """
    async with db.acquire() as conn:
        rows = await conn.fetch(query)
    if not rows:
        raise HTTPException(status_code=404, detail="No breakouts found")
    return [
        Breakout(
            stock_symbol = row["symbol"],
            timestamp = row["dt"],
            breakout_type = row['breakout_type'],
            price = row["price"],
        )
        for row in rows
    ]

@stock_router.get("/breakouts/{stock_symbol}", response_model=List[Breakout])
async def get_stock_breakouts(
    stock_symbol: str = Path(..., description="Symbol of desired stock"),
    db: Pool = Depends(get_timescale),
):
    query = """
        SELECT breakouts.stock_id, stock.symbol, breakouts.dt, breakouts.breakout_type, stock_price.price FROM breakouts INNER JOIN stock_price ON stock_price.stock_id=breakouts.stock_id INNER JOIN stock ON stock.id = breakouts.stock_id WHERE stock.symbol = $1 ORDER BY breakouts.dt DESC;
    """
    async with db.acquire() as conn:
        rows = await conn.fetch(query, stock_symbol)
    if not rows:
        raise HTTPException(status_code=404, detail="No breakouts found")
    return [
        Breakout(
            stock_symbol = row["symbol"],
            timestamp = row["dt"],
            breakout_type = row["breakout_type"],
            price = row["price"],
        )
        for row in rows
    ]

