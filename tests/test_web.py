import time

import pymupdf
from fastapi.testclient import TestClient

from synthy.web.app import create_app

from .fake_engine import FakeEngine


def _client(tmp_path, engine=None):
    return TestClient(create_app(jobs_dir=tmp_path / "jobs", engine=engine or FakeEngine()))


def _pdf_bytes(n=1) -> bytes:
    doc = pymupdf.open()
    for _ in range(n):
        doc.new_page(width=595, height=842)
    return doc.tobytes()


def _wait(client, job_id, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/jobs/{job_id}").json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_index_serves_page(tmp_path):
    r = _client(tmp_path).get("/")
    assert r.status_code == 200
    assert "<title>Synthy</title>" in r.text


def test_job_lifecycle_and_download(tmp_path):
    client = _client(tmp_path)
    r = client.post("/jobs", files={"file": ("nocturne.pdf", _pdf_bytes(2), "application/pdf")},
                    data={"tempo": "96", "pages": ""})
    assert r.status_code == 202
    job_id = r.json()["id"]
    body = _wait(client, job_id)
    assert body["status"] == "done"
    assert body["name"] == "nocturne"
    assert body["tempo"] == 96
    assert body["report"]["pages"] == [1, 2]
    assert len(body["report"]["measures"]) == 4
    assert body["report"]["measures"][0]["raw"] == {"1": 4.0, "2": 4.0}
    midi = client.get(f"/jobs/{job_id}/midi")
    assert midi.status_code == 200
    assert midi.headers["content-type"].startswith("audio/midi")
    assert 'filename="nocturne.mid"' in midi.headers["content-disposition"]
    assert midi.content[:4] == b"MThd"

    notes = client.get(f"/jobs/{job_id}/notes").json()
    assert notes["name"] == "nocturne" and notes["tempo"] == 96
    assert notes["length"] == 16.0
    assert [m["start"] for m in notes["measures"]] == [0.0, 4.0, 8.0, 12.0]
    assert all(m["length"] == 4.0 and not m["suspect"] for m in notes["measures"])
    assert len(notes["notes"]) == 4 * 6
    assert notes["notes"][0] == {"hand": 1, "pitch": 72, "onset": 0.0, "duration": 1.0}
    assert {n["hand"] for n in notes["notes"]} == {1, 2}

    play = client.get(f"/jobs/{job_id}/play")
    assert play.status_code == 200 and "<canvas" in play.text
    assert client.get(f"/jobs/{job_id}/styles").status_code == 200
    assert client.get("/static/piano.js").status_code == 200
    assert client.get("/static/render.js").headers["content-type"].startswith("text/javascript")


def test_engine_failure_reports_error(tmp_path):
    client = _client(tmp_path, FakeEngine(fail_pages={1}))
    job_id = client.post("/jobs", files={"file": ("x.pdf", _pdf_bytes(), "application/pdf")}).json()["id"]
    body = _wait(client, job_id)
    assert body["status"] == "error"
    assert "nothing usable" in body["message"]
    assert client.get(f"/jobs/{job_id}/midi").status_code == 409
    assert client.get(f"/jobs/{job_id}/notes").status_code == 409
    assert client.get(f"/jobs/{job_id}/play").status_code == 409


def test_validation(tmp_path):
    client = _client(tmp_path)
    pdf = _pdf_bytes()
    assert client.post("/jobs", files={"file": ("x.pdf", pdf)}, data={"tempo": "5"}).status_code == 422
    assert client.post("/jobs", files={"file": ("x.pdf", pdf)}, data={"pages": "9-1"}).status_code == 422
    assert client.post("/jobs", files={"file": ("x.txt", b"hi")}).status_code == 422
    assert client.post("/jobs", files={"file": ("x.pdf", b"")}).status_code == 422
    assert client.get("/jobs/nope").status_code == 404
