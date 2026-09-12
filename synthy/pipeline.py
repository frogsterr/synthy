"""input file -> page PNGs -> engine -> RawScore -> normalize -> MIDI."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable

from synthy.engine import AudiverisEngine, Engine
from synthy.midi import write_midi
from synthy.model import ConversionResult
from synthy.normalize import normalize
from synthy.render import render_pages
from synthy.score import merge_scores, parse_musicxml

Progress = Callable[[str, int, int], None]  # (stage, done, total)
DEFAULT_TEMPO = 80


class PipelineError(RuntimeError):
    pass


def convert(
    src: Path,
    out_midi: Path,
    tempo_bpm: int = DEFAULT_TEMPO,
    pages: list[int] | None = None,
    engine: Engine | None = None,
    workdir: Path | None = None,
    progress: Progress | None = None,
) -> ConversionResult:
    src = Path(src)
    out_midi = Path(out_midi)
    engine = engine or AudiverisEngine()
    notify = progress or (lambda stage, done, total: None)
    if workdir is None:
        workdir = Path(tempfile.mkdtemp(prefix="synthy-"))
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    notify("render", 0, 0)
    rendered = render_pages(src, workdir / "pages", pages=pages)
    page_numbers = [n for n, _ in rendered]
    notify("render", len(rendered), len(rendered))

    notify("transcribe", 0, len(rendered))
    outputs = engine.transcribe([p for _, p in rendered], workdir)
    notify("transcribe", len(rendered), len(rendered))

    notify("assemble", 0, len(rendered))
    scores = []
    failed = []
    for (number, _), xml in zip(rendered, outputs):
        if xml is None:
            failed.append(number)
            continue
        try:
            scores.append(parse_musicxml(xml, page=number))
        except Exception as exc:  # music21 can choke on odd engine output
            failed.append(number)
            (workdir / f"parse-error-page{number:03d}.txt").write_text(repr(exc))
    if not scores:
        raise PipelineError(f"engine produced nothing usable for pages {page_numbers}")

    events, reports = normalize(merge_scores(scores))
    write_midi(events, out_midi, tempo_bpm=tempo_bpm)
    notify("assemble", len(rendered), len(rendered))
    return ConversionResult(midi_path=out_midi, events=events, reports=reports, pages=page_numbers,
                            failed_pages=failed, engine_name=engine.name)
