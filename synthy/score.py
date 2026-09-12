"""MusicXML -> RawScore.

Audiveris writes one MusicXML file per page with one part per staff
(treble first). This module reads that into the engine-independent
`RawScore` without interpreting rhythm: raw onsets, raw durations and the
raw length of each staff in each measure are preserved so the
normalizer can decide what to do with them.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from music21 import chord, converter, meter, note, stream

from synthy.model import LEFT_HAND, RIGHT_HAND, RawMeasure, RawNote, RawScore

STAFF_ORDER = (RIGHT_HAND, LEFT_HAND)


def parse_musicxml(path: Path, page: int, first_index: int = 0) -> RawScore:
    """Parse a MusicXML (.xml/.musicxml/.mxl) file for one page."""
    work = converter.parse(str(path))
    parts = list(work.parts) if isinstance(work, stream.Score) else [work]
    parts = parts[: len(STAFF_ORDER)]
    per_part = [list(part.getElementsByClass(stream.Measure)) for part in parts]
    n_measures = max((len(ms) for ms in per_part), default=0)

    measures: list[RawMeasure] = []
    for i in range(n_measures):
        raw = RawMeasure(index=first_index + i, page=page, time_signature=None)
        for staff, part_measures in zip(STAFF_ORDER, per_part):
            if i >= len(part_measures):
                continue
            measure = part_measures[i]
            ts = _time_signature(measure)
            if ts is not None and raw.time_signature is None:
                raw.time_signature = ts
            length = Fraction(0)
            for element in measure.recurse().notes:
                onset = _frac(element.getOffsetInHierarchy(measure))
                duration = _frac(element.duration.quarterLength)
                length = max(length, onset + duration)
                for pitch, tie_start, tie_stop in _pitches(element):
                    raw.notes.append(
                        RawNote(staff=staff, onset=onset, duration=duration, pitch=pitch,
                                tie_start=tie_start, tie_stop=tie_stop)
                    )
            raw.staff_lengths[staff] = length
        measures.append(raw)
    return RawScore(measures=measures)


def merge_scores(scores: list[RawScore]) -> RawScore:
    """Concatenate per-page scores, renumbering measure indexes."""
    merged = RawScore()
    for score in scores:
        for measure in score.measures:
            measure.index = len(merged.measures)
            merged.measures.append(measure)
    return merged


def _time_signature(measure: stream.Measure) -> Fraction | None:
    for ts in measure.getElementsByClass(meter.TimeSignature):
        return _frac(ts.barDuration.quarterLength)
    return None


def _pitches(element) -> list[tuple[int, bool, bool]]:
    if isinstance(element, chord.Chord):
        out = []
        for n in element.notes:
            tie_start, tie_stop = _tie(n.tie or element.tie)
            out.append((n.pitch.midi, tie_start, tie_stop))
        return out
    if isinstance(element, note.Note):
        tie_start, tie_stop = _tie(element.tie)
        return [(element.pitch.midi, tie_start, tie_stop)]
    return []


def _tie(t) -> tuple[bool, bool]:
    if t is None:
        return False, False
    return t.type in ("start", "continue"), t.type in ("stop", "continue")


def _frac(value) -> Fraction:
    return Fraction(value).limit_denominator(64)
