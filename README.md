
# AI Investment Assistant (Stock Chart & EDINET Analysis)

FastAPI + htmx + Python で構築された株式投資分析アシスタント。
J-Quants API からの株価・財務情報の取得に加え、EDINET からの有価証券報告書（XBRL/PDF）の自動取得・解析・全文検索機能を備えています。

## Key Features

### 1. Stock Analysis (Basic)
- **Interactive Charts**: TradingView-like candlesticks (Lightweight Charts).
- **Technical Indicators**: SMA, EMA, RSI, MACD, Bollinger Bands, etc.
- **Pattern Recognition**: Automated candlestick pattern detection (Doji, Engulfing, etc.).

### 2. EDINET Data Pipeline (Advanced)
- **Automated Ingestion**: `fetch_daily_documents.py` retrieves all filings from EDINET API v2.
- **XBRL Parsing**: Extracts 25,000+ financial facts per document, normalizing namespaces.
- **Financial Highlights**: Automatically maps XBRL facts to key metrics (Sales, Operating Profit, Net Income).
- **PDF Search**: Full-text search engine for Annual Reports with Japanese semantic search (TRGM) and query guards.

### 3. Architecture
- **Backend**: FastAPI (Python 3.11)
- **Frontend**: Jinja2 Templates + htmx (No complex SPA build)
- **Database**: 
    - **SQLite**: Local development (default)
    - **PostgreSQL**: Production/Docker (recommended for PDF Search)
- **Container**: Full Docker support (`docker-compose`)

## Quick Start (Docker) - Recommended

Requires: Docker & Docker Compose

```bash
# 1. Start Services (App + Postgres)
docker-compose up -d --build

# 2. Wait for DB check
# (The app container waits for postgres:5432 automatically)

# 3. Access
http://localhost:8000
```

## Quick Start (Local)

Requires: Python 3.11+, SQLite (or Postgres)

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install pdfminer.six

# 2. Setup Database
python scripts/reinit_db.py
python scripts/init_financial_highlight.py
python scripts/init_pdf_search.py

# 3. Run Server
uvicorn app:app --reload
```

## Data Ingestion Workflows

### Phase 1: Fetch Data
Fetch documents for a specific date (e.g., 2024-06-26).
```bash
python scripts/fetch_daily_documents.py --date 2024-06-26
```

### Phase 2: Process XBRL
Parse XBRL files to extract financial facts.
```bash
python scripts/process_xbrl.py
```

### Phase 3: Map Financials
Map extracted facts to utilizing financial highlights.
```bash
python scripts/process_financial_highlights.py
```

### Phase 4: PDF Search Indexing
Extract text from PDFs for the search engine.
```bash
python scripts/process_pdf.py --limit 100
```

## Development & Testing

- **Verify Real Data**: `python scripts/verify_real_data.py`
- **Verify PDF Search**: `python scripts/verify_pdf_search.py`

## Directory Structure
- `app.py`: Main entry point
- `services/`: Business logic (EDINET, Stock, Search, etc.)
- `models/`: SQLAlchemy ORM models
- `scripts/`: CLI tools for batch processing
- `sql/`: Raw DDL for specific schemas
- `templates/`: Jinja2 HTML templates
