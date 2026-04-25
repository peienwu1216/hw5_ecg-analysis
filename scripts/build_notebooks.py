"""Generate all seven notebooks for the HW5 ECG / HRV project.

Run from repo root:
    python scripts/build_notebooks.py

This is a one-shot scaffolder. Once generated, notebooks may be edited
independently in Jupyter. Re-running this script will overwrite them.
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / 'notebooks'
NB_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Notebook helpers
# ---------------------------------------------------------------------------
def md(src: str) -> nbf.notebooknode.NotebookNode:
    return nbf.v4.new_markdown_cell(src.strip('\n'))


def code(src: str) -> nbf.notebooknode.NotebookNode:
    return nbf.v4.new_code_cell(src.strip('\n'))


def nb(*cells) -> nbf.notebooknode.NotebookNode:
    nb_obj = nbf.v4.new_notebook()
    nb_obj.cells = list(cells)
    nb_obj.metadata = {
        'kernelspec': {'display_name': 'Python 3', 'language': 'python',
                       'name': 'python3'},
        'language_info': {'name': 'python'},
    }
    return nb_obj


SETUP_CELL = '''\
from __future__ import annotations

import sys
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

REPO_ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src import config as cfg
from src import pipeline as P
from src import plotting as PL

PL.apply_style()
warnings.filterwarnings('ignore', category=RuntimeWarning)

FIG_DIR = REPO_ROOT / 'outputs' / 'figures'
TBL_DIR = REPO_ROOT / 'outputs' / 'tables'
FIG_DIR.mkdir(parents=True, exist_ok=True)
TBL_DIR.mkdir(parents=True, exist_ok=True)
print('Setup complete. Sessions available:', len(cfg.SESSION_MAP))
'''


# ---------------------------------------------------------------------------
# 00_quality_check
# ---------------------------------------------------------------------------
def make_nb_00():
    cells = [
        md('''
# 00 — Data quality check

Sanity check every one of the 15 recordings in `data-new/` before any analysis
is run. We verify:

1. **Actual duration** matches the expected analysis window.
2. **Channel equality** (`ch0 == ch1`) — in the legend dataset these were raw
   vs device-filtered, but for this 2026-04-24 acquisition they should be
   byte-identical. We assert this and flag any exceptions.
3. **Visual sanity**: full tachogram-less ECG overview + 10 s zoom to catch
   obvious lead-off, clipping, or saturation.

Output: `outputs/tables/quality_check.csv`.
'''),
        code(SETUP_CELL),
        md('## 1. Loop all sessions'),
        code('''\
rows = []
for key, folder in cfg.SESSION_MAP.items():
    root = cfg.get_session_path(key)
    win = cfg.FILE_INVENTORY[key]["window"]
    expected_s = win[1] - win[0]

    # Read ch0 + ch1 (entire recording, no window crop)
    _, ecg0 = P.load_ecg(key, ch=0, apply_window=False)
    t, ecg1 = P.load_ecg(key, ch=1, apply_window=False)

    n_hours = sum(1 for p in root.iterdir() if p.is_dir() and p.name.isdigit())
    duration_s = ecg1.size / cfg.FS
    ch_equal = bool(np.array_equal(ecg0, ecg1))

    pk_pct = float(np.max(np.abs(ecg1)))
    # crude clipping check: flag if >5% of samples sit at |max|
    clip_frac = float(np.mean(np.isclose(np.abs(ecg1), pk_pct, atol=1e-6)))

    rows.append(dict(
        key=key, folder=folder, n_hours=n_hours,
        total_samples=int(ecg1.size),
        actual_duration_s=round(duration_s, 2),
        analysis_window_s=f"{win[0]}-{win[1]} ({expected_s:.0f}s)",
        duration_ok=bool(duration_s >= expected_s - 0.5),
        ch0_eq_ch1=ch_equal,
        peak_abs=round(pk_pct, 1),
        clip_fraction=round(clip_frac, 4),
        note=cfg.FILE_INVENTORY[key]["note"],
    ))

df_quality = pd.DataFrame(rows)
df_quality
'''),
        md('## 2. Assertions'),
        code('''\
assert df_quality["ch0_eq_ch1"].all(), (
    "ch0 and ch1 differ on: " +
    ", ".join(df_quality.loc[~df_quality["ch0_eq_ch1"], "key"]))
assert df_quality["duration_ok"].all(), (
    "Recordings shorter than analysis window: " +
    ", ".join(df_quality.loc[~df_quality["duration_ok"], "key"]))
print("All 15 recordings pass duration + ch0==ch1 assertions.")
'''),
        md('## 3. Visual sanity — ECG full overview + 10 s zoom'),
        code('''\
n = len(cfg.SESSION_MAP)
fig, axes = plt.subplots(n, 2, figsize=(14, 2.0 * n))
for i, key in enumerate(cfg.SESSION_MAP):
    t_full, ecg_full = P.load_ecg(key, ch=1, apply_window=False)
    axes[i, 0].plot(t_full, ecg_full, linewidth=0.3, color="#444")
    w = cfg.FILE_INVENTORY[key]["window"]
    axes[i, 0].axvspan(w[0], w[1], color="tab:blue", alpha=0.08)
    axes[i, 0].set_title(f"{key} — full ({ecg_full.size/cfg.FS:.0f}s)", fontsize=9)
    axes[i, 0].set_ylabel("ch1")

    zoom_start = int(5 * cfg.FS)
    zoom_end = int(15 * cfg.FS)
    axes[i, 1].plot(t_full[zoom_start:zoom_end], ecg_full[zoom_start:zoom_end],
                    linewidth=0.5, color="#222")
    axes[i, 1].set_title(f"{key} — 5-15 s zoom", fontsize=9)
axes[-1, 0].set_xlabel("Time (s)")
axes[-1, 1].set_xlabel("Time (s)")
fig.tight_layout()
fig.savefig(FIG_DIR / "00_quality_overview.png", dpi=110, bbox_inches="tight")
plt.show()
'''),
        md('## 4. Save table'),
        code('''\
out_path = TBL_DIR / "quality_check.csv"
df_quality.to_csv(out_path, index=False)
print(f"Wrote {out_path}")
df_quality.style.set_caption("Quality check — 15 sessions")
'''),
    ]
    return nb(*cells)


# ---------------------------------------------------------------------------
# 01_pipeline_validation
# ---------------------------------------------------------------------------
def make_nb_01():
    cells = [
        md('''
# 01 — Pipeline validation on E1PRE

End-to-end validation of the processing pipeline using E1PRE (supine pre-sleep,
5-min analysis window).

**Two processing paths compared side-by-side:**

| path  | filter    | detection                      | correction                        | HRV                              |
|-------|-----------|--------------------------------|-----------------------------------|----------------------------------|
| scipy | filter_ecg | detect_qrs (Pan-Tompkins port) | reject_artifacts 300–2000 ms      | time_domain + frequency_domain   |
| NK2   | filter_ecg | detect_qrs_nk (ecg_peaks)      | signal_fixpeaks (Kubios iterative)| compute_hrv_full (~95 indices)   |

**Expected (competitive swimmer, supine):**
- Mean HR 50-65 bpm
- SDNN >= 50 ms
- Dominant HF peak in 0.2-0.3 Hz band
- EDR rate consistent across peak-detection and Welch-peak methods
'''),
        code(SETUP_CELL),
        md('## 1. Load + filter'),
        code('''\
key = "E1PRE"
t, ecg_raw = P.load_ecg(key, ch=1)
ecg_f = P.filter_ecg(ecg_raw)
print(f"{key}: {ecg_raw.size} samples = {ecg_raw.size/cfg.FS:.1f}s")
'''),
        md('## 2. scipy Pan-Tompkins path'),
        code('''\
peaks_s = P.detect_qrs(ecg_f)
rr_s, rt_s = P.compute_rr(peaks_s)
rr_s, rt_s, n_rej = P.reject_artifacts(rr_s, rt_s)
td_scipy = P.time_domain_hrv(rr_s)
fd_scipy = P.frequency_domain_hrv(rr_s, rt_s)
print(f"scipy: {peaks_s.size} peaks, {n_rej} RR rejected")
print(f"  Mean HR = {td_scipy['mean_hr_bpm']:.1f} bpm")
print(f"  SDNN    = {td_scipy['sdnn_ms']:.1f} ms")
print(f"  RMSSD   = {td_scipy['rmssd_ms']:.1f} ms")
'''),
        md('## 3. NeuroKit2 path (authoritative)'),
        code('''\
peaks_nk, nk_stats = P.detect_qrs_nk(ecg_f)
rr_nk, rt_nk = P.compute_rr(peaks_nk)
hrv_full = P.compute_hrv_full(peaks_nk)
print("NK2 peak-detection stats:")
for k, v in nk_stats.items():
    print(f"  {k:20s}: {v}")
print(f"\\ncompute_hrv_full: shape={hrv_full.shape}  (indices={hrv_full.shape[1]})")
'''),
        md('## 4. Peak agreement between paths'),
        code('''\
# Match peaks within a 100 ms window for a fair agreement count
tol = int(0.10 * cfg.FS)
matched = 0
i_nk = 0
for p in peaks_s:
    while i_nk < peaks_nk.size and peaks_nk[i_nk] < p - tol:
        i_nk += 1
    if i_nk < peaks_nk.size and abs(peaks_nk[i_nk] - p) <= tol:
        matched += 1
agreement = 100.0 * matched / max(peaks_s.size, peaks_nk.size)
print(f"scipy peaks: {peaks_s.size}   NK2 peaks: {peaks_nk.size}")
print(f"Matched within {tol} samples (+/-100ms): {matched}")
print(f"Agreement: {agreement:.1f} %")
'''),
        md('## 5. Side-by-side HRV comparison'),
        code('''\
# Canonical overlap indices
comp_rows = [
    ("Mean RR (ms)",  td_scipy["mean_rr_ms"],
     float(hrv_full["HRV_MeanNN"].iloc[0]) if "HRV_MeanNN" in hrv_full else np.nan),
    ("Mean HR (bpm)", td_scipy["mean_hr_bpm"],
     60000.0 / float(hrv_full["HRV_MeanNN"].iloc[0]) if "HRV_MeanNN" in hrv_full else np.nan),
    ("SDNN (ms)",     td_scipy["sdnn_ms"],
     float(hrv_full["HRV_SDNN"].iloc[0])  if "HRV_SDNN" in hrv_full  else np.nan),
    ("RMSSD (ms)",    td_scipy["rmssd_ms"],
     float(hrv_full["HRV_RMSSD"].iloc[0]) if "HRV_RMSSD" in hrv_full else np.nan),
    ("pNN50 (%)",     td_scipy["pnn50_pct"],
     float(hrv_full["HRV_pNN50"].iloc[0]) if "HRV_pNN50" in hrv_full else np.nan),
    ("LF/HF (ratio)", fd_scipy["lf_hf_ratio"],
     float(hrv_full["HRV_LFHF"].iloc[0])  if "HRV_LFHF" in hrv_full  else np.nan),
]
df_cmp = pd.DataFrame(comp_rows, columns=["metric", "scipy", "NK2"])
df_cmp["abs_delta"] = (df_cmp["scipy"] - df_cmp["NK2"]).abs()
df_cmp["rel_delta_pct"] = 100.0 * df_cmp["abs_delta"] / df_cmp[["scipy","NK2"]].abs().mean(axis=1)
df_cmp.style.set_caption("E1PRE — scipy vs NeuroKit2 HRV indices (overlap)").format(
    {"scipy":"{:.2f}","NK2":"{:.2f}","abs_delta":"{:.2f}","rel_delta_pct":"{:.2f}"})
'''),
        md('## 6. Pipeline assertions (swimmer-supine expectations)'),
        code('''\
mean_hr = td_scipy["mean_hr_bpm"]
sdnn    = td_scipy["sdnn_ms"]
print(f"Mean HR = {mean_hr:.1f} bpm (expected 50-65)")
print(f"SDNN    = {sdnn:.1f} ms (expected >= 50)")
assert 50.0 <= mean_hr <= 70.0, f"Mean HR out of range: {mean_hr:.1f}"
assert sdnn >= 50.0, f"SDNN below swimmer-supine threshold: {sdnn:.1f}"
print("OK")
'''),
        md('## 7. EDR dual-method breathing-rate cross-check'),
        code('''\
edr = P.derive_respiration_from_ecg(ecg_f)
print(f"Peak-detection rate: {edr['rate_bpm']:.2f} bpm = {edr['rate_hz']:.4f} Hz")
print(f"Welch PSD peak:      {edr['welch_peak_hz']*60:.2f} bpm = {edr['welch_peak_hz']:.4f} Hz")
delta_bpm = abs(edr["rate_bpm"] - edr["welch_peak_hz"] * 60.0)
print(f"|Δ| = {delta_bpm:.2f} bpm")
assert delta_bpm < 4.0, "EDR methods disagree by more than 4 bpm"
assert 10.0 <= edr["rate_bpm"] <= 22.0, "Spontaneous breathing rate outside 10-22 bpm"
print("EDR cross-check OK")
'''),
        md('## 8. Overview figure'),
        code('''\
fig, axes = plt.subplots(3, 1, figsize=(11, 9))
seg = slice(0, int(10 * cfg.FS))

axes[0].plot(t[seg], ecg_f[seg], color="#222", linewidth=0.7, label="filtered ECG")
p_in = peaks_s[peaks_s < seg.stop]
axes[0].plot(t[p_in], ecg_f[p_in], "rv", markersize=6, label="scipy peaks")
p_in_nk = peaks_nk[peaks_nk < seg.stop]
axes[0].plot(t[p_in_nk], ecg_f[p_in_nk] * 0 + ecg_f[p_in_nk].max() * 1.05,
             "g^", markersize=6, label="NK2 peaks")
axes[0].set_xlabel("Time (s)"); axes[0].set_ylabel("ECG")
axes[0].set_title("E1PRE — First 10 s: filtered ECG + detected R-peaks (both paths)")
axes[0].legend(loc="upper right")

PL.plot_rr_tachogram(rr_nk, rt_nk, ax=axes[1],
                     color=PL.STYLE_COLORS[key],
                     title="E1PRE — RR tachogram (NK2 path)",
                     label="NK2")

f, p = P.rr_psd(rr_nk, rt_nk)
PL.plot_rr_psd_pub(f, p, ax=axes[2], color=PL.STYLE_COLORS[key],
                   title="E1PRE — RR PSD (NK2 path, Welch on 4 Hz grid)",
                   label="E1PRE")
fig.tight_layout()
fig.savefig(FIG_DIR / "01_e1pre_validation.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('## 9. Save validation table'),
        code('''\
# Write full 95-index HRV CSV and the comparison table
hrv_full.insert(0, "key", key)
hrv_full.to_csv(TBL_DIR / "e1pre_hrv_full.csv", index=False)
df_cmp.to_csv(TBL_DIR / "e1pre_pipeline_comparison.csv", index=False)
print(f"Wrote {TBL_DIR/'e1pre_hrv_full.csv'}")
print(f"Wrote {TBL_DIR/'e1pre_pipeline_comparison.csv'}")
'''),
    ]
    return nb(*cells)


# ---------------------------------------------------------------------------
# 02_experiment_1
# ---------------------------------------------------------------------------
def make_nb_02():
    cells = [
        md('''
# 02 — Experiment 1: postural baseline

**E1A** supine, **E1B** sitting, **E1C** standing — steady-state segments. **E1PRE** (pre-sleep supine)
is **not** part of Experiment 1 discussion; it remains for e.g.
`01_pipeline_validation`.)

**Deliverables**:
- Figure 1.1 — 1×3 RR tachograms, short posture titles and HR/SDNN/RMSSD in a
  text box per panel.
- Figure 1.2 — ECG PSD **stacked panels** per posture with each condition's
  own HR-harmonic comb (f0, 2f0, 3f0, 4f0) and respiratory peak marked.
- Figure 1.3 — **2×3** RR tachogram (top) and RR PSD (bottom) per posture
  (E1A–C), **shared** RR y-axis, **per-column log PSD** y-scale, high-contrast
  VLF/LF/HF shading, Welch (Hann) spectrum, inset metrics (ms², n.u., LF/HF),
  LF/HF peak annotations. PSD in **ms²/Hz** (Task Force).
- Figure 1.4 — **sliding-window duration-effect sweep on E1A** showing why
  short windows (30 s) are unreliable (high CV) vs long windows (300 s, low
  CV), per Task Force recommendation of ≥ 5 min for reliable HF.
- Table 1.1 — full metric matrix across E1A–C.
'''),
        code(SETUP_CELL),
        md('## 1. Run steady-state pipeline on E1A–C'),
        code('''\
KEYS = ["E1A", "E1B", "E1C"]
# Short pose labels for figures / table (no protocol or window commentary)
E1_FIG_POSE = {"E1A": "supine", "E1B": "sitting", "E1C": "standing"}
results = {k: P.analyze_steady_state(k) for k in KEYS}
for k, r in results.items():
    print(f"{k}: peaks scipy={r.peaks_scipy.size}, NK={r.peaks_nk.size}  "
          f"HR={r.td_hrv['mean_hr_bpm']:.1f} SDNN={r.td_hrv['sdnn_ms']:.1f}")
'''),
        md('## 2. Figure 1.1 — 1×3 RR tachograms'),
        code('''\
# Subplot titles + metrics in a box (same pattern as Figure 1.3).
fig, axes = plt.subplots(1, 3, figsize=(14, 3.8), sharey=True)
for ax, key in zip(axes, KEYS):
    r = results[key]
    PL.plot_rr_tachogram(r.rr_ms_nk, r.rr_times_nk, ax=ax,
        color=PL.STYLE_COLORS[key],
        title=f"{key} — {E1_FIG_POSE[key]}")
    td = r.td_hrv
    ax.text(
        0.02, 0.98,
        (f"HR {td['mean_hr_bpm']:.0f} bpm · SDNN {td['sdnn_ms']:.1f} · "
         f"RMSSD {td['rmssd_ms']:.1f} ms"),
        transform=ax.transAxes, fontsize=7.5, va="top", ha="left", color="0.2",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                  edgecolor="0.6", alpha=0.9),
        zorder=5,
    )
fig.suptitle("Figure 1.1 — Postural RR tachograms (E1A–C)", fontsize=12, y=1.02)
fig.tight_layout(rect=[0, 0, 1, 0.92])
fig.savefig(FIG_DIR / "11_postural_tachograms.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('''
## 3. Figure 1.2 — ECG PSD stacked panels, per-posture harmonic comb

Each condition has its own mean HR, so the harmonic comb (f0 = HR / 60)
sits at a different location in every panel — e.g. E1A supine at
one f0 vs E1C standing at a higher f0. Overlaying them on a
single axis hid this completely. Here we get one panel per condition,
log-Y clamped to 5 decades below the in-view peak (so the comb is
always visible and we're not scrolling through 20 decades of noise
floor), with red dotted lines at 1–4×f0 and a blue dash-dot at the
respiratory peak derived from the R-peak amplitude modulation (EDR).
'''),
        code('''\
fig, axes = plt.subplots(len(KEYS), 1, figsize=(11, 2.1 * len(KEYS)),
                         sharex=True)
for ax, key in zip(axes, KEYS):
    r   = results[key]
    f, p = P.ecg_psd(r.ecg_filt, fs=cfg.FS)
    edr = P.derive_respiration_from_ecg(r.ecg_filt)
    hr  = float(r.td_hrv["mean_hr_bpm"])
    PL.plot_ecg_psd_with_harmonics(
        f, p,
        mean_hr_bpm=hr,
        respiratory_hz=edr.get("welch_peak_hz", float("nan")),
        ax=ax,
        color=PL.STYLE_COLORS[key],
        xlim=(0.05, 5.0),
        title=(f"{key} — {E1_FIG_POSE[key]}"
               f"   (HR = {hr:.1f} bpm, f0 = {hr/60:.2f} Hz)"),
    )
    ax.set_xlabel("")
axes[-1].set_xlabel("Frequency (Hz)")
fig.suptitle("Figure 1.2 — ECG PSD per posture with HR-harmonic comb "
             "(red :) and EDR respiratory peak (blue -.)",
             fontsize=11, y=1.005)
fig.tight_layout()
fig.savefig(FIG_DIR / "12_ecg_psd_harmonics.png", dpi=130, bbox_inches="tight")
plt.show()
'''),
        md('''
## 4. Figure 1.3 — RR tachogram + PSD grid (journal-style)

Overlaying all three postures on one PSD axis hides posture effects on **total
power**. This figure uses a **2×3 grid** (E1A–C): tachogram above, PSD below,
**shared RR y-limits** across columns; **each PSD column has its own y-scale**
(log by default) so orthostatic reductions in total power are not visually
flattened against a large supine peak.

- **RR y-axis**: global min/max across conditions (with small padding).
- **PSD y-axis**: per-column autoscale on 0–0.5 Hz view, **log** scale (aligned
  with Task Force–style log–log spectrum figures).
- **Grayscale VLF/LF/HF** fills under the PSD curve (strong contrast); band
  masks follow pipeline integration `[lo, hi)`.
- **Tachogram**: short title + HR / SDNN / RMSSD in a text box; **PSD**:
  inset table (ms², n.u., LF/HF) and **LF / HF peak** annotations (HF labelled
  with ~breaths/min for RSA).
- **Serif** typography for this figure only (`plt.rc_context`), via
  `plot_rr_tachogram_psd_grid` in `src/plotting.py`.
'''),
        code('''\
psd_items = []
for key in KEYS:
    r = results[key]
    f, p = P.rr_psd(r.rr_ms_nk, r.rr_times_nk)
    psd_items.append({
        "key":             key,
        "subtitle":        E1_FIG_POSE[key],
        "tachogram_title": f"{key} — {E1_FIG_POSE[key]}",
        "td":              r.td_hrv,
        "f":               f,
        "p":               p,
        "color":           PL.STYLE_COLORS[key],
        "fd":              r.fd_hrv,
        "rr_times":        r.rr_times_nk,
        "rr_ms":           r.rr_ms_nk,
    })

ieee_rc = {
    "font.family":      "serif",
    "font.serif":       ["Times New Roman", "DejaVu Serif", "Liberation Serif"],
    "font.size":        10,
    "axes.labelsize":   10,
    "axes.titlesize":   10,
    "legend.fontsize":  9,
    "xtick.labelsize":  9,
    "ytick.labelsize":  9,
}
with plt.rc_context(ieee_rc):
    fig, _axes = PL.plot_rr_tachogram_psd_grid(
        psd_items,
        xlim=(0.0, 0.5),
        suptitle=(
            "Figure 1.3 — RR tachogram and PSD per posture (E1A–C) · "
            "shared RR scale; per-column PSD (log y); VLF/LF/HF; inset ms² / n.u.; "
            "LF & HF peak freqs"
        ),
    )
    fig.savefig(FIG_DIR / "13_rr_psd_postural.png", dpi=300, bbox_inches="tight")
plt.show()
'''),
        md('''
## 5. Figure 1.4 — Duration-effect sweep on E1A

Sliding window with 75 % overlap across `[30, 60, 120, 180, 240, 300] s`.
For each W we compute SDNN, LF, HF on every sub-window, then report
mean ± std and CV %.

Expected checkpoints (T = 300 s, step = W/4):
`W=30 → 37, W=60 → 17, W=120 → 7, W=180 → 4, W=240 → 2, W=300 → 1` (full).
'''),
        code('''\
r_e1a = results["E1A"]
df_sweep = P.duration_effect_sweep(r_e1a.ecg_filt, fs=cfg.FS)
display(df_sweep.pivot(index="window_s", columns="metric",
                       values=["mean","std","cv_pct","n_windows"]).round(2))

fig = plt.figure(figsize=(13, 4))
PL.plot_duration_sweep(df_sweep, metrics=("sdnn_ms", "lf_ms2", "hf_ms2"), fig=fig)
fig.suptitle("Figure 1.4 — Duration-effect sweep on E1A (sliding window, 75 % overlap)",
             y=1.02, fontsize=11)
fig.savefig(FIG_DIR / "14_duration_effect.png", dpi=120, bbox_inches="tight")
plt.show()
df_sweep.to_csv(TBL_DIR / "e1a_duration_sweep.csv", index=False)
'''),
        md('## 6. Table 1.1 — Full metric matrix E1A–C'),
        code('''\
table11 = []
for key in KEYS:
    r = results[key]
    f_nk = r.hrv_full.iloc[0] if r.hrv_full is not None else None
    row = {
        "Condition":            key,
        "Posture":              E1_FIG_POSE[key].title(),
        "Mean HR (bpm)":        r.td_hrv["mean_hr_bpm"],
        "Mean RR (ms)":         r.td_hrv["mean_rr_ms"],
        "SDNN (ms)":            r.td_hrv["sdnn_ms"],
        "RMSSD (ms)":           r.td_hrv["rmssd_ms"],
        "pNN50 (%)":            r.td_hrv["pnn50_pct"],
        "Total Power (ms²)":    r.fd_hrv["total_power_ms2"],
        "VLF (ms²)":            r.fd_hrv["vlf_ms2"],
        "LF (ms²)":             r.fd_hrv["lf_ms2"],
        "HF (ms²)":             r.fd_hrv["hf_ms2"],
        "LF (n.u.)":            r.fd_hrv["lf_nu"],
        "HF (n.u.)":            r.fd_hrv["hf_nu"],
        "LF/HF":                r.fd_hrv["lf_hf_ratio"],
        "HF peak (Hz)":         r.fd_hrv["hf_peak_hz"],
        "n peaks (NK2)":        r.peaks_nk.size,
        "Artifact rate (%)":    ((r.nk_stats["ectopic"] + r.nk_stats["missed"]
                                  + r.nk_stats["extra"] + r.nk_stats["longshort"])
                                 / max(r.peaks_nk.size, 1) * 100.0),
    }
    table11.append(row)
df_t11 = pd.DataFrame(table11)
df_t11.to_csv(TBL_DIR / "table_1_1_postural.csv", index=False)
df_t11.style.set_caption(
    "Table 1.1 — Postural HRV metrics (E1A-E1C). "
    "Band powers follow Task Force 1996: VLF 0.003–0.04, LF 0.04–0.15, "
    "HF 0.15–0.4 Hz. n.u. = 100·X / (LF+HF)."
).format({
    "Mean HR (bpm)": "{:.1f}", "Mean RR (ms)": "{:.1f}",
    "SDNN (ms)": "{:.1f}", "RMSSD (ms)": "{:.1f}", "pNN50 (%)": "{:.1f}",
    "Total Power (ms²)": "{:,.0f}",
    "VLF (ms²)": "{:,.0f}", "LF (ms²)": "{:,.0f}", "HF (ms²)": "{:,.0f}",
    "LF (n.u.)": "{:.1f}", "HF (n.u.)": "{:.1f}", "LF/HF": "{:.2f}",
    "HF peak (Hz)": "{:.3f}", "Artifact rate (%)": "{:.2f}",
})
'''),
        md('## 7. Orthostatic monotonicity check'),
        code('''\
ordered = df_t11.set_index("Condition").loc[["E1A", "E1B", "E1C"]]
print("Orthostatic ramp E1A (supine) -> E1B (sitting) -> E1C (standing):")
print(f"  HR:     {list(ordered['Mean HR (bpm)'].round(1))}  (expect monotonic up)")
print(f"  HF:     {list(ordered['HF (ms²)'].round(0))}  (expect monotonic down)")
print(f"  LF/HF:  {list(ordered['LF/HF'].round(2))}  (expect monotonic up)")

# save full HRV index DataFrame for 06_integration
pd.concat([results[k].hrv_full.assign(key=k) for k in KEYS], axis=0).to_csv(
    TBL_DIR / "e1_hrv_full.csv", index=False)
'''),
    ]
    return nb(*cells)


# ---------------------------------------------------------------------------
# 03_experiment_2
# ---------------------------------------------------------------------------
def make_nb_03():
    cells = [
        md('''
# 03 — Experiment 2: voluntary breath hold

Four trials of ~120 s each:
`E2A_insp_1/2` (inspiratory hold) and `E2B_exp_1/2` (expiratory hold).
Each trial: 0-30 s pre-hold → 30-70 s hold → 70-120 s recovery.

**HF reference baseline strategy**

The pre-hold 30 s is too short for reliable HF (Task Force recommends ≥ 1 min).
We therefore use **E1B (5 min sitting)** as the high-confidence HF reference —
same posture, adequate duration. Pre-hold is kept only for time-domain sanity.
See `config.ANCHOR_KEYS`.

**Deliverables**:
- Figure 2.1 — 2×2 per-trial RR tachograms with hold markers.
- Figure 2.2 — event-aligned HR trajectory, mean ± SD across same-condition trials.
- Figure 2.3 — RR spectrogram (primary dynamic visualization of HF extinction).
- Figure 2.4 — three-line pooled PSD per condition: E1B ref / pooled hold /
  pooled recovery, via `spectral_average_rr`.
- Table 2.1 — per-trial time-domain stats + pooled HF drop ratio.
'''),
        code(SETUP_CELL),
        md('## 1. Load anchor (E1B, 5 min sitting)'),
        code('''\
anchor_key = "E1B"
r_anchor = P.analyze_steady_state(anchor_key)
f_anc, p_anc = P.rr_psd(r_anchor.rr_ms_nk, r_anchor.rr_times_nk)
HF_E1B = r_anchor.fd_hrv["hf_ms2"]
LF_E1B = r_anchor.fd_hrv["lf_ms2"]
print(f"E1B (anchor) — Mean HR {r_anchor.td_hrv['mean_hr_bpm']:.1f} bpm, "
      f"HF = {HF_E1B:.1f} ms², LF = {LF_E1B:.1f} ms²")
'''),
        md('## 2. Load all four E2 trials'),
        code('''\
E2_KEYS = ["E2A_insp_1", "E2A_insp_2", "E2B_exp_1", "E2B_exp_2"]
trials = {k: P.analyze_transient_event(k) for k in E2_KEYS}
for k, r in trials.items():
    th = r.extras["transient_hrv"]
    print(f"{k}: n_peaks={r.peaks_nk.size}  anchor={r.extras['anchor_key']}")
    for reg, d in th.items():
        print(f"  {reg:10s}: HR={d['mean_hr_bpm']:.1f} bpm  "
              f"RMSSD={d['rmssd_ms']:.1f}  slope={d['hr_slope_bpm_per_s']:+.3f} bpm/s  "
              f"n_beats={d['n_beats']}")
'''),
        md('## 3. Figure 2.1 — 2×2 RR tachograms with hold markers'),
        code('''\
fig, axes = plt.subplots(2, 2, figsize=(13, 7), sharey=True)
for ax, key in zip(axes.ravel(), E2_KEYS):
    r = trials[key]
    PL.plot_rr_tachogram(r.rr_ms_nk, r.rr_times_nk, ax=ax,
        color=PL.STYLE_COLORS[key],
        title=f"{key}",
        event_markers=[(cfg.E2_SEG["hold"][0], "hold start"),
                       (cfg.E2_SEG["hold"][1], "hold end")])
    ax.axvspan(*cfg.E2_SEG["hold"], color="0.85", alpha=0.35, zorder=-1)
fig.suptitle("Figure 2.1 — Breath-hold RR tachograms (hold shaded 30-70 s)", fontsize=12)
fig.tight_layout()
fig.savefig(FIG_DIR / "21_e2_tachograms.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('## 4. Figure 2.2 — event-aligned HR trajectory, mean ± SD across trials'),
        code('''\
def hr_trajectory(r, fs_interp=1.0, t_rel_range=(-30.0, 90.0),
                  event_t=30.0):
    """Resample HR onto 1 Hz grid, offset by event_t."""
    if r.rr_ms_nk.size < 4:
        return np.asarray([]), np.asarray([])
    hr = 60000.0 / r.rr_ms_nk
    t_grid = np.arange(t_rel_range[0], t_rel_range[1], 1.0 / fs_interp)
    hr_i = np.interp(t_grid, r.rr_times_nk - event_t, hr,
                     left=np.nan, right=np.nan)
    return t_grid, hr_i

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), sharey=True)
for ax, cond in zip(axes, ["insp", "exp"]):
    keys_cond = [k for k in E2_KEYS if cond in k]
    stack = []
    for k in keys_cond:
        t_rel, hr_i = hr_trajectory(trials[k])
        ax.plot(t_rel, hr_i, linewidth=0.8, alpha=0.5,
                color=PL.STYLE_COLORS[k], label=k)
        stack.append(hr_i)
    arr = np.array(stack, dtype=float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mean_hr = np.nanmean(arr, axis=0)
        std_hr  = np.nanstd(arr, axis=0, ddof=1)
    ax.plot(t_rel, mean_hr, color="black", linewidth=2,
            label=f"{cond} mean")
    ax.fill_between(t_rel, mean_hr - std_hr, mean_hr + std_hr,
                    color="black", alpha=0.12)
    ax.axvline(0.0, color="k", linestyle="--", linewidth=0.8)
    ax.axvline(40.0, color="k", linestyle="--", linewidth=0.8)
    ax.axvspan(0, 40, color="0.85", alpha=0.25)
    ax.set_xlabel("Time relative to hold start (s)")
    ax.set_title(f"{'Inspiratory' if cond=='insp' else 'Expiratory'} hold")
    ax.legend(loc="upper left")
axes[0].set_ylabel("HR (bpm)")
fig.suptitle("Figure 2.2 — Event-aligned HR trajectories (mean ± SD, 2 trials per condition)",
             fontsize=12)
fig.tight_layout()
fig.savefig(FIG_DIR / "22_e2_hr_trajectory.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('## 5. Figure 2.3 — RR spectrogram (one trial per condition, dynamic HF collapse)'),
        code('''\
fig, axes = plt.subplots(2, 1, figsize=(12, 7))
for ax, key in zip(axes, ["E2A_insp_1", "E2B_exp_1"]):
    r = trials[key]
    f_s, t_s, Sxx = P.rr_spectrogram(r.rr_ms_nk, r.rr_times_nk)
    PL.plot_spectrogram_rr(f_s, t_s, Sxx, ax=ax,
        title=f"{key} — RR spectrogram (30 s window, 25 s overlap)",
        event_markers=[(cfg.E2_SEG["hold"][0], "hold"),
                       (cfg.E2_SEG["hold"][1], "release")])
fig.tight_layout()
fig.savefig(FIG_DIR / "23_e2_spectrogram.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('''
## 6. Figure 2.4 — three-line pooled PSD per condition (E1B ref / hold / recovery)

`spectral_average_rr` per-segment Welch → ensemble mean + std across the 2
same-condition trials. Shaded band = ±1 std across segments.
'''),
        code('''\
def trial_segments(r, bounds):
    segs = {}
    for name, (t0, t1) in bounds.items():
        mask = (r.rr_times_nk >= t0) & (r.rr_times_nk < t1)
        segs[name] = (r.rr_ms_nk[mask], r.rr_times_nk[mask])
    return segs

pooled = {}
for cond in ["insp", "exp"]:
    keys_cond = [k for k in E2_KEYS if cond in k]
    hold_segs = [trial_segments(trials[k], cfg.E2_SEG)["hold"]     for k in keys_cond]
    rec_segs  = [trial_segments(trials[k], cfg.E2_SEG)["recovery"] for k in keys_cond]
    pooled[cond] = {
        "hold":     P.spectral_average_rr(hold_segs),
        "recovery": P.spectral_average_rr(rec_segs),
    }

fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
for ax, cond, sub_title in zip(axes, ["insp", "exp"],
                               ["Inspiratory hold", "Expiratory hold"]):
    # Line A: E1B anchor
    PL.plot_rr_psd_pub(f_anc, p_anc, ax=ax, color="#222",
        label=f"E1B anchor (5 min)  HF={HF_E1B:.0f} ms²",
        annotate_peaks=False, logy=True)
    # Line B: pooled hold
    pa = pooled[cond]["hold"]
    if pa["f"].size:
        PL.plot_rr_psd_pub(pa["f"], pa["p_mean"], ax=ax,
            fill_std=pa["p_std"], color="tab:red",
            label=f"Pooled hold ({pa['n_segments']} seg)  HF={pa['band_powers']['HF']:.0f}±{pa['band_powers_std']['HF']:.0f} ms²",
            annotate_peaks=False, logy=True)
    # Line C: pooled recovery
    pr = pooled[cond]["recovery"]
    if pr["f"].size:
        PL.plot_rr_psd_pub(pr["f"], pr["p_mean"], ax=ax,
            fill_std=pr["p_std"], color="tab:green",
            label=f"Pooled recovery ({pr['n_segments']} seg)  HF={pr['band_powers']['HF']:.0f}±{pr['band_powers_std']['HF']:.0f} ms²",
            annotate_peaks=False, logy=True)
    ax.set_title(sub_title)
    ax.legend(loc="upper right", fontsize=8)
fig.suptitle("Figure 2.4 — Three-line PSD: E1B anchor | pooled hold | pooled recovery",
             fontsize=12)
fig.tight_layout()
fig.savefig(FIG_DIR / "24_e2_pooled_psd.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('## 7. Table 2.1 — per-trial time-domain + pooled HF ratio'),
        code('''\
def cv_pct(a, b):
    arr = np.array([a, b], dtype=float)
    m = np.mean(arr)
    if not np.isfinite(m) or abs(m) < 1e-9:
        return float("nan")
    return float(np.std(arr, ddof=1) / abs(m) * 100.0)

rows = []
for cond, keys_cond in [("Inspiratory", ["E2A_insp_1", "E2A_insp_2"]),
                        ("Expiratory",  ["E2B_exp_1",  "E2B_exp_2"])]:
    t1 = trials[keys_cond[0]].extras["transient_hrv"]
    t2 = trials[keys_cond[1]].extras["transient_hrv"]

    def vals(reg, metric):
        return t1[reg][metric], t2[reg][metric]

    rows.append({
        "Condition": cond,
        "Pre-hold HR trial1 (bpm)":  t1["pre"]["mean_hr_bpm"],
        "Pre-hold HR trial2 (bpm)":  t2["pre"]["mean_hr_bpm"],
        "Pre-hold HR CV %":          cv_pct(*vals("pre",   "mean_hr_bpm")),
        "Pre-hold RMSSD trial1 (ms)":t1["pre"]["rmssd_ms"],
        "Pre-hold RMSSD trial2 (ms)":t2["pre"]["rmssd_ms"],
        "Hold mean HR trial1 (bpm)": t1["hold"]["mean_hr_bpm"],
        "Hold mean HR trial2 (bpm)": t2["hold"]["mean_hr_bpm"],
        "Hold min HR (bpm, min of both)": min(t1["hold"]["min_hr_bpm"],
                                              t2["hold"]["min_hr_bpm"]),
        "ΔHR hold-pre trial1 (bpm)": t1["hold"]["mean_hr_bpm"] - t1["pre"]["mean_hr_bpm"],
        "ΔHR hold-pre trial2 (bpm)": t2["hold"]["mean_hr_bpm"] - t2["pre"]["mean_hr_bpm"],
        "HR slope hold trial1 (bpm/s)": t1["hold"]["hr_slope_bpm_per_s"],
        "HR slope hold trial2 (bpm/s)": t2["hold"]["hr_slope_bpm_per_s"],
        "Recovery mean HR trial1 (bpm)": t1["recovery"]["mean_hr_bpm"],
        "Recovery mean HR trial2 (bpm)": t2["recovery"]["mean_hr_bpm"],
    })
df_t21 = pd.DataFrame(rows)
display(df_t21.style.set_caption(
    "Table 2.1a — Per-trial time-domain HRV during inspiratory / expiratory hold"
).format(precision=2))

# Pooled PSD panel: HF drop ratio vs E1B
pool_rows = []
for cond in ["insp", "exp"]:
    pa, pr = pooled[cond]["hold"], pooled[cond]["recovery"]
    pool_rows.append({
        "Condition": "Inspiratory" if cond == "insp" else "Expiratory",
        "HF E1B (ms²)":            HF_E1B,
        "HF hold pooled (ms²)":    pa["band_powers"]["HF"],
        "HF hold SD (ms²)":        pa["band_powers_std"]["HF"],
        "HF hold ratio (E1B/hold)":    HF_E1B / pa["band_powers"]["HF"]
                                        if pa["band_powers"]["HF"] > 0 else float("nan"),
        "HF recovery pooled (ms²)": pr["band_powers"]["HF"],
        "HF recovery SD (ms²)":     pr["band_powers_std"]["HF"],
        "HF recovery ratio (rec/E1B)": pr["band_powers"]["HF"] / HF_E1B
                                       if HF_E1B > 0 else float("nan"),
    })
df_pool = pd.DataFrame(pool_rows)
display(df_pool.style.set_caption(
    "Table 2.1b — HF power: E1B anchor vs pooled hold / recovery"
).format(precision=2))

df_t21.to_csv(TBL_DIR / "table_2_1a_trials.csv", index=False)
df_pool.to_csv(TBL_DIR / "table_2_1b_pooled.csv", index=False)
print("Table 2.1 saved.")
'''),
        md('## 8. Key finding narrative'),
        code('''\
print("=== Key finding 1: HF collapse during breath hold ===")
for row in pool_rows:
    drop_pct = 100.0 * (1 - row["HF hold pooled (ms²)"] / row["HF E1B (ms²)"])
    print(f"  {row['Condition']}: HF dropped to "
          f"{row['HF hold pooled (ms²)']/row['HF E1B (ms²)']*100:.1f}% of E1B "
          f"({drop_pct:.1f}% reduction, ratio {row['HF hold ratio (E1B/hold)']:.2f}×) — "
          f"directly confirming respiratory origin of HF band.")
'''),
    ]
    return nb(*cells)


# ---------------------------------------------------------------------------
# 04_experiment_3
# ---------------------------------------------------------------------------
def make_nb_04():
    cells = [
        md('''
# 04 — Experiment 3: ambulatory motion

`E3_walk` — 180 s recording: 0-60 s seated, 60-120 s walking, 120-180 s recovery.

Anchor seated reference: **E1B** (sitting 5 min). Walking HRV is flagged
**unreliable** due to motion artifact; we still report it for completeness.

**Deliverables**:
- Figure 3.1 — full tachogram with segment shading.
- Figure 3.2 — raw ECG 15 s per segment (shows motion artifact in walking).
- Figure 3.3 — recovery HR with exponential tau fit.
- Figure 3.4 — ECG PSD seated vs walking (motion noise in 1-3 Hz).
- Figure 3.5 — motion-g(t) vs RR tachogram, Pearson corr during walking.
- Table 3.1 — per-segment stats + anchor comparison.
'''),
        code(SETUP_CELL),
        md('## 1. Load pipeline + anchor + gsen'),
        code('''\
r  = P.analyze_transient_event("E3_walk")
r_anc = P.analyze_steady_state("E1B")
t_g, motion_g = P.load_gsen("E3_walk")
print(f"E3_walk:  {r.peaks_nk.size} peaks over {r.ecg_raw.size/cfg.FS:.1f}s")
print(f"E1B anchor: HR={r_anc.td_hrv['mean_hr_bpm']:.1f} bpm, HF={r_anc.fd_hrv['hf_ms2']:.0f} ms²")
for seg, d in r.extras["transient_hrv"].items():
    print(f"  {seg:10s}: HR={d['mean_hr_bpm']:.1f} bpm  RMSSD={d['rmssd_ms']:.1f}  "
          f"slope={d['hr_slope_bpm_per_s']:+.3f}  n_beats={d['n_beats']}")
'''),
        md('## 2. Figure 3.1 — full tachogram with segment shading'),
        code('''\
fig, ax = plt.subplots(figsize=(12, 4))
PL.plot_rr_tachogram(r.rr_ms_nk, r.rr_times_nk, ax=ax,
    color=PL.STYLE_COLORS["E3_walk"],
    title="Figure 3.1 — E3 RR tachogram (seated / walking / recovery)")
for name, (t0, t1) in cfg.E3_SEG.items():
    color = {"seated":"tab:blue","walking":"tab:red","recovery":"tab:green"}[name]
    ax.axvspan(t0, t1, color=color, alpha=0.10)
    ax.text((t0+t1)/2, ax.get_ylim()[1]*0.98, name,
            ha="center", va="top", fontsize=9, color=color)
fig.tight_layout()
fig.savefig(FIG_DIR / "31_e3_tachogram.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('## 3. Figure 3.2 — raw ECG 15 s per segment (motion artifact visible)'),
        code('''\
fig, axes = plt.subplots(3, 1, figsize=(12, 7), sharey=True)
for ax, (name, (t0, t1)) in zip(axes, cfg.E3_SEG.items()):
    mid = (t0 + t1) / 2
    i0 = int((mid - 7.5) * cfg.FS)
    i1 = int((mid + 7.5) * cfg.FS)
    i0 = max(0, i0); i1 = min(r.ecg_filt.size, i1)
    t_seg = r.t[i0:i1]
    ax.plot(t_seg, r.ecg_filt[i0:i1], linewidth=0.5, color="#222")
    ax.set_title(f"{name}  ({mid-7.5:.0f}-{mid+7.5:.0f} s)")
    ax.set_ylabel("ECG (filtered)")
axes[-1].set_xlabel("Time (s)")
fig.suptitle("Figure 3.2 — 15-s ECG snapshots per segment", fontsize=12)
fig.tight_layout()
fig.savefig(FIG_DIR / "32_e3_ecg_snapshots.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('## 4. Figure 3.3 — recovery HR with exponential tau fit'),
        code('''\
from scipy.optimize import curve_fit

def exp_decay(t, A, tau, C):
    return A * np.exp(-t / tau) + C

t_rec0, t_rec1 = cfg.E3_SEG["recovery"]
mask = (r.rr_times_nk >= t_rec0) & (r.rr_times_nk < t_rec1)
t_rec = r.rr_times_nk[mask] - t_rec0
hr_rec = 60000.0 / r.rr_ms_nk[mask]

try:
    popt, _ = curve_fit(exp_decay, t_rec, hr_rec,
                        p0=[hr_rec[0]-hr_rec[-1], 20.0, hr_rec[-1]],
                        maxfev=5000)
    A, tau, C = popt
    t_fit = np.linspace(0, t_rec.max(), 200)
    hr_fit = exp_decay(t_fit, *popt)
    fit_ok = True
except Exception as exc:
    A = tau = C = float("nan"); fit_ok = False
    print(f"Fit failed: {exc}")

fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(t_rec, hr_rec, "o", color=PL.STYLE_COLORS["E3_walk"], label="HR data")
if fit_ok:
    ax.plot(t_fit, hr_fit, "-", color="tab:red", linewidth=1.4,
            label=f"fit: {A:.1f}·exp(-t/{tau:.1f}) + {C:.1f}")
ax.set_xlabel("Time since recovery onset (s)")
ax.set_ylabel("HR (bpm)")
ax.set_title(f"Figure 3.3 — Post-walking HR recovery (τ = {tau:.1f} s)")
ax.legend()
fig.tight_layout()
fig.savefig(FIG_DIR / "33_e3_recovery_tau.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('## 5. Figure 3.4 — ECG PSD seated vs walking'),
        code('''\
seg_idx = {name: (int(t0*cfg.FS), int(t1*cfg.FS))
           for name, (t0,t1) in cfg.E3_SEG.items()}
fig, ax = plt.subplots(figsize=(10, 5))
colors = {"seated":"tab:blue","walking":"tab:red","recovery":"tab:green"}
for name, (i0, i1) in seg_idx.items():
    seg = r.ecg_filt[i0:i1]
    f, p = P.ecg_psd(seg, fs=cfg.FS, nperseg_sec=8)
    ax.semilogy(f, p, color=colors[name], linewidth=0.9, label=name)
ax.set_xlim(0.1, 15)
ax.axvspan(1.0, 3.0, color="0.85", alpha=0.35, zorder=-1)
ax.text(2.0, ax.get_ylim()[1]*0.6, "walking\\ncadence\\n1-3 Hz",
        ha="center", fontsize=8, color="tab:red")
ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel("PSD (mV²/Hz)")
ax.set_title("Figure 3.4 — ECG PSD: seated vs walking vs recovery")
ax.legend()
fig.tight_layout()
fig.savefig(FIG_DIR / "34_e3_ecg_psd.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('## 6. Figure 3.5 — motion-g(t) vs RR tachogram + Pearson correlation'),
        code('''\
fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
PL.plot_rr_tachogram(r.rr_ms_nk, r.rr_times_nk, ax=axes[0],
    color=PL.STYLE_COLORS["E3_walk"], title="RR tachogram (E3_walk)")
for name, (t0, t1) in cfg.E3_SEG.items():
    axes[0].axvspan(t0, t1, color=colors[name], alpha=0.08)
axes[1].plot(t_g, motion_g, color="tab:purple", linewidth=0.6)
axes[1].set_ylabel("motion_g (|g|-1)")
axes[1].set_xlabel("Time (s)")
axes[1].set_title("Accelerometer motion magnitude (gravity subtracted, 10 Hz LP)")
for name, (t0, t1) in cfg.E3_SEG.items():
    axes[1].axvspan(t0, t1, color=colors[name], alpha=0.08)

# Pearson during walking
t0w, t1w = cfg.E3_SEG["walking"]
# resample |ΔRR| on gsen grid within walking segment
m_rr   = (r.rr_times_nk >= t0w) & (r.rr_times_nk < t1w)
rr_w = r.rr_ms_nk[m_rr]; rt_w = r.rr_times_nk[m_rr]
m_g  = (t_g >= t0w) & (t_g < t1w)
t_gw  = t_g[m_g]; mg_w = motion_g[m_g]
if rr_w.size >= 3 and mg_w.size >= 3:
    d_rr = np.abs(np.diff(rr_w))
    t_d  = rt_w[1:]
    mg_i = np.interp(t_d, t_gw, mg_w)
    mask = np.isfinite(d_rr) & np.isfinite(mg_i)
    corr = float(np.corrcoef(d_rr[mask], mg_i[mask])[0,1]) if mask.sum() > 3 else float("nan")
else:
    corr = float("nan")
axes[1].text(t0w + 5, axes[1].get_ylim()[1]*0.85,
             f"Pearson(|ΔRR|, motion_g) during walking = {corr:.3f}",
             fontsize=10, color="tab:purple", bbox=dict(facecolor="white", alpha=0.7))
fig.suptitle("Figure 3.5 — Motion cross-check (walking segment)", fontsize=12)
fig.tight_layout()
fig.savefig(FIG_DIR / "35_e3_motion_crosscheck.png", dpi=120, bbox_inches="tight")
plt.show()
print(f"Pearson corr(|ΔRR|, motion_g) during walking: {corr:.3f}")
'''),
        md('## 7. Table 3.1 — per-segment stats + anchor comparison'),
        code('''\
rows = []
for seg_name, d in r.extras["transient_hrv"].items():
    rows.append({
        "Segment": seg_name,
        "Range (s)": f"{cfg.E3_SEG[seg_name][0]:.0f}-{cfg.E3_SEG[seg_name][1]:.0f}",
        "n_beats":   d["n_beats"],
        "Mean HR (bpm)": d["mean_hr_bpm"],
        "Min HR (bpm)":  d["min_hr_bpm"],
        "Max HR (bpm)":  d["max_hr_bpm"],
        "RMSSD (ms)":    d["rmssd_ms"],
        "HR slope (bpm/s)": d["hr_slope_bpm_per_s"],
        "Note":      "**UNRELIABLE (motion)**" if seg_name == "walking" else "",
    })
rows.append({
    "Segment": "E1B anchor",
    "Range (s)": "300 (5 min)",
    "n_beats": int(r_anc.peaks_nk.size),
    "Mean HR (bpm)": r_anc.td_hrv["mean_hr_bpm"],
    "Min HR (bpm)":  r_anc.td_hrv["min_hr_bpm"],
    "Max HR (bpm)":  r_anc.td_hrv["max_hr_bpm"],
    "RMSSD (ms)":    r_anc.td_hrv["rmssd_ms"],
    "HR slope (bpm/s)": float("nan"),
    "Note": "seated reference",
})
df_t31 = pd.DataFrame(rows)
df_t31["Motion corr (Pearson)"] = ""
df_t31.loc[df_t31["Segment"]=="walking", "Motion corr (Pearson)"] = f"{corr:.3f}"
df_t31["Recovery τ (s)"] = ""
df_t31.loc[df_t31["Segment"]=="recovery", "Recovery τ (s)"] = f"{tau:.1f}" if fit_ok else ""
df_t31.to_csv(TBL_DIR / "table_3_1_walking.csv", index=False)
df_t31.style.set_caption("Table 3.1 — E3 segment HRV vs E1B sitting anchor")
'''),
    ]
    return nb(*cells)


# ---------------------------------------------------------------------------
# 05_experiment_4A
# ---------------------------------------------------------------------------
def make_nb_05():
    cells = [
        md('''
# 05 — Experiment 4A: paced breathing (⭐ money)

Five conditions at fixed metronome-guided rates:
`E4A_12pm` (0.200 Hz), `E4A_9pm` (0.150 Hz), `E4A_6pm` (0.100 Hz, resonance),
`E4A_5pm` (0.0833 Hz), `E4A_3pm` (0.050 Hz — below HF band).

**Deliverables**:
- Figure 4.1 — 5-panel RR tachograms.
- Figure 4.2 — RR PSD overlay, respiratory peaks annotated (money figure).
- Figure 4.3 — peak-frequency scatter vs expected + R² + failure diagnostic.
- Figure 4.4 — LF/HF vs breathing rate (crossover around 0.15 Hz).
- Figure 4.5 — resonance amplitude: peak-to-peak RR + NK2 hrv_rsa P2T.
- Table 4.1 — full 5-column metric matrix.
'''),
        code(SETUP_CELL),
        md('## 1. Run steady-state pipeline across 5 conditions'),
        code('''\
E4A_KEYS = ["E4A_12pm", "E4A_9pm", "E4A_6pm", "E4A_5pm", "E4A_3pm"]
results = {k: P.analyze_steady_state(k) for k in E4A_KEYS}
for k, r in results.items():
    exp_hz = cfg.E4A_EXPECTED_BREATHING_HZ[k]
    print(f"{k}: HR={r.td_hrv['mean_hr_bpm']:.1f}  "
          f"SDNN={r.td_hrv['sdnn_ms']:.1f}  "
          f"LF/HF={r.fd_hrv['lf_hf_ratio']:.2f}  "
          f"expected_rate={exp_hz:.3f}Hz ({exp_hz*60:.0f}/min)")
'''),
        md('## 2. Figure 4.1 — 5-panel RR tachograms'),
        code('''\
fig, axes = plt.subplots(5, 1, figsize=(12, 13), sharex=True)
for ax, key in zip(axes, E4A_KEYS):
    r = results[key]
    PL.plot_rr_tachogram(r.rr_ms_nk, r.rr_times_nk, ax=ax,
        color=PL.STYLE_COLORS[key],
        title=(f"{key} — expected {cfg.E4A_EXPECTED_BREATHING_HZ[key]*60:.0f}/min "
               f"= {cfg.E4A_EXPECTED_BREATHING_HZ[key]:.3f} Hz"))
fig.suptitle("Figure 4.1 — Paced-breathing RR tachograms", fontsize=12)
fig.tight_layout()
fig.savefig(FIG_DIR / "41_e4a_tachograms.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('''
## 3. Figure 4.2 — RR PSD per paced rate (MONEY figure)

Textbook style — one panel per paced condition, shared X axis, linear Y,
band boundaries drawn as thin grey lines with ``LF`` / ``HF`` labels
floating in-figure (no shaded fills). A red dashed line marks the
**target** breathing frequency for that condition; the black ★ shows the
**measured** dominant peak in the RR spectrum. Reading the panels
top-to-bottom (12/min → 3/min) you should see the peak migrate
*leftward* from HF into LF, with 6/min (0.10 Hz) sitting right on the
LF–HF boundary — the classical "resonance" / slow-breathing effect.
'''),
        code('''\
psd_items = []
for key in E4A_KEYS:
    r = results[key]
    f, p = P.rr_psd(r.rr_ms_nk, r.rr_times_nk)
    target = cfg.E4A_EXPECTED_BREATHING_HZ[key]
    psd_items.append({
        "key":       key,
        "subtitle":  f"paced {cfg.FILE_INVENTORY[key]['note']}",
        "f":         f,
        "p":         p,
        "color":     PL.STYLE_COLORS[key],
        "fd":        r.fd_hrv,
        "target_hz": target,
    })

# Widen the X range enough to include 0.05 Hz (3/min target) and draw
# the textbook-style grid lines at VLF/LF and LF/HF boundaries.
fig, _axes = PL.plot_rr_psd_stacked(
    psd_items,
    style="textbook",
    xlim=(0.02, 0.45),
    peak_range=(0.03, 0.40),
    row_height=1.75,
    fig_width=11.0,
    suptitle=("Figure 4.2 — RR PSD per paced rate · red --- = target freq, "
              "★ = measured peak · peak should migrate leftward as "
              "breathing slows"),
)
fig.savefig(FIG_DIR / "42_e4a_psd_overlay.png", dpi=130, bbox_inches="tight")
plt.show()
'''),
        md('## 4. Figure 4.3 — peak-freq scatter + R² + failure diagnostic'),
        code('''\
scatter_rows = []
for key in E4A_KEYS:
    r = results[key]
    f, p = P.rr_psd(r.rr_ms_nk, r.rr_times_nk)
    # Find peak in 0.01-0.4 Hz (spans VLF to HF boundary so 3/min at 0.05Hz is included)
    m = (f >= 0.01) & (f <= 0.45)
    peak_hz = float(f[m][np.argmax(p[m])]) if m.any() else float("nan")
    exp_hz = cfg.E4A_EXPECTED_BREATHING_HZ[key]
    match  = cfg.check_freq_match(peak_hz, exp_hz)
    scatter_rows.append({
        "key": key, "expected_hz": exp_hz, "measured_hz": peak_hz,
        "residual_hz": peak_hz - exp_hz, "check_freq_match": match,
    })
df_scat = pd.DataFrame(scatter_rows)

x = df_scat["expected_hz"].to_numpy()
y = df_scat["measured_hz"].to_numpy()
slope, intercept = np.polyfit(x, y, 1)
ss_res = np.sum((y - (slope * x + intercept)) ** 2)
ss_tot = np.sum((y - y.mean()) ** 2)
r_sq = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")

fig, ax = plt.subplots(figsize=(6.5, 6))
for row in scatter_rows:
    ax.plot(row["expected_hz"], row["measured_hz"], "o", markersize=9,
            color=PL.STYLE_COLORS[row["key"]], label=row["key"])
xline = np.array([0, 0.25])
ax.plot(xline, xline, "k--", linewidth=0.8, label="y = x")
ax.plot(xline, slope * xline + intercept, "r-", linewidth=1,
        label=f"fit  slope={slope:.2f}")
ax.set_xlabel("Expected breathing rate (Hz)")
ax.set_ylabel("Measured RR-PSD peak (Hz)")
ax.set_xlim(0, 0.25); ax.set_ylim(0, 0.25)
ax.set_aspect("equal")
ax.set_title(f"Figure 4.3 — Peak-freq scatter (R² = {r_sq:.3f})")
ax.legend(loc="lower right", fontsize=9)
fig.tight_layout()
fig.savefig(FIG_DIR / "43_e4a_peak_freq.png", dpi=120, bbox_inches="tight")
plt.show()

# --- Failure diagnostic -----------------------------------------------------
if r_sq < 0.95:
    print(f"WARN: R² = {r_sq:.3f} below target 0.95. Diagnostic table:")
    dfd = df_scat.copy()
    dfd["abs_residual_hz"] = dfd["residual_hz"].abs()
    dfd.sort_values("abs_residual_hz", ascending=False, inplace=True)
    display(dfd.style.set_caption("Residuals sorted by |residual|"))
    worst = dfd.iloc[0]
    edr = P.derive_respiration_from_ecg(results[worst["key"]].ecg_filt)
    exp_hz_worst = worst["expected_hz"]
    print(f"Worst offender: {worst['key']}  "
          f"expected={exp_hz_worst:.3f}  measured={worst['measured_hz']:.3f}  "
          f"residual={worst['residual_hz']:+.3f}Hz")
    print(f"EDR welch_peak_hz={edr['welch_peak_hz']:.3f}  "
          f"rate_bpm(peak)={edr['rate_bpm']:.2f}")
    diff_edr_to_rr  = abs(edr["welch_peak_hz"] - worst["measured_hz"])
    diff_edr_to_exp = abs(edr["welch_peak_hz"] - exp_hz_worst)
    if diff_edr_to_rr < diff_edr_to_exp:
        print("  Interpretation: EDR agrees with RR peak, not with metronome -> "
              "subject likely breathed slower/faster than metronome.")
    else:
        print("  Interpretation: EDR agrees with metronome -> "
              "RR-PSD peak may be a pipeline artefact (try longer window or different nperseg).")
else:
    print(f"OK: R² = {r_sq:.3f} >= 0.95. Peak detection across 5 paced conditions is reliable.")
'''),
        md('## 5. Figure 4.4 — LF/HF crossover vs breathing rate'),
        code('''\
rates = [cfg.E4A_EXPECTED_BREATHING_HZ[k] for k in E4A_KEYS]
lfs = [results[k].fd_hrv["lf_ms2"] for k in E4A_KEYS]
hfs = [results[k].fd_hrv["hf_ms2"] for k in E4A_KEYS]
lfhf = [results[k].fd_hrv["lf_hf_ratio"] for k in E4A_KEYS]

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(rates, lfs, "o-", color="tab:orange", label="LF (ms²)", linewidth=1.4)
ax.plot(rates, hfs, "s-", color="tab:green",  label="HF (ms²)", linewidth=1.4)
ax.set_xlabel("Breathing rate (Hz)"); ax.set_ylabel("Power (ms²)")
ax.set_yscale("log")
ax.axvspan(cfg.BANDS["LF"][0], cfg.BANDS["LF"][1],
           color=PL.BAND_COLORS["LF"], alpha=0.15)
ax.axvspan(cfg.BANDS["HF"][0], cfg.BANDS["HF"][1],
           color=PL.BAND_COLORS["HF"], alpha=0.15)
ax2 = ax.twinx()
ax2.plot(rates, lfhf, "v--", color="tab:red", linewidth=1, label="LF/HF")
ax2.set_ylabel("LF / HF (ratio)")
for i, key in enumerate(E4A_KEYS):
    ax.annotate(key, (rates[i], lfs[i]), fontsize=8, color=PL.STYLE_COLORS[key])
ax.set_title("Figure 4.4 — LF and HF crossover with breathing rate")
lines = ax.get_lines() + ax2.get_lines()
ax.legend(lines, [l.get_label() for l in lines], loc="upper left", fontsize=9)
fig.tight_layout()
fig.savefig(FIG_DIR / "44_e4a_lfhf_crossover.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('## 6. Figure 4.5 — resonance amplitude: peak-to-peak RR + NK2 RSA P2T'),
        code('''\
amps_ptp = []
amps_rsa = []
for key in E4A_KEYS:
    r = results[key]
    rr = r.rr_ms_nk
    ptp = float(np.percentile(rr, 95) - np.percentile(rr, 5)) if rr.size else float("nan")
    amps_ptp.append(ptp)
    rsa = P.hrv_rsa_full(r.ecg_filt, fs=cfg.FS)
    p2t_mean = float(rsa.get("RSA_P2T_Mean", float("nan")))
    amps_rsa.append(p2t_mean)

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(rates, amps_ptp, "o-", color="tab:blue",  label="RR p95-p5 (ms)",    linewidth=1.3)
ax.plot(rates, amps_rsa, "s-", color="tab:purple",label="NK2 hrv_rsa P2T (ms)", linewidth=1.3)
ax.set_xlabel("Breathing rate (Hz)"); ax.set_ylabel("Amplitude (ms)")
ax.set_title("Figure 4.5 — Resonance amplitude (peak-to-peak RR + NK2 P2T)")
ax.axvline(0.10, color="gray", linestyle=":", alpha=0.6)
ax.text(0.10, ax.get_ylim()[1]*0.95, " 0.10 Hz\\n resonance\\n (6/min)",
        fontsize=8, va="top", color="gray")
for i, key in enumerate(E4A_KEYS):
    ax.annotate(key, (rates[i], amps_ptp[i]), fontsize=8,
                color=PL.STYLE_COLORS[key])
ax.legend()
fig.tight_layout()
fig.savefig(FIG_DIR / "45_e4a_resonance.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('## 7. Table 4.1 — full 5-column metric matrix'),
        code('''\
rows = []
for key in E4A_KEYS:
    r = results[key]
    exp_hz  = cfg.E4A_EXPECTED_BREATHING_HZ[key]
    meas_hz = next(row["measured_hz"] for row in scatter_rows if row["key"] == key)
    edr = P.derive_respiration_from_ecg(r.ecg_filt)
    rsa = P.hrv_rsa_full(r.ecg_filt)
    rows.append({
        "Condition":      key,
        "Expected rate (Hz)":  exp_hz,
        "Expected rate (/min)": exp_hz * 60,
        "Measured RR peak (Hz)": meas_hz,
        "EDR Welch peak (Hz)":   edr["welch_peak_hz"],
        "EDR rate (/min)":       edr["rate_bpm"],
        "Match (relative)":      cfg.check_freq_match(meas_hz, exp_hz),
        "Mean HR (bpm)": r.td_hrv["mean_hr_bpm"],
        "SDNN (ms)":     r.td_hrv["sdnn_ms"],
        "RMSSD (ms)":    r.td_hrv["rmssd_ms"],
        "LF (ms²)":      r.fd_hrv["lf_ms2"],
        "HF (ms²)":      r.fd_hrv["hf_ms2"],
        "LF/HF":         r.fd_hrv["lf_hf_ratio"],
        "RR p95-p5 (ms)":float(np.percentile(r.rr_ms_nk, 95) - np.percentile(r.rr_ms_nk, 5)) if r.rr_ms_nk.size else np.nan,
        "NK2 P2T Mean (ms)":  rsa.get("RSA_P2T_Mean", np.nan),
        "NK2 P2T SD (ms)":    rsa.get("RSA_P2T_SD", np.nan),
        "Porges-Bohrer":      rsa.get("RSA_PorgesBohrer", np.nan),
    })
df_t41 = pd.DataFrame(rows)
df_t41.to_csv(TBL_DIR / "table_4_1_paced.csv", index=False)
df_t41.style.set_caption("Table 4.1 — Paced breathing full metric matrix").format(precision=3)
'''),
    ]
    return nb(*cells)


# ---------------------------------------------------------------------------
# 06_integration
# ---------------------------------------------------------------------------
def make_nb_06():
    cells = [
        md('''
# 06 — Cross-experiment integration

Assembles the key findings across all four experiments + appendix for E4B.

**Figures**:
- **5.1** — autonomic-state spectrum: LF/HF (log Y) + Mean HR (twin axis) across
  ordered conditions.
- **5.2** — HF vs Mean HR scatter, coloured by experiment. E3_walk excluded
  (motion-unreliable); E4B_sleep marked with open marker (partial).
- **5.3** — pipeline validation bar chart from `analysis_log.csv`: artifact
  rate, peak-detection success, scipy-vs-NK2 agreement, per condition.
- **Appendix A.1** — E4B exploratory HR trajectory anchored to E1PRE pre-sleep HR.
'''),
        code(SETUP_CELL),
        md('## 1. Run every key through dispatch() and save analysis_log.csv'),
        code('''\
# Make sure the log starts empty so we capture exactly this run's records
P.ANALYSIS_LOG.drop(P.ANALYSIS_LOG.index, inplace=True)

results = {}
for key in cfg.CONDITION_ORDER:
    try:
        r = P.dispatch(key)
    except Exception as exc:
        print(f"!! {key}: {type(exc).__name__}: {exc}")
        continue
    results[key] = r

# Additionally capture the 4 E2 trials (not in CONDITION_ORDER for Fig 5.1)
for key in ["E2A_insp_1", "E2A_insp_2", "E2B_exp_1", "E2B_exp_2"]:
    if key not in results:
        results[key] = P.dispatch(key)

log_path = TBL_DIR / "analysis_log.csv"
P.save_analysis_log(log_path)
print(f"Wrote {log_path}")
print("ANALYSIS_LOG preview:")
display(P.ANALYSIS_LOG)
'''),
        md('## 2. Figure 5.1 — autonomic state spectrum (LF/HF + mean HR)'),
        code('''\
# For steady-state keys we have fd_hrv; for transient keys we omit LF/HF
# (per E2/E3 analysis strategy). Therefore only CONDITION_ORDER rows where
# orchestrator == "steady_state" populate LF/HF; E3_walk / E4B_sleep are
# rendered for HR only.
def is_ss(k): return cfg.EXPERIMENT_TYPE.get(k) == "steady_state"

x_keys = [k for k in cfg.CONDITION_ORDER if k in results]
hr = []
lfhf = []
for k in x_keys:
    r = results[k]
    hr.append(r.td_hrv.get("mean_hr_bpm")
              if is_ss(k)
              else (60000.0 / np.mean(r.rr_ms_nk) if r.rr_ms_nk.size else np.nan))
    lfhf.append(r.fd_hrv.get("lf_hf_ratio") if is_ss(k) else np.nan)

fig, ax = plt.subplots(figsize=(13, 5))
x = np.arange(len(x_keys))
ax.set_yscale("log")
# Bars for LF/HF (left axis)
bar = ax.bar(x, lfhf, color=[PL.STYLE_COLORS.get(k, "#888") for k in x_keys],
             alpha=0.75, edgecolor="black", linewidth=0.6)
ax.set_ylabel("LF / HF  (log)", color="tab:red")
ax.set_ylim(0.05, 20)

ax2 = ax.twinx()
ax2.plot(x, hr, "ko-", linewidth=1.3, markersize=6, label="Mean HR")
ax2.set_ylabel("Mean HR (bpm)", color="black")

ax.set_xticks(x)
ax.set_xticklabels(x_keys, rotation=45, ha="right")
ax.set_title("Figure 5.1 — Autonomic state spectrum  (LF/HF log bars + Mean HR line)")

# Flag unreliable
for tick, k in zip(ax.get_xticklabels(), x_keys):
    if k == "E3_walk":
        tick.set_color("tab:red"); tick.set_fontstyle("italic")
    if k == "E4B_sleep":
        tick.set_color("gray");    tick.set_fontstyle("italic")
ax.text(0.01, 0.97,
        "Red italic = motion-unreliable | Gray italic = partial recording\\n"
        "LF/HF bars omitted for transient / exploratory conditions (E3_walk, E4B_sleep)",
        transform=ax.transAxes, fontsize=8, va="top",
        bbox=dict(facecolor="white", alpha=0.8, edgecolor="none"))
fig.tight_layout()
fig.savefig(FIG_DIR / "51_autonomic_spectrum.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('## 3. Figure 5.2 — HF vs mean HR scatter (E3 excluded, E4B open marker)'),
        code('''\
fig, ax = plt.subplots(figsize=(8, 6))
for k, r in results.items():
    if not is_ss(k):
        continue
    if k == "E3_walk":
        continue
    hr_k = r.td_hrv["mean_hr_bpm"]
    hf_k = r.fd_hrv["hf_ms2"]
    marker = "o"
    filled = True
    if k == "E4B_sleep":
        marker = "o"; filled = False
    ax.plot(hr_k, hf_k, marker=marker, markersize=12,
            color=PL.STYLE_COLORS.get(k, "#333"),
            markerfacecolor=PL.STYLE_COLORS.get(k, "#333") if filled else "white",
            markeredgecolor=PL.STYLE_COLORS.get(k, "#333"), linewidth=0)
    ax.annotate(k, (hr_k, hf_k), xytext=(6, 4),
                textcoords="offset points", fontsize=9)

ax.set_xlabel("Mean HR (bpm)"); ax.set_ylabel("HF power (ms²)")
ax.set_yscale("log")
ax.set_title("Figure 5.2 — HF power vs Mean HR  (higher HR → lower HF)")
fig.tight_layout()
fig.savefig(FIG_DIR / "52_hf_vs_hr_scatter.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('## 4. Figure 5.3 — pipeline validation bar chart from ANALYSIS_LOG'),
        code('''\
log = P.ANALYSIS_LOG.copy()
# Keep only one row per key (dispatch already logged each once here)
log = log.drop_duplicates(subset=["key"], keep="last")
log = log.set_index("key")
order_local = [k for k in cfg.CONDITION_ORDER if k in log.index]

artifact = log.loc[order_local, "artifact_rate_pct"].astype(float).to_numpy()
detect_success = 100.0 - artifact
agreement = log.loc[order_local, "n_peaks_agreement_pct"].astype(float).to_numpy()

fig, ax = plt.subplots(figsize=(13, 5))
x = np.arange(len(order_local))
w = 0.28
ax.bar(x - w, artifact,      w, color="tab:red",    label="Artifact rate (%)")
ax.bar(x,      detect_success, w, color="tab:green", label="Detection success (%)")
ax.bar(x + w, agreement,     w, color="tab:blue",   label="scipy-NK agreement (%)")
ax.set_xticks(x)
ax.set_xticklabels(order_local, rotation=45, ha="right")
ax.set_ylabel("%")
ax.set_ylim(0, 105)
ax.set_title("Figure 5.3 — Cross-experiment pipeline validation")
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig(FIG_DIR / "53_pipeline_validation.png", dpi=120, bbox_inches="tight")
plt.show()
'''),
        md('''
## Appendix A — Exploratory findings (E4B sleep onset)

Partial ~14-minute recording captured early wake-to-sleep transition before
the device terminated. Reference horizontal line = E1PRE (pre-sleep supine) mean
HR, i.e. the subject's awake-lying baseline.
'''),
        code('''\
r_e4b = results.get("E4B_sleep") or P.dispatch("E4B_sleep")
r_e1pre = results.get("E1PRE")       or P.dispatch("E1PRE")

t_grid  = r_e4b.extras["t_hr_grid"]
hr_smooth = r_e4b.extras["hr_smooth_bpm"]
hr_e1pre = r_e1pre.td_hrv["mean_hr_bpm"]

t_min = t_grid / 60.0
valid = np.isfinite(hr_smooth) & (hr_smooth > 30)
hr_start = np.nanmean(hr_smooth[(t_grid < 180) & valid])
hr_end   = np.nanmean(hr_smooth[(t_grid > t_grid.max() - 60) & valid])
delta_hr = hr_start - hr_end
dur_min  = (t_grid.max() - 0) / 60.0

fig, ax = plt.subplots(figsize=(12, 4.5))
ax.plot(t_min, hr_smooth, color=PL.STYLE_COLORS["E4B_sleep"], linewidth=1.1,
        label="E4B HR (10 s smoothed)")
ax.axhline(hr_e1pre, color="black", linestyle="--", linewidth=0.9,
           label=f"E1PRE (pre-sleep supine) = {hr_e1pre:.1f} bpm")
ax.axvspan(0, 3, color="0.85", alpha=0.4, zorder=-1)
ax.text(1.5, ax.get_ylim()[1]*0.95, "wake baseline\\n0-3 min",
        ha="center", fontsize=9, va="top")
ax.axvspan(3, t_min.max(), color="#e0e7ff", alpha=0.3, zorder=-2)
ax.text((3 + t_min.max())/2, ax.get_ylim()[1]*0.95,
        "transition\\n3 min → end", ha="center", fontsize=9, va="top")
ax.set_xlabel("Time from recording start (min)")
ax.set_ylabel("HR (bpm)")
ax.set_title(
    f"Figure A.1 — E4B sleep-onset HR trajectory  "
    f"(ΔHR ≈ {delta_hr:+.1f} bpm over {dur_min:.1f} min, "
    f"consistent with N1-N2 vagal activation)")
ax.legend(loc="upper right")
fig.tight_layout()
fig.savefig(FIG_DIR / "A1_e4b_sleep_trajectory.png", dpi=120, bbox_inches="tight")
plt.show()

print(f"Partial E4B recording captured early wake-to-sleep transition. "
      f"HR decreased by {delta_hr:.1f} bpm over {dur_min:.1f} minutes, "
      f"consistent with N1-N2 vagal activation, before recording termination. "
      f"Not included in main results due to incomplete duration.")
'''),
        md('## 5. Summary table — top-level autonomic metrics per condition'),
        code('''\
summary = []
for k in cfg.CONDITION_ORDER:
    r = results.get(k)
    if r is None:
        continue
    ss  = is_ss(k)
    summary.append({
        "key": k,
        "exp_type": cfg.EXPERIMENT_TYPE[k],
        "Mean HR": r.td_hrv.get("mean_hr_bpm")
                   if ss else (60000.0 / np.mean(r.rr_ms_nk) if r.rr_ms_nk.size else np.nan),
        "SDNN (ms)":   r.td_hrv.get("sdnn_ms"),
        "LF (ms²)":    r.fd_hrv.get("lf_ms2")  if ss else np.nan,
        "HF (ms²)":    r.fd_hrv.get("hf_ms2")  if ss else np.nan,
        "LF/HF":       r.fd_hrv.get("lf_hf_ratio") if ss else np.nan,
        "note":        cfg.FILE_INVENTORY[k]["note"],
    })
df_sum = pd.DataFrame(summary)
df_sum.to_csv(TBL_DIR / "table_5_cross_experiment.csv", index=False)
df_sum.style.set_caption("Table 5 — Cross-experiment summary").format(precision=2)
'''),
    ]
    return nb(*cells)


# ---------------------------------------------------------------------------
# Write all notebooks
# ---------------------------------------------------------------------------
def main():
    targets = {
        '00_quality_check.ipynb':      make_nb_00(),
        '01_pipeline_validation.ipynb': make_nb_01(),
        '02_experiment_1.ipynb':       make_nb_02(),
        '03_experiment_2.ipynb':       make_nb_03(),
        '04_experiment_3.ipynb':       make_nb_04(),
        '05_experiment_4A.ipynb':      make_nb_05(),
        '06_integration.ipynb':        make_nb_06(),
    }
    for name, notebook in targets.items():
        path = NB_DIR / name
        with open(path, 'w') as fh:
            nbf.write(notebook, fh)
        print(f'wrote {path}')


if __name__ == '__main__':
    main()
