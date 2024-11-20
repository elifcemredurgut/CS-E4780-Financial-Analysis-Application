from fastapi import FastAPI
from contextlib import asynccontextmanager
from database.timescale import init_timescale, close_timescale
from routes.stock_routes import stock_router
from database.redisclient import init_redis, close_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_timescale()
    await init_redis()
    yield
    await close_timescale()
    await close_redis()

app: FastAPI = FastAPI(lifespan=lifespan, title="FastAPI for timescale stocks")
app.include_router(stock_router)
