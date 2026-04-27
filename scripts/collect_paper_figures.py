from __future__ import annotations

import csv
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import FIGURES_DIR, MANUSCRIPT_NOTES_DIR


FIGURES = [
    {
        "figure_no": "Fig. 1",
        "section": "Results - Postural Baseline",
        "tex_label": "fig:posture",
        "source": "nb02_fig03_rr_psd_postural.pdf",
        "purpose": "Primary posture RR/PSD comparison used in the main text.",
    },
    {
        "figure_no": "Fig. 2",
        "section": "Results - Breath-Hold",
        "tex_label": "fig:breathhold",
        "source": "nb03_fig02_e2_effort_comparison.pdf",
        "purpose": "Main breath-hold comparison figure.",
    },
    {
        "figure_no": "Fig. 3",
        "section": "Results - Walking Challenge",
        "tex_label": "fig:walking",
        "source": "nb04_fig01_e3_tachogram.pdf",
        "purpose": "Walking tachogram used in the main text.",
    },
    {
        "figure_no": "Fig. 4",
        "section": "Results - Paced Breathing",
        "tex_label": "fig:psd_overlay",
        "source": "nb05_fig02_e4a_psd_overlay.pdf",
        "purpose": "Paced-breathing PSD overlay.",
    },
    {
        "figure_no": "Fig. 5",
        "section": "Results - Paced Breathing",
        "tex_label": "fig:peak_tracking",
        "source": "nb05_fig03_e4a_peak_freq.pdf",
        "purpose": "Expected-vs-measured breathing peak tracking.",
    },
    {
        "figure_no": "Fig. 6",
        "section": "Results - Paced Breathing",
        "tex_label": "fig:lfhf_rmssd",
        "source": "nb05_fig04_e4a_lfhf_crossover.pdf",
        "purpose": "LF/HF and RMSSD dissociation figure.",
    },
    {
        "figure_no": "Fig. 7",
        "section": "Results - Cross-Experiment Synthesis",
        "tex_label": "fig:integration",
        "source": "nb06_fig01_autonomic_spectrum.pdf",
        "purpose": "Cross-experiment operating map.",
    },
    {
        "figure_no": "Fig. A1",
        "section": "Appendix - Sleep",
        "tex_label": "fig:sleep",
        "source": "nb06_fig04_e4b_sleep_trajectory.pdf",
        "purpose": "Partial sleep-onset trajectory.",
    },
    {
        "figure_no": "Fig. A2",
        "section": "Appendix - Pipeline Validation",
        "tex_label": "fig:pipeline",
        "source": "nb06_fig03_pipeline_validation.pdf",
        "purpose": "Dual-path detector validation figure.",
    },
]


def write_manifest(rows: list[dict]) -> None:
    MANUSCRIPT_NOTES_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = MANUSCRIPT_NOTES_DIR / "FIGURE_INDEX.csv"
    md_path = MANUSCRIPT_NOTES_DIR / "FIGURE_INDEX.md"

    fieldnames = ["figure_no", "section", "tex_label", "source", "purpose"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Figure Index",
        "",
        "Canonical manuscript figures are loaded directly from `outputs/figures/`.",
        "",
        "| Figure | Section | TeX label | Source PDF | Purpose |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['figure_no']} | `{row['section']}` | `{row['tex_label']}` | `{row['source']}` | {row['purpose']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    missing = [row["source"] for row in FIGURES if not (FIGURES_DIR / row["source"]).exists()]
    if missing:
        missing_text = "\n".join(f"- {name}" for name in missing)
        raise FileNotFoundError(
            "Missing canonical manuscript figure PDFs in outputs/figures:\n"
            f"{missing_text}"
        )

    write_manifest(FIGURES)
    print(
        f"Wrote figure manifest for {len(FIGURES)} figures to "
        f"{MANUSCRIPT_NOTES_DIR}"
    )


if __name__ == "__main__":
    main()
