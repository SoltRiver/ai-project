
import os
from pathlib import Path
import shutil

# Hardcoded root based on services/edinet_storage.py default
ROOT = Path(r"D:\edinet_data")

def clear_logs():
    print(f"Scanning {ROOT} for xbrl_detect.json...")
    count = 0
    for p in ROOT.rglob("xbrl_detect.json"):
        try:
            p.unlink()
            count += 1
            # print(f"Deleted {p}")
        except Exception as e:
            print(f"Error deleting {p}: {e}")
    
    print(f"Deleted {count} logs.")

if __name__ == "__main__":
    clear_logs()
