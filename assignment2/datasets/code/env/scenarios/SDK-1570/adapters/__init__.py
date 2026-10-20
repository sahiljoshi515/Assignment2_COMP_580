"""Adapter registry: one entry per provider."""

from .braintree import BraintreeAdapter
from .checkout import CheckoutAdapter
from .klarna import KlarnaAdapter
from .mollie import MollieAdapter
from .paypal import PayPalAdapter
from .square import SquareAdapter
from .stripe import StripeAdapter
from .worldpay import WorldpayAdapter

ADAPTERS = {
    "braintree": BraintreeAdapter,
    "checkout": CheckoutAdapter,
    "klarna": KlarnaAdapter,
    "mollie": MollieAdapter,
    "paypal": PayPalAdapter,
    "square": SquareAdapter,
    "stripe": StripeAdapter,
    "worldpay": WorldpayAdapter,
}


def adapter_for(name):
    return ADAPTERS[name]
