# Configuration policy for orders-api

Every environment under `config/` is generated from one template. The keys below must hold
the same value in every environment; a difference on any of them is drift and is a defect.

- `service.port`
- `service.request_timeout_ms`
- `service.max_body_kb`
- `database.pool_size`
- `database.statement_timeout_ms`
- `database.ssl_mode`
- `cache.ttl_s`
- `cache.max_entries`
- `auth.issuer`
- `auth.token_ttl_s`
- `auth.allow_anonymous`
- `tls.verify`
- `tls.min_version`
- `logging.format`
- `logging.sample_rate`
- `features.new_checkout`
- `features.async_refunds`
- `features.rate_limiting`
- `payments.provider`
- `payments.retry_limit`
- `payments.backoff_ms`
- `payments.idempotency`
- `database.port`
- `auth.required_scopes`
- `service.name`

These keys may differ between environments and are not drift:

- `cache.endpoint`
- `database.host`
- `logging.level`
- `service.replicas`
- `tls.cert_path`

## Security requirements

- `tls.verify` must be `true` in every environment.
- `auth.allow_anonymous` must be `false` in every environment.

## Completeness

Every environment file carries every key of the template; a missing key falls back to a
built-in default at runtime, which is why a missing key is a defect even when nothing breaks.
