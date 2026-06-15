"""Generate the CV LaTeX source from a folder of JSON data files.

`load_data(dir)` merges every ``*.json`` in the data folder into one dict;
`build_tex(data)` turns that dict into a complete LaTeX document (string).
All string values in the JSON are treated as LaTeX-ready (no auto-escaping).
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def load_data(data_dir: str | Path = "cv_data") -> dict:
    """Merge all *.json files in data_dir into one dict (sorted by filename)."""
    result: dict = {}
    for path in sorted(Path(data_dir).glob("*.json")):
        with open(path, encoding="utf-8") as f:
            result.update(json.load(f))
    if not result:
        raise FileNotFoundError(f"No *.json data files found in {Path(data_dir)!s}")
    # Which §S bibliography categories are non-empty (from the data folder's *.bib).
    result["bib_keywords"] = _bib_keywords(data_dir)
    return result


# ── Shared column widths ────────────────────────────────────────────────
# Every "event/record" table (sec B, C, E, F, G, L, M, N, O) is built so its
# column boundaries line up vertically down the whole CV:
#
#   • the first column uses a shared fixed width when it is a short label
#   • the middle column(s) flex (Y) to absorb slack
#   • the trailing date/year column has ONE uniform width everywhere
#
PRIMARY_W = "5.5cm"   # first column when it is a short label (title / role / degree)
DATE_W    = "3.0cm"   # trailing date / year column — uniform across all sections

# §J Percent-Effort table trailing fixed-width columns.
EFFORT_W = "2.4cm"   # §J "Percent Effort (%)"
DETAIL_W = "5.5cm"   # §J "Involves … trainees?"

# §P Admin + §Q Leadership/Boards tables ("Entity | Role | Dates") share one fixed
# FIRST-column width so their 2nd column (the Role column) starts at the same x.
# Role itself is flexible (Y), so long roles get room and short ones just pad.
ENTITY_W = "7.0cm"

# ── Table helpers ────────────────────────────────────────────────────────
# All tables use tabularx{\linewidth} so they span the full text width.
# Col spec: Y = ragged-right flexible column; L{Ncm} = fixed-width ragged-right.

def breakable_table(col_spec: str, header_cells: list[str], rows: list[list[str]]) -> list[str]:
    """Full-width bordered table that breaks across pages (xltabular + longtable).
    Header row repeats at the top of each page the table spans.
    Blank lines at start/end force LaTeX into vertical mode (paragraph breaks).
    """
    header = " & ".join(r"\textit{" + c + "}" for c in header_cells) + r" \\"
    lines = [
        "",
        r"\noindent\begin{xltabular}{\linewidth}{" + col_spec + "}",
        r"\hline",
        header,
        r"\hline",
        r"\endhead",
    ]
    for row in rows:
        lines.append(" & ".join(row) + r" \\")
        lines.append(r"\hline")
    lines.append(r"\end{xltabular}")
    lines.append("")
    return lines


def event_table(headers: list[str], rows: list[list[str]], left_cols: list[str]) -> list[str]:
    """Breakable 'event / accomplishment' record table (sec B, C, E, F, G, L, M, N, O).

    `left_cols` gives the LaTeX column types for every column EXCEPT the last one;
    a uniform-width date/year column (DATE_W) is always appended, so the trailing
    date columns line up vertically across every section. Breaks across pages with
    the header row repeated at the top of each continuation page.

    With no rows, renders "N/A" instead of an empty header-only table.
    """
    if not rows:
        return ["", r"\noindent N/A", ""]
    col_spec = "|" + "|".join(left_cols + [f"L{{{DATE_W}}}"]) + "|"
    return breakable_table(col_spec, headers, rows)


def kv_table(col_spec: str, rows: list[tuple[str, str]]) -> list[str]:
    """Full-width key-value table (bold keys), breakable across pages."""
    lines = [
        "",
        r"\noindent\begin{xltabular}{\linewidth}{" + col_spec + "}",
        r"\hline",
    ]
    for k, v in rows:
        lines.append(r"\textbf{" + k + "} & " + v + r" \\ \hline")
    lines.append(r"\end{xltabular}")
    lines.append("")
    return lines


# ── Preamble ─────────────────────────────────────────────────────────────

def _font_lines(m: dict) -> list[str]:
    """Main-font setup. With a real meta.font_path directory, load explicit font
    files from it; otherwise look the family up by name among installed system
    fonts. The directory check makes one meta.json portable: an absolute macOS
    font_path is used on that Mac, but ignored (→ system FreeSans) in a Docker
    image / CI where the path doesn't exist."""
    fn = m.get("font_name", "FreeSans")
    fp = m.get("font_path")
    if not fp or not Path(fp).is_dir():
        return [r"\setmainfont{" + fn + "}"]
    return [
        r"\setmainfont{" + fn + "}[",
        r"  BoldFont       = " + m.get("font_bold", fn + "Bold") + ",",
        r"  ItalicFont     = " + m.get("font_italic", fn + "Oblique") + ",",
        r"  BoldItalicFont = " + m.get("font_bold_italic", fn + "BoldOblique") + ",",
        r"  Path           = " + fp + ",",
        r"  Extension      = " + m.get("font_ext", ".ttf"),
        r"]",
    ]


