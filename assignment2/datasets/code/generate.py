"""Assignment 2 -- code: one adapter copy-pasted per payment provider, and the copies that drifted.

Concept this file teaches: the most common near-duplicate in a code base is the file
somebody copied and renamed. Six payment adapters share one template -- the same retry
loop, the same signing, the same idempotency rule -- and differ in a name, a URL and a
handful of provider-specific error codes. The conventions document says what every
copy must do; a few copies quietly do not. Finding them means reading every adapter
against the others, and an agent that reads six copies of the same hundred lines pays
six times for one.

Design rules this file embodies:
  * Rendered from one template with provider slots, so the copies are near-duplicates
    by construction and the planted defects are single-line edits to one copy each.
  * The defects are the kind code review finds: a retry loop one attempt short, a
    timeout constant that drifted, a weaker hash, a call that forgot its idempotency
    key. Each is tied to a numbered rule in docs/CONVENTIONS.md.
  * Legitimate variation exists and must not be reported: names, URLs, headers, the
    decline codes each provider actually returns.

Run from the repo root:  /usr/local/bin/python3.13 assignment2/datasets/code/generate.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common, corpus  # noqa: E402

PROVIDERS = [  # (module, class stem, api domain, decline codes)
    ("stripe", "Stripe", "stripe.com", ["card_declined", "insufficient_funds", "expired_card", "incorrect_cvc"]),
    ("adyen", "Adyen", "adyen.com", ["REFUSED", "NOT_ENOUGH_BALANCE", "EXPIRED_CARD", "CVC_DECLINED"]),
    ("braintree", "Braintree", "braintreegateway.com", ["processor_declined", "gateway_rejected", "settlement_declined"]),
    ("paypal", "PayPal", "paypal.com", ["INSTRUMENT_DECLINED", "PAYER_CANNOT_PAY", "TRANSACTION_REFUSED"]),
    ("square", "Square", "squareup.com", ["CARD_DECLINED", "INSUFFICIENT_FUNDS", "CVV_FAILURE", "CARD_EXPIRED"]),
    ("mollie", "Mollie", "mollie.com", ["card_declined", "invalid_card_number", "insufficient_funds"]),
    ("klarna", "Klarna", "klarna.com", ["REJECTED", "CREDIT_DENIED", "ORDER_LIMIT"]),
    ("worldpay", "Worldpay", "worldpay.com", ["REFUSED", "CANCELLED", "FRAUD_SUSPICION", "EXPIRED"]),
    ("checkout", "Checkout", "checkout.com", ["20005", "20051", "20054", "30004"]),
]
PACKAGES = ["paylane", "tollgate", "cashier", "ledgerline", "settle", "tillbox"]
RULE_TEXT = [
    ("R1", "Transient failures are retried exactly RETRIES = 3 times with exponential backoff BACKOFF_S ** attempt; the loop is `for attempt in range(RETRIES)`."),
    ("R2", "Every adapter uses TIMEOUT_S = 10 for every HTTP call."),
    ("R3", "Request and webhook signatures are HMAC-SHA256 over the canonical JSON body (hashlib.sha256)."),
    ("R4", "charge() and refund() send an Idempotency-Key header derived from the operation and the merchant reference; capture() and status() do not."),
    ("R5", "Amounts are integers in minor units; a non-integer amount raises ValueError before any request."),
    ("R6", "A PermanentError (any 4xx) is never retried; it propagates on the first attempt."),
]
TEMPLATE = '''"""{Class} payment adapter for the {package} SDK.

