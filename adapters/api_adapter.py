from __future__ import annotations

"""
Hybrid AI Agent – APIAdapter.

Lightweight HTTP client adapter for REST-style APIs.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

import json
import urllib.request
import urllib.error


@dataclass
class ApiResult:
    success: bool
    status_code: int
    body: Optional[Dict[str, Any]]
    raw_text: str
    error: Optional[str] = None


class ApiAdapter:
    """
    Very small wrapper around urllib to avoid extra dependencies.
    """

    def request(
        self,
        method: str,
        url: str,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> ApiResult:
        data_bytes: Optional[bytes] = None
        req_headers = dict(headers or {})
        if json_body is not None:
            data_bytes = json.dumps(json_body).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json")

        req = urllib.request.Request(url=url, data=data_bytes, headers=req_headers, method=method.upper())

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                status = resp.getcode()
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return ApiResult(
                success=False,
                status_code=exc.code,
                body=_safe_json(text),
                raw_text=text,
                error=str(exc),
            )
        except Exception as exc:
            return ApiResult(
                success=False,
                status_code=0,
                body=None,
                raw_text="",
                error=str(exc),
            )

        return ApiResult(
            success=200 <= status < 300,
            status_code=status,
            body=_safe_json(text),
            raw_text=text,
        )


def _safe_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        return None

