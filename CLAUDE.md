# WCM Faculty CV — `cvkit`

XeLaTeX CV for Weill Cornell Medicine, generated from JSON data + a BibTeX file by
the **`cvkit`** Python package. Font: FreeSans (GNU FreeFont). Margins: 0.6" all
sides. Paper: US Letter.

## Quick build

```bash
uv sync                                        # one-time: env + install cvkit
uv run compile_cv --data cv_data --out cv_out  # JSON+bib → cv_out/cv.pdf
make pdf                                        # same thing
make tex                                        # write cv_out/cv.tex only (no LaTeX)
uv run pytest                                   # tests (see `tests/`)
```

No local TeX? Pull the prebuilt image (TeX Live + FreeSans + cvkit baked in; data
mounted at runtime) — no local build needed:

```bash
docker run --rm -v "$PWD/cv_data:/data" -v "$PWD/cv_out:/out" ghcr.io/imedslab/cvkit:latest
```

(Building it yourself — `docker build -t cvkit .` — is only needed when changing
the package or the Dockerfile; CI builds and pushes the image from `main`.)

`.github/workflows/ci.yml` runs the unit tests, builds the Docker image,
compiles the sample CV from `cv_data/` with it (uploaded as the `sample-cv`
artifact every run), and (only on `main`) pushes the image to GHCR as
`ghcr.io/<owner>/cvkit:latest` using the built-in `GITHUB_TOKEN`
(`packages: write`) and publishes the sample CV to the `sample-latest` release
(`…/releases/download/sample-latest/cv.pdf`, needs `contents: write`). End users don't build anything: their CV lives in a separate
data-only repo whose workflow just `docker run`s that prebuilt image — see
`examples/cv-repo-workflow.yml`, the drop-in `.github/workflows/cv.yml` that
compiles `cv_data/` and publishes the PDF to a rolling `latest` GitHub Release
(`…/releases/latest/download/cv.pdf`). The GHCR package must be made public once
so the data repo can pull it without auth.
`meta.json`'s `font_path` is honoured only if it's a real directory, so the same
data is portable between the Mac (explicit path) and the container (system FreeSans).

Compilation is **hermetic**: `compile_pdf` writes the `.tex`, copies the data
folder's `*.bib` next to it, and runs `xelatex → bibtex → xelatex → xelatex` all
inside a `tempfile.mkdtemp()` dir, then copies only `cv.pdf` (+ `cv.tex`) into
`--out`. Nothing is written next to the code or data. Needs `xelatex` + `bibtex`
on PATH (the §S Bibliography uses **biblatex with the bibtex backend** — `biber`
is not required).

## File layout

```
src/cvkit/                 # the package (the reusable tool)
  __init__.py
  generate.py              #   data dict → LaTeX string   (load_data, build_tex)
  compile.py               #   LaTeX string → PDF in a temp dir   (compile_pdf)
  cli.py                   #   the `compile_cv` command (argparse)
pyproject.toml             # uv / hatchling packaging; defines compile_cv entry point
Makefile                   # thin `uv run compile_cv` wrappers
cv_out/                    # build output (git-ignored): cv.pdf, cv.tex

cv_data/                   # ← YOUR data (the only thing you personalise)
  meta.json                # name, font settings (Date of Preparation is auto = \today)
  A_personal.json          # §A  Personal Data (incl. work-visa questions)
  B_education.json         # §B  Education
  C_postdoc.json           # §C  Postdoctoral Training
  D_positions.json         # §D  Professional Positions & Employment
  E_employment.json        # §E  Employment Status
  F_licensure.json         # §F  Licensure, Board Certification (N/A)
  G_affiliation.json       # §G  Institutional/Hospital Affiliation (N/A)
  H_honors.json            # §H  Honors, Awards
  I_organizations.json     # §I  Professional Organizations & Society Memberships
  J_percent_effort.json    # §J  Percent Effort & Institutional Responsibilities (TODO)
  K_teaching.json          # §K  Educational Contributions
  L_clinical.json          # §L  Clinical Practice, Innovation, Leadership (N/A)
  M_research.json          # §M  Research (activities, IRB, grants, pending, patents)
  N_mentoring.json         # §N  Mentoring (current + past mentees)
  O_leadership.json        # §O  Institutional Leadership
  P_admin.json             # §P  Institutional Admin
  Q_extramural.json        # §Q  Extramural (boards, reviewing, editorial)
  R_lectures.json          # §R  Invitations to Speak/Present
  refs.bib                 # §S  Bibliography — biblatex source (auto-rendered)
```

`load_data` globs `<data>/*.json`, merges them by top-level key, and stashes the
set of `*.bib` keyword tokens under `bib_keywords` (used to decide which §S
categories are non-empty). The `.bib` lives in the **data** folder, not the repo
root — `compile_pdf` copies it into the temp build dir so `\addbibresource{refs.bib}`
resolves.

Section order, lettering (A–S) and table column labels follow the official
**Blank Cornell CV Template** (`Blank Cornell CV Template[50].docx`). Filenames
are sorted-globbed and merged by their top-level JSON key, so the letter prefix
is just documentation — `build_tex()` in `cvkit/generate.py` controls the order.
Sections that don't apply to a non-clinician (F Licensure, G Affiliation,
L Clinical) are kept as **N/A** for template completeness. J Percent Effort and
S Bibliography are **scaffolds with `TODO` placeholders** to fill in.

## JSON conventions

