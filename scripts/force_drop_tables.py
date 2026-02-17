
import sqlite3
import os

DB_PATH = "ai_project.db"

def force_drop():
    if not os.path.exists(DB_PATH):
        print(f"DB {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tables = ["edinet_files", "company_info", "sectors", "markets"]
    
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"Dropped table {table}")
        except Exception as e:
            print(f"Error dropping {table}: {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    force_drop()
