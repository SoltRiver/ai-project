from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from routers import stocks, fundamental

app = FastAPI(
    title="株価分析アプリ (FastAPI + htmx)",
    description="Server-rendered stock views with FastAPI, Jinja2, and htmx.",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(stocks.router)
app.include_router(fundamental.router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/stocks")


@app.get("/healthz", include_in_schema=False)
async def healthcheck():
    return {"status": "ok"}
