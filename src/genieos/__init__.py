"""
GenieOS — official Python SDK.

Quickstart::

    from genieos import GenieOS

    with GenieOS(api_key="gos_live_...") as mg:
        ws = mg.workspace.get()
        print(ws.name, ws.plan)

        send = mg.templates.send(
            "welcome",
            to="aki@example.com",
            variables={"firstName": "Aki"},
        )
        print("send id:", send.id)

For asynchronous code, use ``AsyncGenieOS`` which exposes the same
resource surface with awaitable methods.
"""
from ._errors import (
    GenieOSAuthError,
    GenieOSConflictError,
    GenieOSError,
    GenieOSNetworkError,
    GenieOSNotFoundError,
    GenieOSRateLimitError,
    GenieOSServerError,
    GenieOSValidationError,
)
from ._transport import DEFAULT_BASE_URL
from .async_client import AsyncGenieOS
from .client import GenieOS
from .webhooks import VerifiedDelivery, WebhookSignatureError, sign_webhook, verify_webhook

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "DEFAULT_BASE_URL",
    "GenieOS",
    "AsyncGenieOS",
    "GenieOSError",
    "GenieOSAuthError",
    "GenieOSNotFoundError",
    "GenieOSValidationError",
    "GenieOSConflictError",
    "GenieOSRateLimitError",
    "GenieOSServerError",
    "GenieOSNetworkError",
    "VerifiedDelivery",
    "WebhookSignatureError",
    "verify_webhook",
    "sign_webhook",
]
