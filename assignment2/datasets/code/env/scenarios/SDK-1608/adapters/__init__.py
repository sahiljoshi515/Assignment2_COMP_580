"""Adapter registry: one entry per provider."""

from .braintree import BraintreeAdapter
from .checkout import CheckoutAdapter
from .paypal import PayPalAdapter
from .square import SquareAdapter
from .stripe import StripeAdapter
from .worldpay import WorldpayAdapter

ADAPTERS = {
    "braintree": BraintreeAdapter,
    "checkout": CheckoutAdapter,
    "paypal": PayPalAdapter,
    "square": SquareAdapter,
    "stripe": StripeAdapter,
    "worldpay": WorldpayAdapter,
}


def adapter_for(name):
    return ADAPTERS[name]
