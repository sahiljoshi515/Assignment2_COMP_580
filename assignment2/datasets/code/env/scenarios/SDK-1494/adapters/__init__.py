"""Adapter registry: one entry per provider."""

from .adyen import AdyenAdapter
from .braintree import BraintreeAdapter
from .checkout import CheckoutAdapter
from .klarna import KlarnaAdapter
from .mollie import MollieAdapter
from .paypal import PayPalAdapter

ADAPTERS = {
    "adyen": AdyenAdapter,
    "braintree": BraintreeAdapter,
    "checkout": CheckoutAdapter,
    "klarna": KlarnaAdapter,
    "mollie": MollieAdapter,
    "paypal": PayPalAdapter,
}


def adapter_for(name):
    return ADAPTERS[name]
