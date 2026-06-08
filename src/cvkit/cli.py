"""``compile_cv`` command-line entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compile import LatexCompileError, LatexNotFound, compile_pdf
from .generate import build_tex, load_data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="compile_cv",
        description="Generate a Weill Cornell Medicine faculty CV (XeLaTeX) "
                    "from a folder of JSON data files + a BibTeX file.",
    )
    parser.add_argument(
        "--data", type=Path, default=Path("cv_data"),
        help="folder with the CV's *.json files and *.bib (default: cv_data)",
    )
    parser.add_argument(
        "--out", type=Path, default=Path("cv_out"),
        help="output folder for the compiled PDF (default: cv_out)",
    )
    parser.add_argument(
        "--name", default="cv",
        help="basename of the output file, e.g. 'cv' -> cv.pdf (default: cv)",
    )
    parser.add_argument(
        "--tex-only", action="store_true",
        help="only write the generated .tex (skip LaTeX compilation)",
    )
    parser.add_argument(
        "--keep-tmp", action="store_true",
        help="keep the temporary LaTeX build directory (for debugging)",
    )
    args = parser.parse_args(argv)

    try:
        data = load_data(args.data)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    tex = build_tex(data)

    if args.tex_only:
        args.out.mkdir(parents=True, exist_ok=True)
        dest = args.out / f"{args.name}.tex"
        dest.write_text(tex, encoding="utf-8")
        print(f"Wrote {dest}")
        return 0

    try:
        pdf = compile_pdf(
            tex, args.data, args.out,
            jobname=args.name, keep_tmp=args.keep_tmp,
        )
    except (LatexNotFound, LatexCompileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
