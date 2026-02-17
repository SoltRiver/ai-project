
import sys
import os
import zipfile
from bs4 import BeautifulSoup
from pathlib import Path

# Add project root
sys.path.insert(0, ".")

from services.edinet_storage import BASE_STORAGE_DIR

def debug_xbrl(doc_id):
    # Hardcoded path relative to BASE_STORAGE_DIR based on previous output
    # Path: 2024\06\S100TSFF\raw\edinet_type1.zip
    # But explicitly using what we found
    
    # We can reconstruct it or just use the relative path found
    rel_path = r"2024\06\S100TSFF\raw\edinet_type1.zip"
    zip_path = BASE_STORAGE_DIR / rel_path
    
    print(f"Debug XBRL for {doc_id} at {zip_path}")
    
    if not zip_path.exists():
        print("File not found!")
        return

    with zipfile.ZipFile(zip_path, 'r') as z:
        print("\n--- ZIP Contents ---")
        xbrl_file = None
        for f in z.namelist():
            print(f" - {f}")
            if f.endswith(".xbrl") and "PublicDoc" in f:
                xbrl_file = f
        
        if xbrl_file:
            print(f"\n--- Parsing {xbrl_file} ---")
            with open("verify_output.txt", "w", encoding="utf-8") as out:
                with z.open(xbrl_file) as f:
                    soup = BeautifulSoup(f, "lxml-xml")
                    
                    out.write(f"Root Tag: {soup.find().name if soup.find() else 'None'}\n")
                    
                    tags = soup.find_all()
                    out.write(f"Total Tags: {len(tags)}\n")
                    
                    out.write(f"\n--- First 20 Content Tags (Non-System) ---\n")
                    count = 0
                    excluded = ["link", "xbrli", "xbrl", "xlink", "xbrldi", "iso4217"]
                    for t in tags:
                        if t.name:
                            prefix = t.prefix if hasattr(t, 'prefix') else 'None'
                            # Check prefix
                            if prefix in excluded: continue
                            
                            out.write(f"Tag: {t.name} (prefix={prefix}) | Ref: {t.get('contextRef')} | Val: {t.text[:20]}\n")
                            count += 1
                            if count >= 20: break
                            
                    out.write("\n--- Context Definitions ---\n")
                    contexts = soup.find_all(["xbrli:context", "context"])
                    out.write(f"Found {len(contexts)} contexts\n")
                    for c in contexts[:5]:
                        out.write(f"ID: {c.get('id')}\n")
            print("Debug output written to verify_output.txt")

        else:
            print("No .xbrl file found in PublicDoc!")

if __name__ == "__main__":
    debug_xbrl("S100TSFF")
