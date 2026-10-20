"""Worldpay payment adapter for the tollgate SDK.

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

NAME = "worldpay"
BASE_URL = "https://api.worldpay.com/v2"
TIMEOUT_S = 10
RETRIES = 3
BACKOFF_S = 2
SIGNATURE_HEADER = "X-Worldpay-Signature"
DECLINE_CODES = ("REFUSED", "CANCELLED", "FRAUD_SUSPICION", "EXPIRED")


class WorldpayAdapter:
    """Charges, refunds, captures and status lookups against Worldpay."""

    def __init__(self, api_key, secret, merchant_id):
        self.api_key = api_key
        self.secret = secret.encode("utf-8")
        self.merchant_id = merchant_id

    def _headers(self, payload, idempotency_key=None):
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json",
            SIGNATURE_HEADER: self._sign(payload),
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def _sign(self, payload):
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(self.secret, body, hashlib.sha256).hexdigest()

    def _request(self, path, payload, idempotency_key=None):
        last_error = None
        for attempt in range(RETRIES):
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
        payload = {"merchant": self.merchant_id, "amount": amount_minor, "currency": currency,
                   "source": source, "reference": reference}
        return self._request("/charges", payload, idempotency_key=self._idempotency_key("charge", reference))

    def refund(self, charge_id, amount_minor, reference):
        if not isinstance(amount_minor, int):
            raise ValueError("amount must be an int in minor units")
        payload = {"merchant": self.merchant_id, "charge": charge_id, "amount": amount_minor,
                   "reference": reference}
        return self._request("/refunds", payload, idempotency_key=self._idempotency_key("refund", reference))

    def capture(self, charge_id):
        return self._request("/charges/%s/capture" % charge_id, {"merchant": self.merchant_id})

    def status(self, charge_id):
        return self._request("/charges/%s" % charge_id, {"merchant": self.merchant_id})

    def _idempotency_key(self, operation, reference):
        raw = "%s:%s:%s:%s" % (NAME, self.merchant_id, operation, reference)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def webhook_valid(self, body, signature):
        expected = hmac.new(self.secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
