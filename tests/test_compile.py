"""Tests for cvkit.compile — the hermetic LaTeX → PDF step."""
from __future__ import annotations

import subprocess

import pytest

from cvkit.compile import LatexCompileError, LatexNotFound, compile_pdf
from cvkit.generate import build_tex, load_data

from conftest import TRIVIAL_TEX, requires_latex


# ── error handling (no real LaTeX needed — subprocess is monkeypatched) ─────

def test_raises_latexnotfound_when_binary_missing(tmp_path, monkeypatch):
    def boom(*_a, **_k):
        raise FileNotFoundError("xelatex")
    monkeypatch.setattr("cvkit.compile.subprocess.run", boom)
    with pytest.raises(LatexNotFound):
        compile_pdf(TRIVIAL_TEX, tmp_path, tmp_path / "out")


def test_raises_compileerror_when_no_pdf_produced(tmp_path, monkeypatch):
    class FakeResult:
        returncode = 0
        stdout = "! Undefined control sequence.\n"
    monkeypatch.setattr("cvkit.compile.subprocess.run", lambda *_a, **_k: FakeResult())
    with pytest.raises(LatexCompileError):
        compile_pdf(TRIVIAL_TEX, tmp_path, tmp_path / "out")


def test_temp_build_dir_is_removed_even_on_failure(tmp_path, monkeypatch):
    import os
    import tempfile

    created = {}
    real_mkdtemp = tempfile.mkdtemp

    def spy(*a, **k):
        path = real_mkdtemp(*a, **k)
        created["dir"] = path
        return path

    monkeypatch.setattr("cvkit.compile.tempfile.mkdtemp", spy)
    monkeypatch.setattr(
        "cvkit.compile.subprocess.run",
        lambda *_a, **_k: type("R", (), {"returncode": 0, "stdout": ""})(),
    )
    with pytest.raises(LatexCompileError):
        compile_pdf(TRIVIAL_TEX, tmp_path, tmp_path / "out")
    assert not os.path.exists(created["dir"])  # cleaned up by the finally: block


# ── real compilation (skipped without xelatex/bibtex) ──────────────────────

@requires_latex
@pytest.mark.integration
def test_compile_trivial_doc_is_hermetic(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    out = tmp_path / "out"
    pdf = compile_pdf(TRIVIAL_TEX, data, out, jobname="cv")
    assert pdf == out / "cv.pdf"
    assert pdf.read_bytes()[:4] == b"%PDF"
    # only the finished artifacts land in out — no .aux/.log/.bbl
    assert {p.name for p in out.iterdir()} == {"cv.pdf", "cv.tex"}


@requires_latex
@pytest.mark.integration
def test_compile_real_cv_produces_multipage_pdf(real_data_dir, tmp_path):
    tex = build_tex(load_data(real_data_dir))
    pdf = compile_pdf(tex, real_data_dir, tmp_path)
    assert pdf.exists()
    assert pdf.read_bytes()[:4] == b"%PDF"
    assert pdf.stat().st_size > 20_000  # the real CV is many pages
