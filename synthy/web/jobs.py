"""In-process job store: one background thread per conversion."""

from __future__ import annotations

import threading
import traceback
import uuid
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from synthy.engine import Engine
from synthy.model import ConversionResult
from synthy.pipeline import convert

STAGE_TEXT = {
    "render": "Rendering pages",
    "transcribe": "Reading the score",
    "assemble": "Building the MIDI",
}


@dataclass
class Job:
    id: str
    src: Path
    stem: str
    tempo: int
    pages: list[int] | None
    workdir: Path
    status: str = "queued"          # queued | running | done | error
    stage: str = ""
    done: int = 0
    total: int = 0
    message: str = ""
    result: ConversionResult | None = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def midi_path(self) -> Path:
        return self.workdir / f"{self.stem}.mid"

    def to_dict(self) -> dict:
        with self.lock:
            out = {
                "id": self.id, "status": self.status, "stage": self.stage,
                "stage_text": STAGE_TEXT.get(self.stage, ""), "done": self.done, "total": self.total,
                "message": self.message, "name": self.stem, "tempo": self.tempo,
            }
            if self.result is not None:
                out["report"] = _report(self.result)
        return out


def _f(x: Fraction) -> float:
    return round(float(x), 3)


def _report(r: ConversionResult) -> dict:
    return {
        "engine": r.engine_name,
        "pages": r.pages,
        "failed_pages": r.failed_pages,
        "measures": [
            {"index": m.index, "page": m.page, "suspect": m.suspect, "expected": _f(m.expected),
             "raw": {str(k): _f(v) for k, v in m.raw.items()}}
            for m in r.reports
        ],
    }


def notes_payload(job: Job) -> dict:
    """Everything the in-browser player needs, in beats (quarter notes)."""
    r = job.result
    assert r is not None
    measures = []
    start = Fraction(0)
    for m in r.reports:
        measures.append({"index": m.index, "page": m.page, "start": _f(start),
                         "length": _f(m.expected), "suspect": m.suspect})
        start += m.expected
    return {
        "name": job.stem,
        "tempo": job.tempo,
        "length": _f(start),
        "notes": [
            {"hand": ev.staff, "pitch": ev.pitch, "onset": _f(ev.onset), "duration": _f(ev.duration)}
            for ev in r.events
        ],
        "measures": measures,
    }


class JobStore:
    def __init__(self, root: Path, engine: Engine | None = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.engine = engine
        self._jobs: dict[str, Job] = {}

    def create(self, filename: str, data: bytes, tempo: int, pages: list[int] | None) -> Job:
        job_id = uuid.uuid4().hex[:12]
        workdir = self.root / job_id
        workdir.mkdir(parents=True)
        safe_name = Path(filename).name or "score.pdf"
        src = workdir / safe_name
        src.write_bytes(data)
        job = Job(id=job_id, src=src, stem=Path(safe_name).stem, tempo=tempo, pages=pages, workdir=workdir)
        self._jobs[job_id] = job
        threading.Thread(target=self._run, args=(job,), daemon=True).start()
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def _run(self, job: Job) -> None:
        def progress(stage: str, done: int, total: int) -> None:
            with job.lock:
                job.stage, job.done, job.total = stage, done, total

        with job.lock:
            job.status = "running"
        try:
            result = convert(job.src, job.midi_path, tempo_bpm=job.tempo, pages=job.pages,
                             engine=self.engine, workdir=job.workdir / "work", progress=progress)
            with job.lock:
                job.result, job.status = result, "done"
        except Exception as exc:  # report anything to the page instead of dying silently
            (job.workdir / "error.txt").write_text(traceback.format_exc())
            with job.lock:
                job.status, job.message = "error", str(exc)
