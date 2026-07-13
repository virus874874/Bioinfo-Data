from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from . import __version__


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class GDCError(RuntimeError):
    pass


class GDCClient:
    def __init__(self, endpoint: str, timeout: float = 30, max_retries: int = 3, retry_backoff: float = 2.0):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def get(self, path: str, params: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        query = urllib.parse.urlencode(params or {})
        url = f"{self.endpoint}/{path.lstrip('/')}" + (f"?{query}" if query else "")
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            timestamp = utcnow()
            try:
                request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": f"gdc-scout/{__version__}"})
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    status = response.status
                    headers = dict(response.headers.items())
                body = json.loads(raw.decode("utf-8"))
                evidence = {
                    "endpoint": "/" + path.lstrip("/"), "url": url,
                    "request_timestamp": timestamp, "http_status": status,
                    "response_sha256": hashlib.sha256(raw).hexdigest(),
                    "parser_version": __version__, "response_headers": headers,
                    "response_size_bytes": len(raw), "query_parameters": params or {},
                }
                return body, evidence
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff * (2 ** attempt))
        raise GDCError(f"GET {url} failed after {self.max_retries + 1} attempts: {last_error}")

