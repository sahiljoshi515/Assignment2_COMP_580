"""Adapter registry: one entry per provider."""

from .adyen import AdyenAdapter
from .braintree import BraintreeAdapter
from .checkout import CheckoutAdapter
from .klarna import KlarnaAdapter
from .paypal import PayPalAdapter
from .square import SquareAdapter
from .worldpay import WorldpayAdapter

ADAPTERS = {
    "adyen": AdyenAdapter,
    "braintree": BraintreeAdapter,
    "checkout": CheckoutAdapter,
    "klarna": KlarnaAdapter,
    "paypal": PayPalAdapter,
    "square": SquareAdapter,
    "worldpay": WorldpayAdapter,
}


def adapter_for(name):
    return ADAPTERS[name]
