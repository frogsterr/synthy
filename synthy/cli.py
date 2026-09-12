"""Command line: `synthy convert score.pdf -o score.mid --tempo 80 --pages 1-3` and `synthy serve`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from synthy.engine import Engine
from synthy.pipeline import DEFAULT_TEMPO, PipelineError, convert
from synthy.render import parse_page_range


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synthy", description="Sheet music to Synthesia-ready MIDI")
    sub = parser.add_subparsers(dest="command", required=True)

    c = sub.add_parser("convert", help="convert a PDF or image to MIDI")
    c.add_argument("input", type=Path)
    c.add_argument("-o", "--output", type=Path, help="output .mid (default: input name with .mid)")
    c.add_argument("--tempo", type=int, default=DEFAULT_TEMPO, help="beats per minute")
    c.add_argument("--pages", type=str, default=None, help='page range like "1-3,5"')
    c.add_argument("--workdir", type=Path, default=None, help="keep intermediate files here")

    s = sub.add_parser("serve", help="run the local web app")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: list[str] | None = None, engine: Engine | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "convert":
        return _convert(args, engine)
    if args.command == "serve":
        import uvicorn

        from synthy.web.app import create_app

        uvicorn.run(create_app(), host=args.host, port=args.port)
        return 0
    return 2


def _convert(args, engine: Engine | None) -> int:
    if args.tempo < 20 or args.tempo > 300:
        print("tempo must be between 20 and 300 BPM", file=sys.stderr)
        return 2
    try:
        pages = parse_page_range(args.pages)
    except ValueError as exc:
        print(f"bad --pages: {exc}", file=sys.stderr)
        return 2
    output = args.output or args.input.with_suffix(".mid")

    def progress(stage: str, done: int, total: int) -> None:
        print(f"[{stage}] {done}/{total}" if total else f"[{stage}]", file=sys.stderr)

    try:
        result = convert(args.input, output, tempo_bpm=args.tempo, pages=pages, engine=engine,
                         workdir=args.workdir, progress=progress)
    except (PipelineError, ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(format_report(result))
    return 0


def format_report(result) -> str:
    lines = [f"wrote {result.midi_path}",
             f"engine {result.engine_name}, pages {result.pages}, measures {len(result.reports)}"]
    if result.failed_pages:
        lines.append(f"pages with no output: {result.failed_pages}")
    suspects = result.suspect_measures
    if suspects:
        lines.append(f"{len(suspects)} suspect measure(s) (raw length vs expected, per hand):")
        for r in suspects:
            raw = ", ".join(f"{'RH' if s == 1 else 'LH'} {float(v):g}" for s, v in sorted(r.raw.items()))
            lines.append(f"  measure {r.index + 1} (page {r.page}): expected {float(r.expected):g}; {raw}")
    else:
        lines.append("no suspect measures")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
