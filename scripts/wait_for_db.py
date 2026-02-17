
import time
import os
import sys
import psycopg2

def wait_for_db():
    db_url = os.getenv("DATABASE_URL")
    if not db_url or "sqlite" in db_url:
        print("Using SQLite or no DB defined. Skipping wait.")
        return

    print("Waiting for database...")
    retries = 30
    while retries > 0:
        try:
            # Parse URL (simple handling for user:pass@host:port/dbname)
            # postgresql://user:password@db:5432/edinet_db
            from urllib.parse import urlparse
            result = urlparse(db_url)
            username = result.username
            password = result.password
            database = result.path[1:]
            hostname = result.hostname
            port = result.port
            
            conn = psycopg2.connect(
                dbname=database,
                user=username,
                password=password,
                host=hostname,
                port=port
            )
            conn.close()
            print("Database is ready!")
            return
        except Exception as e:
            print(f"DB not ready yet: {e}")
            retries -= 1
            time.sleep(2)
            
    print("Database init timed out.")
    sys.exit(1)

if __name__ == "__main__":
    wait_for_db()
