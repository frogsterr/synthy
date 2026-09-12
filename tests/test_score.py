from fractions import Fraction

from synthy.model import LEFT_HAND, RIGHT_HAND
from synthy.score import merge_scores, parse_musicxml

from .helpers import write_score


def _notes(measure, staff):
    return sorted((n.onset, n.pitch, n.duration) for n in measure.notes if n.staff == staff)


def test_two_staves_map_to_hands(tmp_path):
    path = write_score(tmp_path / "s.musicxml", [["C5/1.0", "D5/1.0"]], [["C3/2.0"]])
    score = parse_musicxml(path, page=1)
    assert len(score.measures) == 1
    m = score.measures[0]
    assert _notes(m, RIGHT_HAND) == [(Fraction(0), 72, Fraction(1)), (Fraction(1), 74, Fraction(1))]
    assert _notes(m, LEFT_HAND) == [(Fraction(0), 48, Fraction(2))]
    assert m.page == 1


def test_chords_expand_and_rests_skipped(tmp_path):
    path = write_score(tmp_path / "s.musicxml", [["r/1.0", "C4+E4+G4/1.0"]], [["r/2.0"]])
    m = parse_musicxml(path, page=1).measures[0]
    assert _notes(m, RIGHT_HAND) == [(Fraction(1), 60, Fraction(1)), (Fraction(1), 64, Fraction(1)), (Fraction(1), 67, Fraction(1))]
    assert _notes(m, LEFT_HAND) == []


def test_raw_staff_lengths_reflect_content(tmp_path):
    # Treble is over-long (6 quarters), bass is 2 quarters, in a 4/4 measure.
    path = write_score(tmp_path / "s.musicxml", [["C4/2.0", "D4/2.0", "E4/2.0"]], [["C3/2.0"]])
    m = parse_musicxml(path, page=1).measures[0]
    assert m.staff_lengths[RIGHT_HAND] == Fraction(6)
    assert m.staff_lengths[LEFT_HAND] == Fraction(2)
    assert m.time_signature == Fraction(4)


def test_time_signatures_in_quarters(tmp_path):
    for ts, quarters in (("2/4", 2), ("6/8", 3), ("3/2", 6)):
        path = write_score(tmp_path / f"{ts.replace('/', '_')}.musicxml", [["C4/1.0"]], [["C3/1.0"]], ts=ts)
        assert parse_musicxml(path, page=1).measures[0].time_signature == Fraction(quarters)


def test_missing_time_signature_is_none(tmp_path):
    path = write_score(tmp_path / "s.musicxml", [["C4/1.0"], ["D4/1.0"]], [["C3/1.0"], ["C3/1.0"]], ts=None)
    score = parse_musicxml(path, page=1)
    assert [m.time_signature for m in score.measures] == [None, None]


def test_time_signature_only_on_measure_where_written(tmp_path):
    path = write_score(tmp_path / "s.musicxml", [["C4/1.0"], ["D4/1.0"], ["E4/1.0"]], [["C3/1.0"]] * 3, ts="3/4", ts_at=1)
    score = parse_musicxml(path, page=1)
    assert [m.time_signature for m in score.measures] == [None, Fraction(3), None]


def test_tie_flags(tmp_path):
    path = write_score(tmp_path / "s.musicxml", [["C4/4.0~"], ["~C4/4.0"]], [["C3/4.0"], ["C3/4.0"]])
    score = parse_musicxml(path, page=1)
    first = [n for n in score.measures[0].notes if n.staff == RIGHT_HAND][0]
    second = [n for n in score.measures[1].notes if n.staff == RIGHT_HAND][0]
    assert (first.tie_start, first.tie_stop) == (True, False)
    assert (second.tie_start, second.tie_stop) == (False, True)


def test_grace_notes_have_zero_duration(tmp_path):
    path = write_score(tmp_path / "s.musicxml", [["g:D5", "C5/1.0"]], [["C3/1.0"]])
    m = parse_musicxml(path, page=1).measures[0]
    durations = {n.pitch: n.duration for n in m.notes if n.staff == RIGHT_HAND}
    assert durations[74] == 0
    assert durations[72] == 1


def test_merge_scores_renumbers_and_keeps_pages(tmp_path):
    a = parse_musicxml(write_score(tmp_path / "a.musicxml", [["C4/1.0"], ["C4/1.0"]], [["C3/1.0"]] * 2), page=1)
    b = parse_musicxml(write_score(tmp_path / "b.musicxml", [["D4/1.0"]], [["D3/1.0"]]), page=3)
    merged = merge_scores([a, b])
    assert [(m.index, m.page) for m in merged.measures] == [(0, 1), (1, 1), (2, 3)]


def test_single_staff_score_is_treated_as_right_hand(tmp_path):
    from music21 import stream, note, meter
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    m.append(meter.TimeSignature("4/4"))
    m.append(note.Note("E4", quarterLength=4))
    p.append(m)
    s.append(p)
    path = tmp_path / "one.musicxml"
    s.write("musicxml", fp=path)
    score = parse_musicxml(path, page=1)
    assert [n.staff for n in score.measures[0].notes] == [RIGHT_HAND]
