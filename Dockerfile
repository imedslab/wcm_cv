# syntax=docker/dockerfile:1
#
# Self-contained CV builder: TeX Live (xelatex + bibtex) + FreeSans + uv + cvkit.
# Your data is NOT baked in — mount it at runtime:
#
#   docker build -t cvkit .
#   docker run --rm -v "$PWD/cv_data:/data" -v "$PWD/cv_out:/out" cvkit
#
FROM debian:bookworm-slim

# TeX Live (every package the CV preamble uses), the FreeSans font (registered
# with fontconfig so \setmainfont{FreeSans} resolves by name), and Python.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        texlive-xetex \
        texlive-latex-recommended \
        texlive-latex-extra \
        texlive-bibtex-extra \
        texlive-fonts-recommended \
        fonts-freefont-otf \
    && rm -rf /var/lib/apt/lists/*

# uv, copied straight from its official image (no pip needed).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

# Install just the package (own layer → cached unless the code changes).
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

ENTRYPOINT ["compile_cv"]
CMD ["--data", "/data", "--out", "/out"]
