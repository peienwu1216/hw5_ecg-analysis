#!/usr/bin/env python3
"""Fusion-based recovery of the vagal component (Final Project, Fig. 4).

Three panels, all annotations read from outputs/tables/fusion_recovery.csv:
  (a) log LF/HF vs breathing rate: naive (80x swing) vs IMU-corrected (flat).
  (b) per-rate stacked LF_total = RSA_in_LF (migrated vagal) + LF_residual.
  (c) IMU-anchored respiratory RR power P_resp vs rate (delta-sensitivity band).

Run from repo root:
    ./.venv/bin/python scripts/render_fp_fusion_recovery.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src import config as cfg
from src import plotting as PL

OUTPUT_NAME = "fp_fusion_recovery.pdf"
PRIMARY_DELTA = 0.015

# rate order: slow -> fast (3 .. 12), matching the breathing-rate x-axis
ORDER = ["3/min", "5/min", "6/min", "9/min", "12/min"]
RATE_BPM = {"3/min": 3, "5/min": 5, "6/min": 6, "9/min": 9, "12/min": 12}
COLORS = {
    "12/min": "#3b4cc0", "9/min": "#7b9ef7", "6/min": "#59a14f",
    "5/min": "#f28e2b", "3/min": "#e15759",
}
C_NAIVE = "#c0392b"
C_CORR = "#2471a3"
C_RSA = "#7b9ef7"
C_RESID = "#b0b0b0"

BASE_FS = 8
LABEL_FS = 9
TICK_FS = 7.5
ANNOT_FS = 6.5


def _style() -> None:
    PL.apply_style()
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": BASE_FS,
        "axes.labelsize": LABEL_FS,
        "xtick.labelsize": TICK_FS,
        "ytick.labelsize": TICK_FS,
        "axes.linewidth": 0.6,
        "lines.linewidth": 1.0,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def _panel_a(ax, prim: pd.DataFrame) -> None:
    rates = [RATE_BPM[c] for c in ORDER]
    naive = [float(prim.loc[prim.condition == c, "LFHF_naive"].iloc[0]) for c in ORDER]
    corr = [float(prim.loc[prim.condition == c, "LFHF_corr"].iloc[0]) for c in ORDER]

    # HF<->LF boundary at 0.15 Hz == 9 breaths/min: resp. peak enters LF below 9.
    ax.axvspan(2.5, 9.0, color="#f0e4f8", alpha=0.45, zorder=0)
    ax.text(5.5, 0.155, "resp. peak migrated into LF",
            fontsize=5.4, color="#7b2d8e", ha="center", va="bottom",
            fontstyle="italic")

    h_naive, = ax.plot(rates, naive, "-o", color=C_NAIVE, markersize=5.5, zorder=4,
                       markeredgecolor="white", markeredgewidth=0.5,
                       label="LF/HF naive")
    h_corr, = ax.plot(rates, corr, "-s", color=C_CORR, markersize=5.0, zorder=4,
                      markeredgecolor="white", markeredgewidth=0.5,
                      label="LF/HF IMU-corrected")

    # Time-domain vagal anchor: RMSSD is band-free, so it certifies *which* curve
    # is right. The naive ratio diverges from the near-flat RMSSD; the corrected
    # ratio stays consistent with it.
    rmssd = [float(prim.loc[prim.condition == c, "RMSSD_ms"].iloc[0]) for c in ORDER]
    axr = ax.twinx()
    h_rmssd, = axr.plot(rates, rmssd, ":D", color="#5d6d7e", markersize=3.2,
                        linewidth=0.9, zorder=3, label="RMSSD (time-domain)")
    axr.set_ylim(0, 130)
    axr.set_ylabel("RMSSD (ms)", fontsize=7.5, color="#5d6d7e")
    axr.tick_params(axis="y", direction="in", length=3, labelsize=6.5,
                    colors="#5d6d7e")
    axr.set_yticks([0, 40, 80, 120])

    # Panel (a) value labels — edit xytext (dx, dy in pt), ha, va per rate.
    _naive_label = {
        "3/min":  {"xytext": (0, 4),   "ha": "left",   "va": "bottom"},
        "5/min":  {"xytext": (0, 4),   "ha": "left",   "va": "bottom"},
        "6/min":  {"xytext": (5, 0),   "ha": "left",   "va": "bottom"},
        "9/min":  {"xytext": (3, 4),   "ha": "left",   "va": "bottom"},
        "12/min": {"xytext": (0, 4),   "ha": "center", "va": "bottom"},
    }
    _corr_label = {
        "3/min":  {"xytext": (5, -5), "ha": "center", "va": "top"},
        "5/min":  {"xytext": (0, -8), "ha": "center", "va": "top"},
        "6/min":  {"xytext": (4, -8), "ha": "center", "va": "top"},
        "9/min":  {"xytext": (0, -8), "ha": "center", "va": "top"},
        "12/min": {"xytext": (0, -5), "ha": "center", "va": "top"},
    }
    for cond, x, yn, yc in zip(ORDER, rates, naive, corr):
        # 9/min & 12/min: corrected == naive — label once (blue only).
        if abs(yn - yc) >= 0.005:
            nl = _naive_label[cond]
            ax.annotate(
                f"{yn:.2f}", (x, yn),
                xytext=nl["xytext"], textcoords="offset points",
                ha=nl["ha"], va=nl["va"],
                fontsize=ANNOT_FS, color=C_NAIVE,
            )
        cl = _corr_label[cond]
        ax.annotate(
            f"{yc:.2f}", (x, yc),
            xytext=cl["xytext"], textcoords="offset points",
            ha=cl["ha"], va=cl["va"],
            fontsize=ANNOT_FS, color=C_CORR,
        )

    ax.axhline(1.0, color="0.55", linestyle=":", linewidth=0.75, zorder=1)
    ax.text(11.7, 0.88, "LF/HF = 1", fontsize=5.4, color="0.45", ha="right", va="top")
    ax.set_yscale("log")
    ax.set_ylim(0.12, 40)
    ax.set_yticks([0.2, 0.5, 1, 2, 5, 10, 20])
    ax.set_yticklabels(["0.2", "0.5", "1", "2", "5", "10", "20"])
    ax.set_xticks([3, 5, 6, 9, 12])
    ax.set_xlim(2.4, 12.6)
    ax.set_xlabel("Breathing rate (breaths/min)", fontsize=8)
    ax.set_ylabel("LF / HF ratio", fontsize=LABEL_FS)
    ax.grid(axis="y", linewidth=0.25, alpha=0.20)
    ax.set_axisbelow(True)
    ax.tick_params(direction="in", which="both", length=3)
    leg = ax.legend(
        [h_naive, h_corr, h_rmssd],
        ["LF/HF naive", "LF/HF IMU-corrected", "RMSSD (time-domain)"],
        loc="upper right",
        bbox_to_anchor=(0.92, 1.00),
        borderaxespad=0,
        fontsize=5.0,
        frameon=True,
        framealpha=0.92,
        edgecolor="0.8",
        handlelength=1.1,
        handletextpad=0.3,
        borderpad=0.2,
        labelspacing=0.2,
        markerscale=0.75,
    )
    leg.get_frame().set_linewidth(0.35)
    ax.text(-0.02, 1.04, "(a)", transform=ax.transAxes, fontsize=9,
            fontweight="bold", va="bottom", ha="right")


def _panel_b(ax, prim: pd.DataFrame) -> None:
    x = np.arange(len(ORDER))
    rsa = [float(prim.loc[prim.condition == c, "RSA_in_LF"].iloc[0]) for c in ORDER]
    resid = [float(prim.loc[prim.condition == c, "LF_residual"].iloc[0]) for c in ORDER]
    pct = [float(prim.loc[prim.condition == c, "pct_RSA_in_LF"].iloc[0]) for c in ORDER]
    lf_total = [r + d for r, d in zip(rsa, resid)]

    ax.bar(x, rsa, color=C_RSA, edgecolor="white", linewidth=0.5,
           label="RSA migrated into LF")
    ax.bar(x, resid, bottom=rsa, color=C_RESID, edgecolor="white",
           linewidth=0.5, label="non-respiratory LF residual")

    for xi, tot, pc in zip(x, lf_total, pct):
        if tot <= 1:
            continue
        ax.annotate(f"{pc:.1f}%", (xi, tot), xytext=(0, 3),
                    textcoords="offset points", ha="center",
                    fontsize=ANNOT_FS, fontweight="bold", color="#34495e")

    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("/min", "") for c in ORDER])
    ax.set_xlabel("Breathing rate (breaths/min)", fontsize=8)
    ax.set_ylabel(r"LF power (ms$^{2}$)", fontsize=LABEL_FS)
    ax.grid(axis="y", linewidth=0.25, alpha=0.20)
    ax.set_axisbelow(True)
    ax.tick_params(direction="in", length=3)
    leg = ax.legend(
        loc="upper right",
        bbox_to_anchor=(1.0, 1.03),
        borderaxespad=0,
        fontsize=5.5,
        frameon=True,
        framealpha=0.92,
        edgecolor="0.8",
        handlelength=1.1,
        handletextpad=0.3,
        borderpad=0.2,
        labelspacing=0.2,
    )
    leg.get_frame().set_linewidth(0.35)
    ax.text(-0.02, 1.04, "(b)", transform=ax.transAxes, fontsize=9,
            fontweight="bold", va="bottom", ha="right")


def _panel_c(ax, df: pd.DataFrame) -> None:
    rates, line, lo, hi = [], [], [], []
    for c in ORDER:
        sub = df[(df.condition == c) & (df.imu_confirmed)]
        if sub.empty:
            continue
        rates.append(RATE_BPM[c])
        prim = sub[sub.delta_hz == PRIMARY_DELTA]["P_resp"].iloc[0]
        line.append(float(prim))
        lo.append(float(sub["P_resp"].min()))
        hi.append(float(sub["P_resp"].max()))

    order_idx = np.argsort(rates)
    rates = np.array(rates)[order_idx]
    line = np.array(line)[order_idx]
    lo = np.array(lo)[order_idx]
    hi = np.array(hi)[order_idx]

    ax.fill_between(rates, lo, hi, color="#59a14f", alpha=0.18,
                    label=r"$\delta \in$ [0.015, 0.025] Hz")
    ax.plot(rates, line, "-o", color="#2d8e4e", markersize=5.0, zorder=4,
            markeredgecolor="white", markeredgewidth=0.5,
            label=r"$\delta = 0.015$ Hz")

    ax.set_xticks([3, 5, 6, 9, 12])
    ax.set_xlim(2.4, 12.6)
    ax.set_xlabel("Breathing rate (breaths/min)", fontsize=8)
    ax.set_ylabel(r"IMU-anchored $P_{\mathrm{resp}}$ (ms$^{2}$)", fontsize=LABEL_FS)
    ax.grid(axis="y", linewidth=0.25, alpha=0.20)
    ax.set_axisbelow(True)
    ax.tick_params(direction="in", length=3)
    leg = ax.legend(
        loc="upper right",
        bbox_to_anchor=(0.98, 0.98),
        fontsize=5.5,
        frameon=True,
        framealpha=0.92,
        edgecolor="0.8",
        handlelength=1.1,
        handletextpad=0.3,
        borderpad=0.2,
        labelspacing=0.2,
    )
    leg.get_frame().set_linewidth(0.35)
    ax.text(-0.02, 1.04, "(c)", transform=ax.transAxes, fontsize=9,
            fontweight="bold", va="bottom", ha="right")


def main() -> Path:
    _style()
    csv = cfg.TABLES_DIR / "fusion_recovery.csv"
    df = pd.read_csv(csv)
    prim = df[df.is_primary].copy()

    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.7))
    _panel_a(axes[0], prim)
    _panel_b(axes[1], prim)
    _panel_c(axes[2], df)
    fig.tight_layout(w_pad=1.4)

    out = cfg.FIGURES_DIR / OUTPUT_NAME
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="pdf", dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"Wrote {out}")
    return out


if __name__ == "__main__":
    main()