def _highlight_surname(m: dict) -> str:
    """The surname to bold throughout the §S bibliography (the CV owner).
    Explicit ``meta.highlight_surname`` wins; otherwise it is derived from
    ``meta.name`` (the last word before any ``, PhD`` suffix). Returns "" to
    disable bolding."""
    explicit = m.get("highlight_surname")
    if explicit:
        return explicit
    base = m.get("name", "").split(",")[0].strip()
    return base.split()[-1] if base else ""


def preamble(d: dict) -> str:
    m = d["meta"]
    name = m["name"]

    # Bold the CV owner's name in the bibliography (compare the *expansion* of
    # \namepartfamily — biblatex passes the macro, not the string, to \mkbibname*).
    surname = _highlight_surname(m)
    bib_name_bold = []
    if surname:
        rule = r"[1]{\ifdefstring{\namepartfamily}{" + surname + r"}{\textbf{#1}}{#1}}"
        bib_name_bold = [
            r"\renewcommand*{\mkbibnamefamily}" + rule,
            r"\renewcommand*{\mkbibnamegiven}" + rule,
        ]

    lines = [
        "%% Auto-generated by cvkit — edit the JSON data files, not this file.",
        r"\documentclass[10pt,letterpaper]{article}",
        "",
        r"\usepackage{fontspec}",
        *_font_lines(m),
        "",
        r"\usepackage[top=0.6in, bottom=0.6in, left=0.6in, right=0.6in]{geometry}",
        r"\usepackage{array}",
        r"\usepackage{longtable}",
        r"\usepackage{booktabs}",
        r"\usepackage{tabularx}",
        r"\usepackage{xltabular}",
        r"\usepackage{multirow}",
        r"\usepackage{makecell}",
        r"\usepackage{enumitem}",
        r"\usepackage{parskip}",
        r"\usepackage{hyperref}",
        r"\usepackage{fancyhdr}",
        r"\usepackage{lastpage}",
        r"\usepackage{ragged2e}",
        r"\usepackage{xcolor}",
        r"\usepackage[autostyle]{csquotes}",
        # Auto-rendered publication list from refs.bib (bibtex backend — no biber needed).
        r"\usepackage[backend=bibtex, style=numeric, sorting=ydnt, defernumbers=true,"
        r" maxbibnames=99, giveninits=true, doi=true, url=false, isbn=false, eprint=false]{biblatex}",
        r"\addbibresource{refs.bib}",
        "",
        r"\hypersetup{colorlinks=true, urlcolor=black, linkcolor=black}",
        "",
        *bib_name_bold,
        # 'Other' bibliography category = preprints + conference abstracts/posters + media.
        r"\defbibfilter{cvother}{keyword=preprint or keyword=abstract or keyword=media}",
        "",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{4pt}",
        r"\setlength{\tabcolsep}{4pt}",
        # Width of a \multicolumn cell that spans all columns of a full-width table
        # (used by the §K didactic-teaching cards for the Description/Audience rows).
        r"\newlength{\cvspanwidth}",
        r"\setlength{\cvspanwidth}{\dimexpr\textwidth-2\tabcolsep-2\arrayrulewidth\relax}",
        # No extra glue above/below breakable (longtable/xltabular) tables.
        r"\setlength{\LTpre}{0pt}",
        r"\setlength{\LTpost}{0pt}",
        "",
        r"\newcolumntype{L}[1]{>{\RaggedRight\arraybackslash}p{#1}}",
        r"\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}",
        r"\newcolumntype{R}[1]{>{\RaggedLeft\arraybackslash}p{#1}}",
        r"\newcolumntype{Y}{>{\RaggedRight\arraybackslash}X}",
        "",
        # Headings must never strand at the bottom of a page. \nobreak glues the
        # heading to the content that follows, so if they don't both fit, TeX
        # breaks BEFORE the heading and moves it (with its content) to the next
        # page. (We avoid \needspace here: forcing a break right before an
        # xltabular makes longtable emit a phantom repeated \endhead header.)
        r"\newcommand{\cvsection}[2]{%",
        r"  \par\addvspace{10pt}%",
        r"  \noindent\textbf{#1.\quad\underline{#2}}%",
        r"  \par\nobreak\vspace{5pt}\nobreak%",
        r"}",
        "",
        r"\newcommand{\cvsubsec}[1]{%",
        r"  \par\addvspace{5pt}%",
        r"  \noindent\textbf{\underline{#1}}%",
        r"  \par\nobreak\vspace{3pt}\nobreak%",
        r"}",
        "",
        r"\newcommand{\sublabel}[1]{\textit{#1}}",
        "",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        r"\renewcommand{\headrulewidth}{0pt}",
        r"\fancyhead[L]{\small\textit{" + name + r"}}",
        r"\fancyhead[R]{\small\textit{Curriculum Vitae}}",
        r"\fancyfoot[C]{\small\thepage\ of \pageref{LastPage}}",
        "",
        # Funding entry: no borders, indented label lines (matches the WCM template).
        r"\newcommand{\grantfield}[2]{\item \textbf{#1} #2}",
        r"\newcommand{\grantblock}[8]{%",
        r"  \par\vspace{4pt}%",
        r"  \begin{itemize}[leftmargin=1.8em, label={}, labelsep=0pt,"
        r" topsep=2pt, itemsep=1pt, parsep=0pt]",
        r"  \grantfield{Award Source:}{#1}",
        r"  \grantfield{Project title:}{#2}",
        r"  \grantfield{Name of Principal Investigator:}{#5}",
        r"  \grantfield{Your role in project:}{#6}",
        r"  \grantfield{Your percent (\%) effort:}{#7}",
        r"  \grantfield{Annual direct costs:}{#3}",
        r"  \grantfield{Duration of support:}{#4}",
        r"  \grantfield{The major goals of this project are:}{#8}",
        r"  \end{itemize}%",
        r"}",
        "",
        r"\newcommand{\menteetable}[6]{%",
        r"  \par\vspace{4pt}%",
        r"  \noindent\begin{xltabular}{\linewidth}{|L{5.5cm}|Y|}",
        r"  \hline",
        r"  \textbf{Name:}                     & #1 \\ \hline",
        r"  \textbf{Site/Position:}            & #2 \\ \hline",
        r"  \textbf{Expected Period:}          & #3 \\ \hline",
        r"  \textbf{Project/Accomplishments:}  & #4 \\ \hline",
        r"  \textbf{Goals/Expected Outcomes:}  & #5 \\ \hline",
        r"  \textbf{Type of Supervision:}      & #6 \\ \hline",
        r"  \end{xltabular}\par",
        r"}",
        "",
        r"\newcommand{\pastmenteetable}[6]{%",
        r"  \par\vspace{4pt}%",
        r"  \noindent\begin{xltabular}{\linewidth}{|L{5.5cm}|Y|}",
        r"  \hline",
        r"  \textbf{Name:}                     & #1 \\ \hline",
        r"  \textbf{Site/Position:}            & #2 \\ \hline",
        r"  \textbf{Mentoring Period:}         & #3 \\ \hline",
        r"  \textbf{Project/Accomplishments:}  & #4 \\ \hline",
        r"  \textbf{Current Position:}         & #5 \\ \hline",
        r"  \textbf{Type of Supervision:}      & #6 \\ \hline",
        r"  \end{xltabular}\par",
        r"}",
    ]
    return "\n".join(lines)


