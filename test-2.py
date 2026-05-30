from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import interp1d
from scipy.signal import butter, correlate, sosfiltfilt, welch

from src import config as cfg
from src import pipeline as P
from src import plotting as PL


SESSION_KEY = "E4A_5pm"
TARGET_HZ = 5.0 / 60.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deep-dive raw IMU x/y/z data for the 5 breaths/min paced-breathing trial."
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display the matplotlib window after saving the PDF.",
    )
    return parser.parse_args()


def load_gsen_raw(key: str, apply_window: bool = True) -> tuple[np.ndarray, np.ndarray]:
    root = cfg.get_session_path(key)
    parts: list[np.ndarray] = []
    for hour_dir in P._sorted_hour_dirs(root):
        csv_path = hour_dir / "gsen.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing {csv_path}")
        parts.append(np.loadtxt(csv_path, delimiter=",", dtype=float))
    raw = np.concatenate(parts, axis=0)

    if apply_window:
        start_s, end_s = cfg.FILE_INVENTORY[key]["window"]
        i0 = int(round(start_s * cfg.FS_GSEN))
        i1 = int(round(end_s * cfg.FS_GSEN))
        raw = raw[i0:min(i1, raw.shape[0])]

    t_s = np.arange(raw.shape[0], dtype=float) / cfg.FS_GSEN
    return t_s, raw


