import os
import stat
import subprocess
from pathlib import Path

import pytest

from synthy.engine import AudiverisEngine, EngineError, find_audiveris
from synthy.engine import audiveris as mod


def _fake_binary(tmp_path: Path) -> Path:
    b = tmp_path / "Audiveris"
    b.write_text("#!/bin/sh\nexit 0\n")
    b.chmod(b.stat().st_mode | stat.S_IEXEC)
    return b


def test_find_audiveris_honors_env(tmp_path, monkeypatch):
    b = _fake_binary(tmp_path)
    monkeypatch.setenv(mod.ENV_BINARY, str(b))
    assert find_audiveris() == b


def test_find_audiveris_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv(mod.ENV_BINARY, str(tmp_path / "nope"))
    monkeypatch.setattr(mod, "DEFAULT_BINARIES", (tmp_path / "also-nope",))
    assert find_audiveris() is None


def test_find_audiveris_falls_back_to_defaults(tmp_path, monkeypatch):
    b = _fake_binary(tmp_path)
    monkeypatch.delenv(mod.ENV_BINARY, raising=False)
    monkeypatch.setattr(mod, "DEFAULT_BINARIES", (tmp_path / "nope", b))
    assert find_audiveris() == b


def test_missing_binary_raises_engine_error(tmp_path, monkeypatch):
    monkeypatch.delenv(mod.ENV_BINARY, raising=False)
    monkeypatch.setattr(mod, "DEFAULT_BINARIES", (tmp_path / "nope",))
    with pytest.raises(EngineError):
        AudiverisEngine().transcribe([tmp_path / "page001.png"], tmp_path / "work")


def test_transcribe_builds_command_and_matches_outputs(tmp_path, monkeypatch):
    b = _fake_binary(tmp_path)
    calls = {}

    def fake_run(cmd, stdout, stderr, env):
        calls["cmd"] = cmd
        calls["env"] = env
        out_dir = Path(cmd[cmd.index("-output") + 1])
        (out_dir / "page001").mkdir(parents=True)
        (out_dir / "page001" / "page001.mxl").write_bytes(b"PK")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    engine = AudiverisEngine(binary=b, tessdata=tmp_path / "tess")
    pages = [tmp_path / "page001.png", tmp_path / "page002.png"]
    result = engine.transcribe(pages, tmp_path / "work")
    assert calls["cmd"][:6] == [str(b), "-batch", "-transcribe", "-export", "-output", str(tmp_path / "work" / "audiveris")]
    assert calls["cmd"][-2:] == [str(pages[0]), str(pages[1])]
    assert calls["env"]["TESSDATA_PREFIX"] == str(tmp_path / "tess")
    assert result[0] == tmp_path / "work" / "audiveris" / "page001" / "page001.mxl"
    assert result[1] is None
    assert (tmp_path / "work" / "audiveris.log").exists()


def test_nonzero_exit_raises_with_log_tail(tmp_path):
    b = tmp_path / "Audiveris"
    b.write_text("#!/bin/sh\necho boom failure\nexit 3\n")
    b.chmod(b.stat().st_mode | stat.S_IEXEC)
    engine = AudiverisEngine(binary=b)
    with pytest.raises(EngineError, match="boom failure"):
        engine.transcribe([tmp_path / "page001.png"], tmp_path / "work")
