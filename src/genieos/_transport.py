"""
Low-level transport for the GenieOS Python SDK.

Mirrors the Node SDK's transport contract:

  - Bearer auth on every request.
  - Auto-generated ``Idempotency-Key`` for mutating requests when one
    isn't supplied. Format: ``gos-py-<base36(time_ms)>-<8 hex>``.
  - Retries for network errors and ``429``/``5xx`` responses, with
    exponential back-off and jitter, capped by ``max_retries``. Honors
    ``Retry-After`` (in seconds) when present.
  - Errors are converted into the typed :mod:`._errors` hierarchy.
  - Sync (``Transport``) and async (``AsyncTransport``) variants share
    the URL / header / retry helpers via :class:`_TransportBase`.

This module is intentionally httpx-thin so the SDK is portable to
environments that already pin a specific httpx version (most apps do).
"""
from __future__ import annotations

import json as _json
import os
import random
import secrets
import time
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from . import _errors, _telemetry

DEFAULT_BASE_URL = "https://api.genieos.pro"
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
USER_AGENT = "genieos-python/0.1.0"

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _gen_idempotency_key() -> str:
    """Format mirrors the Node SDK so logs grep cleanly across both."""
    millis = int(time.time() * 1000)
    base36 = ""
    n = millis
    if n == 0:
        base36 = "0"
    while n > 0:
        base36 = "0123456789abcdefghijklmnopqrstuvwxyz"[n % 36] + base36
        n //= 36
    rand = secrets.token_hex(4)
    return f"gos-py-{base36}-{rand}"


def _is_retryable_status(status: int) -> bool:
    return status == 429 or 500 <= status < 600


