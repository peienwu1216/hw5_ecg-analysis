"""ECG / HRV pipeline for HW5.

Design principles:
---
1. **`filter_ecg` is the single source of filtering truth**. Every downstream
   step consumes the already-filtered signal. In particular, NK2 helpers do
   NOT call `nk.ecg_clean` (it would re-apply a 50 Hz notch on top of ours).
1b. The first `config.RR_DROP_LEADING` R-R intervals are removed after
   `compute_rr` in each orchestrator (spurious beats at device capture start).
   NK2 `compute_hrv_full` uses `peaks[RR_DROP_LEADING:]` so HRV and exported
   RR time series match.
2. **Two processing paths**, used side-by-side by `01_pipeline_validation`:
       scipy  : filter_ecg -> detect_qrs     -> compute_rr -> reject_artifacts
                                             -> time/frequency_domain_hrv
       NK2    : filter_ecg -> detect_qrs_nk  -> compute_rr
                (Kubios correction happens inside detect_qrs_nk)
                                             -> compute_hrv_full
3. **No double artifact handling**. `reject_artifacts` is scipy-path only.
   NK2 already interpolates at the peak level via Kubios; applying
   reject_artifacts on top would break the time axis.
4. **NeuroKit2 API confirmed by scripts/preflight_check.py**:
       - `nk.signal_fixpeaks` returns `(info_dict, peaks_array)` (info first!)
       - `nk.ecg_rsp` first arg is an ECG rate series, not the ECG waveform
       - `nk.hrv_rsa` needs full signals DataFrame from `nk.ecg_process`
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.signal import (butter, iirnotch, sosfiltfilt, tf2sos, welch,
                          find_peaks, spectrogram as scipy_spectrogram,
                          filtfilt)
import neurokit2 as nk

from . import config as cfg
from .config import (FS, FS_GSEN, NOTCH_FREQ, NOTCH_Q, BANDPASS, FILTER_ORDER,
                     BASELINE_MED1_MS, BASELINE_MED2_MS,
                     REFRACTORY_MS, RR_MIN_MS, RR_MAX_MS, INTERP_FREQ, BANDS,
                     FILE_INVENTORY, EXPERIMENT_TYPE, ANCHOR_KEYS, E2_SEG, E3_SEG,
                     RR_DROP_LEADING)


# =============================================================================
# Loaders
# =============================================================================
def _sorted_hour_dirs(session_root: Path) -> list[Path]:
    """Return the per-hour subfolders under <session>/20260424/, sorted numerically."""
    dirs = [p for p in session_root.iterdir() if p.is_dir() and p.name.isdigit()]
    return sorted(dirs, key=lambda p: int(p.name))


def flatten_leading_baseline_to_local_mean(
    ecg: np.ndarray,
    fs: float = FS,
    lead_s: float | None = None,
    ref_s: float | None = None,
) -> np.ndarray:
    """Set the first `lead_s` seconds to the mean of the next `ref_s` seconds.

    Use a **local** post-spike window (default ``ECG_LEADING_BASELINE_REF_S``)
    so a long-term DC ramp does not pull the fill value and create a step at
    the boundary. Apply to the full file before `FILE_INVENTORY` crop; absolute
    t=0. Does not shift the time axis.
    """
    if lead_s is None:
        lead_s = float(cfg.ECG_LEADING_BASELINE_S)
    if ref_s is None:
        ref_s = float(cfg.ECG_LEADING_BASELINE_REF_S)
    if lead_s <= 0.0 or ecg.size == 0:
        return np.asarray(ecg, dtype=float)
    ecg = np.asarray(ecg, dtype=float, copy=True)
    n_lead = int(round(lead_s * fs))
    n_lead = max(0, min(n_lead, ecg.size))
    if n_lead == 0:
        return ecg
    i0, i1 = n_lead, n_lead + int(round(max(0.0, ref_s) * fs))
    i1 = min(i1, ecg.size)
    if i0 >= ecg.size:
        return ecg
    if i1 <= i0:
        m = float(np.mean(ecg[i0:]))
    else:
        m = float(np.mean(ecg[i0:i1]))
    ecg[:n_lead] = m
    return ecg


def load_ecg(key: str, ch: int = 1, apply_window: bool = True,
             fs: float = FS) -> tuple[np.ndarray, np.ndarray]:
    """Load ECG for a session key, concatenating multi-hour folders.

    Parameters
    ----------
    key : session key such as 'E1PRE' or 'E1A' (see config.SESSION_MAP)
    ch  : 0 or 1 (chN.csv). Default is 1 per legend convention; new dataset has ch0==ch1.
    apply_window : if True, crop to FILE_INVENTORY[key]['window'] = (start_s, end_s).

    Returns
    -------
    t_s     : time axis in seconds from recording start (after cropping)
    ecg_raw : float array of ADC samples
    """
    root = cfg.get_session_path(key)
    parts = []
    for hour_dir in _sorted_hour_dirs(root):
        csv_path = hour_dir / f'ch{ch}.csv'
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing {csv_path}")
        parts.append(np.loadtxt(csv_path, dtype=float))
    ecg = np.concatenate(parts)
    # Startup spike: absolute t = 0 of the file (before analysis window crop)
    ecg = flatten_leading_baseline_to_local_mean(ecg, fs=fs)

    if apply_window:
        start_s, end_s = FILE_INVENTORY[key]['window']
        i0 = int(round(start_s * fs))
        i1 = int(round(end_s * fs))
        i1 = min(i1, ecg.size)
        ecg = ecg[i0:i1]

    t = np.arange(ecg.size, dtype=float) / fs
    return t, ecg


def load_gsen(key: str, apply_window: bool = True,
              fs_gsen: float = FS_GSEN, lp_cutoff_hz: float = 10.0
              ) -> tuple[np.ndarray, np.ndarray]:
    """Load accelerometer -> gravity-subtracted motion magnitude in g-units.

    Pipeline (faithful to plan spec R2-7):
      1. Read 3-axis gsen.csv (x, y, z).
      2. Normalise: detect unit automatically. If max(|raw|) >> 10 we assume
         values are in mg or raw-ADC and divide by 1000 to get g. Raw new-dataset
         values are on the order of +/- 1000 for 1 g, so divide by 1000.
      3. magnitude = sqrt(x^2 + y^2 + z^2)  per sample
      4. motion_g = |magnitude - 1.0|  (remove gravity baseline; stationary ~ 0)
      5. Low-pass 10 Hz Butterworth filtfilt (preserves walking cadence 1-3 Hz)
      6. Concatenate multi-hour folders, crop to analysis window.

    Returns
    -------
    t    : time axis in seconds
    mg   : motion magnitude in g-units, gravity removed, LP-filtered
    """
    root = cfg.get_session_path(key)
    parts = []
    for hour_dir in _sorted_hour_dirs(root):
        csv_path = hour_dir / 'gsen.csv'
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing {csv_path}")
        parts.append(np.loadtxt(csv_path, delimiter=',', dtype=float))
    raw = np.concatenate(parts, axis=0)              # shape (N, 3)

    # Auto-detect unit: the stationary subject should read magnitude ~ 1 g.
    # Raw sensor emits values ~ +/- 1000 per axis for 1 g gravity -> scale = 1/1000.
    # If values already in g (max |x,y,z| < 10), scale = 1.
    axis_max = np.max(np.abs(raw))
    scale = 1.0 / 1000.0 if axis_max > 10 else 1.0
    accel_g = raw * scale

    mag_g = np.sqrt(np.sum(accel_g ** 2, axis=1))
    motion_g = np.abs(mag_g - 1.0)                    # subtract gravity baseline

    # Low-pass 10 Hz to reduce wideband accelerometer noise
    if motion_g.size > 20:
        sos = butter(FILTER_ORDER, lp_cutoff_hz, btype='low',
                     fs=fs_gsen, output='sos')
        motion_g = sosfiltfilt(sos, motion_g)

    if apply_window:
        start_s, end_s = FILE_INVENTORY[key]['window']
        i0 = int(round(start_s * fs_gsen))
        i1 = int(round(end_s * fs_gsen))
        i1 = min(i1, motion_g.size)
        motion_g = motion_g[i0:i1]

    t = np.arange(motion_g.size, dtype=float) / fs_gsen
    return t, motion_g


def load_device_atr(key: str) -> pd.DataFrame:
    """Load device-reported per-beat annotations (vsc.atr.csv) for cross-check.

    Columns (from device firmware):
        hr_bpm, timestamp_hms_ms, t_seconds, rr_seconds, beat_type_code, label, ...
    We load with minimal assumptions -> first 7 columns as raw strings, then coerce
    numerics. Returns a DataFrame with columns `t_s`, `rr_s`, `hr_bpm`, `label`.
    """
    root = cfg.get_session_path(key)
    frames = []
    for hour_dir in _sorted_hour_dirs(root):
        csv_path = hour_dir / 'vsc.atr.csv'
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path, header=None, dtype=str,
                         names=['hr_bpm', 'hms_ms', 't_s', 'rr_s',
                                'beat_type', 'label', 'letter'])
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=['t_s', 'rr_s', 'hr_bpm', 'label'])

    df = pd.concat(frames, ignore_index=True)
    df['hr_bpm'] = pd.to_numeric(df['hr_bpm'], errors='coerce')
    df['t_s']   = pd.to_numeric(df['t_s'],   errors='coerce')
    df['rr_s']  = pd.to_numeric(df['rr_s'],  errors='coerce')
    return df[['t_s', 'rr_s', 'hr_bpm', 'label']]


# =============================================================================
# Baseline drift removal (two-stage median filter, Wan et al. 2006)
# =============================================================================
def remove_baseline_drift(ecg: np.ndarray, fs: float = FS,
                          med1_ms: float = BASELINE_MED1_MS,
                          med2_ms: float = BASELINE_MED2_MS) -> np.ndarray:
    """Two-stage median filter baseline removal.

    Stage 1 (200 ms): window exceeds QRS width (~100 ms) so the median
    ignores the R-peak spike and tracks slower components.
    Stage 2 (600 ms): smooths the stage-1 output to capture drift from
    respiration, electrode impedance changes, and motion.
    The estimated baseline is subtracted from the original signal.
    """
    from scipy.ndimage import median_filter

    ecg = np.asarray(ecg, dtype=float)
    if ecg.size < 3:
        return ecg
    w1 = int(round(med1_ms * fs / 1000.0)) | 1   # ensure odd
    w2 = int(round(med2_ms * fs / 1000.0)) | 1
    baseline = median_filter(median_filter(ecg, size=w1), size=w2)
    return ecg - baseline


# =============================================================================
# Filtering  (single source of truth)
# =============================================================================
def filter_ecg(ecg: np.ndarray, fs: float = FS,
               notch_freq: float = NOTCH_FREQ,
               bandpass: tuple[float, float] = BANDPASS) -> np.ndarray:
    """Baseline drift removal + 50 Hz notch + 0.5-40 Hz bandpass.

    Pipeline order:
      1. Two-stage median filter removes baseline drift (data-adaptive,
         does not distort QRS morphology).
      2. 50 Hz notch (iirnotch, Q=30).
      3. 0.5-40 Hz Butterworth bandpass (4th order, SOS filtfilt) — the
         high-pass leg now acts as a safety net rather than primary drift
         removal, so edge effects are minimal.

    This is the ONLY filter applied before QRS detection. NK2 helpers that
    would normally call `nk.ecg_clean` internally are fed the output of this
    function so we do not double-notch.
    """
    x = remove_baseline_drift(ecg, fs=fs)

    b_notch, a_notch = iirnotch(w0=notch_freq, Q=NOTCH_Q, fs=fs)
    sos_notch = tf2sos(b_notch, a_notch)
    x = sosfiltfilt(sos_notch, x)

    sos_bp = butter(FILTER_ORDER, bandpass, btype='band', fs=fs, output='sos')
    x = sosfiltfilt(sos_bp, x)
    return x


# =============================================================================
# QRS detection - scipy path (pedagogical)
# =============================================================================
def detect_qrs(ecg_filtered: np.ndarray, fs: float = FS,
               refractory_ms: int = REFRACTORY_MS,
               integration_ms: int = 150,
               thr_frac: float = 0.4,
               adaptive_window_s: float = 1.2,
               snap_ms: int = 75) -> np.ndarray:
    """Pan-Tompkins-style QRS detector (legend.ipynb cell 9 faithful port).

    Steps
    -----
    1. QRS bandpass 5-15 Hz (Butterworth 4, sosfiltfilt) -> isolates QRS
       from P/T waves and high-frequency noise.
    2. Square.
    3. Moving-window integration (150 ms rectangular).
    4. Local adaptive threshold: thr(i) = 0.4 * max(integ) in a
       1.2 s window centred on i.
    5. find_peaks with distance >= 300 ms.
    6. Snap each candidate back to the local max of the bandpassed
       ECG within +/- 75 ms.
    """
    if ecg_filtered.size < int(fs * 1.0):
        return np.asarray([], dtype=int)

    sos = butter(FILTER_ORDER, [5.0, 15.0], btype='band', fs=fs, output='sos')
    qrs_band = sosfiltfilt(sos, ecg_filtered)
    sq = qrs_band ** 2
    w = max(1, int(round(integration_ms * fs / 1000.0)))
    integ = np.convolve(sq, np.ones(w) / w, mode='same')

    hw = int(adaptive_window_s * fs) // 2
    N = integ.size
    thr = np.empty(N)
    for i in range(N):
        lo = max(0, i - hw)
        hi = min(N, i + hw)
        thr[i] = thr_frac * integ[lo:hi].max()

    refractory_samples = int(round(refractory_ms * fs / 1000.0))
    cands, _ = find_peaks(integ, height=thr, distance=refractory_samples)

    snap = int(round(snap_ms * fs / 1000.0))
    refined = np.empty_like(cands)
    for j, c in enumerate(cands):
        lo = max(0, c - snap)
        hi = min(ecg_filtered.size, c + snap + 1)
        refined[j] = lo + int(np.argmax(ecg_filtered[lo:hi]))
    return refined


# =============================================================================
# QRS detection - NeuroKit2 path (authoritative)
# =============================================================================
def detect_qrs_nk(ecg_filtered: np.ndarray, fs: float = FS
                  ) -> tuple[np.ndarray, dict]:
    """NK2 QRS detection + Kubios artifact correction.

    Consumes the already-filtered ECG (no `nk.ecg_clean` call).
    Splits `ecg_peaks` (no correction) + `signal_fixpeaks` so we can
    capture the actual ectopic / missed / extra / longshort counts.

    NOTE (preflight-verified, 2026-04-24, NK 0.2.13):
        nk.signal_fixpeaks returns (info_dict, peaks_array)
        - `info_dict` first, peaks array second.
    """
    _, info_raw = nk.ecg_peaks(ecg_filtered, sampling_rate=fs,
                               correct_artifacts=False)
    peaks_raw = np.asarray(info_raw['ECG_R_Peaks'], dtype=int)

    info_corr, peaks_corrected = nk.signal_fixpeaks(
        peaks_raw, sampling_rate=fs, method='kubios', iterative=True)
    peaks_corrected = np.asarray(peaks_corrected, dtype=int)

    def _len(k):
        v = info_corr.get(k, [])
        return int(len(v)) if hasattr(v, '__len__') else 0

    stats = {
        'n_peaks_raw':       int(peaks_raw.size),
        'n_peaks_corrected': int(peaks_corrected.size),
        'ectopic':           _len('ectopic'),
        'missed':            _len('missed'),
        'extra':             _len('extra'),
        'longshort':         _len('longshort'),
        'method': 'nk.ecg_peaks + signal_fixpeaks(kubios, iterative=True)',
    }
    return peaks_corrected, stats


# =============================================================================
# RR processing
# =============================================================================
def compute_rr(peaks: np.ndarray, fs: float = FS
               ) -> tuple[np.ndarray, np.ndarray]:
    """Peak indices -> RR intervals (ms) and their timestamps (seconds)."""
    peaks = np.asarray(peaks, dtype=int)
    if peaks.size < 2:
        return np.asarray([]), np.asarray([])
    rr_s  = np.diff(peaks) / fs
    rr_ms = rr_s * 1000.0
    rr_t  = peaks[1:] / fs                # time of the 2nd beat of each RR pair
    return rr_ms, rr_t


def reject_artifacts(rr_ms: np.ndarray, rr_times: np.ndarray,
                     min_ms: float = RR_MIN_MS, max_ms: float = RR_MAX_MS
                     ) -> tuple[np.ndarray, np.ndarray, int]:
    """Physiological RR filter: 300 ms (200 bpm) to 2000 ms (30 bpm). SCIPY PATH ONLY.

    NK2 path relies on Kubios correction inside detect_qrs_nk; calling this on
    top of that would double-process. Returns (rr_ms_kept, rr_times_kept,
    n_rejected).
    """
    rr_ms = np.asarray(rr_ms, dtype=float)
    rr_times = np.asarray(rr_times, dtype=float)
    if rr_ms.size == 0:
        return rr_ms, rr_times, 0
    keep = (rr_ms >= min_ms) & (rr_ms <= max_ms)
    n_rej = int((~keep).sum())
    return rr_ms[keep], rr_times[keep], n_rej


def drop_leading_rr_intervals(
    rr_ms: np.ndarray,
    rr_times: np.ndarray,
    n: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Remove the first n RR intervals (e.g. hardware startup at capture onset).

    First intervals share timing with the leading R-peaks; dropping n intervals
    is equivalent to using peaks[n:] in analyses that re-build R-R from indices.
    """
    if n <= 0:
        return np.asarray(rr_ms, dtype=float), np.asarray(rr_times, dtype=float)
    rr_ms = np.asarray(rr_ms, dtype=float)
    rr_times = np.asarray(rr_times, dtype=float)
    if rr_ms.size <= n or rr_ms.size == 0:
        return np.asarray([]), np.asarray([])
    return rr_ms[n:].copy(), rr_times[n:].copy()


