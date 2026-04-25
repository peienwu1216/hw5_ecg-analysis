# HW5 — ECG / HRV Analysis

End-to-end pipeline for a single-lead, 500 Hz ECG dataset spanning 15 recording
sessions (postural baselines, breath-hold events, treadmill walking, paced
breathing, and a partial sleep recording). The project implements both a
scipy-based teaching pipeline and a NeuroKit2-based reference pipeline, and
materializes all figures and tables required by the HW5 specification.

---

## 1. Environment setup

The project targets Python ≥ 3.10. Use **NeuroKit2 ≥ 0.2.13** so HRV frequency
analysis works with **NumPy 2.4+** (``np.trapz`` removed). Pandas is capped at
**< 3** because current NK2 releases declare that upper bound.

```bash
python -m pip install -r requirements.txt
```

Minimum package versions (see `requirements.txt`):

| Package     | Version        |
| ----------- | -------------- |
| numpy       | ≥ 1.23         |
| pandas      | ≥ 2.0, < 3     |
| scipy       | ≥ 1.10         |
| matplotlib  | ≥ 3.7          |
| neurokit2   | ≥ 0.2.13       |
| jupyter     | ≥ 1.0          |

To verify the NeuroKit2 API matches the pipeline assumptions before running
anything else:

```bash
python scripts/preflight_check.py
```

The expected behaviour is documented in `scripts/preflight_report.md`
(critical finding: `nk.signal_fixpeaks` returns `(info_dict, peaks_array)` in
NK2 0.2.x and is handled accordingly in `src/pipeline.py`).

---

## 2. Repository layout

```
hw5_ecg-analysis/
├── data-new/                        # raw CSV sessions (one folder per session)
│   └── 20260424_HHMMSS_<KEY>/       # e.g. E1PRE → …_E1PRE folder (see SESSION_MAP)
│       └── 00/                      # hour-folders, each with ecgh.csv, gsen.csv, deviceatr.csv
├── src/
│   ├── config.py                    # FS, BANDS, SESSION_MAP, FILE_INVENTORY, ANCHOR_KEYS, …
│   ├── pipeline.py                  # loaders, filters, QRS, HRV, RSA, orchestrators, ANALYSIS_LOG
│   └── plotting.py                  # style + reusable plot helpers
├── notebooks/                       # seven notebooks, execute in order
│   ├── 00_quality_check.ipynb
│   ├── 01_pipeline_validation.ipynb
│   ├── 02_experiment_1.ipynb
│   ├── 03_experiment_2.ipynb
│   ├── 04_experiment_3.ipynb
│   ├── 05_experiment_4A.ipynb
│   └── 06_integration.ipynb
├── outputs/
│   ├── figures/                     # all PNGs produced by notebooks
│   └── tables/                      # all CSVs (HRV tables + ANALYSIS_LOG)
├── scripts/
│   ├── preflight_check.py           # verify NK2 API against pipeline assumptions
│   ├── preflight_report.md          # notes from the preflight run
│   └── build_notebooks.py           # regenerates the seven notebook skeletons
└── requirements.txt
```

### Session map

Sessions are referenced by short keys (`E1PRE`, `E1A`, `E1B`, `E1C`,
`E2A_insp_1`, `E2A_insp_2`, `E2B_exp_1`, `E2B_exp_2`, `E3_walk`,
`E4A_12pm/9pm/6pm/5pm/3pm`, `E4B_sleep`). **E1PRE** is pre-sleep supine
(pipeline validation); **E1A–E1C** are the postural ramp (supine → sitting →
standing). Experiment 1 folders use the same suffix as the key (`…_E1PRE`,
`…_E1A`, …); other experiments keep their original naming. `SESSION_MAP` in
`src/config.py` lists the exact directory name for each key.

Each session folder contains one or more hour directories (`00/`, `01/`, …)
each with:

- `ecgh.csv` — two identical ECG channels at 500 Hz (only `ch1` is used).
- `gsen.csv` — 3-axis accelerometer at 25 Hz.
- `deviceatr.csv` — device attribute log.

---

## 3. How to run

After installing dependencies and confirming the preflight passes, run the
notebooks **in order**. `00` gates the rest by asserting `ch0 == ch1` and the
expected analysis-window durations. Every subsequent notebook appends a row
to `outputs/tables/analysis_log.csv` via `pipeline.log_analysis`.

```bash
# From the repo root
jupyter lab                    # recommended; execute notebooks 00 → 06

# Or headless
for nb in notebooks/0*.ipynb; do
  jupyter nbconvert --to notebook --execute "$nb" --output "$(basename "$nb")"
done
```

