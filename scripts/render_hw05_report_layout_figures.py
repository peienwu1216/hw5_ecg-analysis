#!/usr/bin/env python3
"""Regenerate HW05 figures with layouts that avoid LaTeX / PDF clipping issues.

This script does **not** modify manuscript notebooks or their exported PDFs.
It writes **new filenames** under ``outputs/figures/`` intended for ``hw05_report/``:

Q1 — posture ECG PSD + Poincaré (split for vertical stacking in the PDF)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- ``hw05_q1_ecg_psd_postures_row3.pdf`` — three ECG PSD panels in one **row**
  (canonical notebook export ``nb02_fig02_ecg_psd_harmonics.pdf`` is a **column**).
- ``hw05_q1_poincare_postures_row3.pdf`` — three Poincaré panels (row layout with
  publication title sizes).

Use two separate ``figure`` environments (or full-width stacked graphics) so panel
letters stay consistent with the written subcaptions without squeezing narrow
side-by-side subfigures.

Q4 — paced breathing (remove inner subplot «(a)» / «(b)» from LF/HF + RMSSD)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Canonical ``nb05_fig04_e4a_lfhf_crossover.pdf`` carries manuscript-style inner
letters on the LF/HF vs RMSSD stack. For HW05, which already labels panels as
subfigures (a) PSD overlay vs (b) LF/HF+RMSSD, those inner letters conflict.

- ``hw05_q4_rr_psd_overlay_e4a.pdf`` — same content as ``nb05_fig02_e4a_psd_overlay.pdf``.
- ``hw05_q4_lfhf_rmssd_stacked_clean.pdf`` — same dual-axis stack **without**
  inner «(a)»/«(b)» annotations on the matplotlib axes.

Run from the repo root with the project virtualenv (system ``python3`` may lack SciPy)::

    ./.venv/bin/python scripts/render_hw05_report_layout_figures.py
    ./.venv/bin/python scripts/render_hw05_report_layout_figures.py q1-ecg q4-psd

"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import NullLocator
from scipy.signal import butter, sosfiltfilt


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src import config as cfg  # noqa: E402
from src import pipeline as P  # noqa: E402
from src import plotting as PL  # noqa: E402


def _apply_hw05_style() -> None:
    PL.apply_style()
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "figure.titlesize": 10,
        "lines.linewidth": 1.1,
        "axes.linewidth": 0.6,
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def _save_pdf(fig: plt.Figure, name: str) -> Path:
    """Persist with modest padding — reduces tight-bbox cropping on axis labels."""
    path = cfg.FIGURES_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="pdf", dpi=300, bbox_inches="tight", pad_inches=0.06)
    return path


# ---------------------------------------------------------------------------
# Q1 — posture row figures
# ---------------------------------------------------------------------------

_HP_ORDER = 4
_HP_CUTOFF_HZ = 0.7


def render_q1_ecg_psd_row3() -> Path:
    from matplotlib.transforms import blended_transform_factory

    KEYS = ["E1A", "E1B", "E1C"]
    results = {k: P.analyze_steady_state(k) for k in KEYS}
    labels = ["Supine", "Sitting", "Standing"]

    payloads: list[tuple[np.ndarray, np.ndarray, float, float]] = []
    y_candidates: list[float] = []
    for key in KEYS:
        r = results[key]
        sos_hp = butter(_HP_ORDER, _HP_CUTOFF_HZ, btype="highpass",
                        fs=cfg.FS, output="sos")
        ecg_hp = sosfiltfilt(sos_hp, r.ecg_filt)

        f, p = P.ecg_psd(ecg_hp, fs=cfg.FS)

        hr = float(r.td_hrv["mean_hr_bpm"])
        f0 = hr / 60.0
        payloads.append((f, p, hr, f0))

        mask = (f > 0.5) & (f < 5.0)
        if np.any(mask):
            mp = float(np.max(p[mask]))
            if mp > 0:
                y_candidates.append(mp)

    if not y_candidates:
        ymax = 1.0
    else:
        ymax = max(y_candidates) * 1.25

    fig, axes = plt.subplots(
        1, 3, figsize=(7.35, 2.52), sharey=True,
        constrained_layout=True,
    )

    harmonic_trans_tpl = blended_transform_factory
    x_lo, x_hi = 0.05, 5.0

    for i, (ax, label, (f, p, hr, f0)) in enumerate(
            zip(axes, labels, payloads)):
        ax.plot(f, p, color="black", lw=0.8)
        ax.set_xlim(x_lo, x_hi)
        ax.set_ylim(0.0, ymax)

        harmonic_trans = harmonic_trans_tpl(ax.transData, ax.transAxes)

        for harmonic in range(1, 6):
            fx = f0 * harmonic
            if not (x_lo <= fx <= x_hi):
                continue
            ax.axvline(fx, color="red", linestyle=":", alpha=0.6, lw=1)
            h_lbl = r"$f_0$" if harmonic == 1 else rf"${harmonic}f_0$"
            label_x = fx + 0.07
            ax.text(
                label_x,
                0.99,
                h_lbl,
                transform=harmonic_trans,
                ha="left",
                va="top",
                fontsize=7,
                color="red",
                alpha=0.85,
                clip_on=False,
            )

        panel = chr(97 + i)
        ax.set_title(
            rf"({panel}) {label} (HR = {hr:.1f} bpm, $f_0$ = {f0:.2f} Hz)",
            loc="left",
            fontweight="bold",
            fontsize=8,
        )
        ax.set_xlabel("Frequency (Hz)")
        ax.grid(True, linestyle="--", alpha=0.3)

    axes[0].set_ylabel(r"PSD (mV$^2$/Hz)")
    for ax in axes[1:]:
        ax.set_ylabel("")

    path = _save_pdf(fig, "hw05_q1_ecg_psd_postures_row3.pdf")
    plt.close(fig)
    return path


def _poincare_metrics(rr_ms: np.ndarray) -> dict[str, float]:
    rr_ms = np.asarray(rr_ms, dtype=float)
    rr_ms = rr_ms[np.isfinite(rr_ms)]
    rr_n = rr_ms[:-1]
    rr_n1 = rr_ms[1:]
    diff_rr = rr_n1 - rr_n
    sd1 = float(np.sqrt(np.var(diff_rr, ddof=1) / 2))
    sd2 = float(np.sqrt(2 * np.var(rr_ms, ddof=1)
                         - 0.5 * np.var(diff_rr, ddof=1)))
    sd_ratio = sd1 / sd2 if sd2 else float("nan")
    return {"SD1 (ms)": sd1, "SD2 (ms)": sd2, "SD1/SD2": sd_ratio}


def render_q1_poincare_row3() -> Path:
    KEYS = ["E1A", "E1B", "E1C"]
    rr_dict = {
        "Supine": [],
        "Sitting": [],
        "Standing": [],
    }
    order = ["Supine", "Sitting", "Standing"]
    results = {k: P.analyze_steady_state(k) for k in KEYS}
    for name, key in zip(order, KEYS):
        rr_dict[name] = results[key].rr_ms_nk / 1000.0  # convert to seconds

    fig, axes = plt.subplots(1, 3, figsize=(7.35, 2.55),
                             sharex=True, sharey=True, constrained_layout=True)

    for i, (ax, condition) in enumerate(zip(axes, order)):
        rr_s = rr_dict[condition]
        rr_s = np.asarray(rr_s, dtype=float)
        rr_s = rr_s[np.isfinite(rr_s)]

        rr_n = rr_s[:-1]
        rr_n1 = rr_s[1:]

        metrics = _poincare_metrics(rr_s * 1000.0)  # compute in ms, display in s

        ax.scatter(rr_n, rr_n1, s=18, alpha=0.65, edgecolors="none")

        min_rr = min(float(np.min(rr_n)), float(np.min(rr_n1)))
        max_rr = max(float(np.max(rr_n)), float(np.max(rr_n1)))
        ax.plot([min_rr, max_rr], [min_rr, max_rr], linestyle="--", linewidth=1,
                color="0.35")

        panel = chr(97 + i)
        sd1_s = metrics["SD1 (ms)"] / 1000.0
        sd2_s = metrics["SD2 (ms)"] / 1000.0
        ax.set_title(
            f"({panel}) {condition}\n"
            f"SD1={sd1_s:.3f} s, SD2={sd2_s:.3f} s",
            fontsize=8,
            fontweight="bold",
        )
        ax.set_xlabel(r"$\mathrm{RR}_n$ (s)")
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel(r"$\mathrm{RR}_{n+1}$ (s)")
    path = _save_pdf(fig, "hw05_q1_poincare_postures_row3.pdf")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Q4 — paced overlay + clean LF/HF stack
# ---------------------------------------------------------------------------

NPERSEG_PUB = 512
FREQ_RES_HZ = cfg.INTERP_FREQ / NPERSEG_PUB
E4A_KEYS = ["E4A_12pm", "E4A_9pm", "E4A_6pm", "E4A_5pm", "E4A_3pm"]
E4A_PSD_COLORS = {
    "E4A_12pm": "#3b4cc0",
    "E4A_9pm": "#7b9ef7",
    "E4A_6pm": "#59a14f",
    "E4A_5pm": "#f28e2b",
    "E4A_3pm": "#e15759",
}


def _e4a_psd_peak_bundle():
    results = {k: P.analyze_steady_state(k) for k in E4A_KEYS}
    psd_pub: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    peak_pub: dict[str, float] = {}
    for key in E4A_KEYS:
        r = results[key]
        f, p = P.rr_psd(r.rr_ms_nk, r.rr_times_nk, nperseg=NPERSEG_PUB)
        psd_pub[key] = (f, p)
        mask = (f >= 0.01) & (f <= 0.45)
        peak_pub[key] = float(f[mask][np.argmax(p[mask])]) if mask.any() else float("nan")
    return results, psd_pub, peak_pub


def render_q4_psd_overlay() -> Path:
    _, psd_pub, peak_pub = _e4a_psd_peak_bundle()

    fig, ax = plt.subplots(figsize=(6.5, 2.6))
    yscale = 1e3

    _fills = {"VLF": "#f2f2f2", "LF": "#eaeaea", "HF": "#f2f2f2"}
    for band, (lo, hi) in cfg.BANDS.items():
        ax.axvspan(lo, hi, color=_fills[band], linewidth=0, zorder=0)

    for edge in (0.04, 0.15, 0.40):
        ax.axvline(edge, color="0.78", linewidth=0.4, zorder=1)

    for key in E4A_KEYS:
        f, p = psd_pub[key]
        rate = cfg.E4A_EXPECTED_BREATHING_HZ[key] * 60
        ax.plot(f, p / yscale, color=E4A_PSD_COLORS[key], linewidth=1.2,
                label=f"{rate:.0f}/min", zorder=3)

    _offsets = {
        "E4A_3pm": (10, -10),
        "E4A_5pm": (8, 10),
        "E4A_6pm": (8, -18),
        "E4A_9pm": (8, 10),
        "E4A_12pm": (8, 8),
    }
    for key in E4A_KEYS:
        f, p = psd_pub[key]
        color = E4A_PSD_COLORS[key]
        hz = peak_pub[key]
        m = np.isclose(f, hz)
        if not m.any():
            continue
        pw = float(p[m][0]) / yscale
        ax.plot(hz, pw, "o", color=color, markersize=4.5,
                markeredgecolor="white", markeredgewidth=0.5, zorder=4)
        dx, dy = _offsets[key]
        ax.annotate(
            f"{hz:.3f} Hz", xy=(hz, pw), xytext=(dx, dy),
            textcoords="offset points", fontsize=8.2, color=color,
            fontweight="bold",
            arrowprops=dict(arrowstyle="-", color=color, lw=0.5, alpha=0.5),
            zorder=5,
        )

    ymax = max(float(np.max(psd_arr)) for _, psd_arr in psd_pub.values())
    ymax = ymax / yscale * 1.12
    ax.set_xlim(0.0, 0.42)
    ax.set_ylim(0.0, ymax)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel(r"RR PSD ($\times 10^{3}$ ms$^{2}$/Hz)")
    ax.tick_params(direction="in", which="both")
    ax.grid(axis="y", linewidth=0.3, alpha=0.15)
    ax.set_axisbelow(True)

    for name, xc in [("VLF", 0.0215), ("LF", 0.095), ("HF", 0.25)]:
        ax.text(xc, ymax * 0.97, name, fontsize=9.5, fontweight="bold",
                color="0.50", ha="center", va="top", zorder=6)

    ax.legend(
        title="Breathing rate", title_fontsize=7, fontsize=7.5,
        ncols=3, loc="upper right",
        frameon=True, framealpha=0.92, edgecolor="0.80",
        handlelength=1.2, columnspacing=0.8, borderpad=0.3,
    )

    ax.text(
        0.98, 0.04,
        f"Welch, nperseg = {NPERSEG_PUB},  Δf = {FREQ_RES_HZ:.4f} Hz",
        transform=ax.transAxes, fontsize=5.8, color="0.55",
        ha="right", va="bottom",
    )

    fig.tight_layout()
    path = _save_pdf(fig, "hw05_q4_rr_psd_overlay_e4a.pdf")
    plt.close(fig)
    return path


def render_q4_lfhf_rmssd_clean() -> Path:
    results, _, _ = _e4a_psd_peak_bundle()
    freq_hz = np.array([cfg.E4A_EXPECTED_BREATHING_HZ[k] for k in E4A_KEYS])
    ratio_vals = np.array([results[k].fd_hrv["lf_hf_ratio"] for k in E4A_KEYS])
    rmssd_vals = np.array([results[k].td_hrv["rmssd_ms"] for k in E4A_KEYS])
    colors_arr = [E4A_PSD_COLORS[k] for k in E4A_KEYS]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(3.5, 3.8),
        gridspec_kw={"height_ratios": [1.15, 1], "hspace": 0.12},
    )

    for ax in (ax1, ax2):
        ax.axvspan(cfg.BANDS["LF"][0], cfg.BANDS["LF"][1],
                   color="#f3e8f9", alpha=0.50, zorder=0)
        ax.axvspan(cfg.BANDS["HF"][0], cfg.BANDS["HF"][1],
                   color="#e4f2e4", alpha=0.50, zorder=0)
        ax.axvline(0.15, color="0.40", linewidth=0.9, zorder=1)
        ax.set_xlim(0.035, 0.225)
        ax.grid(axis="y", linewidth=0.3, alpha=0.18)
        ax.tick_params(direction="in", which="both")
        ax.set_axisbelow(True)

    ax1.plot(freq_hz, ratio_vals, "-", color="0.60", linewidth=1.0, zorder=2)
    for i, (fh, rv, c) in enumerate(zip(freq_hz, ratio_vals, colors_arr)):
        ax1.plot(fh, rv, "o", color=c, markersize=7, zorder=4,
                 markeredgecolor="white", markeredgewidth=0.7)
        if i == 0:
            xytext, ha, va = (11, 5), "center", "bottom"
        elif i == 1:
            xytext, ha, va = (12, 2), "left", "bottom"
        elif 0.75 <= rv <= 1.05:
            xytext, ha, va = (0, -11), "center", "top"
        else:
            xytext, ha, va = (0, 9), "center", "bottom"
        ax1.annotate(
            f"{rv:.2f}", (fh, rv), xytext=xytext,
            textcoords="offset points", ha=ha, va=va, fontsize=6.2,
        )

    ax1.set_yscale("log")
    ax1.axhline(1.0, color="0.50", linestyle=":", linewidth=0.8, zorder=1)
    ax1.set_ylim(0.12, 40)
    ax1.set_ylabel("LF / HF ratio")
    ax1.tick_params(labelbottom=False)
    ax1.set_yticks([0.2, 0.5, 1, 2, 5, 10, 20])
    ax1.set_yticklabels(["0.2", "0.5", "1", "2", "5", "10", "20"])
    ax1.yaxis.set_minor_locator(NullLocator())

    ax1.text(0.22, 1.15, "LF/HF = 1", fontsize=5.5, color="0.45", ha="right")
    ax1.text(0.125, 28, "LF band", fontsize=7, ha="center",
             color="#7b2d8e", fontweight="bold", fontstyle="italic")
    ax1.text(0.175, 28, "HF band", fontsize=7, ha="center",
             color="#2d8e4e", fontweight="bold", fontstyle="italic")
    ax1.text(
        0.153, 0.5, "0.15 Hz", fontsize=6, color="0.40",
        rotation=90, va="center", ha="left",
        transform=ax1.get_xaxis_transform(),
    )

    ax_bpm = ax1.secondary_xaxis(
        "top",
        functions=(lambda hz: hz * 60, lambda bpm: bpm / 60))
    ax_bpm.set_xticks([3, 5, 6, 9, 12])
    ax_bpm.set_xticklabels(["3", "5", "6", "9", "12"], fontsize=7)
    ax_bpm.set_xlabel("Breathing rate (breaths/min)", fontsize=7, labelpad=5)
    ax_bpm.tick_params(direction="in", length=3)

    ax2.plot(freq_hz, rmssd_vals, "-", color="0.60", linewidth=1.0, zorder=2)
    for fh, rv, c in zip(freq_hz, rmssd_vals, colors_arr):
        ax2.plot(fh, rv, "s", color=c, markersize=6, zorder=4,
                 markeredgecolor="white", markeredgewidth=0.7)
        ax2.annotate(f"{rv:.1f}", (fh, rv), xytext=(0, 7),
                     textcoords="offset points", ha="center", fontsize=6.2)

    rmssd_mean = float(np.mean(rmssd_vals))
    ax2.axhline(rmssd_mean, color="#2980b9", linestyle="--", linewidth=0.8,
                zorder=1)
    ax2.fill_between(
        [0.035, 0.225],
        float(np.min(rmssd_vals)) - 2,
        float(np.max(rmssd_vals)) + 2,
        color="#2980b9", alpha=0.06, zorder=0,
    )
    ax2.text(0.22, rmssd_mean + 2.5, f"mean = {rmssd_mean:.1f} ms", fontsize=6,
             color="#2980b9", ha="right")
    ax2.set_ylabel("RMSSD (ms)")
    ax2.set_xlabel("Breathing frequency (Hz)", fontsize=7, labelpad=2.5)
    ax2.set_ylim(35, 78)
    ax2.set_xticks(freq_hz)
    ax2.set_xticklabels([f"{h:.3f}" for h in freq_hz], fontsize=6.8)
    for tl in ax2.get_xticklabels():
        tl.set_rotation(22)
        tl.set_ha("right")

    ax1.tick_params(axis="y", which="major", pad=2)
    # Slightly tighter left margin once inner «(a)»/(«b)» glyphs are omitted.
    fig.subplots_adjust(left=0.21, right=0.98, top=0.93, bottom=0.14)

    path = _save_pdf(fig, "hw05_q4_lfhf_rmssd_stacked_clean.pdf")
    plt.close(fig)
    return path


def render_q1_rr_psd_postural() -> Path:
    """RR tachogram (100-s excerpt, y in seconds) + RR PSD (full 300 s)."""
    KEYS = ["E1A", "E1B", "E1C"]
    labels = {
        "E1A": "(a) Supine",
        "E1B": "(b) Sitting",
        "E1C": "(c) Standing",
    }
    DISPLAY_WINDOW_S = 100
    results = {k: P.analyze_steady_state(k) for k in KEYS}

    psd_results = {}
    global_max_psd = 0.0
    for key in KEYS:
        r = results[key]
        f, p = P.rr_psd(r.rr_ms_nk / 1000.0, r.rr_times_nk)
        psd_results[key] = (f, p)
        mask = (f >= 0.04) & (f <= 0.5)
        if mask.any():
            global_max_psd = max(global_max_psd, float(np.max(p[mask])))

    global_max_psd *= 1.45

    fig, axes = plt.subplots(
        2, 3, figsize=(7.16, 4.5),
        constrained_layout=True, sharey="row",
    )

    for i, key in enumerate(KEYS):
        r = results[key]
        td = r.td_hrv
        fd = r.fd_hrv
        f, p = psd_results[key]

        ax_t = axes[0, i]
        rr_s = r.rr_ms_nk / 1000.0
        PL.plot_rr_tachogram(rr_s, r.rr_times_nk, ax=ax_t,
                             color=PL.STYLE_COLORS[key])
        if ax_t.lines:
            ax_t.lines[0].set_linewidth(1.2)
        ax_t.set_xlim(0, DISPLAY_WINDOW_S)
        ax_t.set_title(labels[key], loc="left", fontweight="bold", pad=6)

        td_text = (
            f"HR: {td['mean_hr_bpm']:.0f} bpm\n"
            f"SDNN: {td['sdnn_ms'] / 1000.0:.3f} s\n"
            f"RMSSD: {td['rmssd_ms'] / 1000.0:.3f} s"
        )
        _ty, _tva = (0.05, "bottom") if i <= 1 else (0.95, "top")
        ax_t.text(
            0.95, _ty, td_text, transform=ax_t.transAxes, fontsize=8,
            va=_tva, ha="right",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      alpha=0.8, edgecolor="gray", lw=0.5),
        )
        ax_t.grid(True, linestyle=":", alpha=0.6)
        if i == 0:
            ax_t.set_ylabel("RR Interval (s)")

        ax_f = axes[1, i]
        ax_f.plot(f, p, color="black", lw=1.0)
        ax_f.set_xlim(0.04, 0.5)
        ax_f.set_ylim(0, global_max_psd)

        m_lf = (f >= 0.04) & (f < 0.15)
        m_hf = (f >= 0.15) & (f < 0.40)
        ax_f.fill_between(f, p, where=m_lf, color="#A9A9A9", alpha=0.6,
                          label="LF (0.04\u20130.15 Hz)")
        ax_f.fill_between(f, p, where=m_hf, color="#D3D3D3", alpha=0.6,
                          label="HF (0.15\u20130.40 Hz)")

        lf_s2 = float(fd["lf_ms2"]) / 1e6
        hf_s2 = float(fd["hf_ms2"]) / 1e6
        lf_hz = float(fd["lf_peak_hz"])
        hf_hz = float(fd["hf_peak_hz"])
        fd_text = (
            f"LF: {lf_hz:.2f} Hz | {lf_s2:.4f} s\u00b2\n"
            f"HF: {hf_hz:.2f} Hz | {hf_s2:.4f} s\u00b2"
        )
        ax_f.text(
            0.05, 0.95, fd_text, transform=ax_f.transAxes, fontsize=8,
            va="top", ha="left",
            bbox=dict(boxstyle="square,pad=0.4", facecolor="white",
                      alpha=0.9, edgecolor="lightgray", lw=0.5),
        )

        psd_label = ["(d) PSD (Supine)", "(e) PSD (Sitting)",
                     "(f) PSD (Standing)"][i]
        ax_f.set_title(psd_label, loc="left", fontweight="bold", pad=6)
        ax_f.set_xlabel("Frequency (Hz)")
        if i == 0:
            ax_f.set_ylabel(r"Power Spectral Density (s$^2$/Hz)")
        ax_f.grid(True, linestyle=":", alpha=0.6)

    handles, lbls = axes[1, 0].get_legend_handles_labels()
    fig.legend(handles, lbls, loc="lower center", ncol=2,
               bbox_to_anchor=(0.5, -0.05), frameon=False)

    path = _save_pdf(fig, "hw05_q1_rr_psd_postural.pdf")
    plt.close(fig)
    return path


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "parts",
        nargs="*",
        default=["all"],
        help="q1-rr | q1-ecg | q1-poincare | q4-psd | q4-lfhf | all (default)",
    )
    args = parser.parse_args()
    want = set(args.parts)
    all_ = want == {"all"}

    plt.ioff()
    _apply_hw05_style()

    done: list[Path] = []
    if all_ or "q1-rr" in want:
        done.append(render_q1_rr_psd_postural())
    if all_ or "q1-ecg" in want:
        done.append(render_q1_ecg_psd_row3())
    if all_ or "q1-poincare" in want:
        done.append(render_q1_poincare_row3())
    if all_ or "q4-psd" in want:
        done.append(render_q4_psd_overlay())
    if all_ or "q4-lfhf" in want:
        done.append(render_q4_lfhf_rmssd_clean())

    print("Wrote:")
    for p in done:
        print(f"  {p}")


if __name__ == "__main__":
    main()
