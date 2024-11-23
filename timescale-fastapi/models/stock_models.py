from pydantic import BaseModel
from typing import List
from datetime import datetime, date

class Stock(BaseModel):
    stock_id: int
    symbol: str
    security_type: str

class StockPrice(BaseModel):
    stock_symbol: str
    timestamp: datetime
    price: float

class Breakout(BaseModel):
    breakout_id: int
    stock_symbol: str
    timestamp: datetime
    breakout_type: str
    price: float
    latency: float

class BreakoutBatch(BaseModel):
    data: List[Breakout]