# =============================================================================
# HRV - scipy / transparent
# =============================================================================
def time_domain_hrv(rr_ms: np.ndarray) -> dict[str, float]:
    """Classic Task-Force time-domain HRV indices."""
    rr_ms = np.asarray(rr_ms, dtype=float)
    if rr_ms.size < 2:
        return {k: float('nan') for k in
                ('mean_rr_ms', 'mean_hr_bpm', 'sdnn_ms', 'rmssd_ms',
                 'pnn50_pct', 'min_hr_bpm', 'max_hr_bpm')}
    hr = 60000.0 / rr_ms
    d = np.diff(rr_ms)
    return {
        'mean_rr_ms':  float(np.mean(rr_ms)),
        'mean_hr_bpm': float(np.mean(hr)),
        'sdnn_ms':     float(np.std(rr_ms, ddof=1)),
        'rmssd_ms':    float(np.sqrt(np.mean(d ** 2))),
        'pnn50_pct':   float(np.mean(np.abs(d) > 50.0) * 100.0),
        'min_hr_bpm':  float(np.min(hr)),
        'max_hr_bpm':  float(np.max(hr)),
    }


def interpolate_rr(rr_ms: np.ndarray, rr_times: np.ndarray,
                   fs_interp: float = INTERP_FREQ
                   ) -> tuple[np.ndarray, np.ndarray]:
    """Detrend + cubic-spline interpolation of RR onto uniform fs_interp grid."""
    rr_ms = np.asarray(rr_ms, dtype=float)
    rr_times = np.asarray(rr_times, dtype=float)
    if rr_ms.size < 4:
        return np.asarray([]), np.asarray([])
    t_i = np.arange(rr_times[0], rr_times[-1], 1.0 / fs_interp)
    cs = CubicSpline(rr_times, rr_ms - np.mean(rr_ms), extrapolate=False)
    rr_i = cs(t_i)
    rr_i = rr_i[np.isfinite(rr_i)]
    t_i  = t_i[: rr_i.size]
    return rr_i, t_i


