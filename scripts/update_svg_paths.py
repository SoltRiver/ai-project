import re
import os

TARGET_FILE = "services/stock_service.py"


def update_paths():
    if not os.path.exists(TARGET_FILE):
        print(f"Error: {TARGET_FILE} not found.")
        return

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace .png with .svg in candle pattern paths
    # Matches: "svg": "images/candle_patterns/foo.png" -> "svg": "images/candle_patterns/foo.svg"
    new_content = re.sub(r'(images/candle_patterns/[^"]+)\.png', r"\1.svg", content)

    if content != new_content:
        with open(TARGET_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Successfully updated stock_service.py to use .svg extension.")
    else:
        print("No changes needed (already updated or pattern not found).")


if __name__ == "__main__":
    update_paths()
