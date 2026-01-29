import os
import glob
import shutil

# Map of part of the filename to the desired final name (without extension)
mapping = {
    "per_icon": "per",
    "pbr_icon": "pbr",
    "dividend_yield_icon": "dividend_yield",
    "equity_ratio_icon": "equity_ratio",
    "trend_icon": "trend",
    "support_line_icon": "support_line",
    "resistance_line_icon": "resistance_line",
    "volume_icon": "volume",
    "moving_average_icon": "moving_average",
    "rsi_icon": "rsi",
    "macd_icon": "macd",
    "trend_line_icon": "trend_line"
}

target_dir = "static/images/glossary"

files = glob.glob(os.path.join(target_dir, "*_icon_*.png"))

for file_path in files:
    filename = os.path.basename(file_path)
    # Find which key matches
    for key, new_name in mapping.items():
        if key in filename:
            new_path = os.path.join(target_dir, f"{new_name}.png")
            print(f"Renaming {filename} to {new_name}.png")
            os.rename(file_path, new_path)
            break
