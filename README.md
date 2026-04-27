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
│   └── 20260424_HHMMSS_<KEY>/       # e.g. E1A → …_E1A folder (see SESSION_MAP)
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
│   ├── 05_experiment_4.ipynb
│   └── 06_integration.ipynb
├── outputs/
│   ├── figures/                     # PDF exports from notebooks / scripts
│   └── tables/                      # all CSVs (HRV tables + ANALYSIS_LOG)
├── scripts/
│   ├── preflight_check.py           # verify NK2 API against pipeline assumptions
│   ├── preflight_report.md          # notes from the preflight run
│   └── collect_paper_figures.py     # write manuscript/notes/FIGURE_INDEX* from outputs/figures
└── requirements.txt
```

### Session map

Sessions are referenced by short keys (`E1A`, `E1B`, `E1C`,
`E2A_insp_1`, `E2A_insp_2`, `E2B_exp_1`, `E2B_exp_2`, `E3_walk`,
`E4A_12pm/9pm/6pm/5pm/3pm`, `E4B_sleep`). **E1A–E1C** are the postural ramp
(supine → sitting → standing). **E1A** (post-sleep supine) is used for pipeline
validation. Experiment 1 folders use the same suffix as the key (`…_E1A`,
`…_E1B`, …); other experiments keep their original naming. `SESSION_MAP` in
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
| `01_pipeline_validation`  | scipy vs NK2 agreement on **E1A**, `e1a_pipeline_comparison.csv`, `e1a_hrv_full.csv` |
| `02_experiment_1`         | Postural analysis **E1A–E1C**: tachograms, ECG/RR PSD, duration sweep on **E1A** (supine), `table_1_1_postural.csv`, `e1a_duration_sweep.csv`, `e1_hrv_full.csv` |
| `03_experiment_2`         | Breath-hold HR trajectories (mean ± SD across trials), RR spectrograms, pooled PSD against **E1B** seated baseline, `table_2_1a_trials.csv`, `table_2_1b_pooled.csv` |
| `04_experiment_3`         | Walking tachogram, recovery τ fit, ECG snapshots rest/walk/recovery, motion cross-check (GSEN magnitude), `table_3_1_walking.csv` |
| `05_experiment_4`         | Publication-grade paced-breathing analysis: tachograms with EDR inset, single-panel RR PSD overlay, regression-based peak-frequency validation, LF/HF-vs-RMSSD contrast, monotonic-amplitude resonance analysis, expanded `table_4_1_paced.csv`, plus Methods/Results/Discussion text blocks |
| `06_integration`          | Autonomic spectrum (log-scale LF/HF + HR twin-axis), HF-vs-HR scatter, cross-pipeline validation figure, E4B sleep appendix, `table_5_cross_experiment.csv` |

---

## 4. Output summary

All artefacts land under `outputs/`.

### Figures (`outputs/figures/`)

Canonical figure exports are now stored as PDF files in one place: `outputs/figures/`.
Notebook code should go through `src.plotting.save_figure(...)`, which normalizes the
extension to `.pdf` automatically.

The manuscript uses these files directly instead of keeping a second copy under
`manuscript/figures/`. The current main-text / appendix mapping is tracked in:

- `manuscript/notes/FIGURE_INDEX.md`
- `scripts/collect_paper_figures.py`

Representative manuscript figures:

| File | Notebook | Purpose |
| ---- | -------- | ------- |
| `nb02_fig03_rr_psd_postural.pdf` | 02 | Main posture RR/PSD comparison |
| `nb03_fig02_e2_effort_comparison.pdf` | 03 | Main breath-hold comparison |
| `nb04_fig01_e3_tachogram.pdf` | 04 | Walking tachogram for Results |
| `nb05_fig02_e4a_psd_overlay.pdf` | 05 | Paced-breathing PSD overlay |
| `nb05_fig03_e4a_peak_freq.pdf` | 05 | Breathing peak tracking regression |
| `nb05_fig04_e4a_lfhf_crossover.pdf` | 05 | LF/HF vs RMSSD dissociation |
| `nb06_fig01_autonomic_spectrum.pdf` | 06 | Cross-experiment synthesis |
| `nb06_fig03_pipeline_validation.pdf` | 06 | Appendix pipeline validation |
| `nb06_fig04_e4b_sleep_trajectory.pdf` | 06 | Appendix sleep-onset trajectory |

### Tables (`outputs/tables/`)

| File | Contents |
| ---- | -------- |
| `quality_check.csv`             | Per-session duration, channel equality, pass/fail flags |
| `e1a_pipeline_comparison.csv`   | E1A scipy vs NK2 peak counts, RR diff, HRV diff |
| `e1a_hrv_full.csv`              | Full NK2 HRV suite (time / frequency / non-linear) for E1A |
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

- **Single filtering path.** `pipeline.filter_ecg` (60 Hz notch + 0.5–40 Hz
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
