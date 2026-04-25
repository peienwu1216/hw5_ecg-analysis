from __future__ import annotations

import csv
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIG_SRC = REPO_ROOT / "outputs" / "figures"
FIG_DST = REPO_ROOT / "outputs" / "paper_figures_png"


FIGURES = [
    {
        "bucket": "APP",
        "order": "A01",
        "notebook": "00_quality_check",
        "title": "data_quality_overview",
        "source": "00_quality_overview.png",
        "dest": "APP_A01_nb00_data_quality_overview.png",
        "role": "quality_control",
        "note": "15-session ECG sanity panel; useful for methods appendix or lab notebook, not main text.",
    },
    {
        "bucket": "APP",
        "order": "A02",
        "notebook": "01_pipeline_validation",
        "title": "pipeline_validation_e1pre",
        "source": "01_e1pre_validation.png",
        "dest": "APP_A02_nb01_pipeline_validation_e1pre.png",
        "role": "methods_appendix",
        "note": "Teaching pipeline vs NeuroKit2 reference on E1PRE; best kept near Methods / supplement.",
    },
    {
        "bucket": "MAIN",
        "order": "01",
        "notebook": "02_experiment_1",
        "title": "exp1_postural_tachograms",
        "source": "11_postural_tachograms_ieee.png",
        "dest": "MAIN_01_nb02_exp1_postural_tachograms.png",
        "role": "main_text",
        "note": "Figure 1.1",
    },
    {
        "bucket": "MAIN",
        "order": "02",
        "notebook": "02_experiment_1",
        "title": "exp1_ecg_psd_by_posture",
        "source": "12_ecg_psd_journal_ready.png",
        "dest": "MAIN_02_nb02_exp1_ecg_psd_by_posture.png",
        "role": "main_text",
        "note": "Figure 1.2",
    },
    {
        "bucket": "MAIN",
        "order": "03",
        "notebook": "02_experiment_1",
        "title": "exp1_rr_psd_grid",
        "source": "13_hrv_comprehensive_ieee.png",
        "dest": "MAIN_03_nb02_exp1_rr_psd_grid.png",
        "role": "main_text",
        "note": "Figure 1.3",
    },
    {
        "bucket": "MAIN",
        "order": "04",
        "notebook": "02_experiment_1",
        "title": "exp1_duration_sweep",
        "source": "14_duration_effect.png",
        "dest": "MAIN_04_nb02_exp1_duration_sweep.png",
        "role": "main_text",
        "note": "Figure 1.4",
    },
    {
        "bucket": "MAIN",
        "order": "05",
        "notebook": "03_experiment_2",
        "title": "exp2_hf_collapse_verification",
        "source": "fig2_1_hf_verification_final.pdf",
        "dest": "MAIN_05_nb03_exp2_hf_collapse_verification.png",
        "role": "main_text",
        "note": "Deliverable 1 / Figure 2.1",
    },
    {
        "bucket": "MAIN",
        "order": "06",
        "notebook": "03_experiment_2",
        "title": "exp2_effort_comparison",
        "source": "fig2_2_effort_comparison_ieee.pdf",
        "dest": "MAIN_06_nb03_exp2_effort_comparison.png",
        "role": "main_text",
        "note": "Deliverable 2 / Figure 2.2",
    },
    {
        "bucket": "MAIN",
        "order": "07",
        "notebook": "03_experiment_2",
        "title": "exp2_pure_physiology",
        "source": "fig2_3_pure_physiology_ieee.pdf",
        "dest": "MAIN_07_nb03_exp2_pure_physiology.png",
        "role": "main_text",
        "note": "Deliverable 3 / Figure 2.3",
    },
    {
        "bucket": "MAIN",
        "order": "08",
        "notebook": "04_experiment_3",
        "title": "exp3_walking_tachogram",
        "source": "31_e3_tachogram_ieee.png",
        "dest": "MAIN_08_nb04_exp3_walking_tachogram.png",
        "role": "main_text",
        "note": "Figure 3.1",
    },
    {
        "bucket": "MAIN",
        "order": "09",
        "notebook": "04_experiment_3",
        "title": "exp3_signal_processing_snapshots",
        "source": "31_e3_signal_processing_ieee.png",
        "dest": "MAIN_09_nb04_exp3_signal_processing_snapshots.png",
        "role": "main_text",
        "note": "Figure 3.2",
    },
    {
        "bucket": "MAIN",
        "order": "10",
        "notebook": "04_experiment_3",
        "title": "exp3_recovery_tau_fit",
        "source": "33_e3_recovery_tau_ieee.png",
        "dest": "MAIN_10_nb04_exp3_recovery_tau_fit.png",
        "role": "main_text",
        "note": "Figure 3.3",
    },
    {
        "bucket": "MAIN",
        "order": "11",
        "notebook": "04_experiment_3",
        "title": "exp3_ecg_psd_rest_vs_walk",
        "source": "34_e3_ecg_psd.png",
        "dest": "MAIN_11_nb04_exp3_ecg_psd_rest_vs_walk.png",
        "role": "main_text",
        "note": "Figure 3.4",
    },
    {
        "bucket": "MAIN",
        "order": "12",
        "notebook": "04_experiment_3",
        "title": "exp3_multimodal_fusion",
        "source": "35_e3_multimodal_fusion_ieee.png",
        "dest": "MAIN_12_nb04_exp3_multimodal_fusion.png",
        "role": "main_text",
        "note": "Figure 3.5",
    },
    {
        "bucket": "MAIN",
        "order": "13",
        "notebook": "04_experiment_3",
        "title": "exp3_rr_psd_contrast",
        "source": "36_e3_rr_psd_contrast_ieee.png",
        "dest": "MAIN_13_nb04_exp3_rr_psd_contrast.png",
        "role": "main_text",
        "note": "Supplementary contrast figure but still paper-relevant.",
    },
    {
        "bucket": "MAIN",
        "order": "14",
        "notebook": "05_experiment_4A",
        "title": "exp4a_tachograms",
        "source": "41_e4a_tachograms_ieee.png",
        "dest": "MAIN_14_nb05_exp4a_tachograms.png",
        "role": "main_text",
        "note": "Figure 4.1",
    },
    {
        "bucket": "MAIN",
        "order": "15",
        "notebook": "05_experiment_4A",
        "title": "exp4a_psd_overlay",
        "source": "42_e4a_psd_overlay_ieee.png",
        "dest": "MAIN_15_nb05_exp4a_psd_overlay.png",
        "role": "main_text",
        "note": "Figure 4.2",
    },
    {
        "bucket": "MAIN",
        "order": "16",
        "notebook": "05_experiment_4A",
        "title": "exp4a_peak_tracking_regression",
        "source": "43_e4a_peak_freq_ieee.png",
        "dest": "MAIN_16_nb05_exp4a_peak_tracking_regression.png",
        "role": "main_text",
        "note": "Figure 4.3",
    },
    {
        "bucket": "MAIN",
        "order": "17",
        "notebook": "05_experiment_4A",
        "title": "exp4a_lfhf_vs_rmssd",
        "source": "44_e4a_lfhf_crossover.png",
        "dest": "MAIN_17_nb05_exp4a_lfhf_vs_rmssd.png",
        "role": "main_text",
        "note": "Figure 4.4",
    },
    {
        "bucket": "MAIN",
        "order": "18",
        "notebook": "05_experiment_4A",
        "title": "exp4a_resonance_amplitude",
        "source": "45_e4a_resonance.png",
        "dest": "MAIN_18_nb05_exp4a_resonance_amplitude.png",
        "role": "main_text",
        "note": "Figure 4.5",
    },
    {
        "bucket": "MAIN",
        "order": "19",
        "notebook": "06_integration",
        "title": "integration_operating_map",
        "source": "51_autonomic_spectrum.png",
        "dest": "MAIN_19_nb06_integration_operating_map.png",
        "role": "main_text",
        "note": "Figure 5.1",
    },
    {
        "bucket": "MAIN",
        "order": "20",
        "notebook": "06_integration",
        "title": "integration_challenge_recovery_atlas",
        "source": "52_hf_vs_hr_scatter.png",
        "dest": "MAIN_20_nb06_integration_challenge_recovery_atlas.png",
        "role": "main_text",
        "note": "Figure 5.2",
    },
    {
        "bucket": "MAIN",
        "order": "21",
        "notebook": "06_integration",
        "title": "integration_pipeline_reliability",
        "source": "53_pipeline_validation.png",
        "dest": "MAIN_21_nb06_integration_pipeline_reliability.png",
        "role": "main_text",
        "note": "Figure 5.3",
    },
    {
        "bucket": "APP",
        "order": "A03",
        "notebook": "06_integration",
        "title": "partial_sleep_trajectory",
        "source": "A1_e4b_sleep_trajectory.png",
        "dest": "APP_A03_nb06_partial_sleep_trajectory.png",
        "role": "appendix",
        "note": "Appendix A.1",
    },
]


