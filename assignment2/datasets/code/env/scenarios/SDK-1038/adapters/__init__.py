"""Adapter registry: one entry per provider."""

from .adyen import AdyenAdapter
from .braintree import BraintreeAdapter
from .checkout import CheckoutAdapter
from .mollie import MollieAdapter
from .paypal import PayPalAdapter
from .square import SquareAdapter

ADAPTERS = {
    "adyen": AdyenAdapter,
    "braintree": BraintreeAdapter,
    "checkout": CheckoutAdapter,
    "mollie": MollieAdapter,
    "paypal": PayPalAdapter,
    "square": SquareAdapter,
}


def adapter_for(name):
    return ADAPTERS[name]
