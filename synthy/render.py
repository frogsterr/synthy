"""Turn a PDF or image into grayscale page PNGs sized for the OMR engine.

Audiveris rejects images above 20 megapixels, and a 2550 px wide letter
page (about 300 dpi) is the sweet spot from the spike, so every page is
rendered to that width.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

DEFAULT_WIDTH = 2550
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def parse_page_range(text: str | None) -> list[int] | None:
    """Parse "1-3,5" into [1, 2, 3, 5]. Empty or None means all pages."""
    if text is None or not text.strip():
        return None
    pages: set[int] = set()
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            lo_s, hi_s = chunk.split("-", 1)
            lo, hi = _int(lo_s), _int(hi_s)
            if lo > hi:
                raise ValueError(f"bad page range {chunk!r}")
            pages.update(range(lo, hi + 1))
        else:
            pages.add(_int(chunk))
    return sorted(pages)


def _int(s: str) -> int:
    try:
        value = int(s.strip())
    except ValueError as exc:
        raise ValueError(f"bad page number {s!r}") from exc
    if value < 1:
        raise ValueError(f"page numbers start at 1, got {value}")
    return value


def render_pages(
    src: Path,
    out_dir: Path,
    pages: list[int] | None = None,
    width: int = DEFAULT_WIDTH,
) -> list[tuple[int, Path]]:
    """Render selected pages of `src` to `out_dir/pageNNN.png`.

    Returns (page_number, png_path) pairs in page order. Page numbers are
    1-based. Image inputs count as a single page.
    """
    src = Path(src)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = _open(src)
    try:
        total = doc.page_count
        wanted = pages if pages is not None else list(range(1, total + 1))
        bad = [p for p in wanted if p < 1 or p > total]
        if bad:
            raise ValueError(f"pages {bad} out of range; document has {total} page(s)")
        result = []
        for number in wanted:
            page = doc[number - 1]
            zoom = width / page.rect.width
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY)
            path = out_dir / f"page{number:03d}.png"
            pix.save(path)
            result.append((number, path))
        return result
    finally:
        doc.close()


def _open(src: Path) -> pymupdf.Document:
    if src.suffix.lower() in IMAGE_SUFFIXES:
        # Wrap the image in a one-page PDF so both inputs take the same path.
        img = pymupdf.open(src)
        pdf_bytes = img.convert_to_pdf()
        img.close()
        return pymupdf.open("pdf", pdf_bytes)
    return pymupdf.open(src)
