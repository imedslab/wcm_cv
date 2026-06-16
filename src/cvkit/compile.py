"""Compile a generated LaTeX string into a PDF.

The whole LaTeX build runs in a throwaway temporary directory so the data/code
folders are never polluted with .aux/.bbl/.log artifacts — only the finished
PDF (and, for convenience, the .tex) is copied into the output directory.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class LatexNotFound(RuntimeError):
    """xelatex / bibtex is not on PATH."""


class LatexCompileError(RuntimeError):
    """LaTeX ran but produced no PDF."""


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd, cwd=cwd, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    except FileNotFoundError as exc:  # the binary itself is missing
        raise LatexNotFound(
            f"'{cmd[0]}' not found. Install a TeX distribution that provides "
            f"xelatex and bibtex (e.g. TeX Live / MacTeX)."
        ) from exc


def _errors_from_log(log: str) -> str:
    """Pull the LaTeX '!'-prefixed error lines out of a log for friendly output."""
    hits = [ln for ln in log.splitlines() if ln.startswith("! ")]
    return "\n".join(hits[:20])


def _flatten_pdf(pdf: Path) -> Path:
    """Re-distill ``pdf`` through Ghostscript to flatten transparency layers.

    XeLaTeX can emit optional-content/transparency groups that some PDF viewers
    (older Preview, certain print RIPs, ATS résumé parsers) render incorrectly.
    Running the file through Ghostscript's ``pdfwrite`` device with the prepress
    profile collapses those layers into a single flat page stream, maximising
    cross-software compatibility while preserving print quality.

    Returns the flattened file (a sibling of ``pdf``). If Ghostscript is not on
    PATH or the run fails, the original ``pdf`` is returned unchanged — flattening
    is a best-effort enhancement, never a hard build requirement.
    """
    flat = pdf.with_name(f"{pdf.stem}-flat.pdf")
    cmd = [
        "gs", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-q",
        "-sDEVICE=pdfwrite", "-dPDFSETTINGS=/prepress",
        f"-sOutputFile={flat.name}", pdf.name,
    ]
    try:
        result = subprocess.run(
            cmd, cwd=pdf.parent, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        print("[cvkit] ghostscript ('gs') not found — skipping PDF flattening.")
        return pdf
    if result.returncode != 0 or not flat.exists():
        print("[cvkit] ghostscript flattening failed — using unflattened PDF.\n"
              + result.stdout[-1000:])
        return pdf
    return flat


def compile_pdf(
    tex: str,
    data_dir: str | Path,
    out_dir: str | Path,
    *,
    jobname: str = "cv",
    keep_tmp: bool = False,
    save_tex: bool = True,
    flatten: bool = True,
) -> Path:
    """Build ``{jobname}.pdf`` from ``tex`` and return its path in ``out_dir``.

    ``data_dir`` is scanned for ``*.bib`` files, which are copied next to the
    LaTeX source so ``\\addbibresource{...}`` resolves during compilation.
    Runs the xelatex → bibtex → xelatex → xelatex sequence (bibtex backend).

    When ``flatten`` is true (the default) and Ghostscript is available, the
    finished PDF is re-distilled to flatten transparency/optional-content layers
    for maximum viewer compatibility (see :func:`_flatten_pdf`).
    """
    data_dir = Path(data_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tmp = Path(tempfile.mkdtemp(prefix="cvkit-"))
    try:
        (tmp / f"{jobname}.tex").write_text(tex, encoding="utf-8")
        for bib in sorted(data_dir.glob("*.bib")):
            shutil.copy(bib, tmp / bib.name)

        xelatex = ["xelatex", "-interaction=nonstopmode", f"{jobname}.tex"]
        steps = [xelatex, ["bibtex", jobname], xelatex, xelatex]
        last_log = ""
        for cmd in steps:
            result = _run(cmd, tmp)
            if cmd[0] == "xelatex":
                last_log = result.stdout

        pdf = tmp / f"{jobname}.pdf"
        if not pdf.exists():
            raise LatexCompileError(
                "LaTeX did not produce a PDF.\n" + (_errors_from_log(last_log)
                                                    or last_log[-2000:])
            )

        if flatten:
            pdf = _flatten_pdf(pdf)

        dest = out_dir / f"{jobname}.pdf"
        shutil.copy(pdf, dest)
        if save_tex:
            shutil.copy(tmp / f"{jobname}.tex", out_dir / f"{jobname}.tex")
        return dest
    finally:
        if keep_tmp:
            print(f"[cvkit] kept build directory: {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
