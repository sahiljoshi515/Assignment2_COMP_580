# Dataset `code` — one payment adapter copy-pasted per provider, and the copies that drifted

**What a scenario is.** A payments SDK with 6–8 provider adapters under `adapters/`
(`stripe.py`, `adyen.py`, ...), every one a copy of the same ~105-line template: the same
retry loop, signing, idempotency rule and request helpers, differing in the module name,
`BASE_URL`, the signature header, the docstring and the provider's own `DECLINE_CODES`.
`docs/CONVENTIONS.md` states rules R1–R6 that every adapter must follow; `core/` holds the
shared error types and the one HTTP call; `adapters/__init__.py` is the registry.

**What a request is.** `retry_violation` (which adapter's `_request` loop breaks R1),
`timeout_drift` (which adapter sets a different `TIMEOUT_S`, and to what), `weak_signature`
(which adapter signs with `sha1`), `missing_idempotency` (whose `refund` omits the
Idempotency-Key), `base_url_of <provider>`, `decline_codes_of <provider>`.

**What decides the answer.** Four planted defects in four different adapters, each a
one-line edit of the template, and the provider constants. Differences in names, URLs,
headers and decline codes are legitimate and must not be reported.

**Two layers of repetition.** Requests repeat (40 % duplicates, 20 % hard negatives).
Inside a task the adapters are near-duplicates (masked-token Jaccard about 0.88); the
exact diff of one adapter against another is the provider-specific lines plus the
planted one, so reading the second adapter after the first costs a third of its length.

**When a previous answer is safe to reuse.** Same `scenario`, `kind` and `target`.

**Sizes and seed.** 24 scenarios (6.6K–8.6K tokens, 11–13 files), 60 history records,
40 incoming requests, seed 71, about 16K tokens in one task's working directory. Every
generated module compiles.

**Regenerate.**

```sh
/usr/local/bin/python3.13 assignment2/datasets/code/generate.py
/usr/local/bin/python3.13 assignment2/datasets/code/verify.py --tid T-xxxxxx --answer answer.json
```
