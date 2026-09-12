"""Snap every measure to its time signature and flag the suspicious ones.

Both OMR engines in the spike got pitches mostly right but produced
measures 4.5 to 9 quarters long where 4 were expected. Rather than trust
any single note duration, each staff of each measure is time-scaled so
that its raw length equals the expected measure length. Scale factors far
from 1 mark the measure as suspect.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction

from synthy.model import LEFT_HAND, RIGHT_HAND, MeasureReport, NoteEvent, RawMeasure, RawScore

SUSPECT_MIN = Fraction(4, 5)      # scale below this (raw > 125% of expected) is suspect
SUSPECT_MAX = Fraction(5, 4)      # scale above this (raw < 80% of expected) is suspect
DEFAULT_MEASURE = Fraction(4)     # when nothing at all is known
TIE_TOLERANCE = Fraction(1, 16)   # quarters; how far apart a tied pair may be
UNISON_TOLERANCE = Fraction(1, 16)  # quarters; same pitch struck this close is one key press
STAVES = (RIGHT_HAND, LEFT_HAND)


def normalize(score: RawScore) -> tuple[list[NoteEvent], list[MeasureReport]]:
    expected = _expected_lengths(score)
    events: list[NoteEvent] = []
    pending: list[tuple[NoteEvent, bool, bool]] = []  # (event, tie_start, tie_stop)
    reports: list[MeasureReport] = []
    start = Fraction(0)

    for measure, target in zip(score.measures, expected):
        raw: dict[int, Fraction] = {}
        scale: dict[int, Fraction] = {}
        for staff in STAVES:
            length = measure.staff_lengths.get(staff, Fraction(0))
            raw[staff] = length
            scale[staff] = target / length if length > 0 else Fraction(1)
        suspect = any(
            raw[s] > 0 and not (SUSPECT_MIN <= scale[s] <= SUSPECT_MAX) for s in STAVES
        )
        reports.append(MeasureReport(index=measure.index, page=measure.page, expected=target,
                                     raw=raw, scale=scale, suspect=suspect))
        for n in measure.notes:
            if n.duration <= 0:
                continue  # grace note
            k = scale.get(n.staff, Fraction(1))
            ev = NoteEvent(onset=start + n.onset * k, staff=n.staff, pitch=n.pitch, duration=n.duration * k)
            pending.append((ev, n.tie_start, n.tie_stop))
        start += target

    events = _merge_unisons(_merge_ties(pending))
    events.sort()
    return events, reports


def _expected_lengths(score: RawScore) -> list[Fraction]:
    """Expected length per measure: the last TS seen. Measures before the first TS
    use the mode of their own raw lengths; a later TS is borrowed only when they
    carry no notes at all, because OMR often misses the opening TS and a TS found
    pages later may belong to a meter change."""
    out: list[Fraction | None] = []
    current: Fraction | None = None
    for m in score.measures:
        if m.time_signature is not None:
            current = m.time_signature
        out.append(current)
    lead = sum(1 for v in out if v is None)
    if lead:
        first_known = out[lead] if lead < len(out) else None
        fill = _mode_length(score.measures[:lead]) or first_known or DEFAULT_MEASURE
        out[:lead] = [fill] * lead
    return out  # type: ignore[return-value]


def _mode_length(measures: list[RawMeasure]) -> Fraction | None:
    """Mode of the shorter staff per measure: engine mistakes mostly add duration."""
    counts: Counter[Fraction] = Counter()
    for m in measures:
        lengths = [v for v in m.staff_lengths.values() if v > 0]
        if lengths:
            counts[_round_half(min(lengths))] += 1
    if not counts:
        return None
    best = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))
    return best[0]


def _round_half(value: Fraction) -> Fraction:
    return Fraction(round(value * 2), 2)


def _merge_unisons(events: list[NoteEvent]) -> list[NoteEvent]:
    """One key cannot be struck twice at once: a note shared by two voices or both
    staves becomes a single event that lasts as long as the longer of the two."""
    events.sort(key=lambda e: (e.pitch, e.onset, e.staff))
    result: list[NoteEvent] = []
    for ev in events:
        prev = result[-1] if result else None
        if prev is not None and prev.pitch == ev.pitch and ev.onset - prev.onset <= UNISON_TOLERANCE:
            prev.duration = max(prev.onset + prev.duration, ev.onset + ev.duration) - prev.onset
            continue
        result.append(ev)
    return result


def _merge_ties(pending: list[tuple[NoteEvent, bool, bool]]) -> list[NoteEvent]:
    """Extend a tie-start note by every tie-stop note of the same staff/pitch that touches it."""
    pending.sort(key=lambda t: (t[0].staff, t[0].pitch, t[0].onset))
    result: list[NoteEvent] = []
    open_by_key: dict[tuple[int, int], NoteEvent] = {}
    for ev, tie_start, tie_stop in pending:
        key = (ev.staff, ev.pitch)
        prev = open_by_key.get(key)
        if tie_stop and prev is not None and abs(prev.onset + prev.duration - ev.onset) <= TIE_TOLERANCE:
            prev.duration = ev.onset + ev.duration - prev.onset
            if not tie_start:
                del open_by_key[key]
            continue
        result.append(ev)
        if tie_start:
            open_by_key[key] = ev
        else:
            open_by_key.pop(key, None)
    return result