The notebooks are self-contained but share `src/`:

| Notebook | Deliverables |
| -------- | ------------ |
| `00_quality_check`        | Duration assertions, channel equality check, visual sanity panel, `quality_check.csv` |
| `01_pipeline_validation`  | scipy vs NK2 agreement on **E1PRE**, `e1pre_pipeline_comparison.csv`, `e1pre_hrv_full.csv` |
| `02_experiment_1`         | Postural analysis **E1A–E1C**: tachograms, ECG/RR PSD, duration sweep on **E1A** (supine), `table_1_1_postural.csv`, `e1a_duration_sweep.csv`, `e1_hrv_full.csv` |
| `03_experiment_2`         | Breath-hold HR trajectories (mean ± SD across trials), RR spectrograms, pooled PSD against **E1B** seated baseline, `table_2_1a_trials.csv`, `table_2_1b_pooled.csv` |
| `04_experiment_3`         | Walking tachogram, recovery τ fit, ECG snapshots rest/walk/recovery, motion cross-check (GSEN magnitude), `table_3_1_walking.csv` |
| `05_experiment_4A`        | Publication-grade paced-breathing analysis: tachograms with EDR inset, single-panel RR PSD overlay, regression-based peak-frequency validation, LF/HF-vs-RMSSD contrast, monotonic-amplitude resonance analysis, expanded `table_4_1_paced.csv`, plus Methods/Results/Discussion text blocks |
| `06_integration`          | Autonomic spectrum (log-scale LF/HF + HR twin-axis), HF-vs-HR scatter, cross-pipeline validation figure, E4B sleep appendix, `table_5_cross_experiment.csv` |

---

## 4. Output summary

All artefacts land under `outputs/`.

### Figures (`outputs/figures/`)

| File | Notebook | Purpose |
| ---- | -------- | ------- |
| `00_quality_overview.png`            | 00 | 15-session ECG sanity panel |
| `01_e1pre_validation.png`            | 01 | scipy vs NK2 peaks + RR tachogram + pooled PSD on E1PRE |
| `11_postural_tachograms.png`         | 02 | Three-panel tachograms for E1A–E1C |
| `12_ecg_psd_harmonics.png`           | 02 | ECG PSD with f0 harmonics + respiratory peak marker |
| `13_rr_psd_postural.png`             | 02 | 2×3 RR tachogram + PSD (E1A–E1C), shared Y, grayscale LF/HF, inset metrics |
| `14_duration_effect.png`             | 02 | SDNN/LF/HF vs sliding-window length with CV% |
| `21_e2_tachograms.png`               | 03 | E2 trial-by-trial tachograms with hold markers |
| `22_e2_hr_trajectory.png`            | 03 | HR mean ± SD, aligned to hold onset |
| `23_e2_spectrogram.png`              | 03 | RR spectrograms during breath-hold |
| `24_e2_pooled_psd.png`               | 03 | E1B seated anchor vs pooled hold vs pooled recovery PSD |
| `31_e3_tachogram.png`                | 04 | Walking tachogram with rest / walk / recovery regimes |
| `32_e3_ecg_snapshots.png`            | 04 | 10-s ECG snapshots per regime |
| `33_e3_recovery_tau.png`             | 04 | Exponential recovery fit on HR |
| `34_e3_ecg_psd.png`                  | 04 | ECG PSD per regime |
| `35_e3_motion_crosscheck.png`        | 04 | Accelerometer magnitude vs HR |
| `41_e4a_tachograms_ieee.png`         | 05 | Five-panel paced-breathing tachograms with HR / SDNN / RMSSD and EDR rate inset |
| `41_e4a_tachograms_ieee.pdf`         | 05 | Vector-export companion of Figure 4.1 |
| `42_e4a_psd_overlay_ieee.png`        | 05 | Single-panel RR PSD overlay (linear Y) with band shading, imposed-rate lines, peak labels, and verification inset |
| `42_e4a_psd_overlay_ieee.pdf`        | 05 | Vector-export companion of Figure 4.2 |
| `43_e4a_peak_freq_ieee.png`          | 05 | Expected-vs-measured breathing-frequency scatter with `linregress`, 95% CI, and hypothesis tests |
| `43_e4a_peak_freq_ieee.pdf`          | 05 | Vector-export companion of Figure 4.3 |
| `44_e4a_lfhf_crossover.png`          | 05 | Two-panel contrast: LF/HF inflation above, RMSSD stability below |
| `44_e4a_lfhf_crossover.pdf`          | 05 | Vector-export companion of Figure 4.4 |
| `45_e4a_resonance.png`               | 05 | RR amplitude (`p95-p5`) plus NK2 RSA P2T, showing monotonic increase rather than a clear 6/min peak |
| `45_e4a_resonance.pdf`               | 05 | Vector-export companion of Figure 4.5 |
| `51_autonomic_spectrum.png`          | 06 | Cross-experiment LF/HF (log) + HR (twin axis) |
| `52_hf_vs_hr_scatter.png`            | 06 | HF power vs mean HR across all conditions |
| `53_pipeline_validation.png`         | 06 | scipy vs NK2 peak-count / RR / HF agreement |
| `A1_e4b_sleep_trajectory.png`        | 06 | Appendix: E4B wake-to-sleep HR trajectory |

