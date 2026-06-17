import os
import logging
import asyncio
import random
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class EdinetAPIError(Exception):
    """Base exception for EDINET API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class EdinetClient:
    BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=30.0))

    async def close(self):
        await self.client.aclose()

    async def get_documents(self, date: str, type_code: int = 2) -> Dict[str, Any]:
        """
        Fetch documents.json from EDINET API v2.

        Args:
            date (str): YYYY-MM-DD
            type_code (int): 1 (XBRL) or 2 (Metadata)

        Returns:
            Dict[str, Any]: Parsed JSON response (whole object)

        Raises:
            EdinetAPIError: On failure after retries
        """
        api_key = os.environ.get("EDINET_API_KEY")
        if not api_key:
            logger.error("EDINET_API_KEY is not set.")
            raise EdinetAPIError("EDINET_API_KEY is missing.", status_code=503)

        url = f"{self.BASE_URL}/documents.json"
        params = {"date": date, "type": type_code, "Subscription-Key": api_key}

        # Mask API Key for logging
        log_params = params.copy()
        log_params["Subscription-Key"] = "***"
        logger.debug(f"Requesting EDINET API: {url} with params {log_params}")

        retries = 3
        backoff_base = 1.0  # seconds

        for attempt in range(retries + 1):
            try:
                response = await self.client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    count = data.get("resultset", {}).get("count", 0)
                    logger.info(f"EDINET API Success. Count: {count}")
                    return data

                # Check for retryable errors
                if response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < retries:
                        sleep_time = (backoff_base * (2**attempt)) + random.uniform(
                            0, 0.5
                        )
                        logger.warning(
                            f"EDINET API Error {response.status_code}. Retrying in {sleep_time:.2f}s... (Attempt {attempt + 1}/{retries})"
                        )
                        await asyncio.sleep(sleep_time)
                        continue

                # If we reach here, it's a non-retryable error or retries exhausted
                logger.error(
                    f"EDINET API Failed (Non-retryable). Status: {response.status_code}, Body: {response.text[:200]}"
                )
                raise EdinetAPIError(
                    f"EDINET API responded with {response.status_code}",
                    status_code=response.status_code,
                )

            except httpx.RequestError as e:
                if attempt < retries:
                    sleep_time = (backoff_base * (2**attempt)) + random.uniform(0, 0.5)
                    logger.warning(
                        f"EDINET Connection Error: {e}. Retrying in {sleep_time:.2f}s..."
                    )
                    await asyncio.sleep(sleep_time)
                    continue
                logger.error(f"EDINET Connection Failed: {e}")
                raise EdinetAPIError(f"Connection failed: {str(e)}", status_code=502)

        # If loop finishes without return (should satisfy retry limit logic above but for safety)
        raise EdinetAPIError("Max retries exceeded.", status_code=502)

    async def get_document_zip(self, doc_id: str) -> bytes:
        """
        Fetch document ZIP from EDINET API v2.

        Args:
            doc_id (str): Document ID

        Returns:
            bytes: ZIP file content

        Raises:
            EdinetAPIError: On failure
        """
        api_key = os.environ.get("EDINET_API_KEY")
        if not api_key:
            logger.error("EDINET_API_KEY is not set.")
            raise EdinetAPIError("EDINET_API_KEY is missing.", status_code=503)

        url = f"{self.BASE_URL}/documents/{doc_id}"
        params = {"type": 1, "Subscription-Key": api_key}

        log_params = params.copy()
        log_params["Subscription-Key"] = "***"
        logger.debug(f"Requesting EDINET ZIP: {url} with params {log_params}")

        retries = 3
        backoff_base = 1.0

        for attempt in range(retries + 1):
            try:
                response = await self.client.get(url, params=params)

                if response.status_code == 200:
                    logger.info(
                        f"EDINET ZIP Download Success. Size: {len(response.content)} bytes"
                    )
                    return response.content

                # Check for retryable errors
                if response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < retries:
                        sleep_time = (backoff_base * (2**attempt)) + random.uniform(
                            0, 0.5
                        )
                        logger.warning(
                            f"EDINET ZIP Error {response.status_code}. Retrying in {sleep_time:.2f}s... (Attempt {attempt + 1}/{retries})"
                        )
                        await asyncio.sleep(sleep_time)
                        continue

                logger.error(
                    f"EDINET ZIP Failed. Status: {response.status_code}, Body: {response.text[:200]}"
                )
                raise EdinetAPIError(
                    f"EDINET API responded with {response.status_code}",
                    status_code=response.status_code,
                )

            except httpx.RequestError as e:
                if attempt < retries:
                    sleep_time = (backoff_base * (2**attempt)) + random.uniform(0, 0.5)
                    logger.warning(
                        f"EDINET Connection Error: {e}. Retrying in {sleep_time:.2f}s..."
                    )
                    await asyncio.sleep(sleep_time)
                    continue
                logger.error(f"EDINET Connection Failed: {e}")
                raise EdinetAPIError(f"Connection failed: {str(e)}", status_code=502)

        raise EdinetAPIError("Max retries exceeded.", status_code=502)
