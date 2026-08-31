"""Evaluation metrics for document field extraction."""

from docfail.metrics.cfer import (
    ErrorProfile,
    bootstrap_ci,
    critical_field_error_rate,
    error_profile,
    silent_failure_rate,
)
from docfail.metrics.fields import score_document, score_field
from docfail.metrics.normalize import canonicalize

__all__ = [
    "ErrorProfile",
    "bootstrap_ci",
    "canonicalize",
    "critical_field_error_rate",
    "error_profile",
    "score_document",
    "score_field",
    "silent_failure_rate",
]