### Tables (`outputs/tables/`)

| File | Contents |
| ---- | -------- |
| `quality_check.csv`             | Per-session duration, channel equality, pass/fail flags |
| `e1pre_pipeline_comparison.csv` | E1PRE scipy vs NK2 peak counts, RR diff, HRV diff |
| `e1pre_hrv_full.csv`            | Full NK2 HRV suite (time / frequency / non-linear) for E1PRE |
| `e1a_duration_sweep.csv`        | Mean ± SD and CV% of SDNN / LF / HF (sliding windows on **E1A** supine) |
| `e1_hrv_full.csv`               | Full NK2 HRV suite for **E1A–E1C** (stacked for integration) |
| `table_1_1_postural.csv`        | Postural comparison (Task Force HRV indices) |
| `table_2_1a_trials.csv`         | Per-trial time-domain metrics for breath-hold events |
| `table_2_1b_pooled.csv`         | Pooled hold / recovery PSD band powers vs E1B seated baseline |
| `table_3_1_walking.csv`         | Rest / walk / recovery HRV + recovery τ |
| `table_4_1_paced.csv`           | Expanded paced-breathing matrix: expected / measured peak, deviation, EDR, HRV, total power, LF/HF, LF_nu / HF_nu, and RSA metrics |
| `table_5_cross_experiment.csv`  | Cross-experiment HRV summary (sorted per `CONDITION_ORDER`) |
| `analysis_log.csv`              | Append-only audit trail of every `analyze_*` / `load_ecg` call |

---

## 5. Pipeline design notes

- **Single filtering path.** `pipeline.filter_ecg` (50 Hz notch + 0.5–40 Hz
  Butterworth bandpass, `sosfiltfilt`) is the only ECG filter used. NK2 R-peak
  detection receives the already-filtered signal; we do *not* call
  `nk.ecg_clean` to avoid double filtering.
- **Two QRS detectors.** `detect_qrs` is a legend-faithful Pan-Tompkins port
  (5–15 Hz band, squaring, moving-window integration, local adaptive
  threshold, snap-to-max). `detect_qrs_nk` calls
  `nk.ecg_peaks(correct_artifacts=False)` followed by
  `nk.signal_fixpeaks(method='kubios', iterative=True)` so that ectopic /
  missed / extra / longshort counts are explicitly recovered.
- **Artefact rejection is scipy-only.** `reject_artifacts` (300 < RR < 2000 ms)
  runs exclusively in the scipy teaching path; the NK2 path relies on Kubios
  correction at the peak level and does not re-filter at the RR layer.
- **Frequency-domain HRV.** RR series are linearly detrended, cubically
  interpolated to 4 Hz, and Welch-PSD'd with a segment length chosen from the
  available duration. Band definitions follow Task Force of ESC/NASPE (1996).
- **Short segments use spectral averaging.** `spectral_average_rr` pools
  independent PSDs rather than concatenating RR series — used for E2 hold /
  recovery so that the 40–50 s per-trial segments stay below the 60 s HF
  minimum but the pooled PSD still averages four independent Welch estimates.
- **E2 / E3 baseline = E1B (sitting).** The postural anchor for breath-hold and
  walking analysis is the 5-minute seated steady state (**E1B**), not supine
  **E1A**, so the reference is posture-matched to seated tasks.
- **Analysis log.** Every orchestrator call appends one row to the module
  global `ANALYSIS_LOG` (written to `analysis_log.csv`) with session key,
  duration, peak counts, artefact stats, filter parameters, and detection
  method.

---

## 6. Re-generating notebooks

The notebook skeletons are produced by `scripts/build_notebooks.py` (reading
the latest pipeline / plotting API). To re-scaffold:

```bash
python scripts/build_notebooks.py          # overwrites notebooks/*.ipynb
```

This is only needed if you change the plan or the `pipeline` / `plotting`
signatures and want the cell boilerplate regenerated. Day-to-day, edit the
notebooks directly.
