from fractions import Fraction

from synthy.model import LEFT_HAND, RIGHT_HAND, NoteEvent, RawMeasure, RawNote, RawScore


def test_raw_score_constructs():
    note = RawNote(staff=RIGHT_HAND, onset=Fraction(0), duration=Fraction(1), pitch=60)
    measure = RawMeasure(index=0, page=1, time_signature=Fraction(4), notes=[note])
    score = RawScore(measures=[measure])
    assert score.measures[0].notes[0].pitch == 60
    assert LEFT_HAND == 2


def test_note_events_sort_by_onset():
    later = NoteEvent(onset=Fraction(2), staff=1, pitch=60, duration=Fraction(1))
    earlier = NoteEvent(onset=Fraction(1), staff=2, pitch=48, duration=Fraction(1))
    assert sorted([later, earlier]) == [earlier, later]
