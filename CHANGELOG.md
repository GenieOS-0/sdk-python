# genieos (Python SDK)

## 0.1.2

- Links: `links.list` / `utm_suggestions` / `get` / `update` / `analytics`;
  widened `create` (password, schedule, route rules, domain).
- QR: `qr.create` / `update` / `render` on sync and async clients.
- Aligns with `@genie-os/sdk` 0.1.5 / REST deep links surface.

## 0.1.1

- Template create + compose and expanded resource surface to match the Node SDK.
- Docs / examples use `GENIEOS_API_KEY` and `gos_live_*` / `gos_test_*` keys.
- Auto idempotency keys now prefixed `gos-py-` (was `mg-py-`).

## 0.1.0

Initial release.

- `GenieOS` (sync) and `AsyncGenieOS` (async) clients on top of `httpx`.
- Pydantic v2 models for typed responses.
- Auto idempotency keys; retry-on-429/5xx with exponential back-off.
- Resources: `workspace`, `templates`, `events`, `webhooks`, `audit`, `keys`.
- Webhook signature helpers: `verify_webhook`, `sign_webhook`, `WebhookSignatureError`.
- Typed errors inheriting from `GenieOSError`: auth / not-found / validation / conflict / rate-limit / server / network.