def frequency_domain_hrv(rr_ms: np.ndarray, rr_times: np.ndarray,
                         interp_freq: float = INTERP_FREQ,
                         bands: dict | None = None) -> dict[str, float]:
    """Welch-based Task-Force frequency-domain HRV.

    Detrend -> cubic spline to 4 Hz -> Welch PSD -> trapz per band.
    """
    bands = bands if bands is not None else BANDS
    rr_i, t_i = interpolate_rr(rr_ms, rr_times, interp_freq)
    out = {k: float('nan') for k in
           ('total_power_ms2', 'vlf_ms2', 'lf_ms2', 'hf_ms2',
            'lf_nu', 'hf_nu', 'lf_hf_ratio',
            'hf_peak_hz', 'lf_peak_hz')}
    if rr_i.size < 32:
        return out

    nperseg = min(256, rr_i.size)
    f, p = welch(rr_i, fs=interp_freq, nperseg=nperseg)

    def _band_power(band):
        m = (f >= band[0]) & (f < band[1])
        return float(np.trapezoid(p[m], f[m])) if m.any() else 0.0

    vlf = _band_power(bands['VLF'])
    lf  = _band_power(bands['LF'])
    hf  = _band_power(bands['HF'])
    total = vlf + lf + hf

    def _peak(band):
        m = (f >= band[0]) & (f < band[1])
        if not m.any():
            return float('nan')
        return float(f[m][np.argmax(p[m])])

    out.update({
        'total_power_ms2': total,
        'vlf_ms2':   vlf,
        'lf_ms2':    lf,
        'hf_ms2':    hf,
        'lf_nu':     float(100.0 * lf / (lf + hf)) if (lf + hf) > 0 else float('nan'),
        'hf_nu':     float(100.0 * hf / (lf + hf)) if (lf + hf) > 0 else float('nan'),
        'lf_hf_ratio': float(lf / hf) if hf > 0 else float('nan'),
        'hf_peak_hz':  _peak(bands['HF']),
        'lf_peak_hz':  _peak(bands['LF']),
    })
    return out


