
# SQLite to PostgreSQL Migration Guide

## 1. Prerequisites
- PostgreSQL Instance running (v13+ recommended).
- `psql` command line tool available.
- Python environment with `psycopg2` or `psycopg2-binary` installed.

## 2. DDL Application (PostgreSQL)
Create the schema using SQLAlchemy or raw SQL.
Since our models are defined in `models/`, we can use a script to generate the schema.

### 2-1. Generate Schema
Ensure `DATABASE_URL` in `.env` points to your PostgreSQL instance.
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/ai_project
```
Then run the init scripts:
```bash
python -c "from database import Base, engine; from models import edinet_document, edinet_file; Base.metadata.create_all(engine)"
```
*Note: Ensure `ENUM` types are handled if used. Currently we use Strings for compatibility.*

## 3. Data Export (SQLite)
Export data to CSV for bulk import.

```bash
sqlite3 ai_project.db
sqlite> .headers on
sqlite> .mode csv
sqlite> .output edinet_documents.csv
sqlite> SELECT * FROM edinet_documents;
sqlite> .output edinet_files.csv
sqlite> SELECT * FROM edinet_files;
sqlite> .quit
```
*Note: Check boolean fields (0/1 vs t/f). SQLite stores them as 0/1 usually. Postgres accepts 0/1 for BOOLEAN type sometimes, or cast to INTEGER.*

## 4. Data Import (PostgreSQL)
Use `\COPY` command in `psql`.

```sql
-- Connect to Postgres
psql -d ai_project

-- Import Documents
\COPY edinet_documents FROM 'edinet_documents.csv' WITH (FORMAT csv, HEADER true);

-- Import Files
\COPY edinet_files FROM 'edinet_files.csv' WITH (FORMAT csv, HEADER true);
```

## 5. Validation Check
Run the following queries on both DBs to compare.

### 5-1. Count Check
```sql
SELECT count(*) FROM edinet_documents;
SELECT count(*) FROM edinet_files;
```

### 5-2. Idempotency Check
```sql
SELECT doc_id, file_type, count(*) 
FROM edinet_files 
GROUP BY doc_id, file_type 
HAVING count(*) > 1;
-- Should return 0 rows
```

### 5-3. Path Check
```sql
SELECT count(*) FROM edinet_files WHERE storage_path LIKE 'D:%';
-- Should return 0 rows (Must be relative path)
```

## 6. Switch Application Configuration
Update `.env` to use PostgreSQL.

```properties
# .env
DATABASE_URL=postgresql://user:password@localhost:5432/ai_project
```

Restart the application/scripts.
