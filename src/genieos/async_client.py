"""
Asynchronous :class:`AsyncGenieOS` client — same surface as the
sync client, awaitable.
"""
from __future__ import annotations

import builtins
from collections.abc import AsyncIterator, Mapping
from typing import Any

from . import _telemetry
from . import _types as t
from ._transport import (
    DEFAULT_BASE_URL,
    AsyncTransport,
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
    async def list(self) -> builtins.list[t.ApiKeySummary]:
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
    async def list(self) -> builtins.list[t.TemplateSummary]:
        body = await self._t.request("GET", "/v1/templates")
        items = body if isinstance(body, list) else body.get("data", [])
        return [t.TemplateSummary.model_validate(x) for x in items]

    async def get(self, key: str) -> t.Template:
        return t.Template.model_validate(
            await self._t.request("GET", f"/v1/templates/{key}")
        )

    async def create(self, **body: Any) -> dict[str, Any]:
        """Create a blank draft email template."""
        result = await self._t.request("POST", "/v1/templates", json=body)
        return result.get("data", result) if isinstance(result, dict) else result

    async def compose(self, *, prompt: str, **body: Any) -> dict[str, Any]:
        """Compose from a brief and persist. Charges compose-template credits."""
        result = await self._t.request(
            "POST", "/v1/templates/compose", json={"prompt": prompt, **body}
        )
        return result.get("data", result) if isinstance(result, dict) else result

    async def get_schema(self, key: str) -> t.TemplateSchema:
        return t.TemplateSchema.model_validate(
            await self._t.request("GET", f"/v1/templates/{key}/schema")
        )

    async def render(
        self, key: str, *, variables: Mapping[str, Any] | None = None
    ) -> t.RenderResult:
        result = t.RenderResult.model_validate(
            await self._t.request(
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

    async def send(
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
            await self._t.request(
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


class _AsyncSequences(_AsyncResource):
    async def list(self) -> builtins.list[t.SequenceSummary]:
        body = await self._t.request("GET", "/v1/sequences")
        items = body if isinstance(body, list) else body.get("data", [])
        return [t.SequenceSummary.model_validate(x) for x in items]

    async def get(self, key_or_id: str) -> t.Sequence:
        return t.Sequence.model_validate(
            await self._t.request("GET", f"/v1/sequences/{key_or_id}")
        )

    async def patch_graph(
        self,
        key_or_id: str,
        *,
        mutation: Mapping[str, Any],
        base_revision: str,
        idempotency_key: str | None = None,
    ) -> Mapping[str, Any]:
        return await self._t.request(
            "PATCH",
            f"/v1/sequences/{key_or_id}/graph",
            json={
                "baseRevision": base_revision,
                "mutation": dict(mutation),
            },
            idempotency_key=idempotency_key,
        )

    async def simulate(
        self,
        key_or_id: str,
        *,
        subject_id: str,
        subject: Mapping[str, Any],
        run_id: str | None = None,
        enrollment: Mapping[str, Any] | None = None,
        entry_event: Mapping[str, Any] | None = None,
        journey: Mapping[str, str] | None = None,
        signals: builtins.list[Mapping[str, Any]] | None = None,
        started_at: str | None = None,
    ) -> Mapping[str, Any]:
        result = await self._t.request(
            "POST",
            f"/v1/sequences/{key_or_id}/simulate",
            json={
                "runId": run_id,
                "subjectId": subject_id,
                "subject": dict(subject),
                "enrollment": dict(enrollment) if enrollment else None,
                "entryEvent": dict(entry_event) if entry_event else None,
                "journey": dict(journey) if journey else None,
                "signals": [dict(signal) for signal in signals] if signals else None,
                "startedAt": started_at,
            },
        )
        return result["data"]

    async def enroll(
        self,
        key_or_id: str,
        *,
        contact: Mapping[str, Any],
        variables: Mapping[str, Any] | None = None,
        start_at_step: str | None = None,
        idempotency_key: str | None = None,
    ) -> t.EnrollResult:
        result = t.EnrollResult.model_validate(
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
        _telemetry.capture(self._t._api_key, "sequence_enrolled", {
            "has_variables": variables is not None,
            "has_start_at_step": start_at_step is not None,
            "has_idempotency_key": idempotency_key is not None,
        })
        return result


class _AsyncSequenceRuns(_AsyncResource):
    async def get(self, run_id: str) -> t.SequenceRun:
        return t.SequenceRun.model_validate(
            await self._t.request("GET", f"/v1/sequence-runs/{run_id}")
        )

    async def cancel(self, run_id: str) -> t.SequenceRun:
        return t.SequenceRun.model_validate(
            await self._t.request("POST", f"/v1/sequence-runs/{run_id}/cancel")
        )

    async def act(
        self,
        run_id: str,
        *,
        action: str,
        reason: str,
        path_label: str | None = None,
    ) -> t.SequenceRun:
        return t.SequenceRun.model_validate(
            await self._t.request(
                "POST",
                f"/v1/sequence-runs/{run_id}/actions",
                json={
                    "action": action,
                    "reason": reason,
                    "pathLabel": path_label,
                },
            )
        )


class _AsyncEvents(_AsyncResource):
    async def emit(
        self,
        name: str,
        *,
        event_id: str | None = None,
        source: str | None = None,
        schema_version: int | None = None,
        user_id: str | None = None,
        anonymous_id: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        external_ids: Mapping[str, str] | None = None,
        object: Mapping[str, str] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        traits: Mapping[str, Any] | None = None,
        properties: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
        occurred_at: str | None = None,
        idempotency_key: str | None = None,
    ) -> t.EmitEventResult:
        result = t.EmitEventResult.model_validate(
            await self._t.request(
                "POST",
                "/v1/events",
                json={
                    "name": name,
                    "eventId": event_id,
                    "source": source,
                    "schemaVersion": schema_version,
                    "userId": user_id,
                    "anonymousId": anonymous_id,
                    "email": email,
                    "phone": phone,
                    "externalIds": dict(external_ids) if external_ids else None,
                    "object": dict(object) if object else None,
                    "correlationId": correlation_id,
                    "causationId": causation_id,
                    "traits": dict(traits) if traits else {},
                    "properties": dict(properties) if properties else None,
                    "context": dict(context) if context else None,
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


class _AsyncWebhooks(_AsyncResource):
    async def list(self) -> builtins.list[t.WebhookSubscription]:
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
        events: builtins.list[str] | None = None,
        description: str | None = None,
    ) -> t.WebhookSubscription:
        result = t.WebhookSubscription.model_validate(
            await self._t.request(
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

    async def update(
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
            await self._t.request("PATCH", f"/v1/webhooks/{webhook_id}", json=body)
        )

    async def delete(self, webhook_id: str) -> None:
        await self._t.request("DELETE", f"/v1/webhooks/{webhook_id}")
        _telemetry.capture(self._t._api_key, "webhook_deleted", {})


class _AsyncBrand(_AsyncResource):
    async def list(self) -> builtins.list[t.BrandSummary]:
        body = await self._t.request("GET", "/v1/brand")
        items = body if isinstance(body, list) else body.get("data", [])
        return [t.BrandSummary.model_validate(x) for x in items]

    async def get(self, brand_id: str = "default") -> t.BrandDetail:
        return t.BrandDetail.model_validate(
            await self._t.request("GET", f"/v1/brand/{brand_id}")
        )


class _AsyncConnectors(_AsyncResource):
    async def catalog(self) -> dict[str, Any]:
        result = await self._t.request("GET", "/v1/connectors/catalog")
        return result if isinstance(result, dict) else {}

    async def list(self) -> dict[str, Any]:
        result = await self._t.request("GET", "/v1/connectors")
        return result if isinstance(result, dict) else {}


class _AsyncPages(_AsyncResource):
    async def list(self) -> builtins.list[t.PageSummary]:
        body = await self._t.request("GET", "/v1/pages")
        items = body if isinstance(body, list) else body.get("data", [])
        return [t.PageSummary.model_validate(x) for x in items]

    async def get(self, id_or_slug: str) -> t.PageDetail:
        return t.PageDetail.model_validate(
            await self._t.request("GET", f"/v1/pages/{id_or_slug}")
        )

    async def compose(
        self, id_or_slug: str, *, intake: dict[str, Any], persist: bool = True, **fields: Any
    ) -> dict[str, Any]:
        payload = {"intake": intake, "persist": persist, **fields}
        result = await self._t.request(
            "POST", f"/v1/pages/{id_or_slug}/compose", json=payload
        )
        return result if isinstance(result, dict) else {}

    async def publish(self, id_or_slug: str, *, slug: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if slug is not None:
            payload["slug"] = slug
        body = await self._t.request(
            "POST", f"/v1/pages/{id_or_slug}/publish", json=payload
        )
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def unpublish(self, id_or_slug: str) -> dict[str, Any]:
        result = await self._t.request(
            "POST", f"/v1/pages/{id_or_slug}/unpublish", json={}
        )
        return result if isinstance(result, dict) else {}


class _AsyncAudit(_AsyncResource):
    async def list(
        self, *, limit: int = 100, cursor: str | None = None
    ) -> tuple[builtins.list[t.AuditEntry], str | None]:
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
        cursor: str | None = None
        while True:
            entries, cursor = await self.list(limit=page_size, cursor=cursor)
            for e in entries:
                yield e
            if not cursor:
                return


class _AsyncMessaging(_AsyncResource):
    async def kit(self) -> builtins.list[dict[str, Any]]:
        body = await self._t.request("GET", "/v1/messaging/transactional/kit")
        items = body if isinstance(body, list) else body.get("data", [])
        return list(items)

    async def catalog(self) -> builtins.list[dict[str, Any]]:
        body = await self._t.request("GET", "/v1/messaging/transactional/catalog")
        items = body if isinstance(body, list) else body.get("data", [])
        return list(items)

    async def preview(
        self,
        template_key: str,
        *,
        body_template: str | None = None,
        variables: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"templateKey": template_key}
        if body_template is not None:
            payload["bodyTemplate"] = body_template
        if variables is not None:
            payload["variables"] = dict(variables)
        result = await self._t.request(
            "POST", "/v1/messaging/transactional/preview", json=payload
        )
        return result if isinstance(result, dict) else {}

    async def send(
        self,
        template_key: str,
        *,
        to: str | None = None,
        recipient_id: str | None = None,
        variables: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
        consent_proof_id: str | None = None,
        allow_extra_segments: bool | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"templateKey": template_key}
        if to is not None:
            payload["to"] = to
        if recipient_id is not None:
            payload["recipientId"] = recipient_id
        if variables is not None:
            payload["variables"] = dict(variables)
        if consent_proof_id is not None:
            payload["consentProofId"] = consent_proof_id
        if allow_extra_segments is not None:
            payload["allowExtraSegments"] = allow_extra_segments
        result = await self._t.request(
            "POST",
            "/v1/messaging/transactional",
            json=payload,
            idempotency_key=idempotency_key,
        )
        return result if isinstance(result, dict) else {}

    async def list_deliveries(
        self, *, template_key: str | None = None, limit: int = 50
    ) -> builtins.list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if template_key is not None:
            params["templateKey"] = template_key
        body = await self._t.request(
            "GET", "/v1/messaging/transactional/deliveries", params=params
        )
        if isinstance(body, list):
            return list(body)
        return list(body.get("data", []))


class _AsyncTransactionalSocial(_AsyncResource):
    async def catalog(self) -> builtins.list[dict[str, Any]]:
        body = await self._t.request("GET", "/v1/social/transactional/catalog")
        items = body if isinstance(body, list) else body.get("data", [])
        return list(items)

    async def list_templates(self) -> builtins.list[dict[str, Any]]:
        body = await self._t.request("GET", "/v1/social/transactional/templates")
        items = body if isinstance(body, list) else body.get("data", [])
        return list(items)

    async def preview(
        self,
        event_key: str,
        *,
        variables: Mapping[str, Any] | None = None,
        channels: builtins.list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"eventKey": event_key}
        if variables is not None:
            payload["variables"] = dict(variables)
        if channels is not None:
            payload["channels"] = channels
        result = await self._t.request(
            "POST", "/v1/social/transactional/preview", json=payload
        )
        return result if isinstance(result, dict) else {}

    async def trigger(
        self,
        event_key: str,
        *,
        mode: str | None = None,
        variables: Mapping[str, Any] | None = None,
        channels: builtins.list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"eventKey": event_key}
        if mode is not None:
            payload["mode"] = mode
        if variables is not None:
            payload["variables"] = dict(variables)
        if channels is not None:
            payload["channels"] = channels
        result = await self._t.request(
            "POST",
            "/v1/social/transactional/events",
            json=payload,
            idempotency_key=idempotency_key,
        )
        return result if isinstance(result, dict) else {}

    async def list_events(
        self, *, event_key: str | None = None, limit: int = 50
    ) -> builtins.list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if event_key is not None:
            params["eventKey"] = event_key
        body = await self._t.request(
            "GET", "/v1/social/transactional/events", params=params
        )
        items = body if isinstance(body, list) else body.get("data", [])
        return list(items)


class _AsyncSocial(_AsyncResource):
    def __init__(self, transport: AsyncTransport) -> None:
        super().__init__(transport)
        self.transactional = _AsyncTransactionalSocial(transport)

    async def list_networks(self) -> dict[str, Any]:
        result = await self._t.request("GET", "/v1/social/networks")
        return result if isinstance(result, dict) else {"networks": []}

    async def refresh_networks(self) -> dict[str, Any]:
        result = await self._t.request("POST", "/v1/social/networks/refresh")
        return result if isinstance(result, dict) else {}

    async def list(
        self,
        *,
        status: str | None = None,
        channel_id: str | None = None,
        group_id: str | None = None,
        limit: int = 25,
    ) -> builtins.list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if status is not None:
            params["status"] = status
        if channel_id is not None:
            params["channelId"] = channel_id
        if group_id is not None:
            params["groupId"] = group_id
        body = await self._t.request("GET", "/v1/social/posts", params=params)
        items = body if isinstance(body, list) else body.get("data", [])
        return list(items)

    async def get(self, post_id: str) -> dict[str, Any]:
        body = await self._t.request("GET", f"/v1/social/posts/{post_id}")
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def create(self, **body: Any) -> dict[str, Any]:
        idem = body.pop("idempotency_key", None)
        result = await self._t.request(
            "POST",
            "/v1/social/posts",
            json=body,
            idempotency_key=idem if isinstance(idem, str) else None,
        )
        return result if isinstance(result, dict) else {}

    async def update(self, post_id: str, **body: Any) -> dict[str, Any]:
        result = await self._t.request(
            "PATCH", f"/v1/social/posts/{post_id}", json=body
        )
        if isinstance(result, dict) and "data" in result:
            return result["data"]
        return result if isinstance(result, dict) else {}

    async def schedule(
        self,
        post_id: str,
        scheduled_at: str,
        *,
        target_account_ref: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"scheduledAt": scheduled_at}
        if target_account_ref is not None:
            payload["targetAccountRef"] = target_account_ref
        result = await self._t.request(
            "POST",
            f"/v1/social/posts/{post_id}/schedule",
            json=payload,
            idempotency_key=idempotency_key,
        )
        return result if isinstance(result, dict) else {}

    async def publish(
        self,
        post_id: str,
        *,
        target_account_ref: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if target_account_ref is not None:
            payload["targetAccountRef"] = target_account_ref
        result = await self._t.request(
            "POST",
            f"/v1/social/posts/{post_id}/publish",
            json=payload,
            idempotency_key=idempotency_key,
        )
        return result if isinstance(result, dict) else {}

    async def delete(
        self, post_id: str, *, from_provider: bool = False
    ) -> dict[str, Any]:
        params = {"fromProvider": "true"} if from_provider else None
        result = await self._t.request(
            "DELETE", f"/v1/social/posts/{post_id}", params=params
        )
        return result if isinstance(result, dict) else {}

    async def analytics(
        self, post_id: str, *, refresh: bool = False
    ) -> dict[str, Any]:
        params = {"refresh": "true"} if refresh else None
        result = await self._t.request(
            "GET", f"/v1/social/posts/{post_id}/analytics", params=params
        )
        return result if isinstance(result, dict) else {}


class _AsyncMarketing(_AsyncResource):
    async def strategy(self, *, detail: str | None = None) -> dict[str, Any]:
        params = {"detail": "full"} if detail == "full" else None
        result = await self._t.request("GET", "/v1/marketing/strategy", params=params)
        return result if isinstance(result, dict) else {}

    async def list_icps(self, *, detail: str | None = None) -> builtins.list[dict[str, Any]]:
        params = {"detail": "full"} if detail == "full" else None
        body = await self._t.request("GET", "/v1/marketing/icps", params=params)
        items = body if isinstance(body, list) else body.get("data", [])
        return list(items)

    async def get_icp(self, icp_id: str) -> dict[str, Any]:
        body = await self._t.request("GET", f"/v1/marketing/icps/{icp_id}")
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def creation_defaults(self) -> dict[str, Any]:
        body = await self._t.request("GET", "/v1/marketing/creation-defaults")
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def patch_strategy(self, patch: dict[str, Any]) -> dict[str, Any]:
        result = await self._t.request(
            "PATCH", "/v1/marketing/strategy", json={"patch": patch}
        )
        return result if isinstance(result, dict) else {}

    async def set_creation_defaults(self, **fields: Any) -> dict[str, Any]:
        result = await self._t.request(
            "PATCH", "/v1/marketing/creation-defaults", json=fields
        )
        return result if isinstance(result, dict) else {}

    async def create_icp(self, **fields: Any) -> dict[str, Any]:
        result = await self._t.request("POST", "/v1/marketing/icps", json=fields)
        return result if isinstance(result, dict) else {}

    async def update_icp(self, icp_id: str, **fields: Any) -> dict[str, Any]:
        result = await self._t.request(
            "PATCH", f"/v1/marketing/icps/{icp_id}", json=fields
        )
        return result if isinstance(result, dict) else {}


class _AsyncCreations(_AsyncResource):
    async def list(
        self, *, status: str | None = None, limit: int = 25
    ) -> builtins.list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if status is not None:
            params["status"] = status
        body = await self._t.request("GET", "/v1/creations", params=params)
        items = body if isinstance(body, list) else body.get("data", [])
        return list(items)

    async def get(
        self, creation_id: str, *, detail: str | None = None
    ) -> dict[str, Any]:
        params = {"detail": "full"} if detail == "full" else None
        body = await self._t.request(
            "GET", f"/v1/creations/{creation_id}", params=params
        )
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def spawn(
        self, brief: str, *, idempotency_key: str | None = None, **fields: Any
    ) -> dict[str, Any]:
        payload = {"brief": brief, **fields}
        result = await self._t.request(
            "POST",
            "/v1/creations",
            json=payload,
            idempotency_key=idempotency_key,
        )
        return result if isinstance(result, dict) else {}

    async def approve_strategy(self, creation_id: str) -> dict[str, Any]:
        result = await self._t.request(
            "POST", f"/v1/creations/{creation_id}/approve-strategy", json={}
        )
        return result if isinstance(result, dict) else {}


class _AsyncLists(_AsyncResource):
    async def list(self) -> builtins.list[dict[str, Any]]:
        body = await self._t.request("GET", "/v1/lists")
        items = body if isinstance(body, list) else body.get("data", [])
        return list(items)

    async def get(self, list_id: str) -> dict[str, Any]:
        body = await self._t.request("GET", f"/v1/lists/{list_id}")
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def create(self, name: str, **fields: Any) -> dict[str, Any]:
        body = await self._t.request(
            "POST", "/v1/lists", json={"name": name, **fields}
        )
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def update(self, list_id: str, **fields: Any) -> dict[str, Any]:
        body = await self._t.request(
            "PATCH", f"/v1/lists/{list_id}", json=fields
        )
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def delete(self, list_id: str) -> dict[str, Any]:
        result = await self._t.request("DELETE", f"/v1/lists/{list_id}")
        return result if isinstance(result, dict) else {}

    async def add_members(
        self, list_id: str, contact_ids: builtins.list[str]
    ) -> dict[str, Any]:
        body = await self._t.request(
            "POST",
            f"/v1/lists/{list_id}/members",
            json={"contactIds": contact_ids},
        )
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def remove_members(
        self, list_id: str, contact_ids: builtins.list[str]
    ) -> dict[str, Any]:
        body = await self._t.request(
            "POST",
            f"/v1/lists/{list_id}/members/remove",
            json={"contactIds": contact_ids},
        )
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}


class _AsyncApprovals(_AsyncResource):
    async def list_policies(self) -> builtins.list[dict[str, Any]]:
        body = await self._t.request("GET", "/v1/approvals/policies")
        items = body if isinstance(body, list) else body.get("data", [])
        return list(items)

    async def list_pending(self, *, limit: int = 25) -> builtins.list[dict[str, Any]]:
        body = await self._t.request(
            "GET", "/v1/approvals/pending", params={"limit": limit}
        )
        items = body if isinstance(body, list) else body.get("data", [])
        return list(items)

    async def manage_policy(self, surface_kind: str, **fields: Any) -> dict[str, Any]:
        result = await self._t.request(
            "PUT", f"/v1/approvals/policies/{surface_kind}", json=fields
        )
        return result if isinstance(result, dict) else {}

    async def decide(
        self,
        request_id: str,
        *,
        decision: str,
        acting_as_member_uid: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "decision": decision,
            "actingAsMemberUid": acting_as_member_uid,
        }
        if comment is not None:
            payload["comment"] = comment
        result = await self._t.request(
            "POST",
            f"/v1/approvals/pending/{request_id}/decide",
            json=payload,
        )
        return result if isinstance(result, dict) else {}


class _AsyncLinks(_AsyncResource):
    async def list(
        self, *, include_archived: bool = False, limit: int | None = None
    ) -> builtins.list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if include_archived:
            params["includeArchived"] = "true"
        if limit is not None:
            params["limit"] = limit
        body = await self._t.request("GET", "/v1/links", params=params)
        items = body if isinstance(body, list) else body.get("data", [])
        return list(items)

    async def utm_suggestions(
        self, *, field: str | None = None, include_counts: bool = True
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if field is not None:
            params["field"] = field
        if not include_counts:
            params["includeCounts"] = "false"
        body = await self._t.request("GET", "/v1/links/utm-suggestions", params=params)
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def create(
        self, destination_url: str, *, idempotency_key: str | None = None, **fields: Any
    ) -> dict[str, Any]:
        """Create a tracked short link (1 credit).

        ``fields`` accepts (camelCase, matching the REST body): ``slug``,
        ``label``, ``tags``, ``campaignId``, ``domain``, ``utm``,
        ``routeRules`` (geo/platform/device dynamic routing — first match
        wins), ``password`` (plaintext; hashed server-side), ``expiresAt``
        / ``scheduledGoLiveAt`` (ISO-8601 schedule gates). All available on
        every tier.
        """
        body = await self._t.request(
            "POST",
            "/v1/links",
            json={"destinationUrl": destination_url, **fields},
            idempotency_key=idempotency_key,
        )
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def get(self, link_id: str) -> dict[str, Any]:
        """Read one short link — full detail including ``routeRules``,
        whether a password is set, and the schedule window (``list()``
        omits these for brevity)."""
        body = await self._t.request("GET", f"/v1/links/{link_id}")
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def update(self, link_id: str, **fields: Any) -> dict[str, Any]:
        """Free edits to an existing short link.

        ``fields`` accepts: ``destinationUrl``, ``label`` / ``clearLabel``,
        ``tags``, ``utm`` / ``clearUtm``, ``routeRules`` / ``clearRouteRules``,
        ``expiresAt`` / ``clearExpiresAt``, ``scheduledGoLiveAt`` /
        ``clearScheduledGoLiveAt``, ``password`` / ``clearPassword``.
        """
        body = await self._t.request("PATCH", f"/v1/links/{link_id}", json=fields)
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def analytics(
        self,
        *,
        card_key: str,
        link_id: str | None = None,
        days: int | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Short-link click analytics — cache-first (5-minute TTL); cache
        hits are free, misses charge credits per event scanned. Requires
        Glow tier or above.

        ``card_key`` is one of: ``headline``, ``timeseries``, ``geo``,
        ``geo_city``, ``devices``, ``referrers``, ``utm_campaign``,
        ``utm_source``, ``utm_medium``.
        """
        params: dict[str, Any] = {"cardKey": card_key}
        if link_id is not None:
            params["linkId"] = link_id
        if days is not None:
            params["days"] = days
        if force_refresh:
            params["forceRefresh"] = "true"
        body = await self._t.request("GET", "/v1/links/analytics", params=params)
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}


class _AsyncQr(_AsyncResource):
    async def create(
        self, *, idempotency_key: str | None = None, **fields: Any
    ) -> dict[str, Any]:
        """Create a brand-styled QR design (1 credit). Does not render
        bytes — call ``render()`` afterwards for SVG/PNG/WebP/PDF.

        ``fields`` accepts: ``encodes`` (required — e.g.
        ``{"kind": "shortLink", "linkId": "..."}``), ``label``, ``tags``,
        ``style``, ``frame``.
        """
        body = await self._t.request(
            "POST", "/v1/qr", json=fields, idempotency_key=idempotency_key
        )
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def update(self, qr_id: str, **fields: Any) -> dict[str, Any]:
        """Free edits to an existing QR design — style, frame, label,
        tags. Does not re-render bytes; call ``render()`` afterwards for a
        fresh preview/download."""
        body = await self._t.request("PATCH", f"/v1/qr/{qr_id}", json=fields)
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}

    async def render(
        self,
        qr_id: str,
        *,
        format: str | None = None,
        size: int | None = None,
        save_to_assets: bool = False,
    ) -> dict[str, Any]:
        """Render a QR design to bytes. ``svg``/``png``/``webp`` are
        free; ``png-print`` costs 2 credits, ``pdf`` costs 5. Pass
        ``save_to_assets=True`` to also write the render into the
        workspace Asset Manager. Returns ``fileBase64`` (raw bytes,
        base64-encoded, no ``data:`` prefix)."""
        payload: dict[str, Any] = {}
        if format is not None:
            payload["format"] = format
        if size is not None:
            payload["size"] = size
        if save_to_assets:
            payload["saveToAssets"] = True
        body = await self._t.request("POST", f"/v1/qr/{qr_id}/render", json=payload)
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, dict) else {}


# --------------------------------------------------------------------------- #
# Top-level async client
# --------------------------------------------------------------------------- #


class AsyncGenieOS:
    """Asynchronous GenieOS client.

    Example::

        from genieos import AsyncGenieOS

        async with AsyncGenieOS(api_key="gos_live_...") as gos:  # or GENIEOS_API_KEY
            await gos.events.emit("user.signed_up", email="aki@example.com")
            send = await gos.templates.send(
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
        transport: AsyncTransport | None = None,
    ) -> None:
        resolved_key = resolve_api_key(api_key)
        resolved_base = resolve_base_url(base_url)
        if transport is None:
            transport = AsyncTransport(
                resolved_key,
                base_url=resolved_base,
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
        self.brand = _AsyncBrand(transport)
        self.connectors = _AsyncConnectors(transport)
        self.pages = _AsyncPages(transport)
        self.audit = _AsyncAudit(transport)
        self.messaging = _AsyncMessaging(transport)
        self.sms = self.messaging
        self.social = _AsyncSocial(transport)
        self.marketing = _AsyncMarketing(transport)
        self.creations = _AsyncCreations(transport)
        self.lists = _AsyncLists(transport)
        self.approvals = _AsyncApprovals(transport)
        self.links = _AsyncLinks(transport)
        self.qr = _AsyncQr(transport)
        _telemetry.capture(resolved_key, "sdk_client_initialized", {
            "client": "async",
            "has_custom_base_url": bool(base_url),
            "max_retries": max_retries,
        })

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncGenieOS:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.aclose()


__all__ = ["AsyncGenieOS", "DEFAULT_BASE_URL"]