# ── Title page ────────────────────────────────────────────────────────────

def title_page(d: dict) -> str:
    m = d["meta"]
    lines = [
        r"\thispagestyle{empty}",
        r"\begin{center}",
        r"  \textbf{Weill Cornell Medical College, Cornell University}\\",
        r"  \textbf{Faculty Curriculum Vitae Template}\\[8pt]",
        r"  \begin{tabular}{@{}ll@{}}",
        r"    \textbf{Name:}               & " + m["name"] + r" \\[2pt]",
        r"    \textbf{Signature:}          & \\[2pt]",
        # Always the compile date (\today), so it self-updates on every rebuild.
        r"    \textbf{Date of Preparation:}& \today \\",
        r"  \end{tabular}",
        r"\end{center}",
        r"\vspace{6pt}",
    ]
    return "\n".join(lines)


# ── Section A: Personal Data ──────────────────────────────────────────────

def sec_a(d: dict) -> str:
    p = d["personal_data"]
    lines = [
        r"\cvsection{A}{PERSONAL DATA}",
        r"\begin{tabular}{@{}ll@{}}",
        r"  Office address:    & " + p["office_address"] + r" \\[2pt]",
        r"  Office telephone:  & " + p["office_telephone"] + r" \\[2pt]",
        r"  Home address:      & " + p["home_address"] + r" \\[6pt]",
        r"  Cell phone:        & " + p["cell_phone"] + r" \\[2pt]",
        r"  Email address -- Work:     & " + p["email_work"] + r" \\[2pt]",
        r"  Email address -- Personal: & " + p["email_personal"] + r" \\[6pt]",
        r"\end{tabular}",
        "",
        r"\noindent\begin{tabularx}{\linewidth}{@{}L{11cm}Y@{}}",
        r"  Is your eligibility to work in the U.S. based on an employment visa? & "
        + p.get("work_visa", "N/A") + r" \\[2pt]",
        r"  If yes, please provide Visa type (e.g. J-1, H-1B, E-3, O-1, TN): & "
        + p.get("visa_type", "N/A") + r" \\",
        r"\end{tabularx}",
    ]
    return "\n".join(lines)


# ── Section B: Education ──────────────────────────────────────────────────

