from PIL import Image
import os


def split_image(image_path, rows, cols, output_dir, prefix, names=None):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    img = Image.open(image_path)
    width, height = img.size
    cell_width = width // cols
    cell_height = height // rows

    count = 0
    for r in range(rows):
        for c in range(cols):
            if names and count >= len(names):
                break

            left = c * cell_width
            top = r * cell_height
            right = left + cell_width
            bottom = top + cell_height

            # Crop a bit to remove margins if needed, or just full cell
            # Let's do full cell first
            icon = img.crop((left, top, right, bottom))

            name = names[count] if names else f"{prefix}_{count}"
            icon.save(os.path.join(output_dir, f"{name}.png"))
            print(f"Saved {name}.png")
            count += 1


# Paths
artifact_dir = (
    "C:/Users/curem/.gemini/antigravity/brain/f4b4c92b-3ce4-48bd-9067-e642ced6f5e5"
)
output_dir = "static/images/candle_patterns"

# Batch 1 (Basic) - 5x4 grid
batch1_names = [
    "big_bear",
    "small_bear",
    "upper_shadow_bear",
    "lower_shadow_bear",
    "bozu_bear",
    "big_bull",
    "small_bull",
    "upper_shadow_bull",
    "lower_shadow_bull",
    "bozu_bull",
    "doji",
    "upper_shadow_doji",
    "upper_shadow_doji_alt",
    "lower_shadow_doji",
    "marubozu_doji",
    "dragonfly_doji",
    "dragonfly_doji_alt",
    "gravestone_doji",
    "koma",
    "long_legged_doji",
]
split_image(
    os.path.join(artifact_dir, "basic_candles_batch_1_1769699642588.png"),
    4,
    5,
    output_dir,
    "batch1",
    batch1_names,
)

# Batch 2 (Advanced 2-candle) - 4x4 grid (14 icons)
batch2_names = [
    "bull_engulfing",
    "bear_engulfing",
    "harami",
    "bull_bear_harami",
    "kiriage",
    "kirisage",
    "kabuse",
    "sashikomi",
    "sashikomi_alt",
    "kenuki_zoko",
    "kenuki_tenjo",
    "daki_bull",
    "daki_bull_alt",
    "daki_bear",
    "kaeshi",
    "kubitsuri",
]
split_image(
    os.path.join(artifact_dir, "advanced_candles_batch_2_1769699703008.png"),
    4,
    4,
    output_dir,
    "batch2",
    batch2_names,
)

# Batch 3 (Advanced 3-candle) - 3x4 grid (12 icons)
batch3_names = [
    "three_white_soldiers",
    "three_black_crows",
    "morning_star",
    "evening_star",
    "sanbagarasu",
    "sanku_tatakikomi",
    "rising_three_methods",
    "falling_three_methods",
    "sutego",
    "sanpei_hasami",
    "gyaku_sanzon",
    "island_reversal",
]
# Wait, my prompt said 12 icons. 3x4 is 12.
split_image(
    os.path.join(artifact_dir, "advanced_candles_batch_3_1769699756415.png"),
    3,
    4,
    output_dir,
    "batch3",
    batch3_names,
)

# Batch 4 (Reference) - 3x3 grid (7 icons)
batch4_names = [
    "gap_up",
    "gap_down",
    "gap_fill",
    "madokan_sanpou",
    "sakata_gohou",
    "range_break",
    "volume_window",
]
split_image(
    os.path.join(artifact_dir, "reference_patterns_batch_4_1769699806302.png"),
    3,
    3,
    output_dir,
    "batch4",
    batch4_names,
)
