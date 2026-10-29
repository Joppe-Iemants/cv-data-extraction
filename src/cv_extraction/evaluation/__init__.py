"""Offline accuracy evaluation of saved CV extractions."""

from .runner import evaluate_run
from .scoring import evaluate

__all__ = ["evaluate", "evaluate_run"]
