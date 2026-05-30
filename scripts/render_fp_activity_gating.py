#!/usr/bin/env python3
"""Render the activity-channel gating figure for final-project Section 5.2.

This figure is the symmetric partner to the respiratory-fusion figure
(Fig. ``fp_fusion_recovery.pdf``). Where the respiratory channel *reassigns*
IMU-confirmed RSA power, the activity channel *gates* HRV validity: it shows
that walking motion raises the accelerometer envelope ~3x and that the step
frequency overlaps the cardiac fundamental, so walking-phase fine-scale HRV is
motion-limited rather than autonomically interpretable.

All numbers are recomputed from the E3_walk recording; nothing is hard-coded.

Run from the repo root::

    ./.venv/bin/python scripts/render_fp_activity_gating.py

Output: ``outputs/figures/fp_activity_gating.pdf``
"""

from __future__ import annotations

import sys
import warnings
from math import gcd
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import coherence, detrend, resample_poly, welch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src import config as cfg  # noqa: E402
from src import pipeline as P  # noqa: E402
from src import plotting as PL  # noqa: E402

OUTPUT_NAME = "fp_activity_gating.pdf"

SEG_COLORS = {"seated": "#A9A9A9", "walking": "#E8A0A0", "recovery": "#8FBC8F"}


def _apply_style() -> None:
    PL.apply_style()
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 9,
        "axes.labelsize": 10,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def _moving_rms(x: np.ndarray, window_samples: int) -> np.ndarray:
    if window_samples <= 1:
        return np.asarray(x, dtype=float)
    kernel = np.ones(window_samples, dtype=float) / window_samples
    return np.sqrt(np.convolve(np.square(x), kernel, mode="same"))


