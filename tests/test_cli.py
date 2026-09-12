import pymupdf

from synthy.cli import main

from .fake_engine import FakeEngine


def _pdf(path, n=1):
    doc = pymupdf.open()
    for _ in range(n):
        doc.new_page(width=595, height=842)
    doc.save(path)
    return path


def test_convert_writes_default_output(tmp_path, capsys):
    src = _pdf(tmp_path / "piece.pdf")
    code = main(["convert", str(src), "--workdir", str(tmp_path / "w")], engine=FakeEngine())
    assert code == 0
    assert (tmp_path / "piece.mid").exists()
    out = capsys.readouterr().out
    assert "no suspect measures" in out
    assert "measures 2" in out


def test_convert_with_pages_and_output(tmp_path):
    src = _pdf(tmp_path / "piece.pdf", 3)
    code = main(["convert", str(src), "-o", str(tmp_path / "x.mid"), "--pages", "2", "--tempo", "120",
                 "--workdir", str(tmp_path / "w")], engine=FakeEngine())
    assert code == 0
    assert (tmp_path / "x.mid").exists()


def test_bad_pages_is_usage_error(tmp_path, capsys):
    src = _pdf(tmp_path / "piece.pdf")
    assert main(["convert", str(src), "--pages", "5-1"], engine=FakeEngine()) == 2
    assert "bad --pages" in capsys.readouterr().err


def test_bad_tempo_is_usage_error(tmp_path):
    src = _pdf(tmp_path / "piece.pdf")
    assert main(["convert", str(src), "--tempo", "5"], engine=FakeEngine()) == 2


def test_all_pages_failed_is_error(tmp_path, capsys):
    src = _pdf(tmp_path / "piece.pdf")
    assert main(["convert", str(src), "--workdir", str(tmp_path / "w")], engine=FakeEngine(fail_pages={1})) == 1
    assert "error:" in capsys.readouterr().err
