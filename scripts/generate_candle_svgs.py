import os

# Configuration
OUTPUT_DIR = "static/images/candle_patterns"
BG_COLOR = "#0B1E2D"
BULL_COLOR = "#00FF00"
BEAR_COLOR = "#FF0000"
DOJI_COLOR = "#FFFFFF"  # Neutral for Doji

# Canvas size
WIDTH = 200
HEIGHT = 200
PADDING = 20


class Candle:
    def __init__(self, x_cnt, open_p, close_p, high_p, low_p):
        self.x = x_cnt  # 0 to 100 scale ideally, or just relative
        self.open = open_p
        self.close = close_p
        self.high = high_p
        self.low = low_p

    @property
    def is_bull(self):
        return self.close > self.open

    @property
    def is_bear(self):
        return self.close < self.open

    @property
    def is_doji(self):
        return abs(self.close - self.open) < 0.5  # Float tolerance


# 1本足で描画されるパターンのキー一覧（中央に細めに描画するため）
SINGLE_CANDLE_KEYS = {
    "big_bull",
    "small_bull",
    "upper_shadow_bull",
    "lower_shadow_bull",
    "bozu_bull",
    "big_bear",
    "small_bear",
    "upper_shadow_bear",
    "lower_shadow_bear",
    "bozu_bear",
    "doji",
    "upper_shadow_doji",
    "lower_shadow_doji",
    "marubozu_doji",
    "dragonfly_doji",
    "gravestone_doji",
    "koma",
    "long_legged_doji",
    "kubitsuri",
    "closing_marubozu_bull",
    "opening_marubozu_bull",
    "karakasa_bull",
    "tonkachi_bull",
    "closing_marubozu_bear",
    "opening_marubozu_bear",
    "karakasa_bear",
    "tonkachi_bear",
}


def generate_svg(pattern_id, candles):
    # Determine bounds to scale
    min_val = min(c.low for c in candles)
    max_val = max(c.high for c in candles)
    val_range = max_val - min_val if max_val != min_val else 10

    # Add margin to range
    margin_y = val_range * 0.2
    min_val -= margin_y
    max_val += margin_y
    val_range = max_val - min_val

    # Calculate scale Y
    # Canvas Y goes from 0 (top) to HEIGHT (bottom)
    # Price max -> Y=PADDING
    # Price min -> Y=HEIGHT-PADDING
    def get_y(val):
        ratio = (val - min_val) / val_range
        # Invert because screen coords: high val is low Y
        return (HEIGHT - PADDING) - (ratio * (HEIGHT - 2 * PADDING))

    # Calculate X
    # Distribute candles evenly
    count = len(candles)

    # Adjust width for single candles as requested (1/2 width)
    width_factor = 0.5 if pattern_id in SINGLE_CANDLE_KEYS else 1.0

    candle_width = ((WIDTH - 2 * PADDING) / (count * 2)) * width_factor

    # Center them
    # For single candles, we want them centered but narrower.
    # If we reduce candle_width, total_block_width reduces, so it stays centered.

    # Gap between candles = candle_width * 0.5
    gap = candle_width * 0.5
    total_block_width = (count * candle_width) + ((count - 1) * gap)

    start_x = (WIDTH - total_block_width) / 2
    step_x = candle_width + gap

    svg_content = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}">'
    )
    svg_content += f'<rect width="100%" height="100%" fill="{BG_COLOR}"/>'

    for i, c in enumerate(candles):
        cx = start_x + (i * step_x) + (candle_width / 2)
        y_high = get_y(c.high)
        y_low = get_y(c.low)
        y_open = get_y(c.open)
        y_close = get_y(c.close)

        # Color
        if c.is_bull:
            color = BULL_COLOR
            body_top = y_close
            body_bot = y_open
        elif c.is_bear:
            color = BEAR_COLOR
            body_top = y_open
            body_bot = y_close
        else:
            color = DOJI_COLOR
            body_top = y_open - 1  # Minimal thickness
            body_bot = y_open + 1

        # Wick
        svg_content += (
            f'<line x1="{cx}" y1="{y_high}" x2="{cx}" y2="{y_low}" '
            f'stroke="{color}" stroke-width="2" />'
        )

        # Body
        h = max(2, body_bot - body_top)  # Ensure at least 2px height
        svg_content += (
            f'<rect x="{cx - candle_width/2}" y="{body_top}" '
            f'width="{candle_width}" height="{h}" fill="{color}" stroke="none" />'
        )

    svg_content += "</svg>"
    return svg_content


