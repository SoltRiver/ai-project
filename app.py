"""
FastAPI + htmx アプリ起動補助スクリプト。

開発サーバー例:
    uvicorn fastapi_app:app --reload --port 8000
"""

import sys


def main() -> None:
    print(
        "FastAPI + htmx アプリを起動するには `uvicorn fastapi_app:app --reload --port 8000` を実行してください。"
    )


if __name__ == "__main__":
    main()
    sys.exit(0)
