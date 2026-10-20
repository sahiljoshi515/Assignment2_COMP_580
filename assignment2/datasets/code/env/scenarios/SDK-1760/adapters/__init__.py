"""Adapter registry: one entry per provider."""

from .braintree import BraintreeAdapter
from .checkout import CheckoutAdapter
from .klarna import KlarnaAdapter
from .mollie import MollieAdapter
from .square import SquareAdapter
from .worldpay import WorldpayAdapter

ADAPTERS = {
    "braintree": BraintreeAdapter,
    "checkout": CheckoutAdapter,
    "klarna": KlarnaAdapter,
    "mollie": MollieAdapter,
    "square": SquareAdapter,
    "worldpay": WorldpayAdapter,
}


def adapter_for(name):
    return ADAPTERS[name]
