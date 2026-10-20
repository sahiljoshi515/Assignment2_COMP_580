"""Error types shared by every adapter."""


class AdapterError(Exception):
    """Base class."""


class TransientError(AdapterError):
    """A 5xx, a timeout or a connection reset: safe to retry."""


class PermanentError(AdapterError):
    """A 4xx or a decline: retrying cannot help."""
