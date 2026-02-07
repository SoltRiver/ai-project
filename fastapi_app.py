from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from routers import stocks, fundamental, indices, news, ranking, edinet

"""
メインのFastAPIアプリケーション定義ファイル。
アプリケーションの初期化、静的ファイルのマウント、ルーターの登録を行います。
"""

app = FastAPI(
    title="株価分析アプリ (FastAPI + htmx)",
    description="FastAPI, Jinja2, htmxを使用したサーバーサイドレンダリング株価分析アプリケーション。",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(stocks.router)
app.include_router(fundamental.router)
app.include_router(indices.router)
app.include_router(news.router)
app.include_router(ranking.router)
app.include_router(edinet.router, prefix="/api")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/stocks")


@app.get("/healthz", include_in_schema=False)
async def healthcheck():
    return {"status": "ok"}
