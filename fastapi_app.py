from fastapi import FastAPI
# Trigger reload for new dependencies
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from routers import stocks, fundamental, indices, news, ranking, edinet, edinet_docs, fundamentals

"""
メインのFastAPIアプリケーション定義ファイル。
アプリケーションの初期化、静的ファイルのマウント、ルーターの登録を行います。
"""

app = FastAPI(
    title="株価分析アプリ (FastAPI + htmx)",
    description="FastAPI, Jinja2, htmxを使用したサーバーサイドレンダリング株価分析アプリケーション。",
)

# Database Setup
from database import engine, SessionLocal
from models import stock

@app.on_event("startup")
def startup_event():
    # 1. Create Tables
    from database import engine
    from models import stock, master
    stock.Base.metadata.create_all(bind=engine)
    master.Base.metadata.create_all(bind=engine)

    # 2. Seed Initial Watchlist (if empty)
    db = SessionLocal()
    try:
        if db.query(stock.Stock).count() == 0:
            initial_codes = ["7203", "6758", "9984", "8306", "8035"]
            for code in initial_codes:
                db_item = stock.Stock(code=code)
                db.add(db_item)
            db.commit()
    except Exception as e:
        print(f"Error seeding watchlist: {e}")
    finally:
        db.close()
    
    # 3. Initialize Stock Master (Async Background)
    from services.stock_master_service import stock_master_service
    import threading
    
    def run_sync():
        stock_master_service.initialize_and_sync()

    thread = threading.Thread(target=run_sync, daemon=True)
    thread.start()

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(stocks.router)
app.include_router(fundamental.router)
app.include_router(indices.router)
app.include_router(news.router)
app.include_router(ranking.router)
app.include_router(edinet.router, prefix="/api")
app.include_router(edinet_docs.router, prefix="/api")
app.include_router(fundamentals.router, prefix="/api")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/stocks")


@app.get("/healthz", include_in_schema=False)
async def healthcheck():
    return {"status": "ok"}