def rr_psd(rr_ms: np.ndarray, rr_times: np.ndarray,
           interp_freq: float = INTERP_FREQ,
           nperseg: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Return (f, Pxx) from Welch PSD of the interpolated RR series. Helper
    used by `plot_rr_psd_pub` and by `spectral_average_rr`."""
    rr_i, _ = interpolate_rr(rr_ms, rr_times, interp_freq)
    if rr_i.size < 32:
        return np.asarray([]), np.asarray([])
    if nperseg is None:
        nperseg = min(256, rr_i.size)
    else:
        nperseg = min(nperseg, rr_i.size)
    f, p = welch(rr_i, fs=interp_freq, nperseg=nperseg)
    return f, p


def ecg_psd(ecg: np.ndarray, fs: float = FS,
            nperseg_sec: float = 8.0) -> tuple[np.ndarray, np.ndarray]:
    """Welch PSD of the raw / filtered ECG (for harmonic + respiratory annotation)."""
    nperseg = min(int(nperseg_sec * fs), ecg.size)
    nperseg = max(nperseg, 256)
    f, p = welch(ecg - np.mean(ecg), fs=fs, nperseg=nperseg,
                 noverlap=nperseg // 2)
    return f, p


# =============================================================================
# HRV - NeuroKit2 (authoritative, ~86 indices)
# =============================================================================
def compute_hrv_full(peaks: np.ndarray, fs: float = FS) -> pd.DataFrame:
    """Full NK2 HRV: time + frequency (Task-Force Welch) + nonlinear.

    Returns a single-row DataFrame. Does NOT include long-term DFA alpha2 for
    recordings shorter than its minimum window; NK2 emits a warning we suppress.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=Warning)
        df_t = nk.hrv_time(peaks, sampling_rate=fs, show=False)
        df_f = nk.hrv_frequency(peaks, sampling_rate=fs,
                                psd_method='welch', show=False,
                                vlf=BANDS['VLF'], lf=BANDS['LF'],
                                hf=BANDS['HF'])
        df_n = nk.hrv_nonlinear(peaks, sampling_rate=fs, show=False)
    return pd.concat([df_t, df_f, df_n], axis=1)


# =============================================================================
# ECG-derived respiration (EDR) + dual-method breathing-rate estimate
# =============================================================================
def derive_respiration_from_ecg(ecg_filtered: np.ndarray, fs: float = FS
                                ) -> dict[str, Any]:
    """Return EDR signal + two independent breathing-rate estimates.

    API corrected after preflight (NK 0.2.13):
        nk.ecg_rsp expects an ECG rate series, not the waveform.
        Pipeline: peaks -> nk.ecg_rate -> nk.ecg_rsp -> nk.rsp_peaks.

    Returns
    -------
    dict with
        rsp_signal     : EDR waveform at fs
        rsp_peaks      : inspiration-peak sample indices (within rsp_signal)
        rate_bpm       : mean breathing rate from RSP-peak spacing (bpm)
        rate_hz        : rate_bpm / 60
        welch_peak_hz  : dominant frequency of the EDR signal (Welch, 0.05-0.5 Hz)
    """
    _, ecg_info = nk.ecg_peaks(ecg_filtered, sampling_rate=fs,
                               correct_artifacts=True)
    ecg_rate = nk.ecg_rate(ecg_info['ECG_R_Peaks'], sampling_rate=fs,
                           desired_length=len(ecg_filtered))
    rsp = nk.ecg_rsp(ecg_rate, sampling_rate=fs, method='vangent2019')

    # Method A: peak-detection based rate
    rsp_cleaned = nk.rsp_clean(rsp, sampling_rate=fs, method='khodadad2018')
    _, rsp_info = nk.rsp_peaks(rsp_cleaned, sampling_rate=fs)
    rsp_peaks = np.asarray(rsp_info.get('RSP_Peaks', []), dtype=int)

    if rsp_peaks.size >= 2:
        rate_series = nk.signal_rate(rsp_peaks, sampling_rate=fs,
                                     desired_length=len(rsp))
        rate_bpm = float(np.nanmean(rate_series))
    else:
        rate_bpm = float('nan')

    # Method B: Welch peak in plausible breathing band (independent cross-check)
    nperseg = min(fs * 60, len(rsp))
    if nperseg < 256:
        welch_peak_hz = float('nan')
    else:
        f_rsp, P_rsp = welch(rsp - np.mean(rsp), fs=fs, nperseg=nperseg)
        m = (f_rsp >= 0.05) & (f_rsp <= 0.5)
        welch_peak_hz = float(f_rsp[m][np.argmax(P_rsp[m])]) if m.any() else float('nan')

    return {
        'rsp_signal':    rsp,
        'rsp_peaks':     rsp_peaks,
        'rate_bpm':      rate_bpm,
        'rate_hz':       rate_bpm / 60.0 if np.isfinite(rate_bpm) else float('nan'),
        'welch_peak_hz': welch_peak_hz,
    }