def sec_b(d: dict) -> str:
    edu = d["education"]
    lines = [r"\cvsection{B}{EDUCATION}"]
    lines.append(r"\noindent\textbf{Academic Degree(s)} \sublabel{(Bachelor's and higher)}")
    lines.append(r"\vspace{4pt}")
    lines += event_table(
        ["Degree, include", "Institution name, city and state", "Dates attended", "Year Awarded"],
        [[x["degree"], x["institution"], x["dates"], x["year"]] for x in edu["academic_degrees"]],
        [f"L{{{PRIMARY_W}}}", "Y", f"L{{{DATE_W}}}"],
    )
    lines.append(r"\noindent\textbf{Other Educational Experiences} \sublabel{(i.e., certificates, etc)}")
    lines.append(r"\vspace{4pt}")
    lines += event_table(
        ["Description", "Institution, city and state", "Dates attended (mm/yy -- mm/yy)"],
        [[e["description"], e["institution"], e["dates"]] for e in edu["other_experiences"]],
        [f"L{{{PRIMARY_W}}}", "Y"],
    )
    return "\n".join(lines)


# ── Section C: Postdoctoral Training ─────────────────────────────────────

def sec_c(d: dict) -> str:
    lines = [r"\cvsection{C}{POSTDOCTORAL TRAINING}"]
    lines += event_table(
        ["Title, include area of training", "Institution, city and state", "Dates (mm/yy -- mm/yy)"],
        [[p["title"], p["institution"], p["dates"]] for p in d["postdoctoral_training"]],
        [f"L{{{PRIMARY_W}}}", "Y"],
    )
    return "\n".join(lines)


# ── Section D: Employment Status ─────────────────────────────────────────

def sec_d(d: dict) -> str:
    e = d["employment_status"]
    lines = [
        r"\cvsection{E}{EMPLOYMENT STATUS}",
        r"\begin{tabular}{@{}ll@{}}",
        r"  \textbf{Name of Current Employer(s):} & " + e["employer"] + r" \\[2pt]",
        r"  \textbf{Current Employment Status:}   & " + e["status"] + r" \\",
        r"\end{tabular}",
    ]
    return "\n".join(lines)


# ── Section F: Licensure, Board Certification ────────────────────────────

def sec_licensure(d: dict) -> str:
    lic = d.get("licensure", {})
    lines = [r"\cvsection{F}{LICENSURE, BOARD CERTIFICATION}"]
    lines.append(r"\noindent\textbf{Licensure:} " + lic.get("licensure", "N/A") + r"\par")
    lines.append(r"\noindent\textbf{Board Certification:} " + lic.get("board_certification", "N/A"))
    return "\n".join(lines)


# ── Section G: Institutional/Hospital Affiliation ────────────────────────

def sec_affiliation(d: dict) -> str:
    aff = d.get("affiliation", {})
    lines = [r"\cvsection{G}{INSTITUTIONAL/HOSPITAL AFFILIATION}"]
    lines += kv_table(
        f"|L{{{PRIMARY_W}}}|Y|",
        [
            ("Primary Hospital Affiliation:", aff.get("primary_hospital", "N/A")),
            ("Other Hospital Affiliations:", aff.get("other_hospital", "N/A")),
            ("Other Institutional Affiliations:", aff.get("other_institutional", "N/A")),
        ],
    )
    return "\n".join(lines)


# ── Section E: Professional Positions ────────────────────────────────────

def _positions_table(positions: list[dict]) -> list[str]:
    return event_table(
        ["Title", "Institution, city and state", "Dates (mm/yy -- mm/yy)"],
        [[p["title"], p["institution"], p["dates"]] for p in positions],
        [f"L{{{PRIMARY_W}}}", "Y"],
    )


def sec_e(d: dict) -> str:
    pos = d["positions"]
    lines = [r"\cvsection{D}{PROFESSIONAL POSITIONS \& EMPLOYMENT}"]
    lines.append(r"\cvsubsec{Academic Appointments}")
    lines.append(r"\vspace{2pt}")
    lines += _positions_table(pos["academic"])
    lines.append(r"\cvsubsec{Hospital Appointments}")
    lines.append(r"\vspace{2pt}")
    lines += _positions_table(pos["hospital"])
    lines.append(r"\cvsubsec{Other Professional Positions \& Employment}")
    lines.append(r"\vspace{2pt}")
    lines += _positions_table(pos["other"])
    return "\n".join(lines)


# ── Section F: Honors & Awards ────────────────────────────────────────────

def sec_f(d: dict) -> str:
    lines = [r"\cvsection{H}{HONORS, AWARDS}"]
    lines += event_table(
        ["Name of award", "Organization", "Date awarded"],
        [[h["award"], h["source"], h["year"]] for h in d["honors"]],
        [f"L{{{PRIMARY_W}}}", "Y"],
    )
    return "\n".join(lines)


# ── Section G: Professional Organizations ────────────────────────────────

