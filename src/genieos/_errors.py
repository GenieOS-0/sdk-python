"""
Typed error hierarchy for the GenieOS SDK — mirrors the catalogue
in ``packages/sdk-node/src/errors.ts`` so the same docs cover both
SDKs.

The base class is :class:`GenieOSError`. Every subclass corresponds
to a documented API error code so callers can
``except GenieOSRateLimitError`` instead of matching on string codes.
"""
from __future__ import annotations

from typing import Any, Optional


class GenieOSError(Exception):
    """Base class for every error raised by the GenieOS SDK."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "genieos_error",
        status: Optional[int] = None,
        request_id: Optional[str] = None,
        body: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.request_id = request_id
        self.body = body

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        parts = [f"{self.__class__.__name__}({self.args[0]!r}", f"code={self.code!r}"]
        if self.status is not None:
            parts.append(f"status={self.status}")
        if self.request_id is not None:
            parts.append(f"request_id={self.request_id!r}")
        return ", ".join(parts) + ")"


class GenieOSAuthError(GenieOSError):
    """401/403 — bearer token missing, invalid, revoked, or out-of-scope."""


class GenieOSNotFoundError(GenieOSError):
    """404 — addressed resource does not exist (or is in another workspace)."""


class GenieOSValidationError(GenieOSError):
    """422 — request body / query failed schema validation."""


class GenieOSConflictError(GenieOSError):
    """409 — idempotency conflict, optimistic-concurrency mismatch, etc."""


class GenieOSRateLimitError(GenieOSError):
    """429 — per-key or per-workspace rate limit exceeded.

    ``retry_after_seconds`` mirrors the ``Retry-After`` header on the
    response and is the recommended back-off duration before the next
    attempt.
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: float,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after_seconds = retry_after_seconds


class GenieOSServerError(GenieOSError):
    """5xx — transient server-side fault. Retried automatically by the SDK."""


class GenieOSNetworkError(GenieOSError):
    """Local network / DNS / TLS failure."""


def from_response(
    *,
    status: int,
    body: Any,
    request_id: Optional[str],
    retry_after_seconds: Optional[float] = None,
) -> GenieOSError:
    """Convert an HTTP error response into the appropriate typed error."""
    err_obj = (body or {}).get("error", {}) if isinstance(body, dict) else {}
    code = err_obj.get("code") or f"http_{status}"
    message = err_obj.get("message") or f"HTTP {status}"
    common = {"code": code, "status": status, "request_id": request_id, "body": body}
    if status in (401, 403):
        return GenieOSAuthError(message, **common)
    if status == 404:
        return GenieOSNotFoundError(message, **common)
    if status == 409:
        return GenieOSConflictError(message, **common)
    if status == 422:
        return GenieOSValidationError(message, **common)
    if status == 429:
        # `or` would coerce a legitimate 0 ("retry now") into 1s, so check None.
        ra = retry_after_seconds if retry_after_seconds is not None else 1.0
        return GenieOSRateLimitError(message, retry_after_seconds=ra, **common)
    if status >= 500:
        return GenieOSServerError(message, **common)
    return GenieOSError(message, **common)


__all__ = [
    "GenieOSError",
    "GenieOSAuthError",
    "GenieOSNotFoundError",
    "GenieOSValidationError",
    "GenieOSConflictError",
    "GenieOSRateLimitError",
    "GenieOSServerError",
    "GenieOSNetworkError",
    "from_response",
]
