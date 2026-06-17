from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import os
import sys


# Mock request
class MockRequest:
    pass


templates = Jinja2Templates(directory="templates")

# Mock data matching stock_service.get_fundamental_tab output
scores = {
    "安定性": {"stars": 4, "display": "****", "reason": "Test Reason"},
    "成長性": {"stars": 3, "display": "***", "reason": "Test Reason"},
}

context = {
    "request": MockRequest(),
    "scores": scores,
    "fundamentals": [{"label": "PER", "value": "15.0"}],
    "statuses": {"PER": {"label": "Normal", "color": "gray"}},
    "events": {"Test": "Date"},
    "timings": {"Test": "Date"},
    "risks": ["Risk 1"],
    "glossary": [],
    "analysis": {"error": "Mock analysis error"},  # Test error path first
}

try:
    rendered = templates.get_template("stocks/partials/_tab_fundamental.html").render(
        context
    )
    print("Render Success")
    # print(rendered[:100])
except Exception as e:
    print("Render Error:", e)
    import traceback

    traceback.print_exc()
