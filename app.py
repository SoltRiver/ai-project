"""
Legacy Streamlit版は廃止しました。
FastAPI + htmx 版を uvicorn で起動してください:

    uvicorn fastapi_app:app --reload --port 8000
"""

import sys


def main() -> None:
    print(
        "このプロジェクトは FastAPI + htmx 版に移行しました。"
        "実行する場合は `uvicorn fastapi_app:app --reload` を使用してください。"
    )


if __name__ == "__main__":
    main()
    sys.exit(0)
