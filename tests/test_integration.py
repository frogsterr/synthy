"""Runs the real Audiveris on one page of a real scan. Skipped when either is missing.

Set SYNTHY_TEST_PDF to point at a piano score PDF; defaults to the
Bortkiewicz sonata used in the September 2026 spike.
"""

import os
from pathlib import Path

import mido
import pytest

from synthy.engine import find_audiveris
from synthy.pipeline import convert

DEFAULT_PDF = Path("/mnt/c/Users/kryus/Downloads/IMSLP901751-PMLP1418883-Piano_Sonata_No.2_(Sergei_Bortkiewicz).pdf")
PDF = Path(os.environ.get("SYNTHY_TEST_PDF", DEFAULT_PDF))

pytestmark = pytest.mark.skipif(
    find_audiveris() is None or not PDF.exists(),
    reason="needs Audiveris and a test PDF",
)


def test_page_one_of_real_scan(tmp_path):
    result = convert(PDF, tmp_path / "out.mid", tempo_bpm=80, pages=[1], workdir=tmp_path / "work")
    assert result.engine_name == "audiveris"
    assert result.failed_pages == []
    assert len(result.reports) >= 8
    mid = mido.MidiFile(result.midi_path)
    channels = {m.channel for t in mid.tracks for m in t if m.type == "note_on"}
    assert channels == {0, 1}
    notes = sum(1 for t in mid.tracks for m in t if m.type == "note_on")
    assert notes > 100
