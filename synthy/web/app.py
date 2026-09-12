"""FastAPI app: upload a score, poll the job, download the MIDI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from synthy.engine import Engine
from synthy.pipeline import DEFAULT_TEMPO
from synthy.render import IMAGE_SUFFIXES, parse_page_range
from synthy.web.jobs import JobStore

STATIC = Path(__file__).parent / "static"
DEFAULT_JOBS_DIR = Path.home() / ".cache/synthy/jobs"
ALLOWED_SUFFIXES = {".pdf", *IMAGE_SUFFIXES}
MAX_UPLOAD = 200 * 1024 * 1024


def create_app(jobs_dir: Path | None = None, engine: Engine | None = None) -> FastAPI:
    app = FastAPI(title="Synthy")
    store = JobStore(jobs_dir or DEFAULT_JOBS_DIR, engine=engine)
    app.state.store = store

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return (STATIC / "index.html").read_text()

    @app.post("/jobs")
    async def create_job(
        file: UploadFile = File(...),
        tempo: int = Form(DEFAULT_TEMPO),
        pages: str = Form(""),
    ) -> JSONResponse:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(422, "Upload a PDF or a page image (png, jpg, tif).")
        if not 20 <= tempo <= 300:
            raise HTTPException(422, "Tempo must be between 20 and 300 BPM.")
        try:
            page_list = parse_page_range(pages)
        except ValueError as exc:
            raise HTTPException(422, f"Pages: {exc}") from exc
        data = await file.read()
        if not data:
            raise HTTPException(422, "The uploaded file is empty.")
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "File is larger than 200 MB.")
        job = store.create(file.filename or "score.pdf", data, tempo, page_list)
        return JSONResponse({"id": job.id}, status_code=202)

    @app.get("/jobs/{job_id}")
    def job_status(job_id: str) -> dict:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(404, "No such job.")
        return job.to_dict()

    @app.get("/jobs/{job_id}/midi")
    def job_midi(job_id: str) -> FileResponse:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(404, "No such job.")
        if job.status != "done" or not job.midi_path.exists():
            raise HTTPException(409, "The MIDI is not ready yet.")
        return FileResponse(job.midi_path, media_type="audio/midi", filename=f"{job.stem}.mid")

    return app
