"""Audiveris 5.x batch engine.

Install: extract the Ubuntu 22.04 .deb from the Audiveris GitHub release
into ~/.local/opt/audiveris (no root needed) and drop eng.traineddata
into ~/.local/share/AudiverisLtd/audiveris/tessdata. Override the binary
with SYNTHY_AUDIVERIS and the OCR data with TESSDATA_PREFIX.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from synthy.engine.base import EngineError

ENV_BINARY = "SYNTHY_AUDIVERIS"
DEFAULT_BINARY = Path.home() / ".local/opt/audiveris/bin/Audiveris"
DEFAULT_TESSDATA = Path.home() / ".local/share/AudiverisLtd/audiveris/tessdata"
LOG_NAME = "audiveris.log"


def find_audiveris() -> Path | None:
    env = os.environ.get(ENV_BINARY)
    candidates = [Path(env)] if env else []
    candidates.append(DEFAULT_BINARY)
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return c
    return None


class AudiverisEngine:
    name = "audiveris"

    def __init__(self, binary: Path | None = None, tessdata: Path | None = None):
        self.binary = Path(binary) if binary else find_audiveris()
        self.tessdata = Path(tessdata) if tessdata else None

    def command(self, pages: list[Path], out_dir: Path) -> list[str]:
        if self.binary is None:
            raise EngineError(
                f"Audiveris not found. Set {ENV_BINARY} or install it at {DEFAULT_BINARY}"
            )
        return [str(self.binary), "-batch", "-transcribe", "-export", "-output", str(out_dir),
                "--", *(str(p) for p in pages)]

    def environment(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.tessdata is not None:
            env["TESSDATA_PREFIX"] = str(self.tessdata)
        elif "TESSDATA_PREFIX" not in env and DEFAULT_TESSDATA.is_dir():
            env["TESSDATA_PREFIX"] = str(DEFAULT_TESSDATA)
        return env

    def transcribe(self, pages: list[Path], workdir: Path) -> list[Path | None]:
        workdir = Path(workdir)
        out_dir = workdir / "audiveris"
        out_dir.mkdir(parents=True, exist_ok=True)
        log_path = workdir / LOG_NAME
        cmd = self.command(pages, out_dir)
        with open(log_path, "w") as log:
            log.write(" ".join(cmd) + "\n")
            log.flush()
            proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=self.environment())
        if proc.returncode != 0:
            tail = _tail(log_path)
            raise EngineError(f"Audiveris exited with {proc.returncode}. Log tail:\n{tail}")
        return [_find_output(out_dir, Path(p).stem) for p in pages]


def _find_output(out_dir: Path, stem: str) -> Path | None:
    matches = sorted(p for p in out_dir.rglob("*.mxl") if p.stem == stem or p.stem.startswith(stem + "."))
    if not matches:
        matches = sorted(p for p in out_dir.rglob("*.xml") if p.stem == stem)
    return matches[0] if matches else None


def _tail(path: Path, lines: int = 30) -> str:
    try:
        return "\n".join(path.read_text(errors="replace").splitlines()[-lines:])
    except OSError:
        return ""
