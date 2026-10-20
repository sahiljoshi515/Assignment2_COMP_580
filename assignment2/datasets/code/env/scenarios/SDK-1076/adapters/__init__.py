"""Adapter registry: one entry per provider."""

from .adyen import AdyenAdapter
from .braintree import BraintreeAdapter
from .mollie import MollieAdapter
from .paypal import PayPalAdapter
from .square import SquareAdapter
from .stripe import StripeAdapter

ADAPTERS = {
    "adyen": AdyenAdapter,
    "braintree": BraintreeAdapter,
    "mollie": MollieAdapter,
    "paypal": PayPalAdapter,
    "square": SquareAdapter,
    "stripe": StripeAdapter,
}


def adapter_for(name):
    return ADAPTERS[name]