def hrv_rsa_full(ecg_filtered: np.ndarray, fs: float = FS) -> dict[str, float]:
    """Compute RSA (P2T, Porges-Bohrer) via NK2.

    Uses ``ecg_process`` + ``rsp_process`` on EDR (per NK2 docs).  NK 0.2.13:
    default ``window=32`` s for the Gates method triggers a bug when the
    recording is shorter (``rsa.update(np.nan)``) — we shrink ``window`` to fit.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=Warning)
        signals, info = nk.ecg_process(ecg_filtered, sampling_rate=fs)
        ecg_rate = nk.ecg_rate(
            info['ECG_R_Peaks'], sampling_rate=fs, desired_length=len(ecg_filtered)
        )
        rsp_raw = nk.ecg_rsp(ecg_rate, sampling_rate=fs, method='vangent2019')
        rsp_signals, _ = nk.rsp_process(rsp_raw, sampling_rate=fs)

        duration_sec = float(len(ecg_filtered)) / fs
        # Default Gates window is 32 s; must be < recording length to avoid rsa.update(np.nan),
        # and STFT nperseg (= window * 4 Hz on RRI) must fit the interpolated series (~0.85·T).
        window = min(32, max(2, int(duration_sec * 0.85)))
        if duration_sec < window:
            window = max(1, int(duration_sec * 0.5))

        try:
            result = nk.hrv_rsa(
                signals,
                rsp_signals,
                info,
                sampling_rate=fs,
                continuous=False,
                window=window,
            )
        except Exception as exc:
            return {'error': f'{type(exc).__name__}: {exc}'}
    if isinstance(result, pd.DataFrame):
        result = result.iloc[0].to_dict()
    return {k: float(v) if isinstance(v, (int, float, np.floating)) else v
            for k, v in result.items()}


# =============================================================================
# Spectral averaging across short RR segments (E2 pooling)
# =============================================================================
def spectral_average_rr(segments: list[tuple[np.ndarray, np.ndarray]],
                        interp_freq: float = INTERP_FREQ,
                        nperseg_sec: float = 20.0,
                        bands: dict | None = None
                        ) -> dict[str, Any]:
    """Pool multiple short RR segments by averaging their PSDs (not time).

    Each segment is independently detrended, cubic-interpolated to
    `interp_freq` Hz, and Welch-averaged with a common nperseg so all PSDs
    land on the same frequency grid. Ensemble mean / std is then computed per
    frequency bin. Also returns per-band mean + std (the std is the error-bar
    claim for Figure 2.4).

    Parameters
    ----------
    segments : list of (rr_ms, rr_times_s)
    nperseg_sec : Welch segment length in seconds on the interpolated grid.
                  With fs_interp=4 Hz and nperseg_sec=20, nperseg = 80 samples
                  -> frequency resolution 0.05 Hz, enough to resolve HF vs LF.

    Returns
    -------
    dict with
        f             : common frequency axis
        p_mean, p_std : ensemble mean / std of PSD across segments
        n_segments    : count of segments that contributed
        band_powers        : {'VLF': ..., 'LF': ..., 'HF': ...} averaged across segs
        band_powers_std    : per-band std across segments (same keys)
        peak_hz       : {'HF': hz, 'LF': hz} of ensemble-mean PSD
    """
    bands = bands if bands is not None else BANDS
    nperseg = int(round(nperseg_sec * interp_freq))

    stack = []
    per_seg_bands: dict[str, list[float]] = {k: [] for k in bands}
    f_common = None

    for rr_ms, rr_t in segments:
        rr_i, _ = interpolate_rr(np.asarray(rr_ms), np.asarray(rr_t),
                                 interp_freq)
        if rr_i.size < nperseg:
            continue
        f, p = welch(rr_i, fs=interp_freq, nperseg=nperseg)
        if f_common is None:
            f_common = f
        elif f_common.size != f.size:
            continue     # skip mismatched grid (shouldn't happen with fixed nperseg)
        stack.append(p)
        for bname, bounds in bands.items():
            m = (f >= bounds[0]) & (f < bounds[1])
            per_seg_bands[bname].append(float(np.trapezoid(p[m], f[m]))
                                        if m.any() else 0.0)

    if not stack:
        return {'f': np.asarray([]), 'p_mean': np.asarray([]),
                'p_std': np.asarray([]), 'n_segments': 0,
                'band_powers': {k: float('nan') for k in bands},
                'band_powers_std': {k: float('nan') for k in bands},
                'peak_hz': {'HF': float('nan'), 'LF': float('nan')}}

    P = np.vstack(stack)
    p_mean = P.mean(axis=0)
    p_std  = P.std(axis=0, ddof=1) if P.shape[0] >= 2 else np.zeros_like(p_mean)

    band_powers = {k: float(np.mean(v)) if v else float('nan')
                   for k, v in per_seg_bands.items()}
    band_powers_std = {k: float(np.std(v, ddof=1)) if len(v) >= 2 else 0.0
                       for k, v in per_seg_bands.items()}

    def _peak(band):
        m = (f_common >= band[0]) & (f_common < band[1])
        return float(f_common[m][np.argmax(p_mean[m])]) if m.any() else float('nan')

    return {
        'f': f_common, 'p_mean': p_mean, 'p_std': p_std,
        'n_segments': int(P.shape[0]),
        'band_powers': band_powers,
        'band_powers_std': band_powers_std,
        'peak_hz': {'HF': _peak(bands['HF']), 'LF': _peak(bands['LF'])},
    }


# =============================================================================
# Spectrogram (for Figure 2.3)
# =============================================================================
def rr_spectrogram(rr_ms: np.ndarray, rr_times: np.ndarray,
                   interp_freq: float = INTERP_FREQ,
                   window_s: float = 30.0,
                   overlap_s: float = 25.0
                   ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sliding-window Welch spectrogram of the interpolated RR series.

    Returns (f, t_center, Sxx) with t_center in seconds relative to
    the first interpolated sample.
    """
    rr_i, t_i = interpolate_rr(rr_ms, rr_times, interp_freq)
    if rr_i.size < int(window_s * interp_freq):
        return np.asarray([]), np.asarray([]), np.asarray([])
    nperseg = int(window_s * interp_freq)
    noverlap = int(overlap_s * interp_freq)
    f, t, Sxx = scipy_spectrogram(rr_i, fs=interp_freq, nperseg=nperseg,
                                  noverlap=noverlap, scaling='density')
    # shift t so it is relative to rr_times[0]
    t_center = t + (t_i[0] if t_i.size else 0.0)
    return f, t_center, Sxx


