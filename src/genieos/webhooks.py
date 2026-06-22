"""
Webhook signature verification for MailGenius outbound webhooks.

The signature header (``X-GenieOS-Signature``) is Stripe-style:

    t=<unix-seconds>,v1=<hex(hmac_sha256(secret, "<t>.<raw body>"))>

This module provides :func:`verify_webhook` for inbound delivery and
:func:`sign_webhook` for sending the same envelope back during local
testing. Both perform constant-time signature comparison and reject
timestamps outside the allowed window (default ±5 minutes) to defeat
replay attacks.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import _telemetry

DEFAULT_TOLERANCE_SECONDS = 300


class WebhookSignatureError(Exception):
    """Raised when a webhook signature fails verification."""


@dataclass(frozen=True)
class VerifiedDelivery:
    """The successfully verified webhook envelope.

    ``raw_body`` is preserved so callers can re-sign / re-emit the
    payload (useful in fan-out architectures).
    """

    id: str
    type: str
    workspace_id: str
    created_at: str
    data: dict[str, Any]
    raw_body: str
    timestamp: int


def _coerce_body(body: str | bytes | bytearray) -> str:
    if isinstance(body, (bytes, bytearray)):
        return bytes(body).decode("utf-8")
    return body


def _coerce_signature(headers: Mapping[str, Any], header_name: str) -> str:
    val = headers.get(header_name) or headers.get(header_name.lower())
    if val is None:
        # case-insensitive fallback
        for k, v in headers.items():
            if k.lower() == header_name.lower():
                val = v
                break
    if val is None:
        raise WebhookSignatureError(f"Missing {header_name} header")
    if isinstance(val, list):
        if not val:
            raise WebhookSignatureError(f"Empty {header_name} header")
        val = val[0]
    return str(val).strip()


def _parse_signature_header(header_value: str) -> tuple[int, list[str]]:
    timestamp: int | None = None
    sigs: list[str] = []
    for part in header_value.split(","):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        if k == "t":
            try:
                timestamp = int(v)
            except ValueError as e:
                raise WebhookSignatureError(f"Invalid timestamp: {v}") from e
        elif k == "v1":
            sigs.append(v)
    if timestamp is None or not sigs:
        raise WebhookSignatureError("Signature header missing `t` or `v1` component")
    return timestamp, sigs


def _hmac_hex(secret: str, payload: str) -> str:
    return hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def verify_webhook(
    raw_body: str | bytes | bytearray,
    headers: Mapping[str, Any],
    secret: str,
    *,
    tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS,
    header_name: str = "X-GenieOS-Signature",
    now: float | None = None,
) -> VerifiedDelivery:
    """Verify and parse a MailGenius webhook delivery.

    Raises :class:`WebhookSignatureError` if anything is wrong; returns
    a :class:`VerifiedDelivery` on success. The default tolerance of
    ±5 minutes matches the upstream signer in
    ``functions/src/lib/webhookDelivery.ts``.
    """
    try:
        body = _coerce_body(raw_body)
        sig_header = _coerce_signature(headers, header_name)
        timestamp, sigs = _parse_signature_header(sig_header)

        now_ts = int(now if now is not None else time.time())
        if abs(now_ts - timestamp) > tolerance_seconds:
            raise WebhookSignatureError(
                f"Timestamp {timestamp} outside tolerance window of {tolerance_seconds}s"
            )

        expected = _hmac_hex(secret, f"{timestamp}.{body}")
        if not any(hmac.compare_digest(expected, s) for s in sigs):
            raise WebhookSignatureError("Signature mismatch")

        try:
            envelope = json.loads(body)
        except json.JSONDecodeError as e:
            raise WebhookSignatureError(f"Webhook body is not JSON: {e}") from e
        if not isinstance(envelope, dict):
            raise WebhookSignatureError("Webhook body must be a JSON object")

        required = {"id", "type", "workspaceId", "createdAt", "data"}
        missing = required - envelope.keys()
        if missing:
            raise WebhookSignatureError(
                f"Webhook envelope missing required fields: {sorted(missing)}"
            )

        result = VerifiedDelivery(
            id=str(envelope["id"]),
            type=str(envelope["type"]),
            workspace_id=str(envelope["workspaceId"]),
            created_at=str(envelope["createdAt"]),
            data=dict(envelope["data"]),
            raw_body=body,
            timestamp=timestamp,
        )
        _telemetry.capture(
            "",
            "webhook_verified",
            {"event_type": result.type},
            distinct_id=_telemetry.ANONYMOUS_DISTINCT_ID,
        )
        return result

    except WebhookSignatureError as exc:
        _telemetry.capture(
            "",
            "webhook_signature_error",
            {"reason": str(exc)},
            distinct_id=_telemetry.ANONYMOUS_DISTINCT_ID,
        )
        raise


def sign_webhook(
    raw_body: str,
    secret: str,
    *,
    timestamp: int | None = None,
) -> str:
    """Produce the signature header value for ``raw_body``.

    Useful for local testing — re-emit a captured webhook without
    needing to spin up the platform's outbound queue.
    """
    ts = timestamp if timestamp is not None else int(time.time())
    return f"t={ts},v1={_hmac_hex(secret, f'{ts}.{raw_body}')}"


__all__ = [
    "WebhookSignatureError",
    "VerifiedDelivery",
    "verify_webhook",
    "sign_webhook",
]
