<p align="center">
  <img src="assets/banner.jpeg" alt="WCM CV Kit" width="100%">
</p>

<h1 align="center">WCM CV Kit</h1>

<p align="center"><i>Turn a folder of JSON files (+ one BibTeX file) into a polished,
WCM-template XeLaTeX CV. You edit data, not LaTeX; the kit emits the PDF.</i></p>

WCM CV Kit ships as a prebuilt image at **`ghcr.io/imedslab/cvkit:latest`** (rebuilt
by CI on every push here), so the normal way to use it needs **no local install**
— see below. See the output it produces in the
[sample CV](https://github.com/imedslab/wcm_cv/releases/download/sample-latest/cv.pdf),
which CI compiles from `cv_data/` on every push.

## Get your own CV (recommended — zero local setup)

Keep your CV in its own (private) repo holding only your data plus one workflow
that pulls the public image. Your data stays private; no LaTeX, no Python, no
build step:

1. Create a new repo and add a `cv_data/` folder (copy this repo's `cv_data/` as
   a starting point — it's a working example).
2. Copy [`examples/cv-repo-workflow.yml`](examples/cv-repo-workflow.yml) into it
   as `.github/workflows/cv.yml`.
3. Edit `cv_data/`, commit, push.

That's it. Every push compiles the CV, and the freshest PDF is always at:

```
https://github.com/<you>/<repo>/releases/latest/download/cv.pdf
```

New repos have Actions on by default, so there's nothing else to configure. The
`cvkit` image is public, so the pull needs no auth even from a private repo.

**Optional — support the project:** add a repo secret `CVKIT_STAR_TOKEN` (a
classic GitHub PAT with the `public_repo` scope) and each build stars this repo,
so its author can gauge how many people use WCM CV Kit. The step self-skips if the
secret is absent. Note that GitHub stars are public.

## Editing the data

`cv_data/` is the only thing you personalise: one JSON file per CV section, plus
`refs.bib` for the publication list. Strings are LaTeX-ready, so write `\&`,
`5\%`, `--`, etc. directly. The "Date of Preparation" is always the build date.

See [`CLAUDE.md`](CLAUDE.md) for the section→file map, the JSON conventions, and
how to add grants / mentees / publications.

## Build locally (optional)

To compile on your own machine you need [`uv`](https://docs.astral.sh/uv/) and a
TeX distribution with `xelatex` + `bibtex` (TeX Live / MacTeX):

```bash
uv sync                                        # one-time: env + install cvkit
uv run compile_cv --data cv_data --out cv_out  # → cv_out/cv.pdf  (also: make pdf)
```

No local TeX? Use the same image the cloud build uses — it bundles everything:

```bash
docker run --rm -v "$PWD/cv_data:/data" -v "$PWD/cv_out:/out" ghcr.io/imedslab/cvkit:latest
```

Compilation is hermetic: each LaTeX run happens in a throwaway temp dir, and only
`cv.pdf` (+ `cv.tex`) land in `--out`.

### CLI

```
compile_cv --data DIR --out DIR [--name NAME] [--tex-only] [--keep-tmp]
```

| flag         | default   | meaning                                            |
|--------------|-----------|----------------------------------------------------|
| `--data`     | `cv_data` | folder with the `*.json` files **and** the `*.bib` |
| `--out`      | `cv_out`  | output folder for the compiled PDF                 |
| `--name`     | `cv`      | output basename (`cv` → `cv.pdf`)                  |
| `--tex-only` | —         | write the `.tex` only, skip LaTeX                  |
| `--keep-tmp` | —         | keep the temp build dir (to debug LaTeX errors)   |

## Fonts

The CV uses **FreeSans** by default, set in `cv_data/meta.json`:

- **System font (portable):** omit `font_path`; `cvkit` looks the family up by name.
- **Explicit files:** set `font_path` to a directory + `font_ext` (`.otf`/`.ttf`).

A `font_path` that doesn't exist is ignored, so an absolute macOS path falls back
to the system FreeSans inside Docker/CI — the same `meta.json` builds everywhere.

## Developing WCM CV Kit

This repo is the tool. `src/cvkit/` is the package (`generate.py` = JSON→LaTeX,
`compile.py` = LaTeX→PDF, `cli.py` = the command). `ci.yml` runs the tests,
builds the image, smoke-tests it on the demo `cv_data/`, and pushes
`ghcr.io/<owner>/cvkit:latest` from `main`.

```bash
uv run pytest                       # everything
uv run pytest -m "not integration"  # fast unit tests (no TeX)
uv run pytest -m integration        # end-to-end: actually compiles PDFs
```