All string values are **LaTeX-ready** — the generator passes them through verbatim.
Write LaTeX markup directly in the JSON when needed:

| Situation | JSON string |
|---|---|
| Ampersand in text/tables | `"\\&"` |
| Percent sign | `"5\\%"` |
| Euro amount | `"25{,}000\\,€"` (literal € — FreeSans has the glyph; no `eurosym`) |
| Italic journal name | `"\\textit{Spine}"` |
| Bold label | `"\\textbf{Project:} ..."` |
| Math inequality | `"$>$3"` |
| Non-breaking thin space | `"\\,"` |
| Em-dash date range | `"01/2022--03/2026"` (two hyphens) |

Unicode characters (é, ä, ö, ü, Ă, Ö, etc.) are stored as-is — XeLaTeX handles them natively.

## Table types

There are **three** table archetypes, all full-width and all breakable across
pages (built on `xltabular` = `tabularx` X-columns + `longtable` page breaks):

1. **Event/record table** (`event_table`) — sec B, C, E, F, G, L, M, N, O.
   One row per record. The caller passes the column types for every column
   *except* the last; a uniform-width date/year column (`DATE_W = 3.0cm`) is
   always appended, so the trailing date columns line up vertically down the
   whole CV. First column is usually a shared fixed width (`PRIMARY_W = 5.5cm`),
   middle column(s) flex (`Y`). Put the date/year as the **last** column.
2. **Teaching table** (`_teaching_table`) — sec H only. Five fixed/flex columns
   (Term(s), Institution, Course, Role, Content).
3. **Card/list blocks** — `\menteetable`/`\pastmenteetable` are bordered
   bold-key/value cards (one per mentee). `\grantblock` (§M funding) is
   border-free: an indented bold-label/value `itemize`, matching the template.

Column types:

- `Y` — flexible ragged-right column (`>{\RaggedRight}X`); expands to fill remaining space
- `L{Ncm}` — fixed-width ragged-right column; use for short fields (year, dates, row labels)

`event_table` example — `left_cols=[f"L{{{PRIMARY_W}}}", "Y"]` yields
`|L{5.5cm}|Y|L{3.0cm}|` (title | institution | dates). Don't hand-write the
trailing date column — `event_table` adds it so every section stays aligned.

## Adding content

**New publication** — add a BibTeX entry to `refs.bib` with a `keywords=` field. The
§S Bibliography renders the official template's five categories; keywords map as:
`paper` (i.e. `journal` or `conference`) → **Peer-reviewed Research Articles**;
`review` → **Reviews and Editorials**; `books` → **Books**; `chapter` → **Chapters**;
`preprint`/`abstract`/`media` → **Other (media, podcasts, etc.)**. (`patent` is not shown
in §S — patents live in §M Research.) Empty categories print "None to date.". The
owner's surname (derived from `meta.name`, or set `meta.highlight_surname`) is bolded
by a family-name match in the preamble, so `Author+an = {N=highlight}` annotations are
optional. Run `make pdf`.

**New grant** — append an object to `research.past_grants` (or `pending_grants`) in `M_research.json`:
```json
{
  "source": "Funder; grant type",
  "title": "Project title",
  "costs": "50{,}000\\,€",
  "duration": "01/2025--12/2026",
  "pi": "Name",
  "role": "Principal Investigator",
  "effort": "10\\%",
  "goals": "The major goals are …"
}
```
`costs` is the **annual direct costs**. If the value contains a euro sign (`€`),
`_format_costs` in `generate.py` appends the USD equivalent at `EUR_USD_RATE`
(1.1), e.g. `20{,}000\,€` renders as `20{,}000\,€ (≈ $22,000, converted from euro
at a 1.1 exchange rate)`. Already-USD or `N/A` values pass through unchanged.

**New mentee** — append to `mentoring.current_mentees` or `mentoring.past_mentees` in `K_mentoring.json`.

**New lecture** — append `{"text": "Title, Event, Institution, Location", "year": "YYYY"}` to the appropriate list in `O_lectures.json`.

**New position** — append to the relevant array (`academic`, `hospital`, or `other`) in `E_positions.json`.

## Generator internals (`cvkit/generate.py`)

`load_data(dir)` — globs `<dir>/*.json` in sorted order, merges all top-level keys
into one dict, and adds `bib_keywords` (from `<dir>/*.bib`). `build_tex(data)`
returns the full LaTeX string. `cvkit/compile.py::compile_pdf(tex, data, out)`
runs the LaTeX toolchain in a temp dir and returns the PDF path.

`breakable_table(col_spec, header_cells, rows)` — low-level full-width bordered
`xltabular` (breaks across pages, header row repeats via `\endhead`). Blank lines
at start/end force LaTeX vertical mode (prevents inline table placement).

`event_table(headers, rows, left_cols)` — semantic wrapper over `breakable_table`;
appends the uniform `DATE_W` date column. Use this for every record/event section.

`kv_table(col_spec, rows)` — bold-key two-column layout, also breakable.

Breakable tables get no extra surrounding glue: `\LTpre`/`\LTpost` are set to `0pt`
in the preamble so they match the spacing of the old non-breakable tables.

`sec_a()` … `sec_o()` — one function per CV section; each reads its key(s) from the merged dict.

All block macros (`\grantblock`, `\menteetable`, `\pastmenteetable`, `\cvsubsec`, `\cvsection`) start with `\par` to guarantee vertical mode when called.
