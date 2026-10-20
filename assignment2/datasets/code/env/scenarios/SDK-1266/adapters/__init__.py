"""Adapter registry: one entry per provider."""

from .adyen import AdyenAdapter
from .braintree import BraintreeAdapter
from .checkout import CheckoutAdapter
from .mollie import MollieAdapter
from .paypal import PayPalAdapter
from .stripe import StripeAdapter

ADAPTERS = {
    "adyen": AdyenAdapter,
    "braintree": BraintreeAdapter,
    "checkout": CheckoutAdapter,
    "mollie": MollieAdapter,
    "paypal": PayPalAdapter,
    "stripe": StripeAdapter,
}


def adapter_for(name):
    return ADAPTERS[name]
