from pydantic import BaseModel
from typing import List
from datetime import datetime, date

class Stock(BaseModel):
    symbol: str
    security_type: str

class StockPrice(BaseModel):
    timestamp: datetime
    price: float

class Breakout(BaseModel):
    stock_symbol: str
    timestamp: datetime
    breakout_type: str
    price: float

class BreakoutBatch(BaseModel):
    data: List[Breakout]


