"""Validation layer — the bouncer at the door (docs/PLAN.md §8)."""

from app.validation.validate import (
    FATAL_FLAGS,
    Rejection,
    ValidatedPrint,
    ValidationResult,
    print_record,
    validate_rows,
)

__all__ = [
    "FATAL_FLAGS",
    "Rejection",
    "ValidatedPrint",
    "ValidationResult",
    "print_record",
    "validate_rows",
]
