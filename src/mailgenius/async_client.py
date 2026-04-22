"""
Asynchronous :class:`AsyncMailGenius` client — same surface as the
sync client, awaitable.
"""
from __future__ import annotations

from typing import Any, AsyncIterator, List, Mapping, Optional

from . import _types as t
from ._transport import (
    AsyncTransport,
    DEFAULT_BASE_URL,
    resolve_api_key,
    resolve_base_url,
)


class _AsyncResource:
    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport


# --------------------------------------------------------------------------- #
# Workspace + keys
# --------------------------------------------------------------------------- #


class _AsyncWorkspace(_AsyncResource):
    async def get(self) -> t.Workspace:
        return t.Workspace.model_validate(await self._t.request("GET", "/v1/workspace"))


class _AsyncKeys(_AsyncResource):
    async def list(self) -> List[t.ApiKeySummary]:
        body = await self._t.request("GET", "/v1/keys")
        items = body if isinstance(body, list) else body.get("data", [])
        return [t.ApiKeySummary.model_validate(x) for x in items]

    async def get(self, key_id: str) -> t.ApiKeySummary:
        return t.ApiKeySummary.model_validate(
            await self._t.request("GET", f"/v1/keys/{key_id}")
        )


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #


class _AsyncTemplates(_AsyncResource):
    async def list(self) -> List[t.TemplateSummary]:
        body = await self._t.request("GET", "/v1/templates")
        items = body if isinstance(body, list) else body.get("data", [])
        return [t.TemplateSummary.model_validate(x) for x in items]

    async def get(self, key: str) -> t.Template:
        return t.Template.model_validate(
            await self._t.request("GET", f"/v1/templates/{key}")
        )

    async def get_schema(self, key: str) -> t.TemplateSchema:
        return t.TemplateSchema.model_validate(
            await self._t.request("GET", f"/v1/templates/{key}/schema")
        )

    async def render(
        self, key: str, *, variables: Optional[Mapping[str, Any]] = None
    ) -> t.RenderResult:
        return t.RenderResult.model_validate(
            await self._t.request(
                "POST",
                f"/v1/templates/{key}/render",
                json={"variables": dict(variables or {})},
            )
        )

    async def send(
        self,
        key: str,
        *,
        to: str,
        from_: Optional[Mapping[str, Any]] = None,
        reply_to: Optional[Mapping[str, Any]] = None,
        variables: Optional[Mapping[str, Any]] = None,
        tags: Optional[List[str]] = None,
        idempotency_key: Optional[str] = None,
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
        return t.SendResult.model_validate(
            await self._t.request(
                "POST",
                f"/v1/templates/{key}/send",
                json=body,
                idempotency_key=idempotency_key,
            )
        )


# --------------------------------------------------------------------------- #
# Sequences + events
# --------------------------------------------------------------------------- #


class _AsyncSequences(_AsyncResource):
    async def list(self) -> List[t.SequenceSummary]:
        body = await self._t.request("GET", "/v1/sequences")
        items = body if isinstance(body, list) else body.get("data", [])
        return [t.SequenceSummary.model_validate(x) for x in items]

    async def get(self, key_or_id: str) -> t.Sequence:
        return t.Sequence.model_validate(
            await self._t.request("GET", f"/v1/sequences/{key_or_id}")
        )

    async def enroll(
        self,
        key_or_id: str,
        *,
        contact: Mapping[str, Any],
        variables: Optional[Mapping[str, Any]] = None,
        start_at_step: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> t.EnrollResult:
        return t.EnrollResult.model_validate(
            await self._t.request(
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


class _AsyncSequenceRuns(_AsyncResource):
    async def get(self, run_id: str) -> t.SequenceRun:
        return t.SequenceRun.model_validate(
            await self._t.request("GET", f"/v1/sequence-runs/{run_id}")
        )

    async def cancel(self, run_id: str) -> t.SequenceRun:
        return t.SequenceRun.model_validate(
            await self._t.request("POST", f"/v1/sequence-runs/{run_id}/cancel")
        )


class _AsyncEvents(_AsyncResource):
    async def emit(
        self,
        name: str,
        *,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        traits: Optional[Mapping[str, Any]] = None,
        occurred_at: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> t.EmitEventResult:
        return t.EmitEventResult.model_validate(
            await self._t.request(
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


# --------------------------------------------------------------------------- #
# Webhooks + audit
# --------------------------------------------------------------------------- #


class _AsyncWebhooks(_AsyncResource):
    async def list(self) -> List[t.WebhookSubscription]:
        body = await self._t.request("GET", "/v1/webhooks")
        items = body if isinstance(body, list) else body.get("data", [])
        return [t.WebhookSubscription.model_validate(x) for x in items]

    async def get(self, webhook_id: str) -> t.WebhookSubscription:
        return t.WebhookSubscription.model_validate(
            await self._t.request("GET", f"/v1/webhooks/{webhook_id}")
        )

    async def create(
        self,
        *,
        url: str,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> t.WebhookSubscription:
        return t.WebhookSubscription.model_validate(
            await self._t.request(
                "POST",
                "/v1/webhooks",
                json={"url": url, "events": events, "description": description},
            )
        )

    async def update(
        self,
        webhook_id: str,
        *,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
        disabled: Optional[bool] = None,
    ) -> t.WebhookSubscription:
        body: dict[str, Any] = {}
        if events is not None:
            body["events"] = events
        if description is not None:
            body["description"] = description
        if disabled is not None:
            body["disabled"] = disabled
        return t.WebhookSubscription.model_validate(
            await self._t.request("PATCH", f"/v1/webhooks/{webhook_id}", json=body)
        )

    async def delete(self, webhook_id: str) -> None:
        await self._t.request("DELETE", f"/v1/webhooks/{webhook_id}")


class _AsyncAudit(_AsyncResource):
    async def list(
        self, *, limit: int = 100, cursor: Optional[str] = None
    ) -> tuple[List[t.AuditEntry], Optional[str]]:
        body = await self._t.request(
            "GET",
            "/v1/audit",
            params={"limit": limit, "cursor": cursor},
        )
        page = t.Page.model_validate(body)
        return (
            [t.AuditEntry.model_validate(x) for x in page.data],
            page.next_cursor,
        )

    async def iter(self, *, page_size: int = 100) -> AsyncIterator[t.AuditEntry]:
        cursor: Optional[str] = None
        while True:
            entries, cursor = await self.list(limit=page_size, cursor=cursor)
            for e in entries:
                yield e
            if not cursor:
                return


# --------------------------------------------------------------------------- #
# Top-level async client
# --------------------------------------------------------------------------- #


class AsyncMailGenius:
    """Asynchronous MailGenius client.

    Example::

        from mailgenius import AsyncMailGenius

        async with AsyncMailGenius(api_key="mg_live_...") as mg:
            await mg.events.emit("user.signed_up", email="aki@example.com")
            send = await mg.templates.send(
                "welcome",
                to="aki@example.com",
                variables={"firstName": "Aki"},
            )
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        transport: Optional[AsyncTransport] = None,
    ) -> None:
        if transport is None:
            transport = AsyncTransport(
                resolve_api_key(api_key),
                base_url=resolve_base_url(base_url),
                max_retries=max_retries,
            )
        self._transport = transport
        self.workspace = _AsyncWorkspace(transport)
        self.keys = _AsyncKeys(transport)
        self.templates = _AsyncTemplates(transport)
        self.sequences = _AsyncSequences(transport)
        self.sequence_runs = _AsyncSequenceRuns(transport)
        self.events = _AsyncEvents(transport)
        self.webhooks = _AsyncWebhooks(transport)
        self.audit = _AsyncAudit(transport)

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> "AsyncMailGenius":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.aclose()


__all__ = ["AsyncMailGenius", "DEFAULT_BASE_URL"]
