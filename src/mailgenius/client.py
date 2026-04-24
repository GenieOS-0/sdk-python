"""
Synchronous :class:`MailGenius` client.

Resource modules (``templates``, ``sequences``, ``events``,
``webhooks``, ``keys``, ``audit``, ``workspace``) hang off the client
instance and share the underlying :class:`._transport.Transport`. The
parallel async client lives in ``mailgenius.async_client`` and exposes
an identical surface.
"""
from __future__ import annotations

import builtins
from collections.abc import Iterator, Mapping
from typing import Any

from . import _telemetry
from . import _types as t
from ._transport import (
    DEFAULT_BASE_URL,
    Transport,
    resolve_api_key,
    resolve_base_url,
)


class _Resource:
    def __init__(self, transport: Transport) -> None:
        self._t = transport


# --------------------------------------------------------------------------- #
# Workspace + keys
# --------------------------------------------------------------------------- #


class _Workspace(_Resource):
    def get(self) -> t.Workspace:
        return t.Workspace.model_validate(self._t.request("GET", "/v1/workspace"))


class _Keys(_Resource):
    def list(self) -> builtins.list[t.ApiKeySummary]:
        body = self._t.request("GET", "/v1/keys")
        items = body if isinstance(body, list) else body.get("data", [])
        return [t.ApiKeySummary.model_validate(x) for x in items]

    def get(self, key_id: str) -> t.ApiKeySummary:
        return t.ApiKeySummary.model_validate(self._t.request("GET", f"/v1/keys/{key_id}"))


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #


class _Templates(_Resource):
    def list(self) -> builtins.list[t.TemplateSummary]:
        body = self._t.request("GET", "/v1/templates")
        items = body if isinstance(body, list) else body.get("data", [])
        return [t.TemplateSummary.model_validate(x) for x in items]

    def get(self, key: str) -> t.Template:
        return t.Template.model_validate(self._t.request("GET", f"/v1/templates/{key}"))

    def get_schema(self, key: str) -> t.TemplateSchema:
        return t.TemplateSchema.model_validate(
            self._t.request("GET", f"/v1/templates/{key}/schema")
        )

    def render(self, key: str, *, variables: Mapping[str, Any] | None = None) -> t.RenderResult:
        result = t.RenderResult.model_validate(
            self._t.request(
                "POST",
                f"/v1/templates/{key}/render",
                json={"variables": dict(variables or {})},
            )
        )
        _telemetry.capture(self._t._api_key, "template_rendered", {
            "template_key": key,
            "has_variables": variables is not None,
        })
        return result

    def send(
        self,
        key: str,
        *,
        to: str,
        from_: Mapping[str, Any] | None = None,
        reply_to: Mapping[str, Any] | None = None,
        variables: Mapping[str, Any] | None = None,
        tags: builtins.list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> t.SendResult:
        body: dict[str, Any] = {"to": to}
        if from_ is not None:
            body["from"] = dict(from_)
        if reply_to is not None:
            body["replyTo"] = dict(reply_to)
        if variables is not None:
            body["variables"] = dict(variables)
        if tags is not None:
            body["tags"] = list(tags)
        result = t.SendResult.model_validate(
            self._t.request(
                "POST",
                f"/v1/templates/{key}/send",
                json=body,
                idempotency_key=idempotency_key,
            )
        )
        _telemetry.capture(self._t._api_key, "template_sent", {
            "template_key": key,
            "has_from": from_ is not None,
            "has_reply_to": reply_to is not None,
            "has_variables": variables is not None,
            "tag_count": len(tags) if tags else 0,
            "has_idempotency_key": idempotency_key is not None,
        })
        return result


# --------------------------------------------------------------------------- #
# Sequences + events
# --------------------------------------------------------------------------- #


class _Sequences(_Resource):
    def list(self) -> builtins.list[t.SequenceSummary]:
        body = self._t.request("GET", "/v1/sequences")
        items = body if isinstance(body, list) else body.get("data", [])
        return [t.SequenceSummary.model_validate(x) for x in items]

    def get(self, key_or_id: str) -> t.Sequence:
        return t.Sequence.model_validate(
            self._t.request("GET", f"/v1/sequences/{key_or_id}")
        )

    def enroll(
        self,
        key_or_id: str,
        *,
        contact: Mapping[str, Any],
        variables: Mapping[str, Any] | None = None,
        start_at_step: str | None = None,
        idempotency_key: str | None = None,
    ) -> t.EnrollResult:
        result = t.EnrollResult.model_validate(
            self._t.request(
                "POST",
                f"/v1/sequences/{key_or_id}/enroll",
                json={
                    "contact": dict(contact),
                    "variables": dict(variables) if variables else None,
                    "startAtStep": start_at_step,
                },
                idempotency_key=idempotency_key,
            )
        )
        _telemetry.capture(self._t._api_key, "sequence_enrolled", {
            "has_variables": variables is not None,
            "has_start_at_step": start_at_step is not None,
            "has_idempotency_key": idempotency_key is not None,
        })
        return result


class _SequenceRuns(_Resource):
    def get(self, run_id: str) -> t.SequenceRun:
        return t.SequenceRun.model_validate(
            self._t.request("GET", f"/v1/sequence-runs/{run_id}")
        )

    def cancel(self, run_id: str) -> t.SequenceRun:
        return t.SequenceRun.model_validate(
            self._t.request("POST", f"/v1/sequence-runs/{run_id}/cancel")
        )


class _Events(_Resource):
    def emit(
        self,
        name: str,
        *,
        user_id: str | None = None,
        email: str | None = None,
        traits: Mapping[str, Any] | None = None,
        occurred_at: str | None = None,
        idempotency_key: str | None = None,
    ) -> t.EmitEventResult:
        result = t.EmitEventResult.model_validate(
            self._t.request(
                "POST",
                "/v1/events",
                json={
                    "name": name,
                    "userId": user_id,
                    "email": email,
                    "traits": dict(traits) if traits else {},
                    "occurredAt": occurred_at,
                },
                idempotency_key=idempotency_key,
            )
        )
        _telemetry.capture(self._t._api_key, "event_emitted", {
            "has_user_id": user_id is not None,
            "has_traits": traits is not None,
            "has_occurred_at": occurred_at is not None,
            "trait_count": len(traits) if traits else 0,
        })
        return result


# --------------------------------------------------------------------------- #
# Webhooks + audit
# --------------------------------------------------------------------------- #


class _Webhooks(_Resource):
    def list(self) -> builtins.list[t.WebhookSubscription]:
        body = self._t.request("GET", "/v1/webhooks")
        items = body if isinstance(body, list) else body.get("data", [])
        return [t.WebhookSubscription.model_validate(x) for x in items]

    def get(self, webhook_id: str) -> t.WebhookSubscription:
        return t.WebhookSubscription.model_validate(
            self._t.request("GET", f"/v1/webhooks/{webhook_id}")
        )

    def create(
        self,
        *,
        url: str,
        events: builtins.list[str] | None = None,
        description: str | None = None,
    ) -> t.WebhookSubscription:
        result = t.WebhookSubscription.model_validate(
            self._t.request(
                "POST",
                "/v1/webhooks",
                json={"url": url, "events": events, "description": description},
            )
        )
        _telemetry.capture(self._t._api_key, "webhook_created", {
            "event_count": len(events) if events else 0,
            "has_description": description is not None,
        })
        return result

    def update(
        self,
        webhook_id: str,
        *,
        events: builtins.list[str] | None = None,
        description: str | None = None,
        disabled: bool | None = None,
    ) -> t.WebhookSubscription:
        body: dict[str, Any] = {}
        if events is not None:
            body["events"] = events
        if description is not None:
            body["description"] = description
        if disabled is not None:
            body["disabled"] = disabled
        return t.WebhookSubscription.model_validate(
            self._t.request("PATCH", f"/v1/webhooks/{webhook_id}", json=body)
        )

    def delete(self, webhook_id: str) -> None:
        self._t.request("DELETE", f"/v1/webhooks/{webhook_id}")
        _telemetry.capture(self._t._api_key, "webhook_deleted", {})


class _Audit(_Resource):
    def list(
        self, *, limit: int = 100, cursor: str | None = None
    ) -> tuple[builtins.list[t.AuditEntry], str | None]:
        body = self._t.request(
            "GET",
            "/v1/audit",
            params={"limit": limit, "cursor": cursor},
        )
        page = t.Page.model_validate(body)
        return (
            [t.AuditEntry.model_validate(x) for x in page.data],
            page.next_cursor,
        )

    def iter(self, *, page_size: int = 100) -> Iterator[t.AuditEntry]:
        cursor: str | None = None
        while True:
            entries, cursor = self.list(limit=page_size, cursor=cursor)
            yield from entries
            if not cursor:
                return


# --------------------------------------------------------------------------- #
# Top-level client
# --------------------------------------------------------------------------- #


class MailGenius:
    """Synchronous MailGenius client.

    Example::

        from mailgenius import MailGenius

        with MailGenius(api_key="mg_live_...") as mg:
            mg.events.emit("user.signed_up", email="aki@example.com")
            sends = mg.templates.send(
                "welcome",
                to="aki@example.com",
                variables={"firstName": "Aki"},
            )
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        transport: Transport | None = None,
    ) -> None:
        resolved_key = resolve_api_key(api_key)
        resolved_base = resolve_base_url(base_url)
        if transport is None:
            transport = Transport(
                resolved_key,
                base_url=resolved_base,
                max_retries=max_retries,
            )
        self._transport = transport
        self.workspace = _Workspace(transport)
        self.keys = _Keys(transport)
        self.templates = _Templates(transport)
        self.sequences = _Sequences(transport)
        self.sequence_runs = _SequenceRuns(transport)
        self.events = _Events(transport)
        self.webhooks = _Webhooks(transport)
        self.audit = _Audit(transport)
        _telemetry.capture(resolved_key, "sdk_client_initialized", {
            "client": "sync",
            "has_custom_base_url": bool(base_url),
            "max_retries": max_retries,
        })

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> MailGenius:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


__all__ = ["MailGenius", "DEFAULT_BASE_URL"]