# Define Patterns (Relative Values)
# Scale 0-100 roughly
PATTERNS = {
    # Basic Bullish
    "big_bull": [Candle(0, 20, 80, 85, 15)],
    "small_bull": [Candle(0, 45, 55, 60, 40)],
    "upper_shadow_bull": [Candle(0, 40, 60, 90, 35)],  # Long upper shadow
    "lower_shadow_bull": [Candle(0, 40, 60, 65, 10)],  # Long lower shadow
    "bozu_bull": [Candle(0, 20, 80, 80, 20)],  # Shaven
    # Basic Bearish
    "big_bear": [Candle(0, 80, 20, 85, 15)],
    "small_bear": [Candle(0, 55, 45, 60, 40)],
    "upper_shadow_bear": [Candle(0, 60, 40, 90, 35)],
    "lower_shadow_bear": [Candle(0, 60, 40, 65, 10)],
    "bozu_bear": [Candle(0, 80, 20, 80, 20)],
    # Basic Doji/Neutral
    "doji": [Candle(0, 50, 50, 70, 30)],
    "upper_shadow_doji": [Candle(0, 50, 50, 90, 48)],
    "lower_shadow_doji": [Candle(0, 50, 50, 52, 10)],
    "marubozu_doji": [Candle(0, 50, 50, 50, 50)],  # Flat line
    "dragonfly_doji": [Candle(0, 80, 80, 80, 10)],  # High=Open=Close
    "gravestone_doji": [Candle(0, 20, 20, 90, 20)],  # Low=Open=Close
    "koma": [Candle(0, 48, 52, 60, 40)],  # Spinning top (small body)
    "long_legged_doji": [Candle(0, 50, 50, 95, 5)],
    # Advanced
    "bull_engulfing": [
        Candle(0, 55, 45, 60, 40),
        Candle(1, 40, 60, 65, 35),
    ],  # Bear then Big Bull wrapping
    "bear_engulfing": [
        Candle(0, 45, 55, 60, 40),
        Candle(1, 60, 40, 65, 35),
    ],  # Bull then Big Bear wrapping
    "harami": [
        Candle(0, 20, 80, 85, 15),
        Candle(1, 60, 40, 65, 35),
    ],  # Big Bull then Small Bear inside
    "bull_bear_harami": [
        Candle(0, 80, 20, 85, 15),
        Candle(1, 40, 60, 65, 35),
    ],  # Big Bear then Small Bull inside (Was inyo_harami)
    "kiriage": [Candle(0, 30, 50, 55, 25), Candle(1, 55, 75, 80, 50)],  # Rising lows
    "kirisage": [
        Candle(0, 70, 50, 55, 45),
        Candle(1, 45, 25, 30, 20),
    ],  # Lowering highs (Bearish)
    "kabuse": [
        Candle(0, 30, 70, 75, 25),
        Candle(1, 80, 45, 85, 40),
    ],  # Gap up open, close below mid
    "sashikomi": [
        Candle(0, 70, 30, 75, 25),
        Candle(1, 20, 45, 50, 15),
    ],  # Gap down open, close above mid
    "kenuki_zoko": [
        Candle(0, 60, 30, 65, 10),
        Candle(1, 35, 55, 60, 10),
    ],  # Matching Lows
    "kenuki_tenjo": [
        Candle(0, 40, 70, 90, 35),
        Candle(1, 65, 45, 90, 40),
    ],  # Matching Highs
    "daki_bull": [
        Candle(0, 55, 45, 58, 42),
        Candle(1, 40, 60, 65, 35),
    ],  # Same as Engulfing Bull
    "daki_bear": [
        Candle(0, 45, 55, 58, 42),
        Candle(1, 60, 40, 65, 35),
    ],  # Same as Engulfing Bear
    "kaeshi": [Candle(0, 30, 70, 75, 25), Candle(1, 70, 30, 75, 25)],
    "kubitsuri": [
        Candle(0, 40, 50, 55, 10)
    ],  # Hanging Man (Bearish tone usually, but shape is Hammer)
    "three_white_soldiers": [
        Candle(0, 20, 40, 45, 15),
        Candle(1, 40, 60, 65, 35),
        Candle(2, 60, 80, 85, 55),
    ],
    "three_black_crows": [
        Candle(0, 80, 60, 85, 55),
        Candle(1, 60, 40, 65, 35),
        Candle(2, 40, 20, 45, 15),
    ],
    "sanbagarasu": [
        Candle(0, 80, 60, 85, 55),
        Candle(1, 60, 40, 65, 35),
        Candle(2, 40, 20, 45, 15),
    ],  # Alias for crows
    "sanku_tatakikomi": [
        Candle(0, 80, 60, 85, 55),  # Bear
        Candle(1, 55, 45, 58, 42),  # Gap Down Bear
        Candle(2, 40, 30, 42, 28),  # Gap Down Bear
        Candle(3, 25, 15, 28, 12),  # Gap Down Bear
    ],
    "rising_three_methods": [
        Candle(0, 20, 80, 85, 15),  # Big Bull
        Candle(1, 75, 65, 78, 62),  # Small Bear
        Candle(2, 65, 55, 68, 52),  # Small Bear
        Candle(3, 55, 45, 58, 42),  # Small Bear
        Candle(4, 40, 90, 95, 35),  # Big Bull
    ],
    "falling_three_methods": [
        Candle(0, 80, 20, 85, 15),  # Big Bear
        Candle(1, 25, 35, 38, 22),  # Small Bull
        Candle(2, 35, 45, 48, 32),  # Small Bull
        Candle(3, 45, 55, 58, 42),  # Small Bull
        Candle(4, 60, 10, 65, 5),  # Big Bear
    ],
    "morning_star": [
        Candle(0, 80, 40, 85, 35),  # Long Bear
        Candle(1, 30, 25, 35, 20),  # Small/Doji Gap Down
        Candle(2, 45, 75, 80, 40),  # Long Bull Gap Up
    ],
    "evening_star": [
        Candle(0, 20, 60, 65, 15),  # Long Bull
        Candle(1, 75, 70, 80, 65),  # Small/Doji Gap Up
        Candle(2, 55, 25, 60, 20),  # Long Bear Gap Down
    ],
    "sutego": [
        Candle(0, 80, 50, 85, 45),
        Candle(1, 30, 30, 35, 25),  # Doji
        Candle(2, 50, 80, 85, 45),
    ],
    "sanpei_hasami": [
        Candle(0, 20, 50, 55, 15),  # Bull
        Candle(1, 55, 45, 58, 42),  # Bear (harami-ish)
        Candle(2, 45, 80, 85, 40),  # Bull
    ],
    "harami_sanbon": [
        Candle(0, 20, 80, 85, 15),  # Big Bull
        Candle(1, 60, 50, 65, 45),  # Small Bear inside
        Candle(2, 55, 90, 95, 50),  # Breakout Bull
    ],
    "gyaku_sanzon": [
        Candle(0, 60, 40, 65, 35),  # Left shoulder
        Candle(1, 40, 10, 45, 5),  # Head (lower)
        Candle(2, 60, 40, 65, 35),  # Right shoulder
    ],
    "sanzan": [
        Candle(0, 40, 60, 65, 35),  # Left shoulder
        Candle(1, 50, 80, 85, 45),  # Head (higher)
        Candle(2, 40, 60, 65, 35),  # Right shoulder
    ],
    "island_reversal": [
        Candle(0, 30, 50, 52, 28),
        Candle(1, 60, 65, 70, 55),  # Gap up Island
        Candle(2, 45, 25, 48, 22),  # Gap down
    ],
    "gap_up": [Candle(0, 30, 50, 52, 28), Candle(1, 60, 80, 82, 58)],
    "gap_down": [Candle(0, 70, 50, 52, 48), Candle(1, 40, 20, 22, 18)],
    "gap_fill": [
        Candle(0, 20, 40, 45, 15),
        Candle(1, 55, 35, 60, 30),
    ],  # Gap up then fill down
    "madokan_sanpou": [
        Candle(0, 20, 50, 55, 15),  # Bull
        Candle(1, 60, 60, 65, 55),  # Gap Up Doji/Pause
        Candle(2, 65, 90, 95, 60),  # Bull Continuation
    ],
    "range_break": [
        Candle(0, 40, 50, 52, 38),
        Candle(1, 42, 48, 50, 40),
        Candle(2, 45, 80, 85, 42),
    ],
    "volume_window": [
        Candle(0, 30, 50, 55, 25),
        Candle(1, 70, 90, 95, 65),  # Big Gap Up
    ],
    "sakata_gohou": [
        Candle(0, 50, 50, 60, 40),
        Candle(1, 60, 40, 65, 35),
        Candle(2, 30, 70, 75, 25),
        Candle(3, 80, 60, 85, 55),
        Candle(4, 50, 50, 55, 45),
    ],
    # 以下は、新規追加されたローソク足パターン
    "closing_marubozu_bull": [Candle(0, 30, 85, 85, 15)],  # 大引け陽線（上ヒゲなし）
    "opening_marubozu_bull": [Candle(0, 30, 75, 90, 30)],  # 寄付き陽線（下ヒゲなし）
    "karakasa_bull": [
        Candle(0, 70, 80, 80, 15)
    ],  # カラカサ・陽（長い下ヒゲ、上ヒゲなし）
    "tonkachi_bull": [
        Candle(0, 20, 30, 85, 20)
    ],  # トンカチ・陽（長い上ヒゲ、下ヒゲなし）
    "closing_marubozu_bear": [Candle(0, 75, 20, 90, 20)],  # 大引け陰線（下ヒゲなし）
    "opening_marubozu_bear": [Candle(0, 80, 25, 80, 10)],  # 寄付き陰線（上ヒゲなし）
    "karakasa_bear": [
        Candle(0, 80, 70, 80, 15)
    ],  # カラカサ・陰（長い下ヒゲ、上ヒゲなし）
    "tonkachi_bear": [
        Candle(0, 30, 20, 85, 20)
    ],  # トンカチ・陰（長い上ヒゲ、下ヒゲなし）
    "inyo_harami": [  # 陰陽はらみ（大陰線の実体内に小陽線）
        Candle(0, 80, 20, 85, 15),
        Candle(1, 40, 60, 65, 35),
    ],
}

# Ensure directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


# Generate
def run():
    print(f"Generating SVGs to {OUTPUT_DIR}...")
    count = 0
    for pid, candles in PATTERNS.items():
        svg = generate_svg(pid, candles)
        path = os.path.join(OUTPUT_DIR, f"{pid}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        count += 1
        print(f"Generated {pid}.svg")

    print(f"Complete. Generated {count} images.")


if __name__ == "__main__":
    run()
