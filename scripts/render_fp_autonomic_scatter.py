#!/usr/bin/env python3
"""Render a single-panel HR–RMSSD scatter for the final project.

The manuscript / notebook export ``nb06_fig01_autonomic_spectrum.pdf`` is a
two-panel figure (scatter + total-power bars). Panel (B) duplicates the paced-
breathing spectral story already shown in Fig. 3, so the final project uses
this tighter single-panel variant instead.

Run from the repo root::

    ./.venv/bin/python scripts/render_fp_autonomic_scatter.py

Output: ``outputs/figures/fp_autonomic_scatter_hr_rmssd.pdf``
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
from scipy.spatial import ConvexHull

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src import config as cfg  # noqa: E402
from src import pipeline as P  # noqa: E402
from src import plotting as PL  # noqa: E402

OUTPUT_NAME = "fp_autonomic_scatter_hr_rmssd.pdf"

CROSS_KEYS = [
    "E1A", "E1B", "E1C",
    "E4A_12pm", "E4A_9pm", "E4A_6pm", "E4A_5pm", "E4A_3pm",
]
POSTURE_ORDER = ["E1A", "E1B", "E1C"]
PACED_ORDER = ["E4A_12pm", "E4A_9pm", "E4A_6pm", "E4A_5pm", "E4A_3pm"]

E1_COLORS = {
    "E1A": "#2E6F95",
    "E1B": "#5FA65A",
    "E1C": "#C95C5C",
}
E4A_COLORS = {
    "E4A_12pm": "#6C78D8",
    "E4A_9pm": "#7FA2F2",
    "E4A_6pm": "#68A65A",
    "E4A_5pm": "#F29A3A",
    "E4A_3pm": "#E95F64",
}

SHORT_LABELS = {
    "E1A": "Supine",
    "E1B": "Sitting",
    "E1C": "Standing",
    "E4A_12pm": "12/min",
    "E4A_9pm": "9/min",
    "E4A_6pm": "6/min",
    "E4A_5pm": "5/min",
    "E4A_3pm": "3/min",
}

LABEL_ADJUSTMENTS = {
    "Supine": {"xytext": (8, 2), "ha": "left", "va": "center"},
    "Sitting": {"xytext": (-5, 1), "ha": "right", "va": "bottom"},
    "Standing": {"xytext": (-4, 8), "ha": "right", "va": "bottom"},
    "12/min": {"xytext": (-2, -7), "ha": "center", "va": "top"},
    "9/min": {"xytext": (12, 5), "ha": "right", "va": "bottom"},
    "6/min": {"xytext": (7, 2), "ha": "left", "va": "bottom"},
    "5/min": {"xytext": (8, -2), "ha": "left", "va": "top"},
    "3/min": {"xytext": (-5, -3), "ha": "right", "va": "top"},
}


def _apply_style() -> None:
    PL.apply_style()
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 10.5,
        "axes.labelsize": 11.5,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def _integration_color(key: str) -> str:
    return E1_COLORS[key] if key.startswith("E1") else E4A_COLORS[key]


def _build_steady_map_df() -> pd.DataFrame:
    rows = []
    for key in CROSS_KEYS:
        r = P.dispatch(key)
        rows.append({
            "Condition": key,
            "Label": SHORT_LABELS[key],
            "Mean HR (bpm)": r.td_hrv["mean_hr_bpm"],
            "RMSSD (ms)": r.td_hrv["rmssd_ms"],
        })
    map_df = pd.DataFrame(rows)
    map_df["_ord"] = map_df["Condition"].map({k: i for i, k in enumerate(CROSS_KEYS)})
    return map_df.sort_values("_ord").drop(columns=["_ord"])


def render_autonomic_scatter(map_df: pd.DataFrame) -> plt.Figure:
    """Panel (a) only from notebooks/06_integration.ipynb Fig. 5.1."""
    fig, ax = plt.subplots(figsize=(6.2, 3.9))

    posture_data = map_df[map_df["Condition"].isin(POSTURE_ORDER)]
    ax.plot(
        posture_data["Mean HR (bpm)"],
        posture_data["RMSSD (ms)"],
        color="#6E9F64",
        linewidth=1.5,
        alpha=0.85,
        zorder=1,
    )

    paced_data = map_df[map_df["Condition"].isin(PACED_ORDER)].copy()
    if len(paced_data) >= 3:
        pts = paced_data[["Mean HR (bpm)", "RMSSD (ms)"]].values
        hull = ConvexHull(pts)
        hull_xy = pts[hull.vertices]
        poly = Polygon(
            hull_xy,
            facecolor="#F29A3A",
            alpha=0.10,
            edgecolor="none",
            linewidth=0,
            zorder=0,
        )
        ax.add_patch(poly)
        hull_closed = np.vstack([hull_xy, hull_xy[0]])
        ax.plot(
            hull_closed[:, 0],
            hull_closed[:, 1],
            color="#C7772E",
            linewidth=1.1,
            alpha=0.65,
            linestyle="--",
            zorder=1,
        )

    for _, row in map_df.iterrows():
        key = row["Condition"]
        label_text = row["Label"]
        marker = "o" if key.startswith("E1") else "s"
        ax.scatter(
            row["Mean HR (bpm)"],
            row["RMSSD (ms)"],
            s=56,
            color=_integration_color(key),
            marker=marker,
            edgecolor="black",
            linewidth=0.55,
            zorder=3,
        )
        adj = LABEL_ADJUSTMENTS[label_text]
        ax.annotate(
            label_text,
            (row["Mean HR (bpm)"], row["RMSSD (ms)"]),
            xytext=adj["xytext"],
            textcoords="offset points",
            ha=adj["ha"],
            va=adj["va"],
            fontsize=10,
            bbox=dict(
                boxstyle="round,pad=0.15",
                facecolor="white",
                edgecolor="none",
                alpha=0.78,
            ),
            zorder=4,
        )

    ax.set_xlabel("Mean HR (bpm)")
    ax.set_ylabel("RMSSD (ms)")
    ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.22)
    ax.set_xlim(map_df["Mean HR (bpm)"].min() - 1.3, map_df["Mean HR (bpm)"].max() + 1.3)
    ax.set_ylim(map_df["RMSSD (ms)"].min() - 5, map_df["RMSSD (ms)"].max() + 4)

    # Legend encodes marker shape only; per-point colors vary within each series.
    _leg_marker = dict(
        markerfacecolor="white",
        markeredgecolor="black",
        markeredgewidth=0.55,
        markersize=7,
    )
    legend_handles = [
        Line2D([0], [0], marker="o", color="none", label="Posture manipulation", **_leg_marker),
        Line2D([0], [0], marker="s", color="none", label="Paced breathing", **_leg_marker),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper right",
        frameon=True,
        fancybox=False,
        edgecolor="0.75",
        facecolor="white",
        framealpha=0.95,
        fontsize=11.5,
    )

    fig.tight_layout(pad=0.8)
    return fig


def main() -> Path:
    _apply_style()
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    map_df = _build_steady_map_df()
    fig = render_autonomic_scatter(map_df)
    out_path = PL.save_figure(fig, OUTPUT_NAME)
    plt.close(fig)
    print(f"Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    main()
