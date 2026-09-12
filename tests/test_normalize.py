from fractions import Fraction as F

from synthy.model import LEFT_HAND, RIGHT_HAND, NoteEvent, RawMeasure, RawNote, RawScore
from synthy.normalize import SUSPECT_MAX, SUSPECT_MIN, normalize


def note(staff, onset, dur, pitch=60, tie_start=False, tie_stop=False):
    return RawNote(staff, F(onset), F(dur), pitch, tie_start, tie_stop)


def measure(index, notes, ts=4, page=1):
    m = RawMeasure(index=index, page=page, time_signature=None if ts is None else F(ts), notes=notes)
    for staff in (RIGHT_HAND, LEFT_HAND):
        ends = [n.onset + n.duration for n in notes if n.staff == staff]
        m.staff_lengths[staff] = max(ends) if ends else F(0)
    return m


def events_of(staff, events):
    return sorted((e.onset, e.duration, e.pitch) for e in events if e.staff == staff)


def test_overlong_staff_scaled_and_flagged():
    m = measure(0, [note(RIGHT_HAND, 0, 2, 60), note(RIGHT_HAND, 2, 2, 62), note(RIGHT_HAND, 4, 2, 64),
                    note(LEFT_HAND, 0, 4, 48)])
    events, reports = normalize(RawScore([m]))
    assert events_of(RIGHT_HAND, events) == [(F(0), F(4, 3), 60), (F(4, 3), F(4, 3), 62), (F(8, 3), F(4, 3), 64)]
    assert events_of(LEFT_HAND, events) == [(F(0), F(4), 48)]
    r = reports[0]
    assert r.suspect is True
    assert r.expected == 4
    assert r.raw == {RIGHT_HAND: F(6), LEFT_HAND: F(4)}
    assert r.scale == {RIGHT_HAND: F(2, 3), LEFT_HAND: F(1)}


def test_small_deviation_scaled_but_not_flagged():
    m = measure(0, [note(RIGHT_HAND, 0, 4.5, 60), note(LEFT_HAND, 0, 4, 48)])
    events, reports = normalize(RawScore([m]))
    assert events_of(RIGHT_HAND, events) == [(F(0), F(4), 60)]
    assert reports[0].suspect is False
    assert SUSPECT_MIN < F(4) / F(4.5) < SUSPECT_MAX


def test_missing_time_signature_uses_mode_of_lengths():
    ms = [
        measure(0, [note(RIGHT_HAND, 0, 4), note(LEFT_HAND, 0, 4)], ts=None),
        measure(1, [note(RIGHT_HAND, 0, 7), note(LEFT_HAND, 0, 4)], ts=None),
        measure(2, [note(RIGHT_HAND, 0, 4), note(LEFT_HAND, 0, 4)], ts=None),
    ]
    events, reports = normalize(RawScore(ms))
    assert [r.expected for r in reports] == [F(4), F(4), F(4)]
    assert [r.suspect for r in reports] == [False, True, False]
    assert events_of(RIGHT_HAND, events)[1] == (F(4), F(4), 60)


def test_time_signature_applies_forwards_until_the_next_one():
    ms = [
        measure(0, [note(RIGHT_HAND, 0, 3), note(LEFT_HAND, 0, 3)], ts=None),
        measure(1, [note(RIGHT_HAND, 0, 3), note(LEFT_HAND, 0, 3)], ts=None),
        measure(2, [note(RIGHT_HAND, 0, 3), note(LEFT_HAND, 0, 3)], ts=3),
        measure(3, [note(RIGHT_HAND, 0, 2), note(LEFT_HAND, 0, 2)], ts=2),
        measure(4, [note(RIGHT_HAND, 0, 2), note(LEFT_HAND, 0, 2)], ts=None),
    ]
    _, reports = normalize(RawScore(ms))
    assert [r.expected for r in reports] == [F(3), F(3), F(3), F(2), F(2)]
    assert not any(r.suspect for r in reports)


