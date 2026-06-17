import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL compatible database URL handling
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_project.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# SQLiteの場合はStaticPoolではなくQueuePoolを使い、接続を再利用する
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # 接続の生存確認を有効化
)

# SQLite 向け PRAGMA 最適化（接続確立時に毎回適用）
if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        """SQLite接続時にパフォーマンス向上用PRAGMAを設定する"""
        cursor = dbapi_connection.cursor()
        # WALモード: 読み取りと書き込みの同時実行を可能にし、読み取りロックを排除
        cursor.execute("PRAGMA journal_mode=WAL")
        # synchronous=NORMAL: WALモードとの組み合わせでデータ安全性を維持しつつ高速化
        cursor.execute("PRAGMA synchronous=NORMAL")
        # キャッシュサイズを64MB（デフォルト2MB）に拡大し、ディスクI/Oを削減
        cursor.execute("PRAGMA cache_size=-65536")
        # メモリマップI/Oを有効化（256MB）し、大きなテーブルの読み取りを高速化
        cursor.execute("PRAGMA mmap_size=268435456")
        # テンポラリテーブルをメモリに配置
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
