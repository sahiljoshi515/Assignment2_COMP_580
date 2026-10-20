"""Adapter registry: one entry per provider."""

from .adyen import AdyenAdapter
from .checkout import CheckoutAdapter
from .klarna import KlarnaAdapter
from .mollie import MollieAdapter
from .stripe import StripeAdapter
from .worldpay import WorldpayAdapter

ADAPTERS = {
    "adyen": AdyenAdapter,
    "checkout": CheckoutAdapter,
    "klarna": KlarnaAdapter,
    "mollie": MollieAdapter,
    "stripe": StripeAdapter,
    "worldpay": WorldpayAdapter,
}


def adapter_for(name):
    return ADAPTERS[name]
