"""
Transport-layer tests using ``respx`` to mock httpx.

Mirrors ``packages/sdk-node/test/transport.test.ts``: bearer auth,
auto-generated idempotency keys, retry-on-429 with eventual success,
typed error mapping.
"""
from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from mailgenius import (
    AsyncMailGenius,
    MailGenius,
    MailGeniusAuthError,
    MailGeniusRateLimitError,
)


@respx.mock
def test_sends_bearer_auth_and_idempotency_key() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"eventId": "evt_1", "enrollments": []})

    respx.post("https://api.example.com/v1/events").mock(side_effect=handler)

    with MailGenius(api_key="mg_test_unit", base_url="https://api.example.com") as mg:
        out = mg.events.emit("user.signed_up", email="aki@example.com")

    assert out.event_id == "evt_1"
    assert captured[0].headers["authorization"] == "Bearer mg_test_unit"
    assert captured[0].headers["idempotency-key"].startswith("mg-py-")
    body = json.loads(captured[0].content)
    assert body["name"] == "user.signed_up"


@respx.mock
def test_429_then_success_retries() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                429,
                headers={"retry-after": "0"},
                json={"error": {"code": "rate_limited", "message": "slow down"}},
            )
        return httpx.Response(200, json={"eventId": "evt_2", "enrollments": []})

    respx.post("https://api.example.com/v1/events").mock(side_effect=handler)

    with MailGenius(
        api_key="mg_test_unit", base_url="https://api.example.com", max_retries=3
    ) as mg:
        out = mg.events.emit("welcome.shown", email="aki@example.com")

    assert out.event_id == "evt_2"
    assert calls["n"] == 2


@respx.mock
def test_401_raises_auth_error() -> None:
    respx.get("https://api.example.com/v1/workspace").mock(
        return_value=httpx.Response(
            401,
            json={"error": {"code": "invalid_api_key", "message": "bad token"}},
        )
    )
    with MailGenius(api_key="mg_test_bad", base_url="https://api.example.com") as mg:
        with pytest.raises(MailGeniusAuthError) as ctx:
            mg.workspace.get()
    assert ctx.value.code == "invalid_api_key"
    assert ctx.value.status == 401


@respx.mock
def test_exhausted_429s_raise_rate_limit_error() -> None:
    respx.post("https://api.example.com/v1/events").mock(
        return_value=httpx.Response(
            429,
            headers={"retry-after": "0"},
            json={"error": {"code": "rate_limited", "message": "calm down"}},
        )
    )
    with MailGenius(
        api_key="mg_test_unit",
        base_url="https://api.example.com",
        max_retries=2,
    ) as mg:
        with pytest.raises(MailGeniusRateLimitError) as ctx:
            mg.events.emit("never.lands")
    assert ctx.value.retry_after_seconds == 0


@respx.mock
async def test_async_client_round_trip() -> None:
    respx.get("https://api.example.com/v1/workspace").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "ws_async",
                "name": "Async test",
                "plan": "pro",
                "scopes": ["templates:read"],
                "rateLimitPerMinute": 600,
            },
        )
    )
    async with AsyncMailGenius(
        api_key="mg_test_unit", base_url="https://api.example.com"
    ) as mg:
        ws = await mg.workspace.get()
    assert ws.id == "ws_async"
    assert ws.plan == "pro"
    assert ws.rate_limit_per_minute == 600


@respx.mock
def test_keeps_explicit_idempotency_key() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"id": "snd_1", "status": "queued"})

    respx.post("https://api.example.com/v1/templates/welcome/send").mock(
        side_effect=handler
    )

    with MailGenius(api_key="mg_test_unit", base_url="https://api.example.com") as mg:
        mg.templates.send(
            "welcome",
            to="aki@example.com",
            variables={"firstName": "Aki"},
            idempotency_key="caller-supplied-key",
        )

    assert captured[0].headers["idempotency-key"] == "caller-supplied-key"


def test_constructor_resolves_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAILGENIUS_API_KEY", "mg_env_value")
    with MailGenius() as mg:
        # Access protected to verify resolution
        assert mg._transport._api_key == "mg_env_value"  # type: ignore[attr-defined]


def test_constructor_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAILGENIUS_API_KEY", raising=False)
    with pytest.raises(MailGeniusAuthError):
        MailGenius()


def test_idempotency_key_format() -> None:
    from mailgenius._transport import _gen_idempotency_key

    k1 = _gen_idempotency_key()
    k2 = _gen_idempotency_key()
    assert k1.startswith("mg-py-")
    assert k1 != k2
    parts = k1.split("-")
    assert len(parts) == 4  # mg, py, base36-millis, 8 hex
    assert len(parts[3]) == 8


def _silence_unused_import() -> Any:
    """Ensure the typing import is exercised in CI (mypy --strict)."""
    return Any
