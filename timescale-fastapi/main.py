from fastapi import FastAPI
from contextlib import asynccontextmanager
from database.timescale import init_timescale, close_timescale
from routes.stock_routes import stock_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_timescale()
    yield
    await close_timescale()

app: FastAPI = FastAPI(lifespan=lifespan, title="FastAPI for timescale stocks")
app.include_router(stock_router)
