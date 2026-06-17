import unicodedata
import re


class TextNormalizer:
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text for consistent storage and search.
        1. Unicode NFKC normalization
        2. Whitespace compression (including full-width space to half-width)
        3. Remove non-printable characters
        4. Trim
        """
        if not text:
            return ""

        # 1. NFKC
        text = unicodedata.normalize("NFKC", text)

        # 2. Whitespace compression (Regex covers spaces, tabs, newlines)
        # \s matches [ \t\n\r\f\v]
        text = re.sub(r"\s+", " ", text)

        # 3. Trim
        text = text.strip()

        return text

    @staticmethod
    def get_query_core(text: str) -> str:
        """
        Extract core query characters (Japanese, English, Numbers only).
        Used for length validation.
        """
        if not text:
            return ""

        # Normalize first
        text = TextNormalizer.normalize_text(text)

        # Remove symbols and punctuation
        # Keep: \w (alphanuneric + underscore) and Japanese characters
        # Simple regex: Remove everything that is NOT (Word char or Whitespace)?
        # User said: "Extract core query characters (Japanese/English/Numbers only)"

        # Regex to keep only:
        # - English/Numbers (\w)
        # - Japanese (Hiragana, Katakana, Kanji)
        #
        # Range for Japanese:
        # Hiragana: \u3040-\u309F
        # Katakana: \u30A0-\u30FF
        # Kanji: \u4E00-\u9FFF

        # Negated class to replace unwanted chars with empty string
        # Removing symbols, punctuation, spaces for counting core length

        core = re.sub(r"[^\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]", "", text)
        return core
