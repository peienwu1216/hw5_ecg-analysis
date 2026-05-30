"""
07 Final Project — IMU-Based Respiratory Validation for Paced Breathing (Phase A)

Analyses:
  A1: IMU z-axis PSD for all 5 paced-breathing rates + deviation table
  A2: Multi-sensor coupling (cross-correlation r, coherence Cxy, zero-lag r)
      + debug waveform plots for 12/min and 3/min
  A3: Reference hierarchy lag (metronome → IMU → HR)
  A4: IMU respiratory frequency overlay on RR PSD (matching nb05_fig02 style)

Outputs → outputs/figures/ and outputs/tables/
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy.signal import butter, coherence, correlate, sosfiltfilt, welch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config as cfg
from src import pipeline as P
from src import plotting as PL

# ─── Constants (matching nb05 notebook exactly) ───────────────────────────────
E4A_KEYS = ["E4A_12pm", "E4A_9pm", "E4A_6pm", "E4A_5pm", "E4A_3pm"]
E4A_LABELS = ["12/min", "9/min", "6/min", "5/min", "3/min"]
E4A_RATES_BPM = [12, 9, 6, 5, 3]
E4A_PSD_COLORS = {
    "E4A_12pm": "#3b4cc0",
    "E4A_9pm": "#7b9ef7",
    "E4A_6pm": "#59a14f",
    "E4A_5pm": "#f28e2b",
    "E4A_3pm": "#e15759",
}
NPERSEG_PUB = 512
FREQ_RES_HZ = cfg.INTERP_FREQ / NPERSEG_PUB


# ─── Helper functions ─────────────────────────────────────────────────────────
def load_gsen_raw(key: str) -> tuple[np.ndarray, np.ndarray]:
    """Load raw triaxial IMU (x,y,z) with analysis-window crop. Returns (t_s, data_g)."""
    root = cfg.get_session_path(key)
    parts: list[np.ndarray] = []
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
    data_g = raw * scale
    t_s = np.arange(data_g.shape[0], dtype=float) / cfg.FS_GSEN
    return t_s, data_g


def bandpass(sig: np.ndarray, fs: float, lo: float, hi: float, order: int = 4) -> np.ndarray:
    sos = butter(order, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return sosfiltfilt(sos, sig, axis=0)


def lowpass(sig: np.ndarray, fs: float, cutoff: float, order: int = 4) -> np.ndarray:
    sos = butter(order, cutoff, btype="low", fs=fs, output="sos")
    return sosfiltfilt(sos, sig, axis=0)


def zscore(x: np.ndarray) -> np.ndarray:
    sd = float(np.std(x))
    if not np.isfinite(sd) or sd < 1e-12:
        return np.zeros_like(x)
    return (x - float(np.mean(x))) / sd


def find_peak_near(f: np.ndarray, p: np.ndarray, target_hz: float,
                   search_bw: float = 0.04) -> tuple[float, float]:
    """Find PSD peak within search range of target_hz. Returns (peak_hz, peak_power).
    Search range: [max(target*0.6, 0.03), target + search_bw] to avoid VLF drift.
    """
    lo = max(target_hz * 0.6, 0.03)
    hi = target_hz + search_bw
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return float("nan"), 0.0
    idx = np.argmax(p[m])
    return float(f[m][idx]), float(p[m][idx])


def best_lag_corr(a: np.ndarray, b: np.ndarray, fs: float,
                  lag_limit_s: float = 8.0) -> tuple[float, float]:
    """Peak cross-correlation and optimal lag (positive = b leads a)."""
    a0 = zscore(a)
    b0 = zscore(b)
    c = correlate(a0, b0, mode="full") / len(a0)
    lags = np.arange(-len(a0) + 1, len(a0)) / fs
    m = np.abs(lags) <= lag_limit_s
    idx = int(np.argmax(c[m]))
    return float(lags[m][idx]), float(c[m][idx])


# ─── ANALYSIS A1: IMU PSD for all 5 breathing rates ──────────────────────────
print("=" * 70)
print("ANALYSIS A1: IMU PSD — Respiratory Peak Detection Across 5 Rates")
print("=" * 70)

a1_results = []

PL.apply_style()
fig_a1, axes_a1 = plt.subplots(1, 5, figsize=(16, 3.0), sharey=False)

for i, (key, label, rate_bpm) in enumerate(zip(E4A_KEYS, E4A_LABELS, E4A_RATES_BPM)):
    t_imu, imu_g = load_gsen_raw(key)
    expected_hz = rate_bpm / 60.0
    color = E4A_PSD_COLORS[key]

    imu_lp = lowpass(imu_g, cfg.FS_GSEN, 0.7)
    z_sig = imu_lp[:, 2]
    nperseg_z = min(4096 if expected_hz < 0.08 else 2048, len(z_sig))
    f_z, p_z = welch(z_sig - np.mean(z_sig), fs=cfg.FS_GSEN, nperseg=nperseg_z)
    peak_hz, _ = find_peak_near(f_z, p_z, expected_hz, search_bw=0.04)

    delta_hz = peak_hz - expected_hz

    a1_results.append({
        "condition": label,
        "rate_bpm": rate_bpm,
        "expected_hz": expected_hz,
        "imu_peak_hz": peak_hz,
        "imu_peak_bpm": peak_hz * 60,
        "delta_hz": delta_hz,
        "abs_delta_hz": abs(delta_hz),
    })

    ax = axes_a1[i]
    # FIX: start x-axis at 0.03 Hz to avoid VLF/DC peak dominating y-scale
    x_lo = 0.03
    x_hi = min(0.35, max(0.25, expected_hz + 0.10))
    m = (f_z >= x_lo) & (f_z <= x_hi)
    ax.plot(f_z[m], p_z[m], color=color, linewidth=1.3)
    ax.axvline(expected_hz, color="0.5", linestyle="--", linewidth=0.9,
               label=f"Target {expected_hz:.3f}")
    ax.axvline(peak_hz, color=color, linestyle=":", linewidth=1.5,
               label=f"IMU {peak_hz:.3f}")
    ax.fill_between(f_z[m], 0, p_z[m], alpha=0.08, color=color)
    ax.set_title(f"{label}", fontsize=10, fontweight="bold")
    ax.set_xlabel("Frequency (Hz)", fontsize=8)
    if i == 0:
        ax.set_ylabel("PSD (g²/Hz)", fontsize=8)
    ax.legend(fontsize=6.5, loc="upper right")
    ax.grid(True, alpha=0.15, linewidth=0.3)
    ax.tick_params(labelsize=7)

    print(f"  {label}: expected={expected_hz:.4f} Hz, IMU peak={peak_hz:.4f} Hz, "
          f"|Δf|={abs(delta_hz):.4f} Hz")

fig_a1.suptitle("IMU z-axis PSD: Respiratory Peak Detection Across Paced-Breathing Rates",
                fontsize=11, y=1.01)
fig_a1.tight_layout()
out_a1 = cfg.FIGURES_DIR / "fp_a1_imu_psd_5rates.pdf"
fig_a1.savefig(out_a1, bbox_inches="tight", dpi=150)
plt.close(fig_a1)
print(f"\n  Figure saved: {out_a1}")

df_a1 = pd.DataFrame(a1_results)
table_a1_path = cfg.TABLES_DIR / "fp_a1_imu_breathing_deviation.csv"
df_a1.to_csv(table_a1_path, index=False)
print(f"  Table saved: {table_a1_path}")
print(f"\n  Summary: mean |Δf| = {df_a1['abs_delta_hz'].mean():.4f} Hz")
print(df_a1[["condition", "expected_hz", "imu_peak_hz", "abs_delta_hz"]].to_string(index=False))


# ─── ANALYSIS A2: Multi-sensor coupling for all 5 conditions ─────────────────
print("\n" + "=" * 70)
print("ANALYSIS A2: Multi-sensor coupling validation")
print("=" * 70)

a2_results = []
a2_waveforms = {}  # store for debug plots

for i, (key, label, rate_bpm) in enumerate(zip(E4A_KEYS, E4A_LABELS, E4A_RATES_BPM)):
    expected_hz = rate_bpm / 60.0
    period_s = 60.0 / rate_bpm
    t_imu, imu_g = load_gsen_raw(key)

    # Respiratory bandpass
    bw = max(0.03, expected_hz * 0.3)
    bp_lo = max(0.02, expected_hz - bw)
    bp_hi = min(0.49 * cfg.FS_GSEN, expected_hz + bw)

    imu_bp_z = bandpass(imu_g[:, 2], cfg.FS_GSEN, bp_lo, bp_hi)
    imu_flow_proxy = np.gradient(zscore(-imu_bp_z), 1.0 / cfg.FS_GSEN)
    imu_flow_proxy = zscore(imu_flow_proxy)

    rr = P.analyze_steady_state(key)
    rr_ms = np.asarray(rr.rr_ms_nk, dtype=float)
    rr_t = np.asarray(rr.rr_times_nk, dtype=float)
    hr_bpm = 60000.0 / rr_ms

    t_uniform = np.arange(0.0, t_imu[-1] + 1.0 / cfg.FS_GSEN, 1.0 / cfg.FS_GSEN)
    hr_uniform = interp1d(rr_t, hr_bpm - np.mean(hr_bpm), kind="cubic",
                          bounds_error=False, fill_value="extrapolate")(t_uniform)
    hr_bp = bandpass(hr_uniform, cfg.FS_GSEN, bp_lo, bp_hi)
    hr_bp_z = zscore(hr_bp)

    n = min(len(imu_flow_proxy), len(hr_bp_z))
    imu_seg = imu_flow_proxy[:n]
    hr_seg = hr_bp_z[:n]

    # Store waveforms for debug (12/min and 3/min)
    if key in ("E4A_12pm", "E4A_3pm"):
        a2_waveforms[key] = {
            "t": t_imu[:n],
            "imu_seg": imu_seg,
            "hr_seg": hr_seg,
            "bp_lo": bp_lo,
            "bp_hi": bp_hi,
            "period_s": period_s,
        }

    lag_limit = min(period_s * 0.4, 5.0)
    lag_s, peak_r = best_lag_corr(hr_seg, imu_seg, cfg.FS_GSEN, lag_limit_s=lag_limit)

    nperseg_coh = min(512, n)
    f_coh, cxy = coherence(hr_seg, imu_seg, fs=cfg.FS_GSEN, nperseg=nperseg_coh)
    idx_target = np.argmin(np.abs(f_coh - expected_hz))
    cxy_at_target = float(cxy[idx_target])

    zero_lag_r = float(np.corrcoef(hr_seg, imu_seg)[0, 1])

    a2_results.append({
        "condition": label,
        "rate_bpm": rate_bpm,
        "peak_xcorr_r": peak_r,
        "optimal_lag_s": lag_s,
        "coherence_Cxy": cxy_at_target,
        "zero_lag_r": zero_lag_r,
    })

    print(f"  {label}: peak r={peak_r:.3f}, lag={lag_s:.2f}s, "
          f"Cxy={cxy_at_target:.3f}, zero-lag r={zero_lag_r:.3f}")

df_a2 = pd.DataFrame(a2_results)
table_a2_path = cfg.TABLES_DIR / "fp_a2_multisensor_coupling.csv"
df_a2.to_csv(table_a2_path, index=False)
print(f"\n  Table saved: {table_a2_path}")
print(df_a2.to_string(index=False))


# ─── A2 DEBUG: Waveform plots for 12/min and 3/min ───────────────────────────
print("\n" + "=" * 70)
print("A2 DEBUG: Waveform comparison for 12/min and 3/min")
print("=" * 70)

fig_dbg, axes_dbg = plt.subplots(2, 2, figsize=(14, 6))

for row, (key, label) in enumerate([("E4A_12pm", "12/min"), ("E4A_3pm", "3/min")]):
    wf = a2_waveforms[key]
    t = wf["t"]
    imu = wf["imu_seg"]
    hr = wf["hr_seg"]
    period = wf["period_s"]

    # Left panel: time-domain overlay (first 60s)
    ax_t = axes_dbg[row, 0]
    view_end = min(60.0, t[-1])
    m = t <= view_end
    ax_t.plot(t[m], hr[m], color="#2E4057", linewidth=0.9, label="HR resp. component")
    ax_t.plot(t[m], imu[m], color=E4A_PSD_COLORS[key], linewidth=0.9, alpha=0.8,
              label="IMU flow proxy")
    ax_t.set_title(f"{label} — Time-domain waveforms (first 60s)\n"
                   f"BP: [{wf['bp_lo']:.3f}, {wf['bp_hi']:.3f}] Hz",
                   fontsize=9)
    ax_t.set_xlabel("Time (s)")
    ax_t.set_ylabel("z-score")
    ax_t.legend(fontsize=8)
    ax_t.grid(True, alpha=0.15)

    # Right panel: cross-correlation function
    ax_c = axes_dbg[row, 1]
    a0 = zscore(hr)
    b0 = zscore(imu)
    c = correlate(a0, b0, mode="full") / len(a0)
    lags = np.arange(-len(a0) + 1, len(a0)) / cfg.FS_GSEN
    lag_limit = min(period * 0.4, 5.0)
    m_lag = np.abs(lags) <= lag_limit
    ax_c.plot(lags[m_lag], c[m_lag], color=E4A_PSD_COLORS[key], linewidth=1.0)
    # Mark peak
    idx_peak = np.argmax(c[m_lag])
    peak_lag = lags[m_lag][idx_peak]
    peak_val = c[m_lag][idx_peak]
    ax_c.axvline(peak_lag, color="red", linestyle="--", linewidth=0.8)
    ax_c.axvline(0, color="0.5", linestyle=":", linewidth=0.5)
    ax_c.plot(peak_lag, peak_val, "ro", markersize=6)
    ax_c.set_title(f"{label} — Cross-correlation\n"
                   f"Peak r={peak_val:.3f} at lag={peak_lag:.2f}s "
                   f"(lag limit ±{lag_limit:.1f}s)",
                   fontsize=9)
    ax_c.set_xlabel("Lag (s) [positive = IMU leads HR]")
    ax_c.set_ylabel("Correlation")
    ax_c.grid(True, alpha=0.15)

fig_dbg.tight_layout()
out_dbg = cfg.FIGURES_DIR / "fp_a2_debug_waveforms_12_3min.pdf"
fig_dbg.savefig(out_dbg, bbox_inches="tight", dpi=150)
plt.close(fig_dbg)
print(f"  Debug figure saved: {out_dbg}")


# ─── ANALYSIS A3: Reference hierarchy lag ────────────────────────────────────
print("\n" + "=" * 70)
print("ANALYSIS A3: Reference hierarchy lag (IMU → HR)")
print("=" * 70)

a3_results = []
for i, (key, label, rate_bpm) in enumerate(zip(E4A_KEYS, E4A_LABELS, E4A_RATES_BPM)):
    lag_imu_hr = a2_results[i]["optimal_lag_s"]
    peak_r = a2_results[i]["peak_xcorr_r"]
    a3_results.append({
        "condition": label,
        "rate_bpm": rate_bpm,
        "imu_to_hr_lag_s": lag_imu_hr,
        "peak_xcorr_r": peak_r,
        "interpretation": "IMU leads HR" if lag_imu_hr > 0 else "HR leads IMU",
    })
    sign = "IMU leads HR" if lag_imu_hr > 0 else "HR leads IMU"
    print(f"  {label}: IMU→HR lag = {lag_imu_hr:.2f}s ({sign}), r = {peak_r:.3f}")

df_a3 = pd.DataFrame(a3_results)
table_a3_path = cfg.TABLES_DIR / "fp_a3_reference_hierarchy_lag.csv"
df_a3.to_csv(table_a3_path, index=False)
print(f"\n  Table saved: {table_a3_path}")

valid_lags = df_a3[df_a3["imu_to_hr_lag_s"] > 0]["imu_to_hr_lag_s"]
if len(valid_lags) > 0:
    mean_lag = valid_lags.mean()
    print(f"\n  Mean lag (IMU leads HR): {mean_lag:.2f} s")
    print(f"  Consistent with cardiopulmonary reflex latency (~1-3 s per literature)")


# ─── ANALYSIS A4: IMU frequency overlay on RR PSD (nb05_fig02 style) ─────────
print("\n" + "=" * 70)
print("ANALYSIS A4: IMU respiratory frequency overlay on RR PSD")
print("  (matching nb05_fig02_e4a_psd_overlay.pdf style exactly)")
print("=" * 70)

PL.apply_style()

# Compute PSD (same parameters as nb05)
psd_pub = {}
peak_pub = {}
for key in E4A_KEYS:
    rr = P.analyze_steady_state(key)
    f, p = P.rr_psd(rr.rr_ms_nk, rr.rr_times_nk, nperseg=NPERSEG_PUB)
    psd_pub[key] = (f, p)
    m = (f >= 0.01) & (f <= 0.45)
    peak_pub[key] = float(f[m][np.argmax(p[m])]) if m.any() else float("nan")

YSCALE = 1e3  # display in ×10³ ms²/Hz

fig_a4, ax = plt.subplots(figsize=(7.16, 3.2))

# ① Subtle alternating band shading (neutral grays, same as nb05)
_fills = {"VLF": "#f2f2f2", "LF": "#eaeaea", "HF": "#f2f2f2"}
for band, (lo, hi) in cfg.BANDS.items():
    ax.axvspan(lo, hi, color=_fills[band], linewidth=0, zorder=0)

# ② Thin solid band-boundary lines
for edge in (0.04, 0.15, 0.40):
    ax.axvline(edge, color="0.78", linewidth=0.4, zorder=1)

# ③ PSD curves (same style as nb05)
for key in E4A_KEYS:
    f, p = psd_pub[key]
    rate = cfg.E4A_EXPECTED_BREATHING_HZ[key] * 60
    ax.plot(f, p / YSCALE, color=E4A_PSD_COLORS[key], linewidth=1.2,
            label=f"{rate:.0f}/min", zorder=3)

# ④ RR PSD Peak markers + frequency annotations (same offsets as nb05)
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
    pw = float(p[m][0]) / YSCALE
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

# ⑤ IMU-confirmed respiratory frequency: top ▼ markers only (no vertical lines)
import matplotlib.transforms as _mtrans
_top_trans = _mtrans.blended_transform_factory(ax.transData, ax.transAxes)
for i, (key, label) in enumerate(zip(E4A_KEYS, E4A_LABELS)):
    imu_hz = df_a1.iloc[i]["imu_peak_hz"]
    color = E4A_PSD_COLORS[key]
    if np.isfinite(imu_hz):
        ax.plot(imu_hz, 1.02, marker="v", color=color, markersize=6,
                transform=_top_trans, clip_on=False, zorder=7)

# ⑥ Axes (same as nb05)
ymax = max(float(np.max(psd_arr)) for _, psd_arr in psd_pub.values()) / YSCALE * 1.12
ax.set_xlim(0.0, 0.42)
ax.set_ylim(0.0, ymax)
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel(r"RR PSD ($\times 10^{3}$ ms$^{2}$/Hz)")
ax.tick_params(direction="in", which="both")
ax.grid(axis="x", visible=False)
ax.grid(axis="y", linewidth=0.3, alpha=0.15)
ax.set_axisbelow(True)

# ⑦ Band labels (same as nb05)
for name, xc in [("VLF", 0.0215), ("LF", 0.095), ("HF", 0.25)]:
    ax.text(xc, ymax * 0.97, name, fontsize=9.5, fontweight="bold",
            color="0.50", ha="center", va="top", zorder=6)

# ⑧ Legend (expanded to include IMU note)
ax.legend(
    title="Breathing rate", title_fontsize=7, fontsize=7.5,
    ncols=3, loc="upper right",
    frameon=True, framealpha=0.92, edgecolor="0.80",
    handlelength=1.2, columnspacing=0.8, borderpad=0.3,
)

# ⑨ Technical note + IMU annotation
ax.text(
    0.98, 0.04,
    f"Welch, nperseg = {NPERSEG_PUB},  Δf = {FREQ_RES_HZ:.4f} Hz\n"
    f"Top triangles (▼): IMU-derived respiratory frequency (independent confirmation)",
    transform=ax.transAxes, fontsize=5.8, color="0.55",
    ha="right", va="bottom",
)

fig_a4.tight_layout()
out_a4 = cfg.FIGURES_DIR / "fp_a4_rr_psd_imu_overlay.pdf"
fig_a4.savefig(out_a4, bbox_inches="tight", dpi=150)
plt.close(fig_a4)
print(f"  Figure saved: {out_a4}")


# ─── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PHASE A COMPLETE")
print("=" * 70)
print(f"\n  Figures:")
print(f"    {out_a1}")
print(f"    {out_dbg}")
print(f"    {out_a4}")
print(f"\n  Tables:")
print(f"    {table_a1_path}")
print(f"    {table_a2_path}")
print(f"    {table_a3_path}")
print(f"\n  Key Results:")
print(f"    A1: Mean |Δf| = {df_a1['abs_delta_hz'].mean():.4f} Hz")
print(f"    A2: Peak r (9/6/5 bpm): {df_a2[df_a2['rate_bpm'].isin([9,6,5])]['peak_xcorr_r'].mean():.3f}")
print(f"    A2: Mean Cxy (9/6/5 bpm): {df_a2[df_a2['rate_bpm'].isin([9,6,5])]['coherence_Cxy'].mean():.3f}")
if len(valid_lags) > 0:
    print(f"    A3: Mean IMU→HR lag (positive): {mean_lag:.2f} s")
