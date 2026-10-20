# Adapter conventions for the cashier SDK

Every module under `adapters/` is a copy of one template. The provider-specific parts are the
module `NAME`, the `BASE_URL`, the signature header name and the provider's decline codes. The
rules below are not provider-specific; every adapter must follow all of them.

- **R1.** Transient failures are retried exactly RETRIES = 3 times with exponential backoff BACKOFF_S ** attempt; the loop is `for attempt in range(RETRIES)`.
- **R2.** Every adapter uses TIMEOUT_S = 10 for every HTTP call.
- **R3.** Request and webhook signatures are HMAC-SHA256 over the canonical JSON body (hashlib.sha256).
- **R4.** charge() and refund() send an Idempotency-Key header derived from the operation and the merchant reference; capture() and status() do not.
- **R5.** Amounts are integers in minor units; a non-integer amount raises ValueError before any request.
- **R6.** A PermanentError (any 4xx) is never retried; it propagates on the first attempt.

A deviation from any rule is a defect, however small. A difference in `NAME`, `BASE_URL`,
`SIGNATURE_HEADER`, `DECLINE_CODES` or the docstring is not.
