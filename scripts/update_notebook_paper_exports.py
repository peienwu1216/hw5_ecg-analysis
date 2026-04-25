from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = REPO_ROOT / "notebooks"


COMMON_DIR_OLD = "FIG_DIR = REPO_ROOT / 'outputs' / 'figures'"
COMMON_DIR_NEW = "FIG_DIR = REPO_ROOT / 'outputs' / 'paper_figures_png'"
COMMON_DIR_OLD_DQ = 'FIG_DIR = REPO_ROOT / "outputs" / "figures"'
COMMON_DIR_NEW_DQ = 'FIG_DIR = REPO_ROOT / "outputs" / "paper_figures_png"'


REPLACEMENTS: dict[str, list[tuple[str, str]]] = {
    "00_quality_check.ipynb": [
        (COMMON_DIR_OLD, COMMON_DIR_NEW),
        ('fig.savefig(FIG_DIR / "00_quality_overview.png", dpi=110, bbox_inches="tight")',
         'fig.savefig(FIG_DIR / "APP_A01_nb00_data_quality_overview.png", dpi=300, bbox_inches="tight")'),
    ],
    "01_pipeline_validation.ipynb": [
        (COMMON_DIR_OLD, COMMON_DIR_NEW),
        ('fig.savefig(FIG_DIR / "01_e1pre_validation.png", dpi=120, bbox_inches="tight")',
         'fig.savefig(FIG_DIR / "APP_A02_nb01_pipeline_validation_e1pre.png", dpi=300, bbox_inches="tight")'),
    ],
    "02_experiment_1.ipynb": [
        (COMMON_DIR_OLD, COMMON_DIR_NEW),
        ('fig.savefig(FIG_DIR / "11_postural_tachograms_ieee.png", dpi=300, bbox_inches="tight")',
         'fig.savefig(FIG_DIR / "MAIN_01_nb02_exp1_postural_tachograms.png", dpi=300, bbox_inches="tight")'),
        ('fig.savefig(FIG_DIR / "12_ecg_psd_journal_ready.png", dpi=300, bbox_inches="tight")',
         'fig.savefig(FIG_DIR / "MAIN_02_nb02_exp1_ecg_psd_by_posture.png", dpi=300, bbox_inches="tight")'),
        ('fig.savefig(FIG_DIR / "13_hrv_comprehensive_ieee.png", dpi=300, bbox_inches="tight")',
         'fig.savefig(FIG_DIR / "MAIN_03_nb02_exp1_rr_psd_grid.png", dpi=300, bbox_inches="tight")'),
        ('fig.savefig(FIG_DIR / "14_duration_effect.png", dpi=120, bbox_inches="tight")',
         'fig.savefig(FIG_DIR / "MAIN_04_nb02_exp1_duration_sweep.png", dpi=300, bbox_inches="tight")'),
    ],
    "03_experiment_2.ipynb": [
        (COMMON_DIR_OLD, COMMON_DIR_NEW),
        ('"savefig.format": "pdf"', '"savefig.format": "png"'),
        ("plt.savefig(FIG_DIR / \"fig2_1_hf_verification_final.pdf\", bbox_inches='tight')",
         "plt.savefig(FIG_DIR / \"MAIN_05_nb03_exp2_hf_collapse_verification.png\", dpi=300, bbox_inches='tight')"),
        ("plt.savefig(FIG_DIR / \"fig2_2_effort_comparison_ieee.pdf\", bbox_inches='tight')",
         "plt.savefig(FIG_DIR / \"MAIN_06_nb03_exp2_effort_comparison.png\", dpi=300, bbox_inches='tight')"),
        ("plt.savefig(FIG_DIR / \"fig2_3_pure_physiology_ieee.pdf\", bbox_inches=\"tight\")",
         "plt.savefig(FIG_DIR / \"MAIN_07_nb03_exp2_pure_physiology.png\", dpi=300, bbox_inches=\"tight\")"),
    ],
    "04_experiment_3.ipynb": [
        (COMMON_DIR_OLD, COMMON_DIR_NEW),
        ('fig.savefig(FIG_DIR / "31_e3_tachogram_ieee.png", dpi=300, bbox_inches="tight")',
         'fig.savefig(FIG_DIR / "MAIN_08_nb04_exp3_walking_tachogram.png", dpi=300, bbox_inches="tight")'),
        ('fig.savefig(FIG_DIR / "31_e3_signal_processing_ieee.png", dpi=300, bbox_inches="tight")',
         'fig.savefig(FIG_DIR / "MAIN_09_nb04_exp3_signal_processing_snapshots.png", dpi=300, bbox_inches="tight")'),
        ('fig.savefig(FIG_DIR / "33_e3_recovery_tau_ieee.png", dpi=300, bbox_inches="tight")',
         'fig.savefig(FIG_DIR / "MAIN_10_nb04_exp3_recovery_tau_fit.png", dpi=300, bbox_inches="tight")'),
        ('fig.savefig(FIG_DIR / "34_e3_ecg_psd.png", dpi=300, bbox_inches="tight")',
         'fig.savefig(FIG_DIR / "MAIN_11_nb04_exp3_ecg_psd_rest_vs_walk.png", dpi=300, bbox_inches="tight")'),
        ('fig.savefig(FIG_DIR / "35_e3_multimodal_fusion_ieee.png", dpi=300, bbox_inches="tight")',
         'fig.savefig(FIG_DIR / "MAIN_12_nb04_exp3_multimodal_fusion.png", dpi=300, bbox_inches="tight")'),
        ('fig.savefig(FIG_DIR / "36_e3_rr_psd_contrast_ieee.png", dpi=300, bbox_inches="tight")',
         'fig.savefig(FIG_DIR / "MAIN_13_nb04_exp3_rr_psd_contrast.png", dpi=300, bbox_inches="tight")'),
    ],
    "05_experiment_4A.ipynb": [
        (COMMON_DIR_OLD_DQ, COMMON_DIR_NEW_DQ),
        (
            'def save_dual(fig, stem):\n    fig.savefig(FIG_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")\n    fig.savefig(FIG_DIR / f"{stem}.pdf", bbox_inches="tight")',
            'def save_paper_png(fig, filename):\n    fig.savefig(FIG_DIR / filename, dpi=300, bbox_inches="tight")',
        ),
        ('save_dual(fig, "41_e4a_tachograms_ieee")',
         'save_paper_png(fig, "MAIN_14_nb05_exp4a_tachograms.png")'),
        ('save_dual(fig, "42_e4a_psd_overlay_ieee")',
         'save_paper_png(fig, "MAIN_15_nb05_exp4a_psd_overlay.png")'),
        ('save_dual(fig, "43_e4a_peak_freq_ieee")',
         'save_paper_png(fig, "MAIN_16_nb05_exp4a_peak_tracking_regression.png")'),
        ('save_dual(fig, "44_e4a_lfhf_crossover")',
         'save_paper_png(fig, "MAIN_17_nb05_exp4a_lfhf_vs_rmssd.png")'),
        ('save_dual(fig, "45_e4a_resonance")',
         'save_paper_png(fig, "MAIN_18_nb05_exp4a_resonance_amplitude.png")'),
    ],
    "06_integration.ipynb": [
        (COMMON_DIR_OLD_DQ, COMMON_DIR_NEW_DQ),
        (
            'def save_dual(fig, stem):\n    fig.savefig(FIG_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")\n    fig.savefig(FIG_DIR / f"{stem}.pdf", bbox_inches="tight")',
            'def save_paper_png(fig, filename):\n    fig.savefig(FIG_DIR / filename, dpi=300, bbox_inches="tight")',
        ),
        ('save_dual(fig, "51_autonomic_spectrum")',
         'save_paper_png(fig, "MAIN_19_nb06_integration_operating_map.png")'),
        ('save_dual(fig, "52_hf_vs_hr_scatter")',
         'save_paper_png(fig, "MAIN_20_nb06_integration_challenge_recovery_atlas.png")'),
        ('save_dual(fig, "53_pipeline_validation")',
         'save_paper_png(fig, "MAIN_21_nb06_integration_pipeline_reliability.png")'),
        ('save_dual(fig, "A1_e4b_sleep_trajectory")',
         'save_paper_png(fig, "APP_A03_nb06_partial_sleep_trajectory.png")'),
    ],
}


def update_notebook(path: Path, replacements: list[tuple[str, str]]) -> int:
    nb = json.loads(path.read_text(encoding="utf-8"))
    changes = 0
    for cell in nb.get("cells", []):
        src = "".join(cell.get("source", []))
        new_src = src
        for old, new in replacements:
            if old in new_src:
                new_src = new_src.replace(old, new)
                changes += 1
        if new_src != src:
            cell["source"] = new_src.splitlines(keepends=True)
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    return changes


def main() -> None:
    total = 0
    for name, replacements in REPLACEMENTS.items():
        path = NOTEBOOK_DIR / name
        changes = update_notebook(path, replacements)
        total += changes
        print(f"{name}: {changes} replacements")
    print(f"Total replacements: {total}")


if __name__ == "__main__":
    main()
