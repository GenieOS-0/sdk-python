"""
Pydantic models for the GenieOS public API.

Hand-curated to match ``shared/types/devApi.ts`` so the wire shape
stays identical across SDKs. Models are intentionally permissive
(``extra='allow'``) so adding a server-side field doesn't break old
SDK installs — callers can still see the new field via
``.model_extra``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

PlanTier = Literal["free", "starter", "pro", "scale"]
WebhookEventName = Literal[
    "send.queued",
    "send.delivered",
    "send.opened",
    "send.clicked",
    "send.bounced",
    "send.failed",
    "send.complained",
    "sequence_run.enrolled",
    "sequence_run.completed",
    "sequence_run.cancelled",
    "template.schema_proposed",
    "template.schema_ratified",
    "template.schema_rejected",
    "audit.created",
]


class _Model(BaseModel):
    """Base model with permissive forward compatibility."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


# --------------------------------------------------------------------------- #
# Workspace + auth
# --------------------------------------------------------------------------- #


class Workspace(_Model):
    id: str
    name: str
    plan: PlanTier
    scopes: List[str]
    rate_limit_per_minute: int = Field(alias="rateLimitPerMinute")


class ApiKeySummary(_Model):
    id: str
    name: str
    prefix: str
    scopes: List[str]
    created_at: datetime = Field(alias="createdAt")
    last_used_at: Optional[datetime] = Field(default=None, alias="lastUsedAt")
    revoked_at: Optional[datetime] = Field(default=None, alias="revokedAt")


# --------------------------------------------------------------------------- #
# Templates + schema contract
# --------------------------------------------------------------------------- #


class TemplateVariable(_Model):
    key: str
    type: Literal["string", "number", "url", "email"]
    label: Optional[str] = None
    sample: Optional[str] = None
    description: Optional[str] = None
    required: Optional[bool] = None


class TemplateSummary(_Model):
    id: str
    key: str
    name: str
    subject: Optional[str] = None
    version: int
    updated_at: datetime = Field(alias="updatedAt")


class TemplateSchema(_Model):
    declared: List[TemplateVariable]
    observed: List[TemplateVariable]
    # Reserved for future use. Treat as opaque.
    pending: List[Dict[str, Any]] = []


class Template(TemplateSummary):
    body_html: Optional[str] = Field(default=None, alias="bodyHtml")
    schema_contract: TemplateSchema = Field(alias="schemaContract")


class RenderResult(_Model):
    subject: str
    html: str
    warnings: List[str] = []


class SendResult(_Model):
    id: str
    status: Literal["queued", "accepted", "sent"] = "queued"
    connector: Optional[str] = None


# --------------------------------------------------------------------------- #
# Sequences
# --------------------------------------------------------------------------- #


class SequenceSummary(_Model):
    id: str
    key: str
    name: str
    trigger_type: str = Field(alias="triggerType")
    enrolled_count: int = Field(alias="enrolledCount", default=0)


class Sequence(SequenceSummary):
    nodes_count: int = Field(alias="nodesCount", default=0)
    edges_count: int = Field(alias="edgesCount", default=0)
    status: Literal["draft", "published", "paused"] = "draft"


class EnrollResult(_Model):
    run_id: str = Field(alias="runId")
    subject_id: str = Field(alias="subjectId")
    sequence_key: str = Field(alias="sequenceKey")


class SequenceRun(_Model):
    id: str
    sequence_key: str = Field(alias="sequenceKey")
    subject_id: str = Field(alias="subjectId")
    status: Literal["enrolled", "running", "completed", "cancelled", "failed"]
    current_step: Optional[str] = Field(default=None, alias="currentStep")
    started_at: datetime = Field(alias="startedAt")
    finished_at: Optional[datetime] = Field(default=None, alias="finishedAt")


# --------------------------------------------------------------------------- #
# Events
# --------------------------------------------------------------------------- #


class EmitEventResult(_Model):
    event_id: str = Field(alias="eventId")
    enrollments: List[EnrollResult] = []


# --------------------------------------------------------------------------- #
# Webhooks
# --------------------------------------------------------------------------- #


class WebhookSubscription(_Model):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    url: str
    events: List[WebhookEventName] = []
    secret: Optional[str] = None  # only present on create
    description: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    disabled_at: Optional[datetime] = Field(default=None, alias="disabledAt")
    last_delivery_at: Optional[datetime] = Field(default=None, alias="lastDeliveryAt")
    last_delivery_status: Optional[Literal["success", "failure"]] = Field(
        default=None, alias="lastDeliveryStatus"
    )
    consecutive_failures: int = Field(default=0, alias="consecutiveFailures")


class WebhookEnvelope(_Model):
    id: str
    type: WebhookEventName
    created_at: datetime = Field(alias="createdAt")
    workspace_id: str = Field(alias="workspaceId")
    data: Dict[str, Any]


# --------------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------------- #


class AuditEntry(_Model):
    id: str
    actor: str
    action: str
    target: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    occurred_at: datetime = Field(alias="occurredAt")


# --------------------------------------------------------------------------- #
# Brand
# --------------------------------------------------------------------------- #


class BrandSummary(_Model):
    id: str
    name: str
    is_default: bool = Field(alias="isDefault")
    version: int
    origin: Optional[str] = None
    domain: Optional[str] = None
    updated_at: datetime = Field(alias="updatedAt")


class BrandDetail(BrandSummary):
    identity: Dict[str, Any] = Field(default_factory=dict)
    palette: Dict[str, Any] = Field(default_factory=dict)
    typography: Dict[str, Any] = Field(default_factory=dict)
    logos: Dict[str, Any] = Field(default_factory=dict)
    voice: Dict[str, Any] = Field(default_factory=dict)
    imagery: Dict[str, Any] = Field(default_factory=dict)
    email_defaults: Dict[str, Any] = Field(default_factory=dict, alias="emailDefaults")
    # Resolved, pre-flattened brand tokens — what renderers consume.
    tokens: Dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Pages (read-only landing pages)
# --------------------------------------------------------------------------- #


class PageSummary(_Model):
    id: str
    slug: str
    status: Literal["draft", "published", "archived"]
    title: str
    description: str = ""
    published_at: Optional[datetime] = Field(default=None, alias="publishedAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")


class PageDetail(PageSummary):
    brand_id: str = Field(alias="brandId")
    theme_id: Optional[str] = Field(default=None, alias="themeId")
    # Number of top-level sections; the full block tree is not returned
    # over the API (too large) — read it in the SPA editor.
    section_count: int = Field(default=0, alias="sectionCount")
    section_ids: List[str] = Field(default_factory=list, alias="sectionIds")


class Page(_Model):
    """Generic paginated envelope. ``data`` is left as raw dicts —
    the resource-specific helpers parse it into typed lists."""

    data: List[Dict[str, Any]]
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")


__all__ = [
    "PlanTier",
    "WebhookEventName",
    "Workspace",
    "ApiKeySummary",
    "TemplateVariable",
    "TemplateSummary",
    "Template",
    "TemplateSchema",
    "RenderResult",
    "SendResult",
    "SequenceSummary",
    "Sequence",
    "EnrollResult",
    "SequenceRun",
    "EmitEventResult",
    "WebhookSubscription",
    "WebhookEnvelope",
    "AuditEntry",
    "BrandSummary",
    "BrandDetail",
    "PageSummary",
    "PageDetail",
    "Page",
]
