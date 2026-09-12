"""Engine interface. Any OMR engine that can turn page images into MusicXML fits here."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


class EngineError(RuntimeError):
    """The engine failed outright (bad install, non-zero exit)."""


@runtime_checkable
class Engine(Protocol):
    name: str

    def transcribe(self, pages: list[Path], workdir: Path) -> list[Path | None]:
        """Return one MusicXML path per input page, None where nothing was produced."""
        ...
