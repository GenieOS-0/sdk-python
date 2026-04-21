"""
MailGenius — official Python SDK.

Quickstart::

    from mailgenius import MailGenius

    with MailGenius(api_key="mg_live_...") as mg:
        ws = mg.workspace.get()
        print(ws.name, ws.plan)

        send = mg.templates.send(
            "welcome",
            to="aki@example.com",
            variables={"firstName": "Aki"},
        )
        print("send id:", send.id)

For asynchronous code, use ``AsyncMailGenius`` which exposes the same
resource surface with awaitable methods.
"""
from ._errors import (
    MailGeniusAuthError,
    MailGeniusConflictError,
    MailGeniusError,
    MailGeniusNetworkError,
    MailGeniusNotFoundError,
    MailGeniusRateLimitError,
    MailGeniusServerError,
    MailGeniusValidationError,
)
from ._transport import DEFAULT_BASE_URL
from .async_client import AsyncMailGenius
from .client import MailGenius
from .webhooks import VerifiedDelivery, WebhookSignatureError, sign_webhook, verify_webhook

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "DEFAULT_BASE_URL",
    "MailGenius",
    "AsyncMailGenius",
    "MailGeniusError",
    "MailGeniusAuthError",
    "MailGeniusNotFoundError",
    "MailGeniusValidationError",
    "MailGeniusConflictError",
    "MailGeniusRateLimitError",
    "MailGeniusServerError",
    "MailGeniusNetworkError",
    "VerifiedDelivery",
    "WebhookSignatureError",
    "verify_webhook",
    "sign_webhook",
]
