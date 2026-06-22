# genieos — Python SDK

[![PyPI version](https://img.shields.io/pypi/v/genieos.svg)](https://pypi.org/project/genieos)

The official Python SDK for [GenieOS](https://genieos.pro). Sync and
async clients, typed responses (Pydantic), automatic idempotency,
retry-on-429/5xx with exponential back-off, and webhook signature
verification.

## Install

```bash
pip install genieos
```

Requires Python 3.9+ and `httpx>=0.27`, `pydantic>=2.6`.

## Quickstart (sync)

```python
from genieos import GenieOS

with GenieOS(api_key="gos_live_...") as mg:
    ws = mg.workspace.get()
    print(ws.name, "on", ws.plan)

    send = mg.templates.send(
        "welcome",
        to="aki@example.com",
        variables={"firstName": "Aki"},
    )
    print("queued:", send.id)
```

The API key is also picked up from the `GENIEOS_API_KEY` env var,
matching the Node SDK and CLI.

## Quickstart (async)

```python
import asyncio
from genieos import AsyncGenieOS

async def main():
    async with AsyncGenieOS() as mg:  # MAILGENIUS_API_KEY env var
        await mg.events.emit(
            "subscription.cancelled",
            email="aki@example.com",
            traits={"tier": "pro", "reason": "moving to weekly"},
        )

asyncio.run(main())
```

## Webhook verification (Flask)

```python
from flask import Flask, request, abort
from genieos import verify_webhook, WebhookSignatureError

app = Flask(__name__)

@app.post("/genieos/webhook")
def webhook():
    try:
        delivery = verify_webhook(
            request.get_data(as_text=True),
            request.headers,
            secret=os.environ["MAILGENIUS_WEBHOOK_SECRET"],
        )
    except WebhookSignatureError as e:
        abort(400, str(e))

    if delivery.type == "send.delivered":
        ... # handle it
    return "", 204
```

`verify_webhook` rejects out-of-window timestamps (default ±5 min) and
performs constant-time signature comparison. The same module exposes
`sign_webhook` for local testing.

## Error handling

```python
from genieos import (
    GenieOSRateLimitError,
    GenieOSValidationError,
    GenieOSAuthError,
)

try:
    mg.events.emit("checkout.completed", email="aki@example.com")
except GenieOSRateLimitError as e:
    time.sleep(e.retry_after_seconds)
except GenieOSValidationError as e:
    log.warning("422: %s", e.body)
except GenieOSAuthError:
    rotate_my_key()
```

All SDK errors inherit from `GenieOSError` and expose `.code`,
`.status`, `.request_id`, `.body`.

## License

MIT
