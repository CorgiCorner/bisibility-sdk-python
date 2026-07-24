from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .models import ProblemDetails

_SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
}


class BisibilityError(Exception):
    """Common base for every SDK-defined error."""


class BisibilityApiError(BisibilityError):
    body: str
    headers: httpx.Headers
    method: str
    problem: ProblemDetails | None
    status: int
    url: str

    def __init__(
        self,
        message: str,
        *,
        body: str,
        headers: httpx.Headers,
        method: str,
        problem: ProblemDetails | None,
        status: int,
        url: str,
    ) -> None:
        super().__init__(message)
        self.body = body
        self.headers = httpx.Headers(
            [
                (name, value)
                for name, value in headers.multi_items()
                if name.lower() not in _SENSITIVE_HEADERS
            ]
        )
        self.method = method
        self.problem = problem
        self.status = status
        self.url = url

    @property
    def is_rate_limit(self) -> bool:
        return self.status == 429

    @property
    def is_not_found(self) -> bool:
        return self.status == 404

    @property
    def retry_after_seconds(self) -> float | None:
        raw = self.headers.get("Retry-After")
        if raw is None:
            return None
        try:
            seconds = float(raw)
        except ValueError:
            try:
                parsed = parsedate_to_datetime(raw)
            except (TypeError, ValueError):
                return None
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            seconds = max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())
        if seconds < 0:
            return None
        return min(seconds, 60.0)


class BisibilityConfigurationError(BisibilityError):
    pass


class BisibilityNetworkError(BisibilityError):
    cause: BaseException
    method: str
    url: str

    def __init__(self, message: str, *, cause: BaseException, method: str, url: str) -> None:
        super().__init__(message)
        self.cause = cause
        self.method = method
        self.url = url


class BisibilityResponseError(BisibilityError):
    body: str
    cause: Any
    method: str
    status: int
    url: str

    def __init__(
        self,
        message: str,
        *,
        body: str,
        cause: Any,
        method: str,
        status: int,
        url: str,
    ) -> None:
        super().__init__(message)
        self.body = body
        self.cause = cause
        self.method = method
        self.status = status
        self.url = url
