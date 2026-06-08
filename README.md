# cvkit — Weill Cornell Medicine faculty CV builder

`cvkit` turns a folder of plain JSON files (plus one BibTeX file) into a
polished, WCM-template XeLaTeX CV — PDF out, no LaTeX wrangling.

- **Your data lives separately from the code.** Edit JSON, not `.tex`.
- **Compilation is hermetic.** Every LaTeX run happens in a throwaway temp
  directory; only the finished PDF (and `.tex`) land in your output folder.
- **One command:** `uv run compile_cv --data cv_data --out cv_out`.

## Requirements

- [`uv`](https://docs.astral.sh/uv/)
- A TeX distribution providing **`xelatex`** and **`bibtex`** (TeX Live / MacTeX).
- The CV font (default **FreeSans**, GNU FreeFont). Either install it
  system-wide, or point `meta.json`'s `font_path` at a folder of font files
  (see *Fonts* below).

## Quick start

```bash
uv sync                                     # create the env + install cvkit
uv run compile_cv --data cv_data --out cv_out
open cv_out/cv.pdf                           # macOS (xdg-open on Linux)
```

`make pdf` does the same thing.

### Or with Docker (no local TeX needed)

The image bundles TeX Live + FreeSans + `cvkit`; mount your data and an output dir:

```bash
docker build -t cvkit .
docker run --rm -v "$PWD/cv_data:/data" -v "$PWD/cv_out:/out" cvkit
```

Your `meta.json` stays portable: an absolute `font_path` is used on your own
machine but ignored inside the container (which falls back to the system
FreeSans), so the same data builds in both places.

### CLI

```
compile_cv --data DIR --out DIR [--name NAME] [--tex-only] [--keep-tmp]
```

| flag         | meaning                                                         |
|--------------|----------------------------------------------------------------|
| `--data`     | folder with the CV's `*.json` files **and** the `*.bib` (default `cv_data`) |
| `--out`      | folder for the compiled `NAME.pdf` (default `cv_out`)          |
| `--name`     | output basename, e.g. `cv` → `cv.pdf` (default `cv`)           |
| `--tex-only` | generate the `.tex` only, skip the LaTeX run                   |
| `--keep-tmp` | keep the temporary build dir (for debugging LaTeX errors)     |

## Repository layout

```
src/cvkit/        # the package (the reusable tool)
  generate.py     #   JSON  -> LaTeX string  (load_data, build_tex)
  compile.py      #   LaTeX string -> PDF, compiled in a temp dir
  cli.py          #   the `compile_cv` command
cv_data/          # YOUR data — one JSON file per CV section + refs.bib
cv_out/           # build output (git-ignored)
pyproject.toml    # uv / packaging
```

## Suggested workflow

1. This repo is the **example**. Fork/clone it (keep it **private**).
2. Edit the files under `cv_data/` — one JSON per section, plus `refs.bib` for
   the publication list. Strings are LaTeX-ready (write `\&`, `5\%`, `--`, …).
3. `uv run compile_cv --data cv_data --out cv_out` whenever you want a fresh PDF.

The data folder is the only thing you personalise; the package can be updated
independently.

## Fonts

The CV uses **FreeSans** by default. In `cv_data/meta.json`:

- **System-installed font** (portable): omit `font_path` and `cvkit` will look
  the family up by name.
- **Explicit font files**: set `font_path` to a directory and `font_ext`
  (`.otf`/`.ttf`); `cvkit` loads `FreeSans`, `FreeSansBold`, etc. from there.

## Editing the data

See `CLAUDE.md` for the JSON conventions, the section→file map, and the table
helpers. The Date of Preparation is always the compile date (`\today`).

## Tests

```bash
uv run pytest                      # everything
uv run pytest -m "not integration" # fast unit tests only (no LaTeX needed)
uv run pytest -m integration       # end-to-end: actually compiles PDFs
```

Unit tests cover the JSON→LaTeX generation (`generate.py`) and the compile
error paths; integration tests (skipped automatically if `xelatex`/`bibtex`
are not installed) compile both a trivial document and the real `cv_data/`.