def zscore(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    sd = float(np.std(x))
    if not np.isfinite(sd) or sd == 0.0:
        return np.zeros_like(x)
    return (x - float(np.mean(x))) / sd


def bandpass(sig: np.ndarray, fs: float, lo: float, hi: float) -> np.ndarray:
    sos = butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
    axis = 0 if np.ndim(sig) > 1 else -1
    return sosfiltfilt(sos, sig, axis=axis)


def lowpass(sig: np.ndarray, fs: float, cutoff: float) -> np.ndarray:
    sos = butter(4, cutoff, btype="low", fs=fs, output="sos")
    axis = 0 if np.ndim(sig) > 1 else -1
    return sosfiltfilt(sos, sig, axis=axis)


def dominant_peak(sig: np.ndarray, fs: float, lo: float = 0.02, hi: float = 0.5) -> tuple[float, float]:
    f, p = welch(sig - np.mean(sig), fs=fs, nperseg=min(2048, len(sig)))
    m = (f >= lo) & (f <= hi)
    idx = np.argmax(p[m])
    return float(f[m][idx]), float(p[m][idx])


def best_lag_corr(
    a: np.ndarray,
    b: np.ndarray,
    fs: float,
    lag_limit_s: float = 8.0,
    mode: str = "positive",
) -> tuple[float, float]:
    a0 = zscore(a)
    b0 = zscore(b)
    c = correlate(a0, b0, mode="full") / len(a0)
    lags = np.arange(-len(a0) + 1, len(a0)) / fs
    m = np.abs(lags) <= lag_limit_s
    c_view = c[m]
    lags_view = lags[m]
    if mode == "abs":
        idx = int(np.argmax(np.abs(c_view)))
    elif mode == "negative":
        idx = int(np.argmin(c_view))
    else:
        idx = int(np.argmax(c_view))
    return float(lags_view[idx]), float(c_view[idx])


def format_phase_relation(lag_s: float) -> str:
    if abs(lag_s) < 1e-9:
        return "HR and IMU are synchronous"
    if lag_s > 0.0:
        return f"IMU leads HR by {lag_s:.2f}s"
    return f"HR leads IMU by {abs(lag_s):.2f}s"


def main() -> None:
    args = parse_args()
    PL.apply_style()
    crop_start_s = float(cfg.FILE_INVENTORY[SESSION_KEY]["window"][0])
    metronome_period_s = 1.0 / TARGET_HZ
    metronome_offset_s = (-crop_start_s) % metronome_period_s

    rr = P.analyze_steady_state(SESSION_KEY)
    rr_ms = np.asarray(rr.rr_ms_nk, dtype=float)
    rr_t = np.asarray(rr.rr_times_nk, dtype=float)
    hr_bpm = 60000.0 / rr_ms

    t_imu, imu_raw = load_gsen_raw(SESSION_KEY)
    scale = 1.0 / 1000.0 if float(np.max(np.abs(imu_raw))) > 10.0 else 1.0
    imu_g = imu_raw * scale

    imu_lp = lowpass(imu_g, cfg.FS_GSEN, 0.7)
    imu_bp = bandpass(imu_g, cfg.FS_GSEN, 0.04, 0.18)

    rr_uniform_t = np.arange(0.0, t_imu[-1] + 1.0 / cfg.FS_GSEN, 1.0 / cfg.FS_GSEN)
    hr_uniform = interp1d(
        rr_t,
        hr_bpm - np.mean(hr_bpm),
        kind="cubic",
        bounds_error=False,
        fill_value="extrapolate",
    )(rr_uniform_t)
    hr_bp = bandpass(hr_uniform, cfg.FS_GSEN, 0.04, 0.18)

    peak_info = {name: dominant_peak(imu_lp[:, i], cfg.FS_GSEN) for i, name in enumerate("xyz")}

    hr_bp_at_beats = interp1d(
        rr_uniform_t,
        hr_bp,
        kind="linear",
        bounds_error=False,
        fill_value="extrapolate",
    )(rr_t)
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(12, 6.6),
        sharex=False,
        gridspec_kw={"height_ratios": [1.0, 1.0]},
    )

    raw_colors = {"x": "#4C72B0", "y": "#55A868", "z": "#C44E52"}

    ax2 = axes[0]
    for i, name in enumerate(("x", "y", "z")):
        f, p = welch(imu_lp[:, i] - np.mean(imu_lp[:, i]), fs=cfg.FS_GSEN, nperseg=min(2048, len(imu_lp)))
        ax2.plot(f, p, color=raw_colors[name], linewidth=1.25, label=f"{name} PSD")
    ax2.axvline(TARGET_HZ, color="#7f7f7f", linestyle="--", linewidth=1.0, label="5/min target")
    ax2.set_xlim(0.0, 0.25)
    ax2.set_title("Respiratory-band spectral peak", loc="left")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("PSD")
    ax2.legend(loc="upper right", ncol=2)
    ax2.grid(True, linestyle="--", alpha=0.22)
    ax2.text(
        -0.055,
        1.02,
        "(a)",
        transform=ax2.transAxes,
        fontsize=11,
        fontweight="bold",
        ha="right",
        va="bottom",
        clip_on=False,
    )

    ax3 = axes[1]
    view_lo, view_hi = 12.0, 132.0
    lag_limit_s = 0.25 * metronome_period_s
    common_t = np.arange(view_lo, view_hi, 1.0 / cfg.FS_GSEN)
    hr_common = interp1d(
        rr_uniform_t,
        zscore(hr_bp),
        kind="linear",
        bounds_error=False,
        fill_value="extrapolate",
    )(common_t)

    axis_stats = {}
    for i, name in enumerate("xyz"):
        imu_common = interp1d(
            t_imu,
            zscore(imu_bp[:, i]),
            kind="linear",
            bounds_error=False,
            fill_value="extrapolate",
        )(common_t)
        zero_corr = float(np.corrcoef(hr_common, imu_common)[0, 1])
        best_lag_s, best_corr = best_lag_corr(
            hr_common,
            imu_common,
            cfg.FS_GSEN,
            lag_limit_s=lag_limit_s,
            mode="positive",
        )
        axis_stats[name] = {
            "zero_corr": zero_corr,
            "best_lag_s": best_lag_s,
            "best_corr": best_corr,
        }

    strongest_axis = max(("x", "y", "z"), key=lambda k: axis_stats[k]["best_corr"])
    strongest_idx = "xyz".index(strongest_axis)
    imu_display_mode = "z-axis" if strongest_axis == "z" else strongest_axis
    display_sign = -1.0
    strongest_motion = display_sign * zscore(imu_bp[:, strongest_idx])
    strongest_flow_like = np.gradient(strongest_motion, 1.0 / cfg.FS_GSEN)
    strongest_flow_like = zscore(strongest_flow_like)
    strongest_common = interp1d(
        t_imu,
        strongest_flow_like,
        kind="linear",
        bounds_error=False,
        fill_value="extrapolate",
    )(common_t)
    zero_r = float(np.corrcoef(hr_common, strongest_common)[0, 1])
    lag_s, lag_r = best_lag_corr(
        hr_common,
        strongest_common,
        cfg.FS_GSEN,
        lag_limit_s=lag_limit_s,
        mode="positive",
    )
    phase_text = format_phase_relation(lag_s)
    peak_bpm = peak_info[strongest_axis][0] * 60.0
    m_rr = (rr_t >= view_lo) & (rr_t <= view_hi)
    ax3.plot(
        rr_t[m_rr],
        zscore(hr_bp_at_beats)[m_rr],
        color="#2E4057",
        linewidth=0.9,
        marker="o",
        markersize=2.6,
        markerfacecolor="#2E4057",
        markeredgewidth=0.0,
        label="Beatwise HR component",
    )
    ax3.plot(
        t_imu[(t_imu >= view_lo) & (t_imu <= view_hi)],
        strongest_flow_like[(t_imu >= view_lo) & (t_imu <= view_hi)],
        color=raw_colors[strongest_axis],
        linewidth=1.2,
        alpha=0.9,
        label=f"IMU {imu_display_mode} flow proxy",
    )
    first_marker = view_lo + ((metronome_offset_s - view_lo) % metronome_period_s)
    for tv in np.arange(first_marker, view_hi + metronome_period_s, metronome_period_s):
        ax3.axvline(tv, color="0.55", linewidth=0.8, alpha=0.45, linestyle="--")
    ax3.set_xlim(view_lo, view_hi)
    ax3.set_title("Beatwise HR and IMU-derived respiratory flow proxy", loc="left")
    ax3.set_xlabel("Time (s)")
    ax3.set_ylabel("z-score")
    ax3.legend(
        loc="upper right",
        bbox_to_anchor=(1.0, 1.20),
        frameon=True,
        framealpha=0.88,
        edgecolor="0.82",
        borderpad=0.25,
        handlelength=1.8,
        fontsize=9.5,
    )
    ax3.grid(True, linestyle="--", alpha=0.22)
    ax3.text(
        -0.055,
        1.02,
        "(b)",
        transform=ax3.transAxes,
        fontsize=11,
        fontweight="bold",
        ha="right",
        va="bottom",
        clip_on=False,
    )

    text = (
        f"Peak {peak_info[strongest_axis][0]:.4f} Hz ({peak_bpm:.1f} breaths/min); "
        f"{phase_text} (r = {lag_r:.3f})"
    )
    fig.text(
        0.015,
        0.075,
        text,
        fontsize=9.5,
        ha="left",
        va="bottom",
        bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "0.85", "alpha": 0.95},
    )
    fig.tight_layout(rect=(0, 0.1, 1, 1))

    out_path = PL.save_figure(fig, "test-2_e4a_5pm_imu_deep_dive.pdf")
    print(f"Saved figure: {out_path}")
    print(f"Target breathing frequency: {TARGET_HZ:.6f} Hz")
    for name in ("x", "y", "z"):
        peak_hz, peak_pow = peak_info[name]
        stats = axis_stats[name]
        print(
            f"{name}: peak={peak_hz:.6f} Hz power={peak_pow:.6e} "
            f"zero_corr={stats['zero_corr']:.4f} "
            f"best_same_phase_lag={stats['best_lag_s']:.3f} s "
            f"best_same_phase_corr={stats['best_corr']:.4f}"
        )
    print(
        f"displayed_axis={strongest_axis} display_zero_corr={zero_r:.4f} "
        f"display_best_same_phase_lag={lag_s:.3f} s display_best_same_phase_corr={lag_r:.4f} "
        f"phase_relation='{phase_text}'"
    )

    if args.show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    main()
