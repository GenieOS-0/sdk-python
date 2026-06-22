"""
Webhook signature verification tests — mirror the Node SDK's
``test/webhooks.test.ts`` so behaviour stays in lock-step across
SDKs.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from genieos.webhooks import (
    VerifiedDelivery,
    WebhookSignatureError,
    sign_webhook,
    verify_webhook,
)


SECRET = "whsec_unit_test_only_value"


def _envelope() -> str:
    return json.dumps(
        {
            "id": "evt_1",
            "type": "send.delivered",
            "createdAt": "2026-04-20T22:30:00.000Z",
            "workspaceId": "ws_unit_test",
            "data": {"sendId": "snd_1", "to": "aki@example.com"},
        }
    )


def test_accepts_freshly_signed_envelope() -> None:
    body = _envelope()
    header = sign_webhook(body, SECRET)
    out = verify_webhook(body, {"X-GenieOS-Signature": header}, SECRET)
    assert isinstance(out, VerifiedDelivery)
    assert out.id == "evt_1"
    assert out.type == "send.delivered"
    assert out.workspace_id == "ws_unit_test"
    assert out.data["sendId"] == "snd_1"


def test_rejects_tampered_body() -> None:
    body = _envelope()
    header = sign_webhook(body, SECRET)
    tampered = body.replace("evt_1", "evt_2")
    with pytest.raises(WebhookSignatureError, match="mismatch"):
        verify_webhook(tampered, {"X-GenieOS-Signature": header}, SECRET)


def test_rejects_out_of_window_timestamp() -> None:
    body = _envelope()
    header = sign_webhook(body, SECRET, timestamp=int(time.time()) - 10_000)
    with pytest.raises(WebhookSignatureError, match="tolerance"):
        verify_webhook(body, {"X-GenieOS-Signature": header}, SECRET)


def test_rejects_missing_header() -> None:
    body = _envelope()
    with pytest.raises(WebhookSignatureError, match="Missing"):
        verify_webhook(body, {}, SECRET)


def test_handles_case_insensitive_headers_and_lists() -> None:
    body = _envelope()
    header = sign_webhook(body, SECRET)
    out = verify_webhook(body, {"x-genieos-signature": [header]}, SECRET)
    assert out.id == "evt_1"


def test_accepts_byte_body() -> None:
    body = _envelope()
    header = sign_webhook(body, SECRET)
    out = verify_webhook(body.encode("utf-8"), {"X-GenieOS-Signature": header}, SECRET)
    assert out.id == "evt_1"


def test_signature_format_matches_upstream() -> None:
    body = _envelope()
    ts = 1_700_000_000
    header = sign_webhook(body, SECRET, timestamp=ts)
    expected_v1 = hmac.new(
        SECRET.encode("utf-8"), f"{ts}.{body}".encode("utf-8"), hashlib.sha256
    ).hexdigest()
    assert header == f"t={ts},v1={expected_v1}"