def sec_g(d: dict) -> str:
    lines = [r"\cvsection{I}{PROFESSIONAL ORGANIZATIONS AND SOCIETY MEMBERSHIPS}"]
    lines.append(r"\vspace{4pt}")
    lines += event_table(
        ["Organization", "Date (yyyy--yyyy)"],
        [[o["name"], o["dates"]] for o in d["organizations"]],
        ["Y"],
    )
    return "\n".join(lines)


# ── Section J: Percent Effort & Institutional Responsibilities ───────────

def sec_effort(d: dict) -> str:
    pe = d.get("percent_effort", {})
    lines = [r"\cvsection{J}{PERCENT EFFORT AND INSTITUTIONAL RESPONSIBILITIES}"]
    if pe.get("note"):
        lines.append(r"\noindent\textit{" + pe["note"] + r"}")
        lines.append(r"\vspace{4pt}")
    rows = [[r["activity"], r.get("effort", "TODO"), r.get("involves_trainees", "TODO")]
            for r in pe.get("rows", [])]
    rows.append([r"\textbf{Total}", pe.get("total", r"100\%"), ""])
    lines += breakable_table(
        f"|Y|L{{{EFFORT_W}}}|L{{{DETAIL_W}}}|",
        ["Weill Cornell Activity (Current or Anticipated)", "Percent Effort (\\%)",
         "Involves WCM students/research trainees? (Yes/No)"],
        rows,
    )
    return "\n".join(lines)


# ── Section K: Educational Contributions ─────────────────────────────────

def _didactic_card(c: dict) -> list[str]:
    """One per didactic-teaching activity, in the WCM template layout:
    a bordered Activity | Role(s) | Dates header+value, then full-width
    Description and Audience rows. Kept intact (non-breakable) per card.
    """
    activity = c["course"] + r"\newline\textit{" + c["institution"] + "}"
    span = r"\multicolumn{3}{|>{\RaggedRight\arraybackslash}p{\cvspanwidth}|}"
    return [
        "",
        r"\par\vspace{4pt}",
        r"\noindent\begin{tabularx}{\linewidth}{|Y|L{3.2cm}|L{3.0cm}|}",
        r"\hline",
        r"\textit{Activity} & \textit{Role(s)} & \textit{Dates} \\ \hline",
        activity + " & " + c["role"] + " & " + c["terms"] + r" \\ \hline",
        span + r"{\textbf{Description:} " + c["content"] + r"} \\ \hline",
        span + r"{\textbf{Audience:} " + c.get("audience", "TODO") + r"} \\ \hline",
        r"\end{tabularx}",
        "",
    ]


def sec_h(d: dict) -> str:
    ec = d["educational_contributions"]
    lines = [r"\cvsection{K}{EDUCATIONAL CONTRIBUTIONS}"]
    lines.append(r"\cvsubsec{Didactic teaching:}")
    lines.append(r"\vspace{2pt}")
    lines.append(r"\noindent\textit{Courses with primary teaching responsibility}")
    for c in ec["primary_courses"]:
        lines += _didactic_card(c)
    lines.append(r"\vspace{2pt}")
    lines.append(r"\noindent\textit{Contributions to the courses of others}")
    for c in ec["contributions"]:
        lines += _didactic_card(c)
    lines.append(r"\cvsubsec{Clinical teaching:}")
    lines.append(r"\noindent " + ec["clinical_teaching"])
    lines.append(r"\cvsubsec{Administrative teaching:}")
    lines.append(r"\begin{itemize}[leftmargin=1.5em, topsep=2pt, itemsep=1pt]")
    for item in ec["administrative"]:
        lines.append(r"  \item " + item)
    lines.append(r"\end{itemize}")
    lines.append(r"\cvsubsec{Other education/outreach activities:}")
    lines.append(r"\noindent " + ec["other_outreach"])
    return "\n".join(lines)


# ── Section I: Clinical Practice ─────────────────────────────────────────

def sec_i(d: dict) -> str:
    c = d["clinical_practice"]
    lines = [
        r"\cvsection{L}{CLINICAL PRACTICE, INNOVATION, AND LEADERSHIP}",
        r"\noindent\textbf{Clinical Practice:} " + c["practice"] + r"\par",
        r"\noindent\textbf{Clinical Innovations:} " + c["innovations"] + r"\par",
        r"\noindent\textbf{Clinical Leadership:} " + c["leadership"],
    ]
    return "\n".join(lines)


# ── Section J: Research ───────────────────────────────────────────────────

# Grants are recorded in their award currency. Euro amounts are reported with a
# USD equivalent so the WCM "Annual direct costs" line is dollar-denominated; the
# conversion is noted inline rather than silently overwriting the original.
EUR_USD_RATE = 1.1


def _thousands(n: int) -> str:
    """Group an integer with LaTeX-safe thousands separators (12345 -> 12{,}345)."""
    return f"{n:,}".replace(",", "{,}")


