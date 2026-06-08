"""cvkit — generate a WCM faculty CV (XeLaTeX) from JSON + BibTeX data."""
from .compile import compile_pdf
from .generate import build_tex, load_data

__version__ = "0.1.0"
__all__ = ["load_data", "build_tex", "compile_pdf", "__version__"]
