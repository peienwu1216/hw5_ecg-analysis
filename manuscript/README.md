# Manuscript Workspace

`manuscript/` is the local LaTeX workspace for the paper.

## Layout

- [main.tex](/Users/wupeien/Developer/hw5_ecg-analysis/manuscript/main.tex): main IEEE manuscript source
- [notes/](/Users/wupeien/Developer/hw5_ecg-analysis/manuscript/notes): planning notes, figure mapping, Overleaf notes
- [build/](/Users/wupeien/Developer/hw5_ecg-analysis/manuscript/build): local LaTeX build output
- [legacy/figures_png](/Users/wupeien/Developer/hw5_ecg-analysis/manuscript/legacy/figures_png): old duplicated PNG copies kept only for reference

## Figure source of truth

The manuscript now loads figures directly from [outputs/figures](/Users/wupeien/Developer/hw5_ecg-analysis/outputs/figures), and new notebook exports should use `src.plotting.save_figure(...)` so the files are written as PDF.

## Local build

Run from [manuscript/](/Users/wupeien/Developer/hw5_ecg-analysis/manuscript):

```bash
latexmk -pdf main.tex
```

`latexmkrc` sends auxiliary and PDF output into `manuscript/build/`.

## Git: what to track

**Commit:** `main.tex`, `latexmkrc`, this `README`, and anything you add under `notes/` (or other source-only assets you intend to share).

**Do not commit:** anything under `manuscript/build/`, or stray `main.pdf` / `*.aux` / `*.log` in `manuscript/` (e.g. from running `pdflatex` without `-output-directory=build`). Those patterns are listed in the repo root `.gitignore`.

## Refresh figure manifest

From the repo root:

```bash
python scripts/collect_paper_figures.py
```

This writes [FIGURE_INDEX.md](/Users/wupeien/Developer/hw5_ecg-analysis/manuscript/notes/FIGURE_INDEX.md) and the CSV companion under `manuscript/notes/`.
