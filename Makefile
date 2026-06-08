.PHONY: pdf tex clean

# Build the CV PDF into cv_out/ (LaTeX runs in a temp dir; only the PDF is kept).
pdf:
	uv run compile_cv --data cv_data --out cv_out

# Generate only the .tex (no LaTeX compilation).
tex:
	uv run compile_cv --data cv_data --out cv_out --tex-only

clean:
	rm -rf cv_out
