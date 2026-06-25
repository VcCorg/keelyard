"""Devin integration errors."""
from __future__ import annotations


class DevinError(RuntimeError):
    """Raised for non-2xx Devin API responses, carrying the response body."""
