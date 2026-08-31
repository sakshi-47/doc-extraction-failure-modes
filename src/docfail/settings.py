"""Typed, environment-driven settings.

Two deliberate choices:

1. No import-time side effects. Importing this module never creates
   directories, reads a dataset, or touches the network. Entry points call
   `Settings.ensure_dirs()` when they actually intend to write.
2. No dotenv auto-discovery. The CLI loads the dotenv file explicitly at
   startup, so this class is agnostic about where its values came from and
   behaves identically under pytest, CI and Docker.

No provider credentials live on this object. Extraction backends read their own
from the environment at call time, so a Settings instance stays safe to log,
serialise and dump in full.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCFAIL_", extra="forbid")

    data_dir: Path = Path("./data")
    cache_dir: Path = Path("./cache")
    output_dir: Path = Path("./outputs")

    # An extraction counts as a "silent failure" only if the model was confident.
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # Guardrail: refuse absurdly large images rather than exhausting memory.
    max_image_bytes: int = Field(default=25 * 1024 * 1024, gt=0)

    # Bounded concurrency for extractor calls; paired with a rate limiter.
    max_concurrency: int = Field(default=4, ge=1, le=32)

    @field_validator("data_dir", "cache_dir", "output_dir")
    @classmethod
    def _expand(cls, v: Path) -> Path:
        return v.expanduser().resolve()

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.cache_dir, self.output_dir):
            d.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    """Load and validate settings, failing fast with a readable message."""
    return Settings()
