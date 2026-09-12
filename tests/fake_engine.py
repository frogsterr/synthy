"""Engine stand-in for tests: writes a fixed two-staff MusicXML per page."""

from __future__ import annotations

from pathlib import Path

from .helpers import write_score


class FakeEngine:
    name = "fake"

    def __init__(self, fail_pages: set[int] | None = None, measures_per_page: int = 2):
        self.fail_pages = fail_pages or set()
        self.measures_per_page = measures_per_page
        self.calls: list[list[Path]] = []

    def transcribe(self, pages: list[Path], workdir: Path) -> list[Path | None]:
        self.calls.append(list(pages))
        out: list[Path | None] = []
        for i, page in enumerate(pages, start=1):
            if i in self.fail_pages:
                out.append(None)
                continue
            treble = [["C5/1.0", "D5/1.0", "E5/1.0", "F5/1.0"]] * self.measures_per_page
            bass = [["C3/2.0", "G2/2.0"]] * self.measures_per_page
            out.append(write_score(Path(workdir) / f"{page.stem}.musicxml", treble, bass))
        return out
