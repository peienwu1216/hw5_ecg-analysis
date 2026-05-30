#!/usr/bin/env python3
"""Combined LF/HF + RMSSD + RR-PSD figure for the final project (Fig. 3).

Single matplotlib figure replacing the two-minipage LaTeX approach.
Outputs: outputs/figures/fp_lfhf_imu_summary.pdf

Run from repo root:
    ./.venv/bin/python scripts/render_fp_lfhf_imu_combined.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.ticker import NullLocator
from matplotlib.transforms import blended_transform_factory
import numpy as np
from scipy.signal import butter, sosfiltfilt, welch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src import config as cfg
from src import pipeline as P
from src import plotting as PL

OUTPUT_NAME = "fp_lfhf_imu_summary.pdf"

E4A_KEYS = ["E4A_12pm", "E4A_9pm", "E4A_6pm", "E4A_5pm", "E4A_3pm"]
E4A_LABELS = ["12/min", "9/min", "6/min", "5/min", "3/min"]
E4A_RATES_BPM = [12, 9, 6, 5, 3]
E4A_COLORS = {
    "E4A_12pm": "#3b4cc0",
    "E4A_9pm":  "#7b9ef7",
    "E4A_6pm":  "#59a14f",
    "E4A_5pm":  "#f28e2b",
    "E4A_3pm":  "#e15759",
}
# Match src/fusion_recovery.py canonical LF/HF PSD (fs=4 Hz, nperseg=256).
NPERSEG = 256
FREQ_RES = cfg.INTERP_FREQ / NPERSEG
PEAK_SEARCH = (0.04, 0.40)  # same band as fusion_recovery rr_peak

BASE_FS = 8
LABEL_FS = 9
TICK_FS = 7.5
ANNOT_FS = 6.5


def _apply_style() -> None:
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


def _load_imu_peaks() -> dict[str, float]:
    """Return IMU z-axis respiratory peak frequency for each E4A key."""
    peaks: dict[str, float] = {}
    for key, rate_bpm in zip(E4A_KEYS, E4A_RATES_BPM):
        root = cfg.get_session_path(key)
        parts = []
        for hour_dir in P._sorted_hour_dirs(root):
            csv_path = hour_dir / "gsen.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing {csv_path}")
            parts.append(np.loadtxt(csv_path, delimiter=",", dtype=float))
        raw = np.concatenate(parts, axis=0)

        start_s, end_s = cfg.FILE_INVENTORY[key]["window"]
        i0 = int(round(start_s * cfg.FS_GSEN))
        i1 = int(round(end_s * cfg.FS_GSEN))
        raw = raw[i0 : min(i1, raw.shape[0])]
        scale = 1.0 / 1000.0 if float(np.max(np.abs(raw))) > 10.0 else 1.0
        z = raw[:, 2] * scale

        sos = butter(4, 0.7, btype="low", fs=cfg.FS_GSEN, output="sos")
        z_lp = sosfiltfilt(sos, z)

        expected_hz = rate_bpm / 60.0
        nperseg_z = min(4096 if expected_hz < 0.08 else 2048, len(z_lp))
        f_z, p_z = welch(z_lp - np.mean(z_lp), fs=cfg.FS_GSEN, nperseg=nperseg_z)

        lo = max(expected_hz * 0.6, 0.03)
        hi = expected_hz + 0.04
        m = (f_z >= lo) & (f_z <= hi)
        if m.any():
            peaks[key] = float(f_z[m][np.argmax(p_z[m])])
        else:
            peaks[key] = float("nan")
    return peaks


def _draw_left(gs_left, freq_hz, ratio_vals, rmssd_vals):
    """Two stacked subplots: LF/HF (top) and RMSSD (bottom)."""
    colors = [E4A_COLORS[k] for k in E4A_KEYS]

    # --- create axes via inner gridspec ---
    ax1 = plt.subplot(gs_left[0])
    ax2 = plt.subplot(gs_left[1])

    for ax in (ax1, ax2):
        ax.axvspan(cfg.BANDS["LF"][0], cfg.BANDS["LF"][1],
                   color="#f0e4f8", alpha=0.55, zorder=0)
        ax.axvspan(cfg.BANDS["HF"][0], cfg.BANDS["HF"][1],
                   color="#e0f0e4", alpha=0.55, zorder=0)
        ax.axvline(0.15, color="0.45", linewidth=0.8, zorder=1)
        ax.set_xlim(0.035, 0.225)
        ax.grid(axis="y", linewidth=0.25, alpha=0.20)
        ax.tick_params(direction="in", which="both", length=3)
        ax.set_axisbelow(True)

    # ── (a) LF/HF ──────────────────────────────────────────────────
    ax1.plot(freq_hz, ratio_vals, "-", color="0.65", linewidth=0.9, zorder=2)
    for i, (fh, rv, c) in enumerate(zip(freq_hz, ratio_vals, colors)):
        ax1.plot(fh, rv, "o", color=c, markersize=6.5, zorder=4,
                 markeredgecolor="white", markeredgewidth=0.6)
        if i == 0:
            xytext, ha, va = (8, 2), "center", "bottom"
        elif i == 1:
            xytext, ha, va = (6, -4), "left", "bottom"
        elif 0.75 <= rv <= 1.05:
            xytext, ha, va = (0, -10), "center", "top"
        else:
            xytext, ha, va = (0, 4), "center", "bottom"
        ax1.annotate(f"{rv:.2f}", (fh, rv), xytext=xytext,
                     textcoords="offset points", ha=ha, va=va,
                     fontsize=ANNOT_FS)

    ax1.set_yscale("log")
    ax1.axhline(1.0, color="0.55", linestyle=":", linewidth=0.75, zorder=1)
    ax1.set_ylim(0.12, 40)
    ax1.set_ylabel("LF / HF ratio", fontsize=LABEL_FS)
    ax1.tick_params(labelbottom=False)
    ax1.set_yticks([0.2, 0.5, 1, 2, 5, 10, 20])
    ax1.set_yticklabels(["0.2", "0.5", "1", "2", "5", "10", "20"],
                        fontsize=TICK_FS)
    ax1.yaxis.set_minor_locator(NullLocator())

    ax1.text(0.218, 1.28, "LF/HF = 1", fontsize=5.2, color="0.50", ha="right")
    ax1.text(0.125, 26, "LF band", fontsize=6.5, ha="center",
             color="#7b2d8e", fontweight="bold", fontstyle="italic")
    ax1.text(0.178, 26, "HF band", fontsize=6.5, ha="center",
             color="#2d8e4e", fontweight="bold", fontstyle="italic")
    ax1.text(0.153, 0.48, "0.15 Hz", fontsize=5.5, color="0.45",
             rotation=90, va="center", ha="left",
             transform=ax1.get_xaxis_transform())

    ax_bpm = ax1.secondary_xaxis(
        "top",
        functions=(lambda hz: hz * 60, lambda bpm: bpm / 60))
    ax_bpm.set_xticks([3, 5, 6, 9, 12])
    ax_bpm.set_xticklabels(["3", "5", "6", "9", "12"], fontsize=TICK_FS)
    ax_bpm.set_xlabel("Breathing rate (breaths/min)", fontsize=7, labelpad=4)
    ax_bpm.tick_params(direction="in", length=3)

    ax1.text(-0.04, 1.0, "(a)", transform=ax1.transAxes,
             fontsize=9, fontweight="bold", va="top", ha="right", clip_on=False)

    # ── (b) RMSSD ──────────────────────────────────────────────────
    ax2.plot(freq_hz, rmssd_vals, "-", color="0.65", linewidth=0.9, zorder=2)
    # Per-rate RMSSD label offsets (dx, dy) in points; ha/va for alignment.
    _rmssd_label = {
        "E4A_12pm": {"xytext": (0, 7),  "ha": "center", "va": "bottom"},
        "E4A_9pm":  {"xytext": (8, 3),  "ha": "center", "va": "bottom"},
        "E4A_6pm":  {"xytext": (0, 7),  "ha": "center", "va": "bottom"},
        "E4A_5pm":  {"xytext": (0, 7),  "ha": "center", "va": "bottom"},
        "E4A_3pm":  {"xytext": (0, 7),  "ha": "center", "va": "bottom"},
    }
    for key, fh, rv, c in zip(E4A_KEYS, freq_hz, rmssd_vals, colors):
        ax2.plot(fh, rv, "o", color=c, markersize=6.5, zorder=4,
                 markeredgecolor="white", markeredgewidth=0.6)
        lbl = _rmssd_label[key]
        ax2.annotate(
            f"{rv:.1f}", (fh, rv),
            xytext=lbl["xytext"], textcoords="offset points",
            ha=lbl["ha"], va=lbl["va"],
            fontsize=ANNOT_FS,
        )

    rmssd_mean = float(np.mean(rmssd_vals))
    ax2.axhline(rmssd_mean, color="#2980b9", linestyle="--",
                linewidth=0.75, zorder=1)
    ax2.fill_between([0.035, 0.225],
                     float(np.min(rmssd_vals)) - 2,
                     float(np.max(rmssd_vals)) + 2,
                     color="#2980b9", alpha=0.06, zorder=0)
    ax2.text(0.22, rmssd_mean + 1.0, f"mean = {rmssd_mean:.1f} ms",
             fontsize=5.8, color="#2980b9", ha="right")
    ax2.set_ylabel("RMSSD (ms)", fontsize=LABEL_FS)
    ax2.set_xlabel("Breathing frequency (Hz)", fontsize=7, labelpad=2)
    ax2.set_ylim(38, 76)
    ax2.set_xticks(freq_hz)
    ax2.set_xticklabels([f"{h:.3f}" for h in freq_hz], fontsize=TICK_FS - 0.5)
    for tl in ax2.get_xticklabels():
        tl.set_rotation(22)
        tl.set_ha("right")

    ax2.text(-0.04, 1.0, "(b)", transform=ax2.transAxes,
             fontsize=9, fontweight="bold", va="top", ha="right", clip_on=False)


def _draw_right(ax, psd_pub, peak_pub, imu_peaks):
    """RR PSD overlay with clean IMU respiratory frequency markers."""
    yscale = 1e3

    _fills = {"VLF": "#f4f4f4", "LF": "#ebebeb", "HF": "#f4f4f4"}
    for band, (lo, hi) in cfg.BANDS.items():
        ax.axvspan(lo, hi, color=_fills[band], linewidth=0, zorder=0)

    for edge in (0.04, 0.15, 0.40):
        ax.axvline(edge, color="0.80", linewidth=0.35, zorder=1)

    for key in E4A_KEYS:
        f, p = psd_pub[key]
        rate = cfg.E4A_EXPECTED_BREATHING_HZ[key] * 60
        ax.plot(f, p / yscale, color=E4A_COLORS[key], linewidth=1.15,
                label=f"{rate:.0f}/min", zorder=3)

    # Labels sit directly above each peak (no leader arrows). Peaks are well
    # separated in frequency; staggering the small vertical gap keeps the two
    # closest peaks (5/min @0.086, 6/min @0.102) from colliding.
    _label_dx = {
        "E4A_3pm":  2,
        "E4A_5pm":  12,
        "E4A_6pm":  16,
        "E4A_9pm":  0,
        "E4A_12pm": 0,
    }
    _label_dy = {
        "E4A_3pm":  2,
        "E4A_5pm":  6,
        "E4A_6pm":  6,
        "E4A_9pm":  6,
        "E4A_12pm": 7,
    }
    ymax = max(float(np.max(p)) for _, p in psd_pub.values()) / yscale * 1.12

    for key in E4A_KEYS:
        f, p = psd_pub[key]
        color = E4A_COLORS[key]
        hz = peak_pub[key]
        m = np.isclose(f, hz)
        if not m.any():
            continue
        pw = float(p[m][0]) / yscale
        ax.plot(hz, pw, "o", color=color, markersize=4.2,
                markeredgecolor="white", markeredgewidth=0.5, zorder=4)
        ax.annotate(
            f"{hz:.3f} Hz", xy=(hz, pw),
            xytext=(_label_dx[key], _label_dy[key]), textcoords="offset points",
            ha="center", va="bottom",
            fontsize=7.5, color=color, fontweight="bold", zorder=5,
        )

    # IMU markers: top-only ▼ (no full vertical lines). Blended transform
    # (x=data coords, y=axes fraction); placed just above the top spine.
    blend = blended_transform_factory(ax.transData, ax.transAxes)
    for key in E4A_KEYS:
        imu_hz = imu_peaks.get(key, float("nan"))
        if not np.isfinite(imu_hz):
            continue
        color = E4A_COLORS[key]
        ax.plot(imu_hz, 1.02, marker="v", color=color,
                markersize=4.2, markeredgecolor="white", markeredgewidth=0.35,
                transform=blend, clip_on=False, zorder=8)

    ax.set_xlim(0.0, 0.42)
    ax.set_ylim(0.0, ymax)
    ax.set_xlabel("Frequency (Hz)", fontsize=LABEL_FS)
    ax.set_ylabel(r"RR PSD ($\times 10^{3}$ ms$^{2}$/Hz)", fontsize=LABEL_FS)
    ax.tick_params(direction="in", which="both", length=3)
    ax.grid(axis="x", visible=False)
    ax.grid(axis="y", linewidth=0.25, alpha=0.15)
    ax.set_axisbelow(True)

    # Band labels placed at 0.82×ymax — clears the IMU marker row at top
    for name, xc in [("VLF", 0.0215), ("LF", 0.095), ("HF", 0.27)]:
        ax.text(xc, ymax * 0.97, name, fontsize=8.5, fontweight="bold",
                color="0.55", ha="center", va="top", zorder=6)

    # Single-column legend tucked into the empty HF region (x > 0.25)
    ax.legend(
        title="Breathing\nrate", title_fontsize=6.5, fontsize=7,
        ncols=1, loc="upper right",
        frameon=True, framealpha=0.93, edgecolor="0.80",
        handlelength=1.2, borderpad=0.4,
        handletextpad=0.45, labelspacing=0.22,
    )

    # Short technical note in the flat HF region (no overlap with peaks)
    ax.text(
        0.99, 0.018,
        f"Welch nperseg={NPERSEG}, Δf={FREQ_RES:.4f} Hz",
        transform=ax.transAxes, fontsize=5.5, color="0.60",
        ha="right", va="bottom",
    )

    ax.text(-0.10, 1.0, "(c)", transform=ax.transAxes,
            fontsize=9, fontweight="bold", va="top", ha="right", clip_on=False)


def main() -> Path:
    _apply_style()
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    results = {k: P.analyze_steady_state(k) for k in E4A_KEYS}
    freq_hz = np.array([cfg.E4A_EXPECTED_BREATHING_HZ[k] for k in E4A_KEYS])
    ratio_vals = np.array([results[k].fd_hrv["lf_hf_ratio"] for k in E4A_KEYS])
    rmssd_vals = np.array([results[k].td_hrv["rmssd_ms"] for k in E4A_KEYS])

    psd_pub: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    peak_pub: dict[str, float] = {}
    lo_pk, hi_pk = PEAK_SEARCH
    for key in E4A_KEYS:
        r = results[key]
        f, p = P.rr_psd(r.rr_ms_scipy, r.rr_times_scipy, nperseg=NPERSEG)
        psd_pub[key] = (f, p)
        m = (f >= lo_pk) & (f <= hi_pk)
        peak_pub[key] = float(f[m][np.argmax(p[m])]) if m.any() else float("nan")

    imu_peaks = _load_imu_peaks()

    fig = plt.figure(figsize=(7.2, 4.10))

    outer = gridspec.GridSpec(
        1, 2,
        figure=fig,
        width_ratios=[1.15, 1.65],
        left=0.10, right=0.98,
        top=0.91, bottom=0.13,
        wspace=0.36,
    )

    gs_left = gridspec.GridSpecFromSubplotSpec(
        2, 1,
        subplot_spec=outer[0],
        height_ratios=[1.15, 1.0],
        hspace=0.10,
    )

    _draw_left(gs_left, freq_hz, ratio_vals, rmssd_vals)

    ax_right = fig.add_subplot(outer[1])
    _draw_right(ax_right, psd_pub, peak_pub, imu_peaks)

    out_path = cfg.FIGURES_DIR / OUTPUT_NAME
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, format="pdf", dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    main()
