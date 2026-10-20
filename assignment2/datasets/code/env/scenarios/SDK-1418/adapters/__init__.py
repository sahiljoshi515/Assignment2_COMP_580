"""Adapter registry: one entry per provider."""

from .adyen import AdyenAdapter
from .checkout import CheckoutAdapter
from .klarna import KlarnaAdapter
from .mollie import MollieAdapter
from .paypal import PayPalAdapter
from .stripe import StripeAdapter

ADAPTERS = {
    "adyen": AdyenAdapter,
    "checkout": CheckoutAdapter,
    "klarna": KlarnaAdapter,
    "mollie": MollieAdapter,
    "paypal": PayPalAdapter,
    "stripe": StripeAdapter,
}


def adapter_for(name):
    return ADAPTERS[name]
