import mido
import pymupdf
import pytest

from synthy.pipeline import PipelineError, convert

from .fake_engine import FakeEngine


def _pdf(path, n):
    doc = pymupdf.open()
    for _ in range(n):
        doc.new_page(width=595, height=842)
    doc.save(path)
    return path


def test_convert_end_to_end(tmp_path):
    src = _pdf(tmp_path / "score.pdf", 2)
    engine = FakeEngine()
    stages = []
    result = convert(src, tmp_path / "out.mid", tempo_bpm=100, engine=engine,
                     workdir=tmp_path / "work", progress=lambda stage, done, total: stages.append(stage))
    assert result.midi_path.exists()
    assert result.engine_name == "fake"
    assert result.pages == [1, 2]
    assert result.failed_pages == []
    assert len(result.reports) == 4
    assert [r.page for r in result.reports] == [1, 1, 2, 2]
    assert not result.suspect_measures
    assert len(result.events) == 4 * (4 + 2)
    assert result.events == sorted(result.events)
    assert stages[0] == "render" and "transcribe" in stages and stages[-1] == "assemble"
    mid = mido.MidiFile(result.midi_path)
    channels = {m.channel for t in mid.tracks for m in t if m.type == "note_on"}
    assert channels == {0, 1}
    assert len(engine.calls) == 1 and len(engine.calls[0]) == 2


def test_failed_page_recorded_and_others_continue(tmp_path):
    src = _pdf(tmp_path / "score.pdf", 3)
    result = convert(src, tmp_path / "out.mid", engine=FakeEngine(fail_pages={2}), workdir=tmp_path / "work")
    assert result.failed_pages == [2]
    assert [r.page for r in result.reports] == [1, 1, 3, 3]


def test_page_selection(tmp_path):
    src = _pdf(tmp_path / "score.pdf", 3)
    result = convert(src, tmp_path / "out.mid", pages=[3], engine=FakeEngine(), workdir=tmp_path / "work")
    assert result.pages == [3]
    assert [r.page for r in result.reports] == [3, 3]


def test_all_pages_failed_raises(tmp_path):
    src = _pdf(tmp_path / "score.pdf", 1)
    with pytest.raises(PipelineError):
        convert(src, tmp_path / "out.mid", engine=FakeEngine(fail_pages={1}), workdir=tmp_path / "work")
