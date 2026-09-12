"""Data model shared by the pipeline stages.

All onsets and durations are in quarter notes as `fractions.Fraction`
until MIDI ticks are computed. Staff 1 is the right hand, staff 2 the
left hand, everywhere in the project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

RIGHT_HAND = 1
LEFT_HAND = 2


@dataclass
class RawNote:
    staff: int
    onset: Fraction
    duration: Fraction
    pitch: int
    tie_start: bool = False
    tie_stop: bool = False


@dataclass
class RawMeasure:
    index: int
    page: int
    time_signature: Fraction | None
    notes: list[RawNote] = field(default_factory=list)
    staff_lengths: dict[int, Fraction] = field(default_factory=dict)


@dataclass
class RawScore:
    measures: list[RawMeasure] = field(default_factory=list)


@dataclass(order=True)
class NoteEvent:
    onset: Fraction
    staff: int
    pitch: int
    duration: Fraction


@dataclass
class MeasureReport:
    index: int
    page: int
    expected: Fraction
    raw: dict[int, Fraction]
    scale: dict[int, Fraction]
    suspect: bool


@dataclass
class ConversionResult:
    midi_path: Path
    events: list[NoteEvent]
    reports: list[MeasureReport]
    pages: list[int]
    failed_pages: list[int]
    engine_name: str

    @property
    def suspect_measures(self) -> list[MeasureReport]:
        return [r for r in self.reports if r.suspect]
