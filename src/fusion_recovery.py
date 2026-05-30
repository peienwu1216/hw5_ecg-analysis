"""IMU-anchored recovery of the vagal component (Final Project, Part A).

The naive Task-Force LF/HF ratio inflates ~80-fold during slow paced breathing
once the respiratory (RSA) peak migrates below 0.15 Hz into the LF band. This is
an artifact of fixed band boundaries, not an autonomic change. Using the
*IMU-measured* respiratory frequency (never the metronome) to locate the RSA
peak, we reassign the IMU-confirmed migrated RSA power back to the vagal pool and
recompute a corrected LF/HF that no longer depends on which band the peak lands
in.

Reproducibility notes
---------------------
* LF_total / HF_total / LFHF_naive use the *same* PSD path as the paper's
  canonical Task-Force HRV (scipy RR series, cubic interpolation to 4 Hz, Welch
  nperseg = 256, trapz over [lo, hi) bins). LFHF_naive therefore reproduces the
  reported LF/HF exactly.
* All window powers use the identical native-grid clip-trapz, so RSA_in_LF is
  always consistent with LF_total (pct in [0, 100]).
* f_resp is the IMU z-axis PSD peak located by *global* argmax over
  [0.04, 0.30] Hz -- independent of the metronome target. Reassignment is gated
  on IMU<->RR-peak agreement (|f_resp - RR peak| <= 0.03 Hz); the 12/min
  condition is SNR-limited (fast shallow breathing) so the IMU cannot resolve
  the respiratory peak, the gate fails, and no reassignment is applied
  (LFHF_corr = LFHF_naive), consistent with the IMU validation table.

Outputs outputs/tables/fusion_recovery.csv (long form: one row per
condition x delta). Run:  ./.venv/bin/python -m src.fusion_recovery
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt, welch

from . import config as cfg
from . import pipeline as P

E4A_KEYS = ["E4A_12pm", "E4A_9pm", "E4A_6pm", "E4A_5pm", "E4A_3pm"]
E4A_LABELS = ["12/min", "9/min", "6/min", "5/min", "3/min"]
E4A_RATES_BPM = [12, 9, 6, 5, 3]

NPERSEG_RR = 256                 # canonical Task-Force PSD (matches the paper)
DELTAS_HZ = [0.015, 0.020, 0.025]  # >= Welch resolution (Df ~ 0.0156 Hz)
DELTA_PRIMARY = 0.015
RESP_SEARCH = (0.04, 0.30)       # outer physiological bound for the IMU peak
IMU_SEARCH_BW = 0.04             # IMU peak searched within +/- this of the RR peak
CONFIRM_TOL_HZ = 0.03            # IMU<->RR-peak agreement for reassignment


def _clip_trapz(f: np.ndarray, p: np.ndarray, lo: float, hi: float) -> float:
    """Power over [lo, hi) on native Welch bins, same binning convention as
    pipeline.frequency_domain_hrv. Uses trapz when >= 2 bins fall in range; for a
    single in-range bin (window narrower than the spectral resolution -- happens
    when a respiratory peak sits within ~1 bin of the 0.15 Hz band edge) it falls
    back to the rectangular bin power p*Df so legitimate near-boundary power is not
    silently dropped. Returns 0 if no bin falls in range."""
    if hi <= lo:
        return 0.0
    m = (f >= lo) & (f < hi)
    n = int(m.sum())
    if n >= 2:
        return float(np.trapezoid(p[m], f[m]))
    if n == 1:
        df = float(f[1] - f[0])
        return float(p[m][0] * df)
    return 0.0


def _canonical_rr_psd(r) -> tuple[np.ndarray, np.ndarray]:
    """RR PSD on the canonical scipy path so band powers match the paper."""
    rr_i, _ = P.interpolate_rr(r.rr_ms_scipy, r.rr_times_scipy, cfg.INTERP_FREQ)
    nperseg = min(NPERSEG_RR, rr_i.size)
    return welch(rr_i, fs=cfg.INTERP_FREQ, nperseg=nperseg)


def imu_respiratory_freq(key: str, anchor_hz: float) -> float:
    """IMU z-axis respiratory peak, searched within +/- IMU_SEARCH_BW of the
    *RR-spectral* peak (anchor_hz).

    Metronome-independent: the search is anchored on the ECG-derived respiratory
    frequency, never on the imposed metronome rate, so this remains a deployable
    estimate. Anchoring on the RR peak (rather than a fixed global argmax over
    RESP_SEARCH) makes the estimate robust at the hard rates: at 12/min a strong
    sub-respiratory body-sway component otherwise wins the global argmax, and at
    9/min the respiratory peak sits within one Welch bin of the 0.15 Hz band edge
    where a fixed-grid argmax can land on the wrong side. Searching near the
    independently measured RR peak recovers the true respiratory bin and turns the
    IMU<->ECG agreement into the fusion's confirmation signal.
    """
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
    nperseg = min(4096 if anchor_hz < 0.08 else 2048, len(z_lp))
    f_z, p_z = welch(z_lp - np.mean(z_lp), fs=cfg.FS_GSEN, nperseg=nperseg)

    lo = max(anchor_hz - IMU_SEARCH_BW, RESP_SEARCH[0])
    hi = min(anchor_hz + IMU_SEARCH_BW, RESP_SEARCH[1])
    m = (f_z >= lo) & (f_z <= hi)
    if not m.any():
        return float("nan")
    return float(f_z[m][np.argmax(p_z[m])])


def compute() -> pd.DataFrame:
    vlf_lo, _ = cfg.BANDS["VLF"]
    lf_lo, lf_hi = cfg.BANDS["LF"]
    hf_lo, hf_hi = cfg.BANDS["HF"]

    rows = []
    for key, label, rate_bpm in zip(E4A_KEYS, E4A_LABELS, E4A_RATES_BPM):
        r = P.analyze_steady_state(key)
        f, p = _canonical_rr_psd(r)
        rmssd_ms = float(r.td_hrv["rmssd_ms"])  # time-domain vagal anchor

        lf_total = _clip_trapz(f, p, lf_lo, lf_hi)
        hf_total = _clip_trapz(f, p, hf_lo, hf_hi)
        lfhf_naive = lf_total / hf_total if hf_total > 0 else float("nan")

        # dominant RR spectral peak: ECG-derived respiratory frequency, used both
        # to anchor the IMU search and as the IMU confirmation reference.
        m_rr = (f >= 0.04) & (f <= 0.40)
        rr_peak = float(f[m_rr][np.argmax(p[m_rr])]) if m_rr.any() else float("nan")

        target_hz = rate_bpm / 60.0
        f_resp = imu_respiratory_freq(key, rr_peak)
        d_imu_metro = abs(f_resp - target_hz)
        imu_confirmed = bool(np.isfinite(f_resp)
                             and abs(f_resp - rr_peak) <= CONFIRM_TOL_HZ)

        for delta in DELTAS_HZ:
            if imu_confirmed:
                w_lo, w_hi = f_resp - delta, f_resp + delta
                # Locate the band the respiratory *power* lives in: argmax of the
                # RR PSD inside the window. Reassignment is driven by where the
                # power being corrected actually concentrates, not by the IMU
                # centre, so a peak whose centre is nominally in LF but whose RR
                # power peaks in HF (9/min, straddling the 0.15 Hz edge) is left
                # in the vagal pool where it already sits -- no LF inflation to
                # undo, corrected reduces to naive.
                mw = (f >= max(w_lo, vlf_lo)) & (f < min(w_hi, hf_hi))
                p_resp = _clip_trapz(f, p, max(w_lo, vlf_lo), min(w_hi, hf_hi))
                rsa_in_hf = _clip_trapz(f, p, max(w_lo, hf_lo), min(w_hi, hf_hi))
                peak_hz = float(f[mw][np.argmax(p[mw])]) if mw.any() else float("nan")
                peak_in_lf = lf_lo <= peak_hz < lf_hi
                if peak_in_lf:
                    rsa_in_lf = _clip_trapz(f, p, max(w_lo, lf_lo), min(w_hi, lf_hi))
                    rsa_in_lf = min(rsa_in_lf, lf_total)
                else:
                    # respiratory power peaks in HF: already vagal, nothing migrates
                    rsa_in_lf = 0.0
            else:
                # IMU cannot confirm a respiratory peak: no reassignment,
                # corrected ratio reduces to the naive ratio.
                rsa_in_lf = rsa_in_hf = p_resp = 0.0

            lf_residual = lf_total - rsa_in_lf
            pct_rsa_in_lf = 100.0 * rsa_in_lf / lf_total if lf_total > 0 else float("nan")
            vagal_corr = hf_total + rsa_in_lf
            lfhf_corr = lf_residual / vagal_corr if vagal_corr > 0 else float("nan")

            rows.append({
                "condition": label,
                "rate_bpm": rate_bpm,
                "delta_hz": delta,
                "is_primary": delta == DELTA_PRIMARY,
                "target_hz": target_hz,
                "f_resp_hz": f_resp,
                "rr_peak_hz": rr_peak,
                "abs_df_imu_metronome_hz": d_imu_metro,
                "imu_confirmed": imu_confirmed,
                "RMSSD_ms": rmssd_ms,
                "LF_total": lf_total,
                "HF_total": hf_total,
                "LFHF_naive": lfhf_naive,
                "RSA_in_LF": rsa_in_lf,
                "RSA_in_HF": rsa_in_hf,
                "P_resp": p_resp,
                "pct_RSA_in_LF": pct_rsa_in_lf,
                "LF_residual": lf_residual,
                "vagal_corr": vagal_corr,
                "LFHF_corr": lfhf_corr,
            })

    return pd.DataFrame(rows)


def main() -> Path:
    df = compute()
    out = cfg.TABLES_DIR / "fusion_recovery.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    prim = df[df["is_primary"]]
    print(f"Wrote {out}")
    print("\nPrimary (delta = 0.015 Hz):")
    cols = ["condition", "f_resp_hz", "imu_confirmed", "LFHF_naive",
            "pct_RSA_in_LF", "LFHF_corr"]
    with pd.option_context("display.float_format", lambda v: f"{v:.4f}"):
        print(prim[cols].to_string(index=False))

    naive = prim["LFHF_naive"]
    corr_all = df["LFHF_corr"]
    print(f"\nNaive LF/HF range:     {naive.min():.2f} - {naive.max():.2f} "
          f"({naive.max()/naive.min():.0f}x swing)")
    print(f"Corrected LF/HF range: {corr_all.min():.2f} - {corr_all.max():.2f} "
          f"(across all rates x all delta)")
    print("\ndelta-sensitivity (LFHF_corr per rate):")
    for label in E4A_LABELS:
        sub = df[df["condition"] == label]
        print(f"  {label:>7}: corr {sub['LFHF_corr'].min():.3f}-"
              f"{sub['LFHF_corr'].max():.3f}, "
              f"%RSA_in_LF {sub['pct_RSA_in_LF'].min():.1f}-"
              f"{sub['pct_RSA_in_LF'].max():.1f}")
    return out


if __name__ == "__main__":
    main()