def convert_pdf_to_png(pdf_path: Path, dest_png: Path) -> None:
    dest_base = dest_png.with_suffix("")
    subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-r",
            "300",
            "-singlefile",
            str(pdf_path),
            str(dest_base),
        ],
        check=True,
    )


def write_manifest(rows: list[dict]) -> None:
    csv_path = FIG_DST / "FIGURE_INDEX.csv"
    md_path = FIG_DST / "FIGURE_INDEX.md"

    fieldnames = [
        "bucket",
        "order",
        "notebook",
        "title",
        "source",
        "dest",
        "role",
        "note",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Paper Figure Index",
        "",
        "Unified PNG export folder for thesis / manuscript editing.",
        "",
        "| Exported PNG | Notebook | Role | Source | Note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['dest']}` | `{row['notebook']}` | `{row['role']}` | `{row['source']}` | {row['note']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    FIG_DST.mkdir(parents=True, exist_ok=True)

    copied_rows = []
    for row in FIGURES:
        src = FIG_SRC / row["source"]
        dst = FIG_DST / row["dest"]
        if not src.exists():
            raise FileNotFoundError(f"Missing source figure: {src}")
        if src.suffix.lower() == ".png":
            shutil.copy2(src, dst)
        elif src.suffix.lower() == ".pdf":
            convert_pdf_to_png(src, dst)
        else:
            raise ValueError(f"Unsupported figure format: {src.suffix}")
        copied_rows.append(row)

    write_manifest(copied_rows)
    print(f"Collected {len(copied_rows)} figures into {FIG_DST}")


if __name__ == "__main__":
    main()