Copied from the shared adapter template; the retry, timeout and signing behaviour must stay
identical across providers (docs/CONVENTIONS.md). Only names, URLs, headers and the
provider's own decline codes are meant to differ.
"""

import hashlib
import hmac
import json
import time

from core.errors import PermanentError, TransientError
from core.http import post

NAME = "{module}"
BASE_URL = "https://api.{domain}/v{apiver}"
TIMEOUT_S = {timeout}
RETRIES = 3
BACKOFF_S = 2
SIGNATURE_HEADER = "X-{Class}-Signature"
DECLINE_CODES = ({codes})


class {Class}Adapter:
    """Charges, refunds, captures and status lookups against {Class}."""

    def __init__(self, api_key, secret, merchant_id):
        self.api_key = api_key
        self.secret = secret.encode("utf-8")
        self.merchant_id = merchant_id

    def _headers(self, payload, idempotency_key=None):
        headers = {{
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json",
            SIGNATURE_HEADER: self._sign(payload),
        }}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def _sign(self, payload):
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(self.secret, body, hashlib.{algo}).hexdigest()

    def _request(self, path, payload, idempotency_key=None):
        last_error = None
        for attempt in range({retry_range}):
            try:
                response = post(BASE_URL + path, payload, self._headers(payload, idempotency_key),
                                timeout=TIMEOUT_S)
            except TransientError as error:
                last_error = error
                time.sleep(BACKOFF_S ** attempt)
                continue
            except PermanentError:
                raise
            return self._check(response)
        raise TransientError("%s: gave up after %d attempts: %s" % (NAME, RETRIES, last_error))

    def _check(self, response):
        code = response.get("decline_code") or response.get("error_code")
        if code in DECLINE_CODES:
            raise PermanentError("%s declined the request: %s" % (NAME, code))
        if response.get("status") == "error":
            raise TransientError("%s returned an error without a decline code" % NAME)
        return response

    def charge(self, amount_minor, currency, source, reference):
        if not isinstance(amount_minor, int):
            raise ValueError("amount must be an int in minor units")
        payload = {{"merchant": self.merchant_id, "amount": amount_minor, "currency": currency,
                   "source": source, "reference": reference}}
        return self._request("/charges", payload, idempotency_key=self._idempotency_key("charge", reference))

    def refund(self, charge_id, amount_minor, reference):
        if not isinstance(amount_minor, int):
            raise ValueError("amount must be an int in minor units")
        payload = {{"merchant": self.merchant_id, "charge": charge_id, "amount": amount_minor,
                   "reference": reference}}
        return self._request("/refunds", payload{refund_key})

    def capture(self, charge_id):
        return self._request("/charges/%s/capture" % charge_id, {{"merchant": self.merchant_id}})

    def status(self, charge_id):
        return self._request("/charges/%s" % charge_id, {{"merchant": self.merchant_id}})

    def _idempotency_key(self, operation, reference):
        raw = "%s:%s:%s:%s" % (NAME, self.merchant_id, operation, reference)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def webhook_valid(self, body, signature):
        expected = hmac.new(self.secret, body, hashlib.{algo}).hexdigest()
        return hmac.compare_digest(expected, signature)
'''
ERRORS_PY = '''"""Error types shared by every adapter."""


class AdapterError(Exception):
    """Base class."""


class TransientError(AdapterError):
    """A 5xx, a timeout or a connection reset: safe to retry."""


class PermanentError(AdapterError):
    """A 4xx or a decline: retrying cannot help."""
'''
HTTP_PY = '''"""The one HTTP call every adapter makes."""

import json
import urllib.error
import urllib.request

from .errors import PermanentError, TransientError


def post(url, payload, headers, timeout):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if 400 <= error.code < 500:
            raise PermanentError("%s: HTTP %d" % (url, error.code))
        raise TransientError("%s: HTTP %d" % (url, error.code))
    except (urllib.error.URLError, TimeoutError) as error:
        raise TransientError("%s: %s" % (url, error))
'''


def kinds():
    def retry_violation(state, target):
        return {"file": "adapters/%s.py" % state["retry_violator"], "function": "_request"}

    def timeout_drift(state, target):
        return {"file": "adapters/%s.py" % state["timeout_violator"], "value": state["timeout_value"]}

    def weak_signature(state, target):
        return {"file": "adapters/%s.py" % state["hash_violator"], "algorithm": "sha1"}

    def missing_idempotency(state, target):
        return {"file": "adapters/%s.py" % state["idempotency_violator"], "function": "refund"}

    def base_url_of(state, target):
        return {"file": "adapters/%s.py" % target, "value": state["urls"][target]}

    def decline_codes_of(state, target):
        return {"file": "adapters/%s.py" % target, "codes": list(state["codes"][target])}

    def two_providers(state):
        return state["targets"]

    return (
        corpus.Kind("retry_violation", "which adapter breaks the retry rule",
                    ["Rule R1 in docs/CONVENTIONS.md fixes the retry loop. One adapter in adapters/ does not follow it. Which file, and which method holds the loop?",
                     "Please find the adapter whose retry behaviour deviates from rule R1 (three attempts with exponential backoff) and tell me the file and the method.",
                     "One of the {service} adapters retries differently from the convention in R1. Name the file and the method where the retry loop lives."],
                    ["All adapters were copied from one template, so the deviating line stands out against the others.",
                     "The adapters are copies of one template; compare the retry loops.",
                     "Every adapter should have the same loop; one does not."],
                    retry_violation, ("file", "function"), example={"file": "adapters/adyen.py", "function": "_request"}),
        corpus.Kind("timeout_drift", "which adapter uses a different timeout",
                    ["Rule R2 says every adapter uses TIMEOUT_S = 10. One adapter sets a different value. Which file, and what value does it set?",
                     "Find the adapter whose TIMEOUT_S constant differs from the convention (R2) and report the file and the value.",
                     "Which {service} adapter drifted on its HTTP timeout constant, and to what value?"],
                    ["The constant is near the top of each adapter module.",
                     "TIMEOUT_S is a module-level constant in every adapter file.",
                     "Compare the module constants across adapters/."],
                    timeout_drift, ("file", "value"), example={"file": "adapters/square.py", "value": 30}),
        corpus.Kind("weak_signature", "which adapter signs with a weaker hash",
                    ["Rule R3 requires HMAC-SHA256 signatures. One adapter signs with a different hash algorithm. Which file, and which algorithm does it use?",
                     "One of the {service} adapters violates R3 by using a weaker hash for its signatures. Name the file and the hashlib algorithm it uses.",
                     "Which adapter under adapters/ computes its request and webhook signatures with an algorithm other than sha256, and which algorithm is it?"],
                    ["Look at _sign and webhook_valid in each adapter.",
                     "The hash appears in the two HMAC calls of each adapter.",
                     "The algorithm name is the hashlib attribute passed to hmac.new."],
                    weak_signature, ("file", "algorithm"), example={"file": "adapters/mollie.py", "algorithm": "sha1"}),
        corpus.Kind("missing_idempotency", "which adapter forgets the idempotency key",
                    ["Rule R4 requires charge() and refund() to send an Idempotency-Key. One adapter's method does not. Which file, and which method?",
                     "Find the adapter that violates R4: one of its two idempotent operations calls _request without an idempotency key. File and method, please.",
                     "Which {service} adapter has a charge or refund method that omits the idempotency key required by R4, and which method is it?"],
                    ["The key is passed as idempotency_key= to _request in the compliant copies.",
                     "In the compliant adapters both methods pass idempotency_key= to _request.",
                     "Compare the charge and refund methods across the adapter files."],
                    missing_idempotency, ("file", "function"), example={"file": "adapters/klarna.py", "function": "refund"}),
        corpus.Kind("base_url_of", "what base URL does the {target} adapter call",
                    ["What is the BASE_URL constant of the {target} adapter in the {service} SDK?",
                     "Please read adapters/{target}.py and report its BASE_URL.",
                     "Which API base URL does adapters/{target}.py send its requests to?"],
                    ["Report the string exactly as written in the module.",
                     "The constant is near the top of the file.",
                     "Just the value of BASE_URL for that adapter."],
                    base_url_of, ("file", "value"), targets=two_providers,
                    example={"file": "adapters/stripe.py", "value": "https://api.stripe.com/v3"}),
        corpus.Kind("decline_codes_of", "which decline codes does the {target} adapter treat as permanent",
                    ["Which decline codes does the {target} adapter of {service} treat as permanent failures?",
                     "List the DECLINE_CODES of adapters/{target}.py.",
                     "Please give me the provider decline codes that adapters/{target}.py maps to PermanentError."],
                    ["They are the entries of the DECLINE_CODES tuple; report them as a list of strings.",
                     "Report the tuple's entries as a JSON list of strings.",
                     "The codes are listed in the module constant DECLINE_CODES."],
                    decline_codes_of, ("file", "codes"), targets=two_providers,
                    example={"file": "adapters/adyen.py", "codes": ["REFUSED", "NOT_ENOUGH_BALANCE"]}),
    )


class CodeSpec(corpus.CorpusSpec):
    NAME = "code"
    FILE = __file__
    TITLE = "Convention audit of copy-pasted payment adapters"
    ROLE = ("You are reviewing a payments SDK. One request about its adapters is in `task.json`; answer it from the\n"
            "source files in `adapters/`, `core/` and `docs/` and write the answer to `answer.json`.")
    FILE_LAYOUT = ("`adapters/<provider>.py`: one adapter module per payment provider, all copied from one template; "
                   "`adapters/__init__.py`: the registry; `core/errors.py`, `core/http.py`: shared helpers; "
                   "`docs/CONVENTIONS.md`: the numbered rules R1-R6 every adapter must follow.")
    KINDS = kinds()
    SCENARIOS = 24
    SCENARIO_PREFIX = "SDK"
    DEFAULT_SEED = 71

    def service_of(self, state):
        return state["package"]

    def scenario_state(self, sid, rng):
        package = common.pick(rng, PACKAGES)
        n = rng.randrange(6, 9)
        providers = rng.sample(PROVIDERS, n)
        providers.sort()
        modules = [p[0] for p in providers]
        violators = rng.sample(modules, 4)
        apiver = {m: rng.randrange(1, 4) for m in modules}
        urls = {m: "https://api.%s/v%d" % (domain, apiver[m]) for m, _, domain, _ in providers}
        return {"scenario": sid, "package": package, "providers": providers, "modules": modules, "urls": urls,
                "codes": {m: codes for m, _, _, codes in providers},
                "retry_violator": violators[0], "timeout_violator": violators[1], "hash_violator": violators[2],
                "idempotency_violator": violators[3], "timeout_value": common.pick(rng, [5, 30, 60]),
                "retry_range": common.pick(rng, ["RETRIES - 1", "2", "RETRIES + 2"]),
                "targets": rng.sample(modules, 2)}

    def render_adapter(self, state, module):
        provider = next(p for p in state["providers"] if p[0] == module)
        _, stem, domain, codes = provider
        text = TEMPLATE.format(
            Class=stem, module=module, package=state["package"], domain=domain,
            apiver=state["urls"][module].rsplit("/v", 1)[1],
            timeout=state["timeout_value"] if module == state["timeout_violator"] else 10,
            algo="sha1" if module == state["hash_violator"] else "sha256",
            retry_range=state["retry_range"] if module == state["retry_violator"] else "RETRIES",
            refund_key="" if module == state["idempotency_violator"] else ', idempotency_key=self._idempotency_key("refund", reference)',
            codes=", ".join('"%s"' % c for c in codes) + ("," if len(codes) == 1 else ""))
        lines = text.split("\n")
        marks = []
        for n, line in enumerate(lines, 1):
            if line.startswith("BASE_URL =") or line.startswith("DECLINE_CODES ="):
                marks.append(n)
            if module == state["timeout_violator"] and line.startswith("TIMEOUT_S ="):
                marks.append(n)
            if module == state["hash_violator"] and "hashlib.sha1" in line:
                marks.append(n)
            if module == state["retry_violator"] and "for attempt in range(" in line:
                marks.append(n)
            if module == state["idempotency_violator"] and 'self._request("/refunds"' in line:
                marks.append(n)
        return text, marks

    def conventions(self, state):
        lines = ["# Adapter conventions for the %s SDK" % state["package"], "",
                 "Every module under `adapters/` is a copy of one template. The provider-specific parts are the",
                 "module `NAME`, the `BASE_URL`, the signature header name and the provider's decline codes. The",
                 "rules below are not provider-specific; every adapter must follow all of them.", ""]
        lines += ["- **%s.** %s" % (rid, text) for rid, text in RULE_TEXT]
        lines += ["", "A deviation from any rule is a defect, however small. A difference in `NAME`, `BASE_URL`,",
                  "`SIGNATURE_HEADER`, `DECLINE_CODES` or the docstring is not."]
        return "\n".join(lines) + "\n"

    def registry(self, state):
        lines = ['"""Adapter registry: one entry per provider."""', ""]
        lines += ["from .%s import %sAdapter" % (m, stem) for m, stem, _, _ in state["providers"]]
        lines += ["", "ADAPTERS = {"]
        lines += ['    "%s": %sAdapter,' % (m, stem) for m, stem, _, _ in state["providers"]]
        lines += ["}", "", "", "def adapter_for(name):", "    return ADAPTERS[name]"]
        return "\n".join(lines) + "\n"

    def scenario_files(self, state):
        files = {"docs/CONVENTIONS.md": self.conventions(state), "adapters/__init__.py": self.registry(state),
                 "core/__init__.py": "", "core/errors.py": ERRORS_PY, "core/http.py": HTTP_PY}
        for module in state["modules"]:
            text, _ = self.render_adapter(state, module)
            files["adapters/%s.py" % module] = text
        return files

    def content_truth(self, state, files):
        answer_lines = {}
        for module in state["modules"]:
            _, marks = self.render_adapter(state, module)
            answer_lines["adapters/%s.py" % module] = marks
        return {"groups": [{"name": "provider-adapters", "files": sorted("adapters/%s.py" % m for m in state["modules"])}],
                "answer_lines": answer_lines}

    def domain_instructions(self):
        return ["## The scenario", "",
                "`adapters/` holds one Python module per payment provider. All of them were copied from one template",
                "and are meant to behave identically except for the provider's name, URL, signature header and decline",
                "codes. `docs/CONVENTIONS.md` states rules R1-R6 that every adapter must follow. A few adapters have",
                "drifted from the template on exactly one rule each.", "",
                "## How to decide", "",
                "- Compare each adapter against the others and against the rules; a deviation on a rule is the",
                "  answer, a difference in a provider-specific constant is not.",
                "- Report files with their path relative to this directory (`adapters/adyen.py`), methods by name",
                "  (`_request`, `refund`), hash algorithms by their hashlib name (`sha1`), constants as written.",
                "- `DECLINE_CODES` are reported as a list of the strings in the tuple."]


SPEC = CodeSpec()

if __name__ == "__main__":
    sys.exit(corpus.main(SPEC))