def test_measures_before_first_time_signature_trust_their_own_lengths():
    # opening TS missed by the engine, a genuine 2/4 change arrives later
    ms = [measure(i, [note(RIGHT_HAND, 0, 4), note(LEFT_HAND, 0, 4)], ts=None) for i in range(4)]
    ms[1] = measure(1, [note(RIGHT_HAND, 0, 7), note(LEFT_HAND, 0, 4)], ts=None)
    ms += [measure(4, [note(RIGHT_HAND, 0, 2), note(LEFT_HAND, 0, 2)], ts=2),
           measure(5, [note(RIGHT_HAND, 0, 2), note(LEFT_HAND, 0, 2)], ts=None)]
    _, reports = normalize(RawScore(ms))
    assert [r.expected for r in reports] == [F(4)] * 4 + [F(2), F(2)]
    assert [r.suspect for r in reports] == [False, True, False, False, False, False]


def test_empty_measures_before_first_time_signature_borrow_it():
    ms = [measure(0, [], ts=None), measure(1, [note(RIGHT_HAND, 0, 3), note(LEFT_HAND, 0, 3)], ts=3)]
    _, reports = normalize(RawScore(ms))
    assert [r.expected for r in reports] == [F(3), F(3)]


def test_absolute_onsets_accumulate_expected_lengths():
    ms = [
        measure(0, [note(RIGHT_HAND, 0, 4, 60), note(LEFT_HAND, 0, 4, 48)], ts=4),
        measure(1, [note(RIGHT_HAND, 0, 2, 62), note(LEFT_HAND, 0, 2, 50)], ts=2),
        measure(2, [note(RIGHT_HAND, 1, 1, 64), note(LEFT_HAND, 0, 2, 52)], ts=None),
    ]
    events, _ = normalize(RawScore(ms))
    assert events_of(RIGHT_HAND, events) == [(F(0), F(4), 60), (F(4), F(2), 62), (F(7), F(1), 64)]


def test_ties_merge_across_barline():
    ms = [
        measure(0, [note(RIGHT_HAND, 0, 4, 60, tie_start=True), note(LEFT_HAND, 0, 4, 48)]),
        measure(1, [note(RIGHT_HAND, 0, 2, 60, tie_stop=True), note(RIGHT_HAND, 2, 2, 62), note(LEFT_HAND, 0, 4, 48)]),
    ]
    events, _ = normalize(RawScore(ms))
    assert events_of(RIGHT_HAND, events) == [(F(0), F(6), 60), (F(6), F(2), 62)]


def test_tie_stop_without_start_stays_a_note():
    ms = [measure(0, [note(RIGHT_HAND, 0, 4, 60, tie_stop=True), note(LEFT_HAND, 0, 4, 48)])]
    events, _ = normalize(RawScore(ms))
    assert events_of(RIGHT_HAND, events) == [(F(0), F(4), 60)]


def test_same_note_in_two_voices_becomes_one_event():
    ms = [measure(0, [note(RIGHT_HAND, 0, 1, 60), note(RIGHT_HAND, 0, 2, 60), note(RIGHT_HAND, 2, 2, 60),
                      note(LEFT_HAND, 0, 4, 48)])]
    events, _ = normalize(RawScore(ms))
    assert events_of(RIGHT_HAND, events) == [(F(0), F(2), 60), (F(2), F(2), 60)]


def test_unison_across_hands_keeps_the_earlier_hand():
    ms = [measure(0, [note(RIGHT_HAND, 0, 4, 60), note(LEFT_HAND, 0, 2, 60), note(LEFT_HAND, 2, 2, 48)])]
    events, _ = normalize(RawScore(ms))
    assert events_of(RIGHT_HAND, events) == [(F(0), F(4), 60)]
    assert events_of(LEFT_HAND, events) == [(F(2), F(2), 48)]


def test_grace_notes_dropped():
    ms = [measure(0, [note(RIGHT_HAND, 0, 0, 74), note(RIGHT_HAND, 0, 4, 72), note(LEFT_HAND, 0, 4, 48)])]
    events, _ = normalize(RawScore(ms))
    assert events_of(RIGHT_HAND, events) == [(F(0), F(4), 72)]


def test_empty_staff_not_flagged_and_reported_as_zero():
    ms = [measure(0, [note(RIGHT_HAND, 0, 4, 60)])]
    events, reports = normalize(RawScore(ms))
    assert reports[0].suspect is False
    assert reports[0].scale[LEFT_HAND] == F(1)
    assert events_of(LEFT_HAND, events) == []


def test_no_time_signature_and_no_notes_defaults_to_four():
    ms = [measure(0, [], ts=None)]
    _, reports = normalize(RawScore(ms))
    assert reports[0].expected == F(4)
