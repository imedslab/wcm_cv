"""Shared fixtures and the xelatex/bibtex availability gate."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_DATA = REPO_ROOT / "cv_data"

HAS_LATEX = bool(shutil.which("xelatex") and shutil.which("bibtex"))
requires_latex = pytest.mark.skipif(
    not HAS_LATEX, reason="xelatex/bibtex not on PATH"
)

TRIVIAL_TEX = (
    "\\documentclass{article}\n"
    "\\begin{document}\n"
    "Hello from the cvkit test-suite.\n"
    "\\end{document}\n"
)


@pytest.fixture
def real_data_dir() -> Path:
    """The repository's example data folder (skips the test if it's absent)."""
    if not REAL_DATA.is_dir():
        pytest.skip("example cv_data/ not present")
    return REAL_DATA


@pytest.fixture
def tiny_data(tmp_path: Path) -> Path:
    """A minimal data folder: two JSON files + a .bib with keywords."""
    (tmp_path / "a.json").write_text('{"alpha": 1}', encoding="utf-8")
    (tmp_path / "b.json").write_text('{"beta": {"x": 2}}', encoding="utf-8")
    (tmp_path / "refs.bib").write_text(
        "@article{x, keywords={paper, journal}, title={T}, author={A}, year={2020}}\n"
        "@misc{y, keywords={media}, title={P}, author={B}, year={2021}}\n",
        encoding="utf-8",
    )
    return tmp_path
