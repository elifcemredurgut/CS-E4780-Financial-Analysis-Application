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

@stock_router.get("/breakouts/{stock_id}", response_model=List[Breakout])
async def get_stock_breakouts(
    stock_id: int = Path(..., description="ID of desired stock"),
    db: Pool = Depends(get_timescale),
):
    query = """
        SELECT breakouts.stock_id, breakouts.dt, breakouts.breakout_type, stock_price.price FROM breakouts INNER JOIN stock_price ON stock_price.stock_id=breakouts.stock_id WHERE breakouts.stock_id = $1 ORDER BY breakouts.dt DESC;
    """
    async with db.acquire() as conn:
        rows = await conn.fetch(query, stock_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No breakouts found")
    return [
        Breakout(
            timestamp = row["dt"],
            breakout_type = row["breakout_type"],
            price = row["price"],
        )
        for row in rows
    ]

