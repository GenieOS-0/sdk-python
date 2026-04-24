"""
Optional PostHog telemetry for the MailGenius Python SDK.

Telemetry is enabled only when POSTHOG_PROJECT_TOKEN is set.  It tracks
SDK-usage signals (which operations are called, error rates by code,
webhook verification outcomes) to help the MailGenius team understand
how the SDK is used and where developers hit problems.

No PII is ever sent — the distinct_id is a SHA-256 hash of the API key
prefix, so it is workspace-scoped but cannot be reverse-engineered.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any

_client: Any = None
_initialized = False

# Used for calls (e.g. webhook verification) where no API key is available.
ANONYMOUS_DISTINCT_ID = "sdk-py-webhook-verifier"


def _distinct_id(api_key: str) -> str:
    """Return a non-reversible, workspace-scoped identifier."""
    return "sdk-py-" + hashlib.sha256(api_key.encode()).hexdigest()[:16]


def get_client() -> Any | None:
    """Return the (lazily-initialized) PostHog client, or None if disabled."""
    global _client, _initialized
    if _initialized:
        return _client

    _initialized = True
    token = os.environ.get("POSTHOG_PROJECT_TOKEN", "").strip()
    if not token:
        return None

    try:
        from posthog import Posthog  # type: ignore[import]

        kwargs: dict[str, Any] = {"enable_exception_autocapture": True}
        host = os.environ.get("POSTHOG_HOST", "").strip()
        if host:
            kwargs["host"] = host
        _client = Posthog(token, **kwargs)
    except Exception:
        # Never let PostHog errors surface to SDK consumers.
        _client = None

    return _client


def capture(
    api_key: str,
    event: str,
    properties: dict[str, Any] | None = None,
    *,
    distinct_id: str | None = None,
) -> None:
    """Fire a PostHog event; silently no-ops if telemetry is disabled.

    If ``distinct_id`` is provided it is used directly; otherwise it is
    derived from ``api_key`` via SHA-256 so no raw key is transmitted.
    """
    client = get_client()
    if client is None:
        return
    try:
        did = distinct_id if distinct_id is not None else _distinct_id(api_key)
        client.capture(
            distinct_id=did,
            event=event,
            properties=properties or {},
        )
    except Exception:
        pass


__all__ = ["capture", "get_client", "ANONYMOUS_DISTINCT_ID"]
