# Project Rules — HW5 ECG/HRV Analysis

## CRITICAL: Notebook Protection
- **NEVER** run `scripts/build_notebooks.py` — it overwrites ALL notebooks and destroys manual edits.
- **NEVER** execute any script that batch-writes to `notebooks/*.ipynb` without explicit user confirmation.
- **NEVER** use `nbformat.write()` or `json.dump()` to overwrite an existing notebook unless the user explicitly asks for it.
- When modifying notebooks, use `NotebookEdit` (single-cell edits) instead of `Write` (full overwrite).
- Before committing, always check `git diff --stat` to verify no unexpected notebook changes.

## Commit Discipline
- After making changes to notebooks or src/ files, **always remind the user to commit**.
- Never run `git add -A` or `git add .` — always add specific files.

## Figure Naming Convention
- All figures use `PL.save_figure(fig, "nbXX_figYY_description.pdf")` format.
- FIG_DIR = `outputs/figures` (NOT `outputs/paper_figures_png`).
- Output format is PDF, not PNG.

## Project Structure
- `notebooks/` — Jupyter notebooks (primary work, often edited in Jupyter)
- `src/` — shared Python modules (config, pipeline, plotting)
- `outputs/figures/` — generated figure PDFs
- `outputs/tables/` — generated CSV tables
- `manuscript/` — LaTeX paper source