def rr_spectrogram_lf_hf_ms2(
        f: np.ndarray, Sxx: np.ndarray,
        bands: dict | None = None) -> tuple[np.ndarray, np.ndarray]:
    """LF/HF band power (ms²) at each STFT time column, by ∫ PSD df.

    Integrates the same `scaling='density'` spectrogram that `rr_spectrogram`
    returns, so the tracks align with the heatmap and use Task-Force bands.
    """
    if Sxx.size == 0 or f.size == 0:
        return np.asarray([]), np.asarray([])
    bands = bands if bands is not None else BANDS
    (lo_lf, hi_lf) = bands['LF']
    (lo_hf, hi_hf) = bands['HF']
    m_lf = (f >= lo_lf) & (f < hi_lf)
    m_hf = (f >= lo_hf) & (f < hi_hf)
    if not (m_lf.any() and m_hf.any()):
        n_t = Sxx.shape[1]
        nan = np.full(n_t, np.nan)
        return nan, nan
    lf = np.trapezoid(Sxx[m_lf, :], f[m_lf], axis=0)
    hf = np.trapezoid(Sxx[m_hf, :], f[m_hf], axis=0)
    return lf, hf


# =============================================================================
# Duration-effect sweep (Figure 1.4)
# =============================================================================
def duration_effect_sweep(ecg_filtered: np.ndarray, fs: float = FS,
                          window_lengths: tuple[int, ...] = (30, 60, 120, 180,
                                                             240, 300),
                          overlap_frac: float = 0.75,
                          metrics: tuple[str, ...] = ('sdnn_ms', 'lf_ms2',
                                                      'hf_ms2')
                          ) -> pd.DataFrame:
    """Sliding-window duration sensitivity study for Figure 1.4.

    For every window length W we slide with step = W*(1-overlap_frac). For the
    full recording length (W == T_total), we collapse to a single point; std
    is reported as NaN for that row.

    Expected row counts for postural supine E1A (T_total = 300 s, step = W/4):
        W=30 -> 37, W=60 -> 17, W=120 -> 7, W=180 -> 4, W=240 -> 2, W=300 -> 1.

    Returns a DataFrame with columns:
        window_s, metric, n_windows, mean, std, cv_pct
    """
    rows = []
    T = ecg_filtered.size / fs
    for W in window_lengths:
        step = W * (1.0 - overlap_frac)
        if step <= 0 or W > T + 1e-3:
            continue
        if abs(W - T) < 0.5:
            starts = np.array([0.0])
        else:
            starts = np.arange(0.0, T - W + 1e-9, step)

        per_metric: dict[str, list[float]] = {m: [] for m in metrics}
        for s in starts:
            i0 = int(round(s * fs))
            i1 = int(round((s + W) * fs))
            seg = ecg_filtered[i0:i1]
            if seg.size < int(fs * 10):
                continue
            peaks, _ = detect_qrs_nk(seg, fs=fs)
            rr_ms, rr_t = compute_rr(peaks, fs=fs)
            if rr_ms.size < 4:
                continue
            td = time_domain_hrv(rr_ms)
            fd = frequency_domain_hrv(rr_ms, rr_t)
            bag = {**td, **fd}
            for m in metrics:
                v = bag.get(m, float('nan'))
                if np.isfinite(v):
                    per_metric[m].append(v)

        for m, vals in per_metric.items():
            if not vals:
                continue
            arr = np.asarray(vals, dtype=float)
            mean = float(np.mean(arr))
            std  = float(np.std(arr, ddof=1)) if arr.size >= 2 else float('nan')
            cv_pct = float((std / mean) * 100.0) if (arr.size >= 2 and mean > 0) else float('nan')
            rows.append({
                'window_s':  W,
                'metric':    m,
                'n_windows': int(arr.size),
                'mean':      mean,
                'std':       std,
                'cv_pct':    cv_pct,
            })

    return pd.DataFrame(rows)


# =============================================================================
# Transient-event HRV (E2, E3)
# =============================================================================
def compute_transient_hrv(rr_ms: np.ndarray, rr_times: np.ndarray,
                          regime_bounds: dict[str, tuple[float, float]],
                          poly_degree: int = 1) -> dict[str, dict]:
    """Per-regime time-domain HRV + HR-trajectory slope for transient events.

    `regime_bounds` example for E2 (relative to trial start):
        {'pre': (0, 30), 'hold': (30, 70), 'recovery': (70, 120)}

    The slope is fitted on HR(t) = 60000 / RR_ms, NOT on RR(t). Output dict
    keyed by regime name with sub-keys:
        mean_hr_bpm, rmssd_ms, min_hr_bpm, max_hr_bpm, hr_slope_bpm_per_s,
        n_beats
    No frequency-domain HRV at this layer: short segments violate the Task
    Force minimum. For frequency analysis on transient data, use
    `spectral_average_rr` across trials OR `compute_hrv_full` on the anchor
    reference.
    """
    rr_ms = np.asarray(rr_ms, dtype=float)
    rr_times = np.asarray(rr_times, dtype=float)
    out: dict[str, dict] = {}
    for name, (t0, t1) in regime_bounds.items():
        m = (rr_times >= t0) & (rr_times < t1)
        seg_rr = rr_ms[m]
        seg_t  = rr_times[m]
        if seg_rr.size < 3:
            out[name] = {k: float('nan') for k in
                         ('mean_hr_bpm', 'rmssd_ms', 'min_hr_bpm', 'max_hr_bpm',
                          'hr_slope_bpm_per_s')}
            out[name]['n_beats'] = int(seg_rr.size)
            continue
        hr = 60000.0 / seg_rr
        d  = np.diff(seg_rr)
        coeffs = np.polyfit(seg_t, hr, poly_degree)
        slope = float(coeffs[0]) if poly_degree >= 1 else float('nan')
        out[name] = {
            'mean_hr_bpm':        float(np.mean(hr)),
            'rmssd_ms':           float(np.sqrt(np.mean(d ** 2))),
            'min_hr_bpm':         float(np.min(hr)),
            'max_hr_bpm':         float(np.max(hr)),
            'hr_slope_bpm_per_s': slope,
            'n_beats':            int(seg_rr.size),
        }
    return out


