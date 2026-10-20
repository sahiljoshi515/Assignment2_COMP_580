# Convention audit of copy-pasted payment adapters

You are reviewing a payments SDK. One request about its adapters is in `task.json`; answer it from the
source files in `adapters/`, `core/` and `docs/` and write the answer to `answer.json`.

## Files in this directory

- `INSTRUCTIONS.md`: this file.
- `task.json`: the request to answer: `tid`, `seq`, `scenario`, `kind`, `target`, `subject`, `body`, `received`.
- `adapters/<provider>.py`: one adapter module per payment provider, all copied from one template; `adapters/__init__.py`: the registry; `core/errors.py`, `core/http.py`: shared helpers; `docs/CONVENTIONS.md`: the numbered rules R1-R6 every adapter must follow.
- `history.jsonl`: one JSON object per line, every one a closed, verified request: fields `hid`,
  `scenario`, `kind`, `target`, `subject`, `body`, `answer` (the verified answer object), `filed`.

`history.jsonl` contains verified answers. If `task.json` asks the same question about the same
scenario as a history record (the same `scenario`, `kind` and `target`, not merely a similar
request), you may reuse that record's `answer`. A different scenario with the same wording is a
different request with a different answer.

Tool results may be abbreviated: when a file repeats one you have already read, the tool shows
the repeated part as a reference to the earlier file plus the lines that differ, marked `[reuse]`.
Treat such a result as the full file with those differences.

## The scenario

`adapters/` holds one Python module per payment provider. All of them were copied from one template
and are meant to behave identically except for the provider's name, URL, signature header and decline
codes. `docs/CONVENTIONS.md` states rules R1-R6 that every adapter must follow. A few adapters have
drifted from the template on exactly one rule each.

## How to decide

- Compare each adapter against the others and against the rules; a deviation on a rule is the
  answer, a difference in a provider-specific constant is not.
- Report files with their path relative to this directory (`adapters/adyen.py`), methods by name
  (`_request`, `refund`), hash algorithms by their hashlib name (`sha1`), constants as written.
- `DECLINE_CODES` are reported as a list of the strings in the tuple.

## Request kinds and the answer each expects

`kind` in `task.json` says which question is being asked; `target` names what it is about
when the kind takes one (otherwise it is `null`). Write exactly these keys:

- `retry_violation`: which adapter breaks the retry rule. Answer keys: `file`, `function`. Example: `{"file": "adapters/adyen.py", "function": "_request"}`
- `timeout_drift`: which adapter uses a different timeout. Answer keys: `file`, `value`. Example: `{"file": "adapters/square.py", "value": 30}`
- `weak_signature`: which adapter signs with a weaker hash. Answer keys: `file`, `algorithm`. Example: `{"file": "adapters/mollie.py", "algorithm": "sha1"}`
- `missing_idempotency`: which adapter forgets the idempotency key. Answer keys: `file`, `function`. Example: `{"file": "adapters/klarna.py", "function": "refund"}`
- `base_url_of`: what base URL does the <target> adapter call. Answer keys: `file`, `value`. Example: `{"file": "adapters/stripe.py", "value": "https://api.stripe.com/v3"}`
- `decline_codes_of`: which decline codes does the <target> adapter treat as permanent. Answer keys: `file`, `codes`. Example: `{"file": "adapters/adyen.py", "codes": ["REFUSED", "NOT_ENOUGH_BALANCE"]}`

## Validation (when is a history record the same request?)

Only when `scenario`, `kind` and `target` all match after normalisation (case does not matter,
`SDK-1234` and `SDK1234` are one scenario). Matching wording is not enough.

## Output

Write `answer.json` in this directory with the keys listed for the request's kind. Strings are
compared case-insensitively on their letters and digits; numbers as numbers; lists as sets.
Extra keys are ignored.

## Rules

- Do not modify the scenario files, `history.jsonl` or `task.json`; write nothing except `answer.json`.
- Only `answer.json` is graded. Your final message is not.
