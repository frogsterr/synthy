from pathlib import Path

import pymupdf
import pytest

from synthy.render import parse_page_range, render_pages


def _make_pdf(path: Path, n_pages: int) -> Path:
    doc = pymupdf.open()
    for i in range(n_pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"page {i + 1}")
    doc.save(path)
    return path


def _png_info(path: Path) -> tuple[int, int, int]:
    pix = pymupdf.Pixmap(str(path))
    return pix.width, pix.height, pix.n


def test_render_pdf_all_pages(tmp_path):
    pdf = _make_pdf(tmp_path / "in.pdf", 2)
    out = render_pages(pdf, tmp_path / "pages")
    assert [p for p, _ in out] == [1, 2]
    for _, png in out:
        w, h, n = _png_info(png)
        assert w == 2550
        assert h > w  # portrait preserved
        assert n == 1  # grayscale


def test_render_pdf_selected_pages(tmp_path):
    pdf = _make_pdf(tmp_path / "in.pdf", 3)
    out = render_pages(pdf, tmp_path / "pages", pages=[3])
    assert [p for p, _ in out] == [3]
    assert out[0][1].name == "page003.png"


def test_render_pdf_page_out_of_range(tmp_path):
    pdf = _make_pdf(tmp_path / "in.pdf", 1)
    with pytest.raises(ValueError):
        render_pages(pdf, tmp_path / "pages", pages=[2])


def test_render_image_input(tmp_path):
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 400, 600), False)
    pix.clear_with(255)
    src = tmp_path / "photo.png"
    pix.save(src)
    out = render_pages(src, tmp_path / "pages")
    assert [p for p, _ in out] == [1]
    w, h, n = _png_info(out[0][1])
    assert (w, n) == (2550, 1)


def test_parse_page_range():
    assert parse_page_range("1-3,5") == [1, 2, 3, 5]
    assert parse_page_range(" 4 , 2-2 ") == [2, 4]
    assert parse_page_range("") is None
    assert parse_page_range(None) is None
    with pytest.raises(ValueError):
        parse_page_range("3-1")
    with pytest.raises(ValueError):
        parse_page_range("a")