def _format_costs(costs: str) -> str:
    """Render a grant's annual direct costs. Euro amounts (the string contains €)
    get their USD equivalent appended at EUR_USD_RATE, noting the conversion; any
    other value (already-USD, "N/A", etc.) passes through verbatim."""
    if "€" not in costs:
        return costs
    # Strip LaTeX dressing (thousands {,}, thin spaces \,, the € glyph) to the digits.
    amount = re.sub(r"[^0-9.]", "", costs.replace("{,}", "").replace(r"\,", ""))
    if not amount:
        return costs
    usd = round(float(amount) * EUR_USD_RATE)
    rate = f"{EUR_USD_RATE:g}"
    return (costs + r" ($\approx$ \$" + _thousands(usd)
            + ", converted from euro at a " + rate + " exchange rate)")


def sec_j(d: dict) -> str:
    r = d["research"]
    lines = [r"\cvsection{M}{RESEARCH}"]
    lines.append(r"\cvsubsec{Research Activities}")
    lines.append(r"\begin{itemize}[leftmargin=1.5em, topsep=2pt, itemsep=2pt]")
    for act in r["activities"]:
        label = act["label"]
        if act.get("subitems"):
            lines.append(r"  \item \textbf{" + label + r":}")
            lines.append(r"    \begin{itemize}[leftmargin=1.5em, topsep=1pt, itemsep=1pt]")
            for sub in act["subitems"]:
                lines.append(r"      \item " + sub)
            lines.append(r"    \end{itemize}")
        else:
            lines.append(r"  \item \textbf{" + label + r":} " + (act.get("content") or ""))
    lines.append(r"\end{itemize}")

    lines.append(r"\noindent\textbf{IRB protocols:} " + r.get("irb_protocols", "N/A"))

    lines.append(r"\cvsubsec{Research Support}")
    lines.append(r"\noindent\textbf{Current Research Funding:} " + r["current_funding"] + r"\par")
    lines.append(r"\vspace{2pt}")
    lines.append(r"\noindent\textbf{Past (Completed) Funding:}")
    lines.append(r"\vspace{4pt}")
    for g in r["past_grants"]:
        lines.append(
            r"\grantblock"
            + "{" + g["source"] + "}"
            + "{" + g["title"] + "}"
            + "{" + _format_costs(g["costs"]) + "}"
            + "{" + g["duration"] + "}"
            + "{" + g["pi"] + "}"
            + "{" + g["role"] + "}"
            + "{" + g["effort"] + "}"
            + "{" + g.get("goals", "TODO") + "}"
        )

    lines.append(r"\vspace{6pt}")
    lines.append(r"\noindent\textbf{Pending Funding:}")
    pending = r.get("pending_grants", [])
    if pending:
        lines.append(r"\vspace{4pt}")
        for g in pending:
            lines.append(
                r"\grantblock"
                + "{" + g["source"] + "}"
                + "{" + g["title"] + "}"
                + "{" + _format_costs(g["costs"]) + "}"
                + "{" + g["duration"] + "}"
                + "{" + g["pi"] + "}"
                + "{" + g["role"] + "}"
                + "{" + g["effort"] + "}"
            )
    else:
        lines.append(r" None.")

    lines.append(r"\vspace{6pt}")
    lines.append(r"\cvsubsec{Patents \& Inventions:}")
    patents = r.get("patents", [])
    if patents:
        lines.append(r"\begin{enumerate}[leftmargin=2em, topsep=2pt]")
        for p in patents:
            lines.append(r"  \item \textbf{Patent:} " + p["title"] + " (" + p["id"] + r")\\")
            lines.append(r"    {\small\url{" + p["url"] + r"}}\\")
            lines.append(r"    \textit{Status: " + p["status"] + "}")
        lines.append(r"\end{enumerate}")
    else:
        lines.append(r"\noindent N/A")
    return "\n".join(lines)


# ── Section K: Mentoring ──────────────────────────────────────────────────

def _fmt_proj(mentee: dict) -> str:
    """Build the Project/Accomplishments cell: always a bold 'Project:' label, plus
    a bold 'Accomplishments:' block when present (so every mentee cell looks alike).
    """
    proj = r"\textbf{Project:} " + mentee.get("project", "")
    acc  = mentee.get("accomplishments") or ""
    if acc:
        # Use a paragraph break (\par), NOT \\ — inside a tabularx/xltabular cell
        # \\ ends the table ROW, which would spill "Accomplishments" into column 1.
        return proj + r"\par\vspace{4pt}\textbf{Accomplishments:} " + acc
    return proj


def _fmt_goals(goals: str) -> str:
    """Put the 'Expected outcomes' clause on its own line within the
    Goals/Outcomes cell, mirroring the Project/Accomplishments layout.
    Uses \\par (a row break \\\\ would spill into column 1).
    """
    for marker in (r"\textbf{Expected outcomes:}", r"\textbf{Expected Outcomes:}"):
        if marker in goals:
            goals = goals.replace(" " + marker, marker).replace(
                marker, r"\par\vspace{4pt}" + marker)
    return goals