def _retry_after_seconds(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


@dataclass
class _RequestPlan:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes | None


class _TransportBase:
    """Shared URL building, header assembly, retry math."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        max_retries: int = 3,
        retry_base_ms: int = 250,
        retry_cap_ms: int = 8_000,
        user_agent: str = USER_AGENT,
    ) -> None:
        if not api_key:
            raise _errors.GenieOSAuthError(
                "GenieOS API key is required.", code="missing_api_key", status=None
            )
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._retry_base_ms = retry_base_ms
        self._retry_cap_ms = retry_cap_ms
        self._user_agent = user_agent

    # -------------------- request planning -------------------- #
    def _plan(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> _RequestPlan:
        method = method.upper()
        url = f"{self._base_url}{path}"
        if params:
            cleaned = {k: v for k, v in params.items() if v is not None}
            if cleaned:
                url = str(httpx.URL(url, params=cleaned))
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }
        if extra_headers:
            headers.update(extra_headers)
        body: bytes | None = None
        if method in _MUTATING_METHODS:
            headers.setdefault(
                "Idempotency-Key", idempotency_key or _gen_idempotency_key()
            )
            if json is not None:
                headers["Content-Type"] = "application/json"
                body = _json.dumps(json, separators=(",", ":")).encode("utf-8")
        return _RequestPlan(method=method, url=url, headers=headers, body=body)

    def _backoff_ms(self, attempt: int, retry_after_seconds: float | None) -> int:
        if retry_after_seconds is not None:
            return int(retry_after_seconds * 1000)
        exp = self._retry_base_ms * (2**attempt)
        capped = min(exp, self._retry_cap_ms)
        # Full jitter — recommended by AWS / Stripe for transient rate-limits.
        return random.randint(0, capped)

    def _parse(self, response: httpx.Response) -> Any:
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except _json.JSONDecodeError:
            return response.text

    def _raise_for(self, response: httpx.Response, body: Any) -> None:
        if 200 <= response.status_code < 300:
            return
        err_body = body if isinstance(body, dict) else {"raw": body}
        err_code = (err_body.get("error") or {}).get("code") or f"http_{response.status_code}"
        _telemetry.capture(self._api_key, "api_error", {
            "status_code": response.status_code,
            "error_code": err_code,
        })
        raise _errors.from_response(
            status=response.status_code,
            body=err_body,
            request_id=response.headers.get("x-request-id"),
            retry_after_seconds=_retry_after_seconds(response),
        )


# --------------------------------------------------------------------------- #
# Sync transport
# --------------------------------------------------------------------------- #


class Transport(_TransportBase):
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        max_retries: int = 3,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        client: httpx.Client | None = None,
        user_agent: str = USER_AGENT,
    ) -> None:
        super().__init__(
            api_key, base_url=base_url, max_retries=max_retries, user_agent=user_agent
        )
        self._owned_client = client is None
        self._client = client or httpx.Client(timeout=timeout)
        self._sleep: Callable[[float], None] = time.sleep

    def close(self) -> None:
        if self._owned_client:
            self._client.close()

    def __enter__(self) -> Transport:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> Any:
        plan = self._plan(
            method,
            path,
            json=json,
            params=params,
            idempotency_key=idempotency_key,
            extra_headers=extra_headers,
        )
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.request(
                    plan.method,
                    plan.url,
                    headers=plan.headers,
                    content=plan.body,
                )
            except httpx.HTTPError as e:
                last_exc = e
                if attempt >= self._max_retries:
                    raise _errors.GenieOSNetworkError(
                        f"Network error contacting GenieOS: {e}",
                        code="network_error",
                    ) from e
                self._sleep(self._backoff_ms(attempt, None) / 1000)
                continue
            body = self._parse(response)
            if 200 <= response.status_code < 300:
                return body
            if _is_retryable_status(response.status_code) and attempt < self._max_retries:
                self._sleep(
                    self._backoff_ms(attempt, _retry_after_seconds(response)) / 1000
                )
                continue
            self._raise_for(response, body)
        # unreachable but keeps mypy happy
        raise _errors.GenieOSNetworkError(
            f"Unreachable: retries exhausted with no response: {last_exc}",
            code="network_error",
        )


# --------------------------------------------------------------------------- #
# Async transport
# --------------------------------------------------------------------------- #


class AsyncTransport(_TransportBase):
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        max_retries: int = 3,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        client: httpx.AsyncClient | None = None,
        user_agent: str = USER_AGENT,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        super().__init__(
            api_key, base_url=base_url, max_retries=max_retries, user_agent=user_agent
        )
        self._owned_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)
        # Lazy-import asyncio.sleep so the sync path doesn't trip a missing
        # loop in Python <3.10 environments.
        if sleep is None:
            import asyncio

            sleep = asyncio.sleep
        self._sleep = sleep

    async def aclose(self) -> None:
        if self._owned_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncTransport:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> Any:
        plan = self._plan(
            method,
            path,
            json=json,
            params=params,
            idempotency_key=idempotency_key,
            extra_headers=extra_headers,
        )
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.request(
                    plan.method,
                    plan.url,
                    headers=plan.headers,
                    content=plan.body,
                )
            except httpx.HTTPError as e:
                last_exc = e
                if attempt >= self._max_retries:
                    raise _errors.GenieOSNetworkError(
                        f"Network error contacting GenieOS: {e}",
                        code="network_error",
                    ) from e
                await self._sleep(self._backoff_ms(attempt, None) / 1000)
                continue
            body = self._parse(response)
            if 200 <= response.status_code < 300:
                return body
            if _is_retryable_status(response.status_code) and attempt < self._max_retries:
                await self._sleep(
                    self._backoff_ms(attempt, _retry_after_seconds(response)) / 1000
                )
                continue
            self._raise_for(response, body)
        raise _errors.GenieOSNetworkError(
            f"Unreachable: retries exhausted with no response: {last_exc}",
            code="network_error",
        )


def resolve_api_key(explicit: str | None) -> str:
    """Resolve the bearer token from the constructor arg or env var."""
    return (explicit or os.environ.get("GENIEOS_API_KEY", "")).strip()


def resolve_base_url(explicit: str | None) -> str:
    return (explicit or os.environ.get("GENIEOS_API_URL", "")).strip() or DEFAULT_BASE_URL


__all__ = [
    "Transport",
    "AsyncTransport",
    "DEFAULT_BASE_URL",
    "USER_AGENT",
    "resolve_api_key",
    "resolve_base_url",
]


def _unused() -> tuple[str, ...]:  # pragma: no cover
    return (DEFAULT_BASE_URL, USER_AGENT)
