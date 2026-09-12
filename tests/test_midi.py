from fractions import Fraction as F

import mido

from synthy.midi import TICKS_PER_BEAT, write_midi
from synthy.model import LEFT_HAND, RIGHT_HAND, NoteEvent


def ev(staff, onset, dur, pitch):
    return NoteEvent(onset=F(onset), staff=staff, pitch=pitch, duration=F(dur))


def _abs_msgs(track):
    t = 0
    out = []
    for msg in track:
        t += msg.time
        out.append((t, msg))
    return out


def test_three_tracks_with_names_and_tempo(tmp_path):
    out = tmp_path / "x.mid"
    write_midi([ev(RIGHT_HAND, 0, 1, 60), ev(LEFT_HAND, 0, 1, 48)], out, tempo_bpm=90)
    mid = mido.MidiFile(out)
    assert mid.type == 1
    assert mid.ticks_per_beat == TICKS_PER_BEAT == 480
    assert len(mid.tracks) == 3
    tempos = [m for m in mid.tracks[0] if m.type == "set_tempo"]
    assert tempos and tempos[0].tempo == mido.bpm2tempo(90)
    names = [m.name for t in mid.tracks[1:] for m in t if m.type == "track_name"]
    assert names == ["Right Hand", "Left Hand"]


def test_channels_and_ticks(tmp_path):
    out = tmp_path / "x.mid"
    write_midi([ev(RIGHT_HAND, F(3, 2), 1, 60), ev(LEFT_HAND, 0, F(1, 2), 48)], out, tempo_bpm=120)
    mid = mido.MidiFile(out)
    right = [(t, m) for t, m in _abs_msgs(mid.tracks[1]) if m.type in ("note_on", "note_off")]
    left = [(t, m) for t, m in _abs_msgs(mid.tracks[2]) if m.type in ("note_on", "note_off")]
    assert right[0] == (720, mido.Message("note_on", note=60, velocity=80, channel=0, time=right[0][1].time))
    assert right[1][0] == 1200 and right[1][1].type == "note_off"
    assert left[0][1].channel == 1
    assert left[1][0] == 240


def test_note_off_precedes_note_on_at_same_tick(tmp_path):
    out = tmp_path / "x.mid"
    write_midi([ev(RIGHT_HAND, 0, 1, 60), ev(RIGHT_HAND, 1, 1, 60)], out, tempo_bpm=120)
    mid = mido.MidiFile(out)
    at_480 = [m.type for t, m in _abs_msgs(mid.tracks[1]) if t == 480 and m.type.startswith("note")]
    assert at_480 == ["note_off", "note_on"]


def test_tiny_note_still_has_one_tick(tmp_path):
    out = tmp_path / "x.mid"
    write_midi([ev(RIGHT_HAND, 0, F(1, 10000), 60)], out, tempo_bpm=120)
    mid = mido.MidiFile(out)
    notes = [(t, m.type) for t, m in _abs_msgs(mid.tracks[1]) if m.type.startswith("note")]
    assert notes == [(0, "note_on"), (1, "note_off")]


def test_empty_events_writes_valid_file(tmp_path):
    out = tmp_path / "x.mid"
    write_midi([], out, tempo_bpm=80)
    assert len(mido.MidiFile(out).tracks) == 3
