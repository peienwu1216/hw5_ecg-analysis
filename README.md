# HW5 — ECG / HRV Analysis

> **Paper:** *HRV Interpretation Across Physiological Tasks Using Single-Lead ECG*
> Pei-En Wu · NYCU EEEC 1099 Biomedical Sensors · April 2026
> [**Download manuscript (PDF)**](https://github.com/peienwu1216/hw5_ecg-analysis/releases/latest/download/main.pdf) · [Code & data](https://github.com/peienwu1216/hw5_ecg-analysis)

End-to-end analysis pipeline for 14 single-lead ECG recordings (500 Hz) acquired
from one healthy participant across four physiological paradigms: postural baselines,
voluntary breath-hold, treadmill walking, and paced breathing at five metronome-guided
rates. The project implements a dual-detector strategy (scipy Pan–Tompkins teaching
path + NeuroKit2/Kubios primary path) and generates all figures and tables for the
accompanying IEEE-format manuscript.

**Key findings:**
- Postural loading: HR rose from 54.0 to 79.7 bpm; RMSSD fell from 99.1 to 25.2 ms (supine → standing).
- Breath-hold: inspiratory hold produced 28.7× stronger HF suppression than expiratory hold; both recovered to near-baseline within 50 s.
- Walking: rapid post-exercise HR recovery (τ = 6.8 s); fine-scale HRV motion-limited (step frequency ≈ cardiac fundamental).
- Paced breathing: LF/HF rose from 0.22 to 17.47 as breathing slowed from 12 to 3 breaths/min, while RMSSD remained within 48–66 ms — spectral-band migration, not sympathovagal shift. RR oscillation amplitude increased monotonically (no resonance peak at 6 breaths/min).

---

## 1. Environment setup

The project targets Python ≥ 3.10. Use **NeuroKit2 ≥ 0.2.13** so HRV frequency
analysis works with **NumPy 2.4+** (`np.trapz` removed). Pandas is capped at
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
├── manuscript/
│   └── main.tex                     # IEEE-format paper (IEEEtran conference)
├── scripts/
│   ├── preflight_check.py           # verify NK2 API against pipeline assumptions
│   ├── preflight_report.md          # notes from the preflight run
│   └── collect_paper_figures.py     # write manuscript/notes/FIGURE_INDEX* from outputs/figures
└── requirements.txt
```

### Session map

All 14 recordings were acquired on 2026-04-24 in a single session.
Sessions are referenced by short keys:

| Key | Paradigm | Duration | Posture |
| --- | -------- | -------- | ------- |
| `E1A` | Postural baseline — supine | 300 s | Supine |
| `E1B` | Postural baseline — sitting | 300 s | Sitting |
| `E1C` | Postural baseline — standing | 300 s | Standing |
| `E2A_insp_1/2` | Inspiratory breath-hold (2 trials) | ~120 s each | Sitting |
| `E2B_exp_1/2` | Expiratory breath-hold (2 trials) | ~120 s each | Sitting |
| `E3_walk` | Rest / walk / recovery | 180 s | Sitting → Walking |
| `E4A_12/9/6/5/3pm` | Paced breathing (5 rates) | 220–280 s each | Sitting |

**E1B** (sitting) is used as the posture-matched anchor for E2 and E3 comparisons.
`SESSION_MAP` in `src/config.py` lists the exact directory name for each key.

Each session folder contains one or more hour directories (`00/`, `01/`, …) each with:

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
| `01_pipeline_validation`  | scipy vs NK2 agreement on **E1A** (≥99.5% peak-count, RMSSD diff <2.7 ms), Bland–Altman plots, `e1a_pipeline_comparison.csv`, `e1a_hrv_full.csv` |
| `02_experiment_1`         | Postural analysis **E1A–E1C**: tachograms, ECG PSD harmonics, RR PSD comparison, Poincaré maps, window-duration CV sweep, `table_1_1_postural.csv`, `e1a_duration_sweep.csv`, `e1_hrv_full.csv` |
| `03_experiment_2`         | Breath-hold: effort vs. relaxed trial contrast (inspiratory), pure-physiology overlay (insp. vs. exp. relaxed), HF collapse + spectral dynamics vs. **E1B** anchor, `table_2_1a_trials.csv`, `table_2_1b_pooled.csv` |
| `04_experiment_3`         | Walking: tachogram + motion cross-check, exponential recovery fit (τ = 6.8 s), ECG snapshots, cadence–cardiac spectral overlap, `table_3_1_walking.csv` |
| `05_experiment_4`         | Paced breathing: tachograms, RR PSD overlay, regression-based peak-frequency tracking (R² = 0.998), LF/HF-vs-RMSSD dissociation, respiratory-centered power (monotonic, no 6/min resonance peak), sensitivity analysis (±0.010/0.015/0.020 Hz), `table_4_1_paced.csv` |
| `06_integration`          | Cross-experiment HR vs. RMSSD scatter and total-power summary, `table_5_cross_experiment.csv` |

---

## 4. Output summary

All artefacts land under `outputs/`.

### Figures (`outputs/figures/`)

All figures are exported as PDFs via `src.plotting.save_figure(fig, "nbXX_figYY_*.pdf")`.
The manuscript (`manuscript/main.tex`) reads these directly via `\graphicspath{{../outputs/figures/}}`.

**Main-text figures:**

| File | Notebook | Paper location |
| ---- | -------- | -------------- |
| `nb01_fig01_pipeline_overview.pdf` | 01 | Fig. 1 — ECG processing workflow |
| `nb02_fig03_rr_psd_postural.pdf` | 02 | Fig. 2 — Postural RR/PSD comparison |
| `nb02_fig02_ecg_psd_harmonics.pdf` | 02 | Fig. 3 — ECG PSD harmonics across postures |
| `nb02_fig05_poincare_plot.pdf` | 02 | Fig. 4 — Poincaré return maps |
| `nb03_fig02_e2_effort_vs_relaxed.pdf` | 03 | Fig. 5 — Inspiratory trial effort vs. relaxed |
| `nb03_fig01_e2_hf_collapse.pdf` | 03 | Fig. 6 — HF collapse + spectral dynamics |
| `nb04_fig05_e3_motion_crosscheck.pdf` | 04 | Fig. 7 — Walking overview + motion check |
| `nb04_fig03_e3_recovery_tau.pdf` | 04 | Fig. 8 — Post-walking HR recovery (τ = 6.8 s) |
| `nb04_fig04_e3_ecg_psd.pdf` | 04 | Fig. 9 — Walking ECG/accelerometer spectra |
| `nb05_fig01_e4a_tachograms.pdf` | 05 | Fig. 10 — Paced-breathing tachograms |
| `nb05_fig02_e4a_psd_overlay.pdf` | 05 | Fig. 11 — Paced-breathing RR PSD overlay |
| `nb05_fig04_e4a_lfhf_crossover.pdf` | 05 | Fig. 12 — LF/HF vs. RMSSD dissociation |
| `nb05_fig05b_e4a_resp_power_and_amplitude.pdf` | 05 | Fig. 13 — Resp.-centered power + RR amplitude |
| `nb06_fig01_autonomic_spectrum.pdf` | 06 | Fig. 14 — Cross-experiment autonomic summary |

**Appendix figures:**

| File | Notebook | Appendix |
| ---- | -------- | -------- |
| `appendixA_bland_altman.pdf` | 01 | App. A — Dual-path Bland–Altman + artifact rates |
| `nb02_fig04_duration_effect.pdf` | 02 | App. A — Window-duration CV sweep |
| `nb05_fig03_e4a_peak_freq_optimized.pdf` | 05 | App. A — Peak-frequency entrainment regression |
| `nb03_fig03_e2_pure_physiology.pdf` | 03 | App. B — Insp. vs. exp. relaxed-trial overlay |
| `nb04_fig02_e3_ecg_snapshots.pdf` | 04 | App. C — Walking ECG pre/post-filter snapshots |
| `nb04_fig06_e3_rr_psd_contrast.pdf` | 04 | App. C — Seated vs. walking RR PSD contrast |
| `nb05_fig05_e4a_resp_centered_power.pdf` | 05 | App. D — Resonance sensitivity (3 bandwidths) |

### Tables (`outputs/tables/`)

| File | Contents |
| ---- | -------- |
| `quality_check.csv`             | Per-session duration, channel equality, pass/fail flags |
| `e1a_pipeline_comparison.csv`   | E1A scipy vs NK2 peak counts, RR diff, HRV diff |
| `e1a_hrv_full.csv`              | Full NK2 HRV suite (time / frequency / non-linear) for E1A |
| `e1a_duration_sweep.csv`        | CV% of SDNN / LF / HF vs sliding window duration on E1A |
| `e1_hrv_full.csv`               | Full NK2 HRV suite for E1A–E1C (stacked) |
| `table_1_1_postural.csv`        | Postural comparison (Task Force HRV indices) |
| `table_2_1a_trials.csv`         | Per-trial time-domain metrics for breath-hold events |
| `table_2_1b_pooled.csv`         | Hold / recovery PSD band powers vs E1B seated anchor |
| `table_3_1_walking.csv`         | Rest / walk / recovery HRV + recovery τ |
| `table_4_1_paced.csv`           | Paced-breathing matrix: peak tracking, HRV, LF/HF, resp.-centered power, RR amplitude |
| `table_5_cross_experiment.csv`  | Cross-experiment HRV summary |
| `analysis_log.csv`              | Append-only audit trail of every `analyze_*` / `load_ecg` call |

---

## 5. Pipeline design notes

- **Single filtering path.** `pipeline.filter_ecg` applies a 60 Hz notch ($Q=30$)
  and a 0.5–40 Hz fourth-order Butterworth bandpass (`sosfiltfilt`). NK2 R-peak
  detection receives the already-filtered signal; `nk.ecg_clean` is *not* called
  to avoid double filtering.
- **Two QRS detectors.** `detect_qrs` is a Pan–Tompkins port (5–15 Hz band,
  squaring, moving-window integration, local adaptive threshold, snap-to-max).
  `detect_qrs_nk` calls `nk.ecg_peaks(correct_artifacts=False)` followed by
  `nk.signal_fixpeaks(method='kubios', iterative=True)`.
  The NeuroKit2 path is the **primary source** for all reported results.
- **Artifact rejection.** The scipy teaching path applies physiological-range
  filtering (300 < RR < 2000 ms). The NK2 path relies on Kubios correction at
  the peak level.
- **Frequency-domain HRV.** RR series are linearly detrended, cubically
  interpolated to 4 Hz, and Welch-PSD'd. `nperseg = 256` (Δ*f* ≈ 0.0156 Hz)
  for 5-min steady-state windows; `nperseg = 512` (Δ*f* ≈ 0.0078 Hz) for
  ≥220 s paced-breathing recordings. Band definitions follow Task Force 1996:
  VLF 0.003–0.04 Hz, LF 0.04–0.15 Hz, HF 0.15–0.40 Hz.
- **Short segments use spectral averaging.** `spectral_average_rr` pools
  independent PSDs for E2 hold/recovery segments rather than concatenating
  short RR series.
- **E2 / E3 baseline = E1B (sitting).** The posture-matched anchor for
  breath-hold and walking analysis is the 5-min seated steady state (E1B).
- **Analysis log.** Every orchestrator call appends one row to `ANALYSIS_LOG`
  (written to `analysis_log.csv`) with session key, duration, peak counts,
  artifact stats, filter parameters, and detection method.
