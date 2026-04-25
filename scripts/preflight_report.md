# Preflight report — NeuroKit2 API verification

**Date**: 2026-04-24
**NK2 version**: 0.2.13
**Python**: miniconda3 / 3.13.12

## Summary

Preflight **PASSED** with one critical deviation from the plan's assumed API. All
four assumptions from the plan are reconciled below.

## Findings vs plan assumptions

### 1. `nk.ecg_peaks(..., correct_artifacts=False)` info dict

- info keys: `['ECG_R_Peaks', 'method_fixpeaks', 'method_peaks', 'sampling_rate']`
- `'ECG_R_Peaks'` present. **PLAN ASSUMPTION CONFIRMED**.

### 2. `nk.signal_fixpeaks(peaks, ..., method='kubios', iterative=True)` return signature

**CRITICAL: return order is `(info_dict, peaks_array)` — NOT the `(peaks, info)`
that the plan originally assumed.**

```python
# WRONG (from original plan):
peaks_corrected, info_corr = nk.signal_fixpeaks(peaks_raw, ...)

# RIGHT (confirmed by preflight; matches legend.ipynb cell 19):
info_corr, peaks_corrected = nk.signal_fixpeaks(peaks_raw, sampling_rate=fs,
                                                method='kubios', iterative=True)
```

- info_corr keys: `['c1', 'c2', 'drrs', 'ectopic', 'extra', 'longshort', 'method',
  'missed', 'mrrs', 'rr', 's12', 's22']`
- `ectopic`, `missed`, `extra`, `longshort` all present (as lists). Good.
- Output is a numpy ndarray of corrected peak indices (same order of magnitude
  as raw peak count — not RR intervals).

### 3. `nk.hrv_frequency` parameters

- Full parameter list: `peaks, sampling_rate, ulf, vlf, lf, hf, vhf, psd_method,
  show, silent, normalize, order_criteria, interpolation_rate, kwargs`
- `psd_method='welch'` supported. `vlf/lf/hf` tuples supported.
- **PLAN ASSUMPTION CONFIRMED**.

### 4. `nk.ecg_rsp` signature

**Plan originally wrote `nk.ecg_rsp(ecg_filtered, sampling_rate=fs, peaks=...)` —
this is WRONG for NK 0.2.13.**

Correct signature: `nk.ecg_rsp(ecg_rate, sampling_rate, method)`. First arg is
the **instantaneous ECG rate series**, not the ECG waveform.

Working pattern (from legend.ipynb cell 47):

```python
rate = nk.ecg_rate(peaks, sampling_rate=fs, desired_length=len(ecg))
edr = nk.ecg_rsp(rate, sampling_rate=fs, method='vangent2019')
```

### 5. `nk.signal_rate` parameters

- `peaks, sampling_rate, desired_length, interpolation_method, show`
- Takes peak indices (not raw signal). **CONFIRMED**.

### 6. `nk.hrv_rsa` signature

Full signature: `ecg_signals, rsp_signals, rpeaks, sampling_rate, continuous,
window, window_number`.

The plan's original call `nk.hrv_rsa(ecg_info, rsp_info, sampling_rate=fs)` is
WRONG — needs DataFrames from `nk.ecg_process` / `nk.rsp_process`, not info dicts.

Working pattern (from legend.ipynb cell 51):

```python
signals_nk, info_nk = nk.ecg_process(ecg, sampling_rate=fs)
rsa = nk.hrv_rsa(signals_nk, rpeaks=info_nk, sampling_rate=fs, continuous=False)
```

`rsp_signals` is optional — `ecg_process` produces an internal EDR used as
fallback.

### 7. `nk.rsp_peaks` signature

- `rsp_cleaned, sampling_rate, method, kwargs`
- Takes a cleaned RSP signal (not the raw EDR).

### 8. End-to-end full HRV on synthetic 60 s @ 60 bpm

- Shape: `(1, 86)` — DataFrame with 86 HRV indices (exceeds plan estimate of ~50)
- Sample columns: `HRV_MeanNN, HRV_SDNN, HRV_SDANN1, HRV_SDNNI1, HRV_SDANN2, ...`
- `HRV_MeanNN = 999.6 ms` at 60 bpm -> correct.
- Note: `DFA_alpha2` will warn for recordings < 5 min (only E2 trials affected,
  and those don't run through `compute_hrv_full` per plan).

## Adjustments to apply in `src/pipeline.py`

1. `detect_qrs_nk`: unpack signal_fixpeaks as `info_corr, peaks_corrected = ...`
   (info first, peaks second).
2. `derive_respiration_from_ecg`: compute `nk.ecg_rate(...)` first, pass as the
   first arg to `nk.ecg_rsp(rate, sampling_rate=fs, method='vangent2019')`.
3. `hrv_rsa_full`: use `nk.ecg_process` to produce signals + info, then
   `nk.hrv_rsa(signals_nk, rpeaks=info_nk, sampling_rate=fs, continuous=False)`.
4. Also compute `hrv_nonlinear` with `silent=True` / warnings suppressed for
   short recordings.
