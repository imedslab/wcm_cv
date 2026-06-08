"""Tests for the `compile_cv` CLI (cvkit.cli:main)."""
from __future__ import annotations

import pytest

from cvkit.cli import main

from conftest import requires_latex


def test_tex_only_writes_tex_and_returns_0(real_data_dir, tmp_path):
    rc = main(["--data", str(real_data_dir), "--out", str(tmp_path), "--tex-only"])
    assert rc == 0
    tex = tmp_path / "cv.tex"
    assert tex.exists()
    assert r"\begin{document}" in tex.read_text(encoding="utf-8")


def test_custom_name(real_data_dir, tmp_path):
    rc = main(
        ["--data", str(real_data_dir), "--out", str(tmp_path),
         "--name", "myresume", "--tex-only"]
    )
    assert rc == 0
    assert (tmp_path / "myresume.tex").exists()


def test_missing_data_dir_returns_2(tmp_path):
    rc = main(["--data", str(tmp_path / "nope"), "--out", str(tmp_path / "out")])
    assert rc == 2


@requires_latex
@pytest.mark.integration
def test_full_compile_returns_0_and_writes_pdf(real_data_dir, tmp_path):
    rc = main(["--data", str(real_data_dir), "--out", str(tmp_path)])
    assert rc == 0
    pdf = tmp_path / "cv.pdf"
    assert pdf.exists()
    assert pdf.read_bytes()[:4] == b"%PDF"
