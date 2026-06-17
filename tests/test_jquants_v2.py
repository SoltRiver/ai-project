import sys
import os

sys.path.append(os.getcwd())

import pytest
from unittest.mock import patch, MagicMock
from services.jquants_client import JQuantsClient


@pytest.fixture
def client():
    # Mock environment variable if needed, or rely on existing
    return JQuantsClient()


def test_get_listed_issues_success(client):
    """Verify master data retrieval with standard response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"Code": "72030", "CoName": "Toyota", "MktNm": "Prime"}]
    }

    with patch("requests.get", return_value=mock_response) as mock_get:
        result = client.get_listed_issues()
        assert len(result) == 1
        assert result[0]["Code"] == "72030"
        # Check if URL was correct (v2)
        args, kwargs = mock_get.call_args
        assert "/v2/equities/master" in args[0]
        assert "x-api-key" in kwargs["headers"]


def test_get_listed_issues_fallback(client):
    """Verify fallback logic when primary date fails."""
    # First call raises Exception or returns error
    # Second call succeeds

    # We need to mock requests.get to return different values for sequential calls
    # 1. 400 Error (Today) -> raises Exception in client.get or handled
    # 2. Success (13 weeks ago or next retry)

    mock_fail = MagicMock()
    mock_fail.status_code = 400
    mock_fail.raise_for_status.side_effect = Exception("400 Bad Request")

    mock_success = MagicMock()
    mock_success.status_code = 200
    mock_success.json.return_value = {"data": [{"Code": "99840"}]}

    with patch("services.jquants_client.requests.get") as mock_get:
        # side_effect can be an iterable
        # First attempt failed, sleep, Second attempt (13 weeks ago) succeeds
        mock_get.side_effect = [mock_fail, mock_success]

        # We also need to patch time.sleep to speed up test
        with patch("time.sleep"):
            result = client.get_listed_issues()

        assert len(result) == 1
        assert result[0]["Code"] == "99840"
        assert mock_get.call_count == 2  # 1 fail + 1 success


def test_get_daily_quotes_mapping(client):
    """Verify O->Open mapping and data wrapper."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "Date": "20240101",
                "Code": "72030",
                "O": 100,
                "H": 110,
                "L": 90,
                "C": 105,
                "Vo": 1000,
            }
        ]
    }

    with patch("requests.get", return_value=mock_response):
        data = client.get_daily_quotes("7203")

        # Check if 'daily_quotes' key exists (backward compatibility)
        assert "daily_quotes" in data
        quotes = data["daily_quotes"]
        assert len(quotes) == 1

        # Check mapping
        q = quotes[0]
        assert "Open" in q
        assert q["Open"] == 100
        assert "High" in q
        assert q["High"] == 110
        assert "Volume" in q
        assert (
            "O" not in q
        )  # Should be removed/mapped? Logic said "new_item[new_k] = new_item.pop(old_k)"