def sec_k(d: dict) -> str:
    m = d["mentoring"]
    lines = [r"\cvsection{N}{MENTORING}"]
    lines.append(r"\noindent\textbf{Leadership and mentoring in programs:} " + m["leadership_programs"] + r"\par")
    lines.append(r"\vspace{6pt}")
    lines.append(r"\noindent\textbf{Institutional Training Grants and Mentored Trainee Grants:}")
    lines.append(r"\vspace{4pt}")
    for tg in m["training_grants"]:
        lines += kv_table(
            f"|L{{{PRIMARY_W}}}|Y|",
            [
                ("Award Source:", tg["source"]),
                ("Project Title:", tg["title"]),
                ("Duration:", tg["duration"]),
            ],
        )
    lines.append(r"\vspace{6pt}")
    lines.append(r"\cvsubsec{Current Mentees:}")
    lines.append(r"\vspace{2pt}")
    for mt in m["current_mentees"]:
        lines.append(
            r"\menteetable"
            + "{" + mt["name"] + "}"
            + "{" + mt["position"] + "}"
            + "{" + mt["period"] + "}"
            + "{" + _fmt_proj(mt) + "}"
            + "{" + _fmt_goals(mt["goals"]) + "}"
            + "{" + mt["supervision"] + "}"
        )
    lines.append(r"\vspace{8pt}")
    lines.append(r"\cvsubsec{Past Mentees:}")
    lines.append(r"\vspace{2pt}")
    for mt in m["past_mentees"]:
        lines.append(
            r"\pastmenteetable"
            + "{" + mt["name"] + "}"
            + "{" + mt["position"] + "}"
            + "{" + mt["period"] + "}"
            + "{" + _fmt_proj(mt) + "}"
            + "{" + mt["current_position"] + "}"
            + "{" + mt["supervision"] + "}"
        )
    return "\n".join(lines)


# ── Section L: Institutional Leadership ──────────────────────────────────

def sec_l(d: dict) -> str:
    lines = [r"\cvsection{O}{INSTITUTIONAL LEADERSHIP ACTIVITIES}"]
    lines += event_table(
        ["Role(s)/Position", "Institution/Location", "Dates (yyyy--yyyy)"],
        [[ldr["role"], ldr["institution"], ldr["dates"]] for ldr in d["leadership"]],
        [f"L{{{PRIMARY_W}}}", "Y"],
    )
    return "\n".join(lines)


# ── Section M: Institutional Admin ───────────────────────────────────────

def sec_m(d: dict) -> str:
    lines = [r"\cvsection{P}{INSTITUTIONAL ADMINISTRATIVE ACTIVITIES}"]
    # In the data, the "role" field holds the committee/body name and "activity"
    # holds the person's role — map them to the template's columns accordingly.
    lines += event_table(
        ["Name of Committee", "Role (i.e., member, secretary, etc.)", "Dates (yyyy--yyyy)"],
        [[a["role"], a["activity"], a["dates"]] for a in d["admin"]],
        [f"L{{{ENTITY_W}}}", "Y"],
    )
    return "\n".join(lines)


# ── Section N: Extramural ─────────────────────────────────────────────────

def _boards_table(boards: list[dict]) -> list[str]:
    return event_table(
        ["Organization (Institution/Location)", "Role (i.e., member, fellow, etc.)",
         "Dates (yyyy--yyyy)"],
        [[b["organization"], b["role"], b["dates"]] for b in boards],
        [f"L{{{ENTITY_W}}}", "Y"],
    )


def sec_n(d: dict) -> str:
    ext = d["extramural"]
    lines = [r"\cvsection{Q}{EXTRAMURAL PROFESSIONAL RESPONSIBILITIES}"]

    lines.append(r"\cvsubsec{Leadership in Extramural Organizations}")
    lines.append(r"\vspace{2pt}")
    lines += event_table(
        ["Organization", "Role (i.e., officer, secretary, chair, etc.)", "Dates (yyyy--yyyy)"],
        [[ldr["organization"], ldr["role"], ldr["dates"]] for ldr in ext["leadership"]],
        [f"L{{{ENTITY_W}}}", "Y"],
    )

    lines.append(r"\cvsubsec{Service on Boards and/or Committees}")
    lines.append(r"\vspace{2pt}")
    for label, key in (("Regional", "boards_regional"), ("National", "boards_national"),
                       ("International", "boards_international")):
        lines.append(r"\noindent\textit{" + label + r"}\par")
        lines.append(r"\vspace{4pt}")
        lines += _boards_table(ext.get(key, []))

    lines.append(r"\cvsubsec{Grant Reviewing/Study Sections}")
    lines.append(r"\vspace{2pt}")
    lines += event_table(
        ["Organization Name", "Dates (yyyy--yyyy)"],
        [[g["organization"], g["year"]] for g in ext["grant_reviewing"]],
        ["Y"],
    )

    lines.append(r"\cvsubsec{Editorial Activities}")
    lines.append(r"\vspace{2pt}")
    ed = ext["editorial"]
    lines += kv_table(
        f"|L{{{PRIMARY_W}}}|Y|",
        [
            ("Editor/Co-Editor:", ed["editor"]),
            ("Editorial Board Membership:", ed["board"]),
        ],
    )

    lines.append(r"\noindent\textbf{Journal Reviewing/Ad hoc Reviewing:}")
    lines.append(r"\begin{itemize}[leftmargin=1.5em, topsep=2pt, itemsep=1pt]")
    for j in ext["ad_hoc_reviewing"]:
        lines.append(r"  \item " + j["text"] + ": " + j["dates"])
    lines.append(r"\end{itemize}")

    return "\n".join(lines)


