"""Extractor interface.

Backends are untrusted input sources. Whatever a VLM returns is parsed against
the document schema and never executed, rendered as markup, or used to build a
query. Each backend reads its own credential from the environment at call time;
credentials are never stored on a settings object or written to disk.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from docfail.types import FieldPrediction, FieldSpec


class Extractor(Protocol):
    """Contract every extraction backend satisfies."""

    name: str

    def extract(
        self,
        image_path: Path,
        schema: Sequence[FieldSpec],
    ) -> Sequence[FieldPrediction]:
        """Return one prediction per schema field.

        Implementations must return a prediction for every field in `schema`,
        using value=None to signal a genuine abstention. Silence and refusal
        are different outcomes and are scored differently.
        """
        ...
