"""Build small MusicXML files with music21 for tests.

Measure spec strings: "C4/1.0" note, "C4+E4/0.5" chord, "r/1.0" rest,
"C4/1.0~" starts a tie, "~C4/1.0" ends one, "g:D5" is a grace note.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from music21 import chord, clef, meter, note, stream, tie


def _element(spec: str):
    tie_start = spec.endswith("~")
    tie_stop = spec.startswith("~")
    spec = spec.strip("~")
    if spec.startswith("g:"):
        n = note.Note(spec[2:])
        n = n.getGrace()
        return n
    name, dur = spec.split("/")
    ql = Fraction(dur)
    if name == "r":
        return note.Rest(quarterLength=ql)
    if "+" in name:
        el = chord.Chord(name.split("+"), quarterLength=ql)
    else:
        el = note.Note(name, quarterLength=ql)
    if tie_start and tie_stop:
        el.tie = tie.Tie("continue")
    elif tie_start:
        el.tie = tie.Tie("start")
    elif tie_stop:
        el.tie = tie.Tie("stop")
    return el


def build_score(
    treble: list[list[str]],
    bass: list[list[str]],
    ts: str | None = "4/4",
    ts_at: int = 0,
) -> stream.Score:
    """Two-staff score. `ts` is placed in measure `ts_at` (0-based)."""
    score = stream.Score()
    for staff_no, (measures, clf) in enumerate(((treble, clef.TrebleClef()), (bass, clef.BassClef())), start=1):
        part = stream.Part(id=f"P{staff_no}")
        for i, specs in enumerate(measures):
            m = stream.Measure(number=i + 1)
            if i == 0:
                m.append(clf)
            if ts and i == ts_at:
                m.append(meter.TimeSignature(ts))
            for spec in specs:
                m.append(_element(spec))
            part.append(m)
        score.append(part)
    return score


def write_score(path: Path, treble, bass, ts: str | None = "4/4", ts_at: int = 0) -> Path:
    build_score(treble, bass, ts, ts_at).write("musicxml", fp=path)
    return path