# ── Section O: Invited Lectures ───────────────────────────────────────────

def _lectures_table(lectures: list[dict]) -> list[str]:
    return event_table(
        ["Title, Event, Institution, Location", "Year"],
        [[lec["text"], lec["year"]] for lec in lectures],
        ["Y"],
    )


def sec_o(d: dict) -> str:
    lec = d["invited_lectures"]
    lines = [r"\cvsection{R}{INVITATIONS TO SPEAK/PRESENT}"]
    for label, key in (("Regional", "regional"), ("National", "national"),
                       ("International", "international")):
        lines.append(r"\noindent\textit{" + label + r"}\par")
        lines.append(r"\vspace{4pt}")
        lines += _lectures_table(lec.get(key, []))
    return "\n".join(lines)


# ── Section S: Bibliography ───────────────────────────────────────────────

def _bib_keywords(data_dir: str | Path) -> set[str]:
    """All keyword tokens used across every *.bib in data_dir (lower-cased), so we
    can tell which template categories are non-empty without re-implementing biber.
    Computed at load time and stashed in the data dict under 'bib_keywords'."""
    kws: set[str] = set()
    for bib in Path(data_dir).glob("*.bib"):
        text = bib.read_text(encoding="utf-8")
        for m in re.finditer(r"keywords\s*=\s*\{([^}]*)\}", text, re.IGNORECASE):
            kws.update(tok.strip().lower() for tok in m.group(1).split(","))
    return kws


def sec_bibliography(d: dict) -> str:
    """§S Bibliography in the official template's five categories, auto-rendered
    from refs.bib via biblatex. Continuous numbering across categories
    (defernumbers + resetnumbers=false). Headings always shown (template form);
    categories with no entries print 'None to date.' instead of an empty list.
    """
    kws = d.get("bib_keywords", set())
    # (heading, has-entries?, \printbibliography selector)
    cats = [
        ("Peer-reviewed Research Articles", "paper" in kws,            "keyword=paper"),
        ("Reviews and Editorials",          "review" in kws,           "keyword=review"),
        ("Books",                           "books" in kws,            "keyword=books"),
        ("Chapters",                        "chapter" in kws,          "keyword=chapter"),
        ("Other (media, podcasts, etc.)",
         bool({"preprint", "abstract", "media"} & kws),                "filter=cvother"),
    ]
    lines = [r"\cvsection{S}{BIBLIOGRAPHY}"]
    # bibtex backend only processes cited entries, so pull in the whole .bib.
    lines.append(r"\nocite{*}")
    first = True
    for title, present, selector in cats:
        lines.append(r"\cvsubsec{" + title + "}")
        if present:
            reset = "" if first else ", resetnumbers=false"
            lines.append(r"\printbibliography[heading=none, " + selector + reset + "]")
            first = False
        else:
            lines.append(r"\noindent None to date.\par\vspace{2pt}")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────

def build_tex(d: dict) -> str:
    """Assemble the whole CV (preamble + sections A–S) into one LaTeX string."""
    parts = [
        preamble(d),
        "",
        r"\begin{document}",
        "",
        title_page(d),
        "",
        sec_a(d),            # A  Personal Data
        "",
        sec_b(d),            # B  Education
        "",
        sec_c(d),            # C  Postdoctoral Training
        "",
        sec_e(d),            # D  Professional Positions & Employment
        "",
        sec_d(d),            # E  Employment Status
        "",
        sec_licensure(d),    # F  Licensure, Board Certification
        "",
        sec_affiliation(d),  # G  Institutional/Hospital Affiliation
        "",
        sec_f(d),            # H  Honors, Awards
        "",
        sec_g(d),            # I  Professional Organizations & Society Memberships
        "",
        sec_effort(d),       # J  Percent Effort & Institutional Responsibilities
        "",
        sec_h(d),            # K  Educational Contributions
        "",
        sec_i(d),            # L  Clinical Practice, Innovation, and Leadership
        "",
        sec_j(d),            # M  Research
        "",
        sec_k(d),            # N  Mentoring
        "",
        sec_l(d),            # O  Institutional Leadership Activities
        "",
        sec_m(d),            # P  Institutional Administrative Activities
        "",
        sec_n(d),            # Q  Extramural Professional Responsibilities
        "",
        sec_o(d),            # R  Invitations to Speak/Present
        "",
        sec_bibliography(d), # S  Bibliography
        "",
        r"\end{document}",
    ]
    return "\n".join(parts)
