"""Adapter registry: one entry per provider."""

from .adyen import AdyenAdapter
from .braintree import BraintreeAdapter
from .checkout import CheckoutAdapter
from .paypal import PayPalAdapter
from .square import SquareAdapter
from .stripe import StripeAdapter
from .worldpay import WorldpayAdapter

ADAPTERS = {
    "adyen": AdyenAdapter,
    "braintree": BraintreeAdapter,
    "checkout": CheckoutAdapter,
    "paypal": PayPalAdapter,
    "square": SquareAdapter,
    "stripe": StripeAdapter,
    "worldpay": WorldpayAdapter,
}


def adapter_for(name):
    return ADAPTERS[name]