# =============================================================================
# Analysis log (metadata / audit trail)
# =============================================================================
ANALYSIS_LOG_COLUMNS = [
    'key', 'orchestrator', 'duration_s',
    'ch0_eq_ch1', 'n_peaks_scipy', 'n_peaks_nk',
    'n_peaks_agreement_pct',
    'ectopic', 'missed', 'extra', 'longshort',
    'artifact_rate_pct', 'n_rejected_scipy',
    'filter_params', 'detection_method',
]
ANALYSIS_LOG: pd.DataFrame = pd.DataFrame(columns=ANALYSIS_LOG_COLUMNS)


def log_analysis(record: dict) -> None:
    """Append a row to the module-global ANALYSIS_LOG."""
    global ANALYSIS_LOG
    row = {c: record.get(c, None) for c in ANALYSIS_LOG_COLUMNS}
    new = pd.DataFrame([row])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', FutureWarning)
        ANALYSIS_LOG = (new if ANALYSIS_LOG.empty
                        else pd.concat([ANALYSIS_LOG, new], ignore_index=True))


def save_analysis_log(path: Path | str) -> None:
    """Persist ANALYSIS_LOG -> CSV (notebook 06 Figure 5.3 reads this)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ANALYSIS_LOG.to_csv(path, index=False)


# =============================================================================
# Orchestrators
# =============================================================================
@dataclass
class AnalysisResult:
    key: str
    orchestrator: str
    t: np.ndarray = field(default_factory=lambda: np.asarray([]))
    ecg_raw: np.ndarray = field(default_factory=lambda: np.asarray([]))
    ecg_filt: np.ndarray = field(default_factory=lambda: np.asarray([]))
    peaks_scipy: np.ndarray = field(default_factory=lambda: np.asarray([]))
    peaks_nk: np.ndarray = field(default_factory=lambda: np.asarray([]))
    rr_ms_scipy: np.ndarray = field(default_factory=lambda: np.asarray([]))
    rr_times_scipy: np.ndarray = field(default_factory=lambda: np.asarray([]))
    rr_ms_nk: np.ndarray = field(default_factory=lambda: np.asarray([]))
    rr_times_nk: np.ndarray = field(default_factory=lambda: np.asarray([]))
    nk_stats: dict = field(default_factory=dict)
    td_hrv: dict = field(default_factory=dict)
    fd_hrv: dict = field(default_factory=dict)
    hrv_full: pd.DataFrame | None = None
    extras: dict[str, Any] = field(default_factory=dict)


def _load_and_filter(key: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, bool]:
    """Shared prep: read ch0 + ch1, filter ch1. Returns (t, ecg_raw_ch1,
    ecg_filt, ch0_eq_ch1)."""
    t, ecg1 = load_ecg(key, ch=1)
    try:
        _, ecg0 = load_ecg(key, ch=0)
        ch_eq = bool(np.array_equal(ecg0, ecg1))
    except FileNotFoundError:
        ch_eq = False
    ecg_f = filter_ecg(ecg1)
    return t, ecg1, ecg_f, ch_eq


def analyze_steady_state(key: str) -> AnalysisResult:
    """Full scipy + NK2 pipeline for E1PRE / E1A–C, E4A_*."""
    t, ecg_raw, ecg_f, ch_eq = _load_and_filter(key)

    # scipy path
    peaks_s = detect_qrs(ecg_f)
    rr_s, rt_s = compute_rr(peaks_s)
    rr_s, rt_s, n_rej = reject_artifacts(rr_s, rt_s)
    rr_s, rt_s = drop_leading_rr_intervals(rr_s, rt_s, RR_DROP_LEADING)
    td = time_domain_hrv(rr_s)
    fd = frequency_domain_hrv(rr_s, rt_s)

    # NK2 path
    peaks_nk, nk_stats = detect_qrs_nk(ecg_f)
    rr_nk, rt_nk = compute_rr(peaks_nk)
    rr_nk, rt_nk = drop_leading_rr_intervals(rr_nk, rt_nk, RR_DROP_LEADING)
    hrv_full = compute_hrv_full(peaks_nk[RR_DROP_LEADING:])

    # agreement summary for analysis log
    nmin = min(peaks_s.size, peaks_nk.size)
    nmax = max(peaks_s.size, peaks_nk.size)
    agree_pct = float(nmin / nmax * 100.0) if nmax > 0 else float('nan')

    log_analysis({
        'key': key, 'orchestrator': 'steady_state',
        'duration_s': float(ecg_raw.size / FS),
        'ch0_eq_ch1': ch_eq,
        'n_peaks_scipy': int(peaks_s.size),
        'n_peaks_nk': int(peaks_nk.size),
        'n_peaks_agreement_pct': agree_pct,
        'ectopic': nk_stats['ectopic'], 'missed': nk_stats['missed'],
        'extra': nk_stats['extra'], 'longshort': nk_stats['longshort'],
        'artifact_rate_pct': float((nk_stats['ectopic'] + nk_stats['missed']
                                    + nk_stats['extra'] + nk_stats['longshort'])
                                   / max(peaks_nk.size, 1) * 100.0),
        'n_rejected_scipy': n_rej,
        'filter_params': f'notch {NOTCH_FREQ} Q={NOTCH_Q}, BP {BANDPASS}',
        'detection_method': 'scipy Pan-Tompkins + NK2 ecg_peaks+Kubios',
    })

    return AnalysisResult(
        key=key, orchestrator='steady_state',
        t=t, ecg_raw=ecg_raw, ecg_filt=ecg_f,
        peaks_scipy=peaks_s, peaks_nk=peaks_nk,
        rr_ms_scipy=rr_s, rr_times_scipy=rt_s,
        rr_ms_nk=rr_nk, rr_times_nk=rt_nk,
        nk_stats=nk_stats, td_hrv=td, fd_hrv=fd, hrv_full=hrv_full,
        extras={'n_rejected_scipy': n_rej},
    )


def analyze_transient_event(key: str,
                            regime_bounds: dict | None = None
                            ) -> AnalysisResult:
    """Segment-wise + trajectory analysis for E2 / E3.

    `regime_bounds` defaults to config.E2_SEG for E2_* keys and config.E3_SEG
    for E3_walk. No per-segment PSD (short segments) -- pooled PSD is computed
    at the notebook level via `spectral_average_rr` across trials.
    """
    t, ecg_raw, ecg_f, ch_eq = _load_and_filter(key)
    peaks_nk, nk_stats = detect_qrs_nk(ecg_f)
    rr_nk, rt_nk = compute_rr(peaks_nk)
    rr_nk, rt_nk = drop_leading_rr_intervals(rr_nk, rt_nk, RR_DROP_LEADING)

    if regime_bounds is None:
        if key.startswith('E2'):
            regime_bounds = dict(E2_SEG)
        elif key == 'E3_walk':
            regime_bounds = dict(E3_SEG)
        else:
            regime_bounds = {}

    transient_hrv = (compute_transient_hrv(rr_nk, rt_nk, regime_bounds)
                     if regime_bounds else {})

    log_analysis({
        'key': key, 'orchestrator': 'transient',
        'duration_s': float(ecg_raw.size / FS),
        'ch0_eq_ch1': ch_eq,
        'n_peaks_scipy': None, 'n_peaks_nk': int(peaks_nk.size),
        'n_peaks_agreement_pct': float('nan'),
        'ectopic': nk_stats['ectopic'], 'missed': nk_stats['missed'],
        'extra': nk_stats['extra'], 'longshort': nk_stats['longshort'],
        'artifact_rate_pct': float((nk_stats['ectopic'] + nk_stats['missed']
                                    + nk_stats['extra'] + nk_stats['longshort'])
                                   / max(peaks_nk.size, 1) * 100.0),
        'n_rejected_scipy': None,
        'filter_params': f'notch {NOTCH_FREQ} Q={NOTCH_Q}, BP {BANDPASS}',
        'detection_method': 'NK2 ecg_peaks+Kubios',
    })

    return AnalysisResult(
        key=key, orchestrator='transient',
        t=t, ecg_raw=ecg_raw, ecg_filt=ecg_f,
        peaks_nk=peaks_nk, rr_ms_nk=rr_nk, rr_times_nk=rt_nk,
        nk_stats=nk_stats,
        extras={'transient_hrv': transient_hrv,
                'regime_bounds': regime_bounds,
                'anchor_key': ANCHOR_KEYS.get(key)},
    )


def analyze_exploratory(key: str) -> AnalysisResult:
    """Minimal pipeline for E4B_sleep: load + filter + peaks + smoothed HR
    trajectory (for Figure A.1). No HRV table."""
    t, ecg_raw, ecg_f, ch_eq = _load_and_filter(key)
    peaks_nk, nk_stats = detect_qrs_nk(ecg_f)
    rr_nk, rt_nk = compute_rr(peaks_nk)
    rr_nk, rt_nk = drop_leading_rr_intervals(rr_nk, rt_nk, RR_DROP_LEADING)

    # Smoothed HR trajectory at 1 Hz (for Figure A.1)
    hr_bpm = 60000.0 / rr_nk if rr_nk.size else np.asarray([])
    t_grid = np.arange(0.0, ecg_raw.size / FS, 1.0)
    hr_interp = (np.interp(t_grid, rt_nk, hr_bpm)
                 if rr_nk.size >= 2 else np.asarray([]))
    # 10 s rolling mean
    if hr_interp.size > 10:
        kernel = np.ones(10) / 10.0
        hr_smooth = np.convolve(hr_interp, kernel, mode='same')
    else:
        hr_smooth = hr_interp

    log_analysis({
        'key': key, 'orchestrator': 'exploratory',
        'duration_s': float(ecg_raw.size / FS),
        'ch0_eq_ch1': ch_eq,
        'n_peaks_scipy': None, 'n_peaks_nk': int(peaks_nk.size),
        'n_peaks_agreement_pct': float('nan'),
        'ectopic': nk_stats['ectopic'], 'missed': nk_stats['missed'],
        'extra': nk_stats['extra'], 'longshort': nk_stats['longshort'],
        'artifact_rate_pct': float((nk_stats['ectopic'] + nk_stats['missed']
                                    + nk_stats['extra'] + nk_stats['longshort'])
                                   / max(peaks_nk.size, 1) * 100.0),
        'n_rejected_scipy': None,
        'filter_params': f'notch {NOTCH_FREQ} Q={NOTCH_Q}, BP {BANDPASS}',
        'detection_method': 'NK2 ecg_peaks+Kubios',
    })

    return AnalysisResult(
        key=key, orchestrator='exploratory',
        t=t, ecg_raw=ecg_raw, ecg_filt=ecg_f,
        peaks_nk=peaks_nk, rr_ms_nk=rr_nk, rr_times_nk=rt_nk,
        nk_stats=nk_stats,
        extras={'t_hr_grid': t_grid, 'hr_smooth_bpm': hr_smooth,
                'anchor_key': ANCHOR_KEYS.get(key)},
    )


def dispatch(key: str) -> AnalysisResult:
    """Call the right orchestrator for this session key."""
    exp_type = EXPERIMENT_TYPE.get(key)
    if exp_type == 'steady_state':
        return analyze_steady_state(key)
    if exp_type == 'transient':
        return analyze_transient_event(key)
    if exp_type == 'exploratory':
        return analyze_exploratory(key)
    raise ValueError(
        f"No orchestrator mapped for key {key!r}. "
        f"Add it to config.EXPERIMENT_TYPE if this is a new experiment.")


__all__ = [
    # loaders
    'load_ecg', 'load_gsen', 'load_device_atr',
    # filter / detection
    'remove_baseline_drift', 'filter_ecg', 'detect_qrs', 'detect_qrs_nk',
    # RR
    'compute_rr', 'reject_artifacts', 'drop_leading_rr_intervals',
    'flatten_leading_baseline_to_local_mean', 'interpolate_rr',
    # HRV (scipy)
    'time_domain_hrv', 'frequency_domain_hrv', 'rr_psd', 'ecg_psd',
    # HRV (NK2)
    'compute_hrv_full', 'derive_respiration_from_ecg', 'hrv_rsa_full',
    # pooling / spectrograms / sweeps
    'spectral_average_rr', 'rr_spectrogram', 'rr_spectrogram_lf_hf_ms2',
    'duration_effect_sweep',
    'compute_transient_hrv',
    # orchestrators
    'analyze_steady_state', 'analyze_transient_event', 'analyze_exploratory',
    'dispatch', 'AnalysisResult',
    # logging
    'ANALYSIS_LOG', 'ANALYSIS_LOG_COLUMNS', 'log_analysis', 'save_analysis_log',
]