def _compute() -> dict:
    r = P.analyze_transient_event("E3_walk")
    t_g, motion_g = P.load_gsen("E3_walk")

    # --- segment motion RMS + 2-s envelope ---
    env_win_n = max(3, int(round(2.0 * cfg.FS_GSEN)))
    motion_env = _moving_rms(motion_g, env_win_n)
    motion_rms = {}
    for name, (t0, t1) in cfg.E3_SEG.items():
        m = (t_g >= t0) & (t_g < t1)
        motion_rms[name] = (
            float(np.sqrt(np.mean(np.square(motion_g[m])))) if np.any(m) else float("nan")
        )

    # --- walking accelerometer PSD + step peak ---
    t0w, t1w = cfg.E3_SEG["walking"]
    m_w = (t_g >= t0w) & (t_g < t1w)
    f_g, p_g = welch(
        motion_g[m_w] - np.mean(motion_g[m_w]),
        fs=cfg.FS_GSEN,
        nperseg=min(256, int(np.sum(m_w))),
    )
    cad = (f_g >= 0.8) & (f_g <= 3.5)
    step_peak_hz = float(f_g[cad][np.argmax(p_g[cad])])

    # --- walking ECG PSD + cardiac fundamental ---
    i0, i1 = int(t0w * cfg.FS), int(t1w * cfg.FS)
    ecg_w = r.ecg_filt[i0:i1].astype(float)
    f_ecg, p_ecg = P.ecg_psd(ecg_w, fs=cfg.FS, nperseg_sec=8)
    hr_walk = r.extras["transient_hrv"]["walking"]["mean_hr_bpm"]
    ecg_f0 = hr_walk / 60.0

    # --- ECG-motion coherence (replicates notebook 04) ---
    motion_w = motion_g[m_w].astype(float)
    fs_ecg, fs_motion = int(cfg.FS), int(cfg.FS_GSEN)
    g = gcd(fs_ecg, fs_motion)
    ecg_ds = resample_poly(ecg_w, up=fs_motion // g, down=fs_ecg // g)
    n = min(len(ecg_ds), len(motion_w))
    ecg_ds = detrend(ecg_ds[:n] - np.mean(ecg_ds[:n]))
    motion_w = detrend(motion_w[:n] - np.mean(motion_w[:n]))
    nperseg = min(256, n)
    f_coh, cxy = coherence(ecg_ds, motion_w, fs=fs_motion,
                           nperseg=nperseg, noverlap=nperseg // 2)
    cad_band = (f_coh >= 1.0) & (f_coh <= 3.0)
    coh_at_step = float(np.interp(step_peak_hz, f_coh, cxy))
    coh_band_mean = float(np.nanmean(cxy[cad_band]))

    return dict(
        t_g=t_g, motion_g=motion_g, motion_env=motion_env, motion_rms=motion_rms,
        f_g=f_g, p_g=p_g, step_peak_hz=step_peak_hz,
        f_ecg=f_ecg, p_ecg=p_ecg, ecg_f0=ecg_f0, hr_walk=hr_walk,
        coh_at_step=coh_at_step, coh_band_mean=coh_band_mean,
    )


def render(d: dict) -> plt.Figure:
    fig, (ax_t, ax_p) = plt.subplots(2, 1, figsize=(6.6, 6.4))

    # ---------- (a) accelerometer magnitude + RMS envelope ----------
    ax_t.plot(d["t_g"], d["motion_g"], color="#B8A1E3", lw=0.7, alpha=0.6,
              label="Motion magnitude")
    ax_t.plot(d["t_g"], d["motion_env"], color="#5A189A", lw=1.8,
              label="2-s RMS envelope")
    ax_t.set_xlim(0, 180)
    ax_t.set_xlabel("Time (s)")
    ax_t.set_ylabel("Motion magnitude (g)")
    ax_t.set_title("(a) Accelerometer magnitude across seated / walking / recovery",
                   loc="left", fontsize=10, fontweight="bold")
    ax_t.grid(True, linestyle="--", alpha=0.3)

    for name, (t0, t1) in cfg.E3_SEG.items():
        ax_t.axvspan(t0, t1, color=SEG_COLORS.get(name, "gray"), alpha=0.18, zorder=-1)
        ax_t.text((t0 + t1) / 2, 0.04, name.capitalize(),
                  transform=ax_t.get_xaxis_transform(),
                  ha="center", va="bottom", fontsize=8.5, fontweight="bold",
                  color="dimgray")

    rms = d["motion_rms"]
    fold = rms["walking"] / rms["seated"] if rms["seated"] else float("nan")
    stats = (
        "Segment motion RMS\n"
        f"Seated:   {rms['seated']:.3f} g\n"
        f"Walking:  {rms['walking']:.3f} g\n"
        f"Recovery: {rms['recovery']:.3f} g"
    )
    ax_t.text(0.985, 0.94, stats, transform=ax_t.transAxes, fontsize=8.2,
              ha="right", va="top",
              bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                        alpha=0.92, edgecolor="gray"))
    ax_t.legend(loc="upper left", framealpha=0.95, fontsize=8.2)

    # ---------- (b) step vs cardiac spectral overlap ----------
    ax_p.axvspan(1.0, 3.0, color="#F4D6D6", alpha=0.45, zorder=-1)

    ln_ecg, = ax_p.semilogy(d["f_ecg"], d["p_ecg"], color="#C44E52", lw=1.3,
                            label="ECG PSD (walking)")
    ax_p.set_xlim(0.4, 4.0)
    mask = (d["f_ecg"] > 0.5) & (d["f_ecg"] < 4.0) & np.isfinite(d["p_ecg"]) & (d["p_ecg"] > 0)
    ymax = np.max(d["p_ecg"][mask])
    ax_p.set_ylim(ymax / 1e4, ymax * 5)
    ax_p.set_xlabel("Frequency (Hz)")
    ax_p.set_ylabel("ECG PSD (mV$^2$/Hz)", color="#C44E52")
    ax_p.tick_params(axis="y", colors="#C44E52")

    # cardiac fundamental
    ax_p.axvline(d["ecg_f0"], color="#C44E52", linestyle=":", lw=1.4)
    ax_p.annotate(rf"cardiac $f_0$ = {d['ecg_f0']:.2f} Hz",
                  xy=(d["ecg_f0"], 0.97), xycoords=("data", "axes fraction"),
                  xytext=(-4, 0), textcoords="offset points",
                  ha="right", va="top", fontsize=8.5, color="#C44E52",
                  bbox=dict(facecolor="white", alpha=0.8, edgecolor="none", pad=1.2))

    # accelerometer PSD on twin axis
    ax_g = ax_p.twinx()
    ax_g.spines["top"].set_visible(False)
    ln_g, = ax_g.semilogy(d["f_g"], d["p_g"], color="#6F2DBD", lw=1.5,
                          label="Accelerometer PSD (walking)")
    gm = (d["f_g"] >= 0.4) & (d["f_g"] <= 4.0) & np.isfinite(d["p_g"]) & (d["p_g"] > 0)
    g_ymax = float(np.max(d["p_g"][gm]) * 5.0)
    ax_g.set_ylim(g_ymax / 1e4, g_ymax)
    ax_g.set_ylabel("Accelerometer PSD (g$^2$/Hz)", color="#6F2DBD")
    ax_g.tick_params(axis="y", colors="#6F2DBD")

    sp = d["step_peak_hz"]
    ax_g.axvline(sp, color="#3A1A6B", linestyle="--", lw=1.4)
    ax_g.annotate(f"step peak = {sp:.2f} Hz\n({60 * sp:.0f} steps/min)",
                  xy=(sp, 0.97), xycoords=("data", "axes fraction"),
                  xytext=(6, 0), textcoords="offset points",
                  ha="left", va="top", fontsize=8.5, color="#3A1A6B",
                  bbox=dict(facecolor="white", alpha=0.8, edgecolor="none", pad=1.2))

    ax_p.set_title("(b) Step-frequency vs. cardiac-fundamental spectral overlap",
                   loc="left", fontsize=10, fontweight="bold")

    coh_text = (
        "ECG–motion coherence\n"
        f"at step peak: $C_{{xy}}$ = {d['coh_at_step']:.2f}\n"
        f"1–3 Hz band mean: {d['coh_band_mean']:.2f}"
    )
    ax_p.text(0.985, 0.05, coh_text, transform=ax_p.transAxes, fontsize=8.2,
              ha="right", va="bottom",
              bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                        alpha=0.92, edgecolor="gray"))
    ax_p.text(2.0, 0.30, "1–3 Hz overlap band", transform=ax_p.get_xaxis_transform(),
              ha="center", va="center", fontsize=8.5, color="#B03A3A",
              fontweight="bold",
              bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=1.2))

    leg = ax_g.legend(handles=[ln_ecg, ln_g], loc="lower right",
                      bbox_to_anchor=(0.7, 0), framealpha=1.0,
                      fontsize=8.0, edgecolor="0.3", facecolor="white",
                      borderpad=0.55, handlelength=1.8, fancybox=False)
    leg.set_zorder(50)
    frame = leg.get_frame()
    frame.set_linewidth(0.8)
    frame.set_boxstyle("square,pad=0.35")

    fig.tight_layout(pad=0.8)
    return fig


def main() -> Path:
    _apply_style()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    d = _compute()
    print(
        "Verified: step={step_peak_hz:.3f} Hz, f0={ecg_f0:.3f} Hz, "
        "Cxy@step={coh_at_step:.3f}, Cxy(1-3)={coh_band_mean:.3f}, "
        "RMS seated/walk/recov={s:.3f}/{w:.3f}/{rc:.3f} g".format(
            **d, s=d["motion_rms"]["seated"], w=d["motion_rms"]["walking"],
            rc=d["motion_rms"]["recovery"],
        )
    )
    fig = render(d)
    out = PL.save_figure(fig, OUTPUT_NAME)
    plt.close(fig)
    print(f"Wrote {out}")
    return out


if __name__ == "__main__":
    main()
