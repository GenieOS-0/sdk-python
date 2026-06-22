# genieos (Python SDK)

## 0.1.0

Initial release.

- `GenieOS` (sync) and `AsyncGenieOS` (async) clients on top of `httpx`.
- Pydantic v2 models for typed responses.
- Auto idempotency keys; retry-on-429/5xx with exponential back-off.
- Resources: `workspace`, `templates`, `events`, `webhooks`, `audit`, `keys`.
- Webhook signature helpers: `verify_webhook`, `sign_webhook`, `WebhookSignatureError`.
- Typed errors inheriting from `GenieOSError`: auth / not-found / validation / conflict / rate-limit / server / network.
