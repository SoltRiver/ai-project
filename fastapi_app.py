from fastapi import FastAPI

# Trigger reload for new dependencies
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

# (Removed TemplateResponse Compatibility Patch)


from routers import (
    stocks,
    fundamental,
    indices,
    news,
    ranking,
    edinet,
    edinet_docs,
    fundamentals,
    calendar,
    edinet_diff,
    analysis_internal,
    stock_ai,
)

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
    from models import stock, master, edinet_file, company_info, stock_impact
    from models import event_source_policy, event
    from models import edinet_facts_snapshot, edinet_diff_summary

    # AI分析SWRシステム用モデル
    from models import analysis_snapshot, analysis_job, analysis_config

    # ニュースAI要約システム用モデル
    from models import news_article, news_ai_summary, news_related_ticker

    stock.Base.metadata.create_all(bind=engine)
    master.Base.metadata.create_all(bind=engine)
    edinet_file.Base.metadata.create_all(bind=engine)
    company_info.Base.metadata.create_all(bind=engine)
    stock_impact.Base.metadata.create_all(bind=engine)
    # イベント自動抽出用テーブル（ソースポリシー＋冪等管理）
    event_source_policy.Base.metadata.create_all(bind=engine)
    # イベントカレンダー用テーブル
    event.Base.metadata.create_all(bind=engine)
    # EDINET差分比較用テーブル
    edinet_facts_snapshot.Base.metadata.create_all(bind=engine)
    edinet_diff_summary.Base.metadata.create_all(bind=engine)
    # AI分析SWRシステム用テーブル
    analysis_snapshot.Base.metadata.create_all(bind=engine)
    analysis_job.Base.metadata.create_all(bind=engine)
    analysis_config.Base.metadata.create_all(bind=engine)
    # ニュースAI要約システム用テーブル
    news_article.Base.metadata.create_all(bind=engine)
    news_ai_summary.Base.metadata.create_all(bind=engine)
    news_related_ticker.Base.metadata.create_all(bind=engine)

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

    # 4. analysis_config の初期データ投入（未登録のキーのみ）
    from models.analysis_config import AnalysisConfig, DEFAULT_CONFIG

    db2 = SessionLocal()
    try:
        for cfg_key, cfg_val in DEFAULT_CONFIG.items():
            exists = db2.query(AnalysisConfig).filter_by(key=cfg_key).first()
            if not exists:
                db2.add(AnalysisConfig(key=cfg_key, value=cfg_val))
        db2.commit()
    except Exception as e:
        print(f"Error seeding analysis_config: {e}")
        db2.rollback()
    finally:
        db2.close()

    # 3. Initialize Stock Master (Async Background)
    from services.stock_master_service import stock_master_service
    import threading

    def run_sync():
        stock_master_service.initialize_and_sync()

    thread = threading.Thread(target=run_sync, daemon=True)
    thread.start()

    # 4. ニュースバッチ処理スケジューラ起動
    from services.news_batch_service import start_news_scheduler

    start_news_scheduler()


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
app.include_router(calendar.router)
app.include_router(edinet_diff.router)
# AI分析SWRシステム用ルーター
app.include_router(analysis_internal.router)
# LangGraph AIニュース要約用ルーター
app.include_router(stock_ai.router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/stocks")


@app.get("/healthz", include_in_schema=False)
async def healthcheck():
    return {"status": "ok"}
