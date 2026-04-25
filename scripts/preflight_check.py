"""Preflight check: confirm installed NeuroKit2 matches pipeline.py assumptions.

Run once before implementing src/pipeline.py:
    python scripts/preflight_check.py
Capture the output and reconcile any mismatches before proceeding.
"""
from __future__ import annotations

import inspect
import sys

import numpy as np

try:
    import neurokit2 as nk
except ImportError:
    sys.exit("FAIL: neurokit2 not installed. pip install -r requirements.txt")

FS = 500
print(f"NeuroKit2 version: {nk.__version__}")
print("=" * 72)

# -- Synthetic ECG for all downstream tests ----------------------------------
ecg = nk.ecg_simulate(duration=60, sampling_rate=FS, heart_rate=60, random_state=0)

# -- Test 1: ecg_peaks return signature and info keys ------------------------
print("\n[1] nk.ecg_peaks return structure")
signals, info = nk.ecg_peaks(ecg, sampling_rate=FS, correct_artifacts=False)
print(f"  signals type:    {type(signals).__name__}")
print(f"  info type:       {type(info).__name__}")
print(f"  info keys:       {sorted(info.keys())}")
assert 'ECG_R_Peaks' in info, "pipeline assumes info['ECG_R_Peaks'] exists"
peaks = np.asarray(info['ECG_R_Peaks'], dtype=int)
print(f"  n_peaks on 60 s @ 60 bpm: {peaks.size}  (expected ~60)")

# -- Test 2: signal_fixpeaks signature -- does it take peaks or RR? ---------
print("\n[2] nk.signal_fixpeaks input/output signature")
sig = inspect.signature(nk.signal_fixpeaks)
print(f"  parameters:      {list(sig.parameters.keys())}")

result = nk.signal_fixpeaks(peaks, sampling_rate=FS, method='kubios', iterative=True)
print(f"  return type:     {type(result).__name__}")
info_corr = None
corr_peaks = None
if isinstance(result, tuple) and len(result) == 2:
    print(f"  tuple length:    2")
    for i, part in enumerate(result):
        print(f"    [{i}] type={type(part).__name__}, "
              f"len={len(part) if hasattr(part, '__len__') else 'n/a'}")
    # NeuroKit 0.2.x returns (info_dict, peaks_array). Legend uses: _, peaks_corr = ...
    if isinstance(result[0], dict) and isinstance(result[1], np.ndarray):
        info_corr, corr_peaks = result
        print("  ORDER DETECTED:  (info_dict, peaks_array)  <-- NK 0.2.x canonical")
    elif isinstance(result[1], dict) and isinstance(result[0], np.ndarray):
        corr_peaks, info_corr = result
        print("  ORDER DETECTED:  (peaks_array, info_dict)")
    else:
        print("  !! unexpected types in the 2-tuple")

if info_corr is not None:
    print(f"  info_corr keys:  {sorted(info_corr.keys())}")
    for k in ('ectopic', 'missed', 'extra', 'longshort'):
        v = info_corr.get(k, None)
        print(f"    {k:10s}: present={v is not None}, "
              f"len={len(v) if hasattr(v, '__len__') else 'n/a'}")

if corr_peaks is not None:
    corr_peaks = np.asarray(corr_peaks, dtype=int)
    print(f"  peaks_raw size=  {peaks.size}")
    print(f"  corr_peaks size= {corr_peaks.size}")
    if abs(corr_peaks.size - peaks.size) > 5:
        print("  !! Large size delta suggests signal_fixpeaks may return RR intervals.")

# -- Test 3: hrv_frequency parameter names -----------------------------------
print("\n[3] nk.hrv_frequency parameters")
sig_f = inspect.signature(nk.hrv_frequency)
params = list(sig_f.parameters.keys())
print(f"  parameters:      {params}")
for wanted in ('psd_method', 'vlf', 'lf', 'hf', 'show', 'sampling_rate'):
    print(f"    {wanted:14s}: present={wanted in params}")

# -- Test 4: hrv_rsa signature -----------------------------------------------
print("\n[4] nk.hrv_rsa parameters")
sig_r = inspect.signature(nk.hrv_rsa)
print(f"  parameters:      {list(sig_r.parameters.keys())}")

# -- Test 5: ecg_rsp signature -----------------------------------------------
print("\n[5] nk.ecg_rsp parameters")
sig_e = inspect.signature(nk.ecg_rsp)
print(f"  parameters:      {list(sig_e.parameters.keys())}")

# -- Test 6: signal_rate signature -------------------------------------------
print("\n[6] nk.signal_rate parameters")
sig_sr = inspect.signature(nk.signal_rate)
print(f"  parameters:      {list(sig_sr.parameters.keys())}")

# -- Test 7: hrv_time / hrv_nonlinear signatures ----------------------------
print("\n[7] nk.hrv_time / nk.hrv_nonlinear parameters")
print(f"  hrv_time:        {list(inspect.signature(nk.hrv_time).parameters.keys())}")
print(f"  hrv_nonlinear:   {list(inspect.signature(nk.hrv_nonlinear).parameters.keys())}")

# -- Test 8: rsp_peaks signature ---------------------------------------------
print("\n[8] nk.rsp_peaks parameters")
print(f"  parameters:      {list(inspect.signature(nk.rsp_peaks).parameters.keys())}")

# -- Test 9: End-to-end sanity: full NK2 HRV DataFrame ----------------------
print("\n[9] Full NK2 HRV on synthetic 60 s @ 60 bpm ECG")
try:
    df_t = nk.hrv_time(peaks, sampling_rate=FS, show=False)
    df_f = nk.hrv_frequency(peaks, sampling_rate=FS,
                            psd_method='welch', show=False,
                            vlf=(0.003, 0.04), lf=(0.04, 0.15), hf=(0.15, 0.40))
    df_n = nk.hrv_nonlinear(peaks, sampling_rate=FS, show=False)
    import pandas as pd
    df_all = pd.concat([df_t, df_f, df_n], axis=1)
    print(f"  shape:           {df_all.shape}")
    print(f"  n_cols (HRV indices): {df_all.shape[1]}")
    print(f"  sample columns:  {list(df_all.columns[:8])}")
    if 'HRV_MeanNN' in df_all.columns:
        print(f"  HRV_MeanNN:      {float(df_all['HRV_MeanNN'].iloc[0]):.1f} ms  (expected ~1000)")
    if 'HRV_SDNN' in df_all.columns:
        print(f"  HRV_SDNN:        {float(df_all['HRV_SDNN'].iloc[0]):.1f} ms")
except Exception as exc:
    print(f"  !! Full HRV failed: {type(exc).__name__}: {exc}")

print("\n" + "=" * 72)
print("Preflight complete. Reconcile any !! lines in pipeline.py before scaffolding.")
