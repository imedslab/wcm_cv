"""Unit tests for cvkit.generate — pure LaTeX-string generation, no xelatex."""
from __future__ import annotations

import pytest

from cvkit.generate import (
    DATE_W,
    _bib_keywords,
    _font_lines,
    _format_costs,
    breakable_table,
    build_tex,
    event_table,
    kv_table,
    load_data,
    sec_bibliography,
)


# ── load_data ──────────────────────────────────────────────────────────────

def test_load_data_merges_json_and_collects_bib_keywords(tiny_data):
    d = load_data(tiny_data)
    assert d["alpha"] == 1
    assert d["beta"] == {"x": 2}
    assert d["bib_keywords"] == {"paper", "journal", "media"}


def test_load_data_empty_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_data(tmp_path)


# ── _bib_keywords ──────────────────────────────────────────────────────────

def test_bib_keywords_reads_every_bib(tiny_data):
    assert _bib_keywords(tiny_data) == {"paper", "journal", "media"}


def test_bib_keywords_empty_without_bib(tmp_path):
    assert _bib_keywords(tmp_path) == set()


# ── fonts ──────────────────────────────────────────────────────────────────

def test_font_lines_system_lookup_when_no_path():
    assert _font_lines({"font_name": "FreeSans"}) == [r"\setmainfont{FreeSans}"]


def test_font_lines_falls_back_when_path_missing():
    # a non-existent font_path -> system lookup (so the same meta.json is portable
    # to Docker/CI, where an absolute macOS path won't exist)
    assert _font_lines({"font_name": "FreeSans", "font_path": "/no/such/dir"}) == [
        r"\setmainfont{FreeSans}"
    ]


def test_font_lines_explicit_path_when_dir_exists(tmp_path):
    joined = "\n".join(
        _font_lines({"font_name": "FreeSans", "font_path": str(tmp_path), "font_ext": ".otf"})
    )
    assert r"\setmainfont{FreeSans}[" in joined
    assert str(tmp_path) in joined
    assert ".otf" in joined
    assert "FreeSansBold" in joined  # default derived bold face


# ── table helpers ──────────────────────────────────────────────────────────

def test_event_table_empty_renders_na_not_a_table():
    out = "\n".join(event_table(["Org", "Dates"], [], ["Y"]))
    assert "N/A" in out
    assert "xltabular" not in out


def test_event_table_appends_uniform_date_column_and_italic_header():
    out = "\n".join(event_table(["Title", "Dates"], [["X", "2020"]], ["Y"]))
    assert r"\begin{xltabular}" in out
    assert f"L{{{DATE_W}}}" in out         # trailing uniform date column
    assert r"\textit{Title}" in out        # italic column header
    assert "X & 2020" in out


def test_kv_table_uses_bold_keys():
    out = "\n".join(kv_table("|L{3cm}|Y|", [("Award Source:", "NIH")]))
    assert r"\textbf{Award Source:} & NIH" in out
    assert r"\begin{xltabular}" in out


def test_breakable_table_repeats_header_via_endhead():
    out = "\n".join(breakable_table("|Y|", ["Col"], [["v"]]))
    assert r"\endhead" in out
    assert r"\textit{Col}" in out


# ── grant cost currency conversion ─────────────────────────────────────────

def test_format_costs_euro_appends_usd_at_rate():
    out = _format_costs(r"20{,}000\,€")
    assert r"20{,}000\,€" in out                       # original kept verbatim
    assert r"\$22{,}000" in out                        # 20000 * 1.1, grouped
    assert "converted from euro at a 1.1 exchange rate" in out


def test_format_costs_non_euro_passes_through():
    assert _format_costs(r"\$50{,}000") == r"\$50{,}000"
    assert _format_costs("N/A") == "N/A"


# ── bibliography category logic (regression for the refs.bib path bug) ──────

def test_bibliography_all_empty_when_no_keywords():
    out = sec_bibliography({"bib_keywords": set()})
    assert out.count("None to date.") == 5  # all five template categories empty


def test_bibliography_respects_bib_keywords():
    out = sec_bibliography({"bib_keywords": {"paper", "books", "media"}})
    assert "keyword=paper" in out      # Peer-reviewed Research Articles populated
    assert "keyword=books" in out      # Books populated
    assert "filter=cvother" in out     # media -> Other populated
    assert out.count("None to date.") == 2  # only Reviews + Chapters empty


# ── whole-document assembly (uses the repo's example data) ─────────────────

def test_build_tex_document_skeleton(real_data_dir):
    tex = build_tex(load_data(real_data_dir))
    assert tex.count(r"\documentclass") == 1
    assert tex.count(r"\begin{document}") == 1
    assert tex.count(r"\end{document}") == 1


def test_build_tex_contains_all_sections_A_to_S(real_data_dir):
    tex = build_tex(load_data(real_data_dir))
    for letter in "ABCDEFGHIJKLMNOPQRS":
        assert "\\cvsection{%s}" % letter in tex, f"missing section {letter}"


def test_build_tex_date_of_preparation_is_today(real_data_dir):
    tex = build_tex(load_data(real_data_dir))
    assert r"\today" in tex
