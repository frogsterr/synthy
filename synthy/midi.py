"""NoteEvents -> two-track Standard MIDI File.

Track 0 carries tempo and time-signature meta events, track 1 the right
hand on channel 0, track 2 the left hand on channel 1. Synthesia reads
each track as a hand.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import mido

from synthy.model import LEFT_HAND, RIGHT_HAND, NoteEvent

TICKS_PER_BEAT = 480
VELOCITY = 80
TRACKS = ((RIGHT_HAND, "Right Hand", 0), (LEFT_HAND, "Left Hand", 1))


def write_midi(events: list[NoteEvent], out: Path, tempo_bpm: int) -> None:
    mid = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)

    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo_bpm), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    meta.append(mido.MetaMessage("end_of_track", time=0))
    mid.tracks.append(meta)

    for staff, name, channel in TRACKS:
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name=name, time=0))
        track.append(mido.Message("program_change", program=0, channel=channel, time=0))
        timed: list[tuple[int, int, mido.Message]] = []  # (tick, order, msg); order 0 = off, 1 = on
        for ev in events:
            if ev.staff != staff:
                continue
            start = _ticks(ev.onset)
            end = max(start + 1, _ticks(ev.onset + ev.duration))
            timed.append((start, 1, mido.Message("note_on", note=ev.pitch, velocity=VELOCITY, channel=channel)))
            timed.append((end, 0, mido.Message("note_off", note=ev.pitch, velocity=0, channel=channel)))
        timed.sort(key=lambda t: (t[0], t[1]))
        last = 0
        for tick, _, msg in timed:
            msg.time = tick - last
            last = tick
            track.append(msg)
        track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(track)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    mid.save(out)


def _ticks(quarters: Fraction) -> int:
    return int(round(quarters * TICKS_PER_BEAT))
