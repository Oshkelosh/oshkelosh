# app/exceptions.py
"""
Central place for all application-specific exceptions.
Makes error handling predictable and testable.
"""
from __future__ import annotations

class OshkeloshError(Exception):
    """Base exception for all app errors — never raised directly."""
    status_code = 500
    message = "An unexpected error occurred"

    def __init__(self, message: str | None = None, **payload):
        super().__init__(message or self.message)
        self.payload = payload

class AuthorizationError(OshkeloshError):
    status_code = 403
    message = "You do not have permission to perform this action"

class NotFoundError(OshkeloshError):
    status_code = 404
    message = "The requested resource was not found"

class ValidationError(OshkeloshError):
    status_code = 400
    message = "Invalid input"

class PaymentError(OshkeloshError):
    status_code = 402
    message = "Payment failed"

class SupplierSyncError(OshkeloshError):
    status_code = 502
    message = "Failed to sync with supplier"
