"""Adapter registry: one entry per provider."""

from .checkout import CheckoutAdapter
from .mollie import MollieAdapter
from .paypal import PayPalAdapter
from .square import SquareAdapter
from .stripe import StripeAdapter
from .worldpay import WorldpayAdapter

ADAPTERS = {
    "checkout": CheckoutAdapter,
    "mollie": MollieAdapter,
    "paypal": PayPalAdapter,
    "square": SquareAdapter,
    "stripe": StripeAdapter,
    "worldpay": WorldpayAdapter,
}


def adapter_for(name):
    return ADAPTERS[name]
