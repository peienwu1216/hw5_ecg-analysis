"""Global configuration for HW5 ECG analysis.

Constants, Task-Force HRV bands, session path mapping, anchor-baseline mapping
(which steady-state condition a transient event is compared against), and a
dispatch table selecting which orchestrator to call per experiment key.

No symlinks: paths are resolved lazily via get_session_path() so the project
is cross-platform (Windows-safe).
"""
from __future__ import annotations

from pathlib import Path

# =============================================================================
# Sampling & filtering
# =============================================================================
FS = 500                          # ECG sampling rate [Hz]
FS_GSEN = 25                      # 3-axis accelerometer sampling rate [Hz]
NOTCH_FREQ = 60.0                 # confirmed mains interference peak [Hz]
NOTCH_Q = 30.0                    # notch quality factor
BANDPASS = (0.5, 40.0)            # ECG bandpass cutoffs [Hz]
FILTER_ORDER = 4                  # Butterworth order (4th, applied as SOS + filtfilt)
# Before `FILE_INVENTORY` crop: replace the first ECG_LEADING_BASELINE_S at
# absolute file t=0 (brief ADC startup).  The fill value is the mean of the
# following ECG_LEADING_BASELINE_REF_S seconds only (local DC), not the full
# recording, to avoid a step when the trace drifts. 0 = disabled.
ECG_LEADING_BASELINE_S = 0.02
ECG_LEADING_BASELINE_REF_S = 0.5
# Two-stage median filter for baseline drift removal (Wan et al., 2006).
# Stage 1 window must exceed QRS width (~100 ms) so median ignores QRS.
# Stage 2 window captures slower drift (respiration, electrode impedance).
BASELINE_MED1_MS = 200            # first-stage median window [ms]
BASELINE_MED2_MS = 600            # second-stage median window [ms]

# =============================================================================
# QRS / RR
# =============================================================================
REFRACTORY_MS = 300               # minimum gap between R-peaks (physiological)
RR_MIN_MS = 300                   # 200 bpm ceiling for artifact rejection
RR_MAX_MS = 2000                  # 30 bpm floor for artifact rejection
# Some hardware captures show spurious 1–2 RR intervals at file start; drop them
# before HRV/HR so pre-segment means and trajectories are not pulled by outliers.
RR_DROP_LEADING = 0
INTERP_FREQ = 4.0                 # RR interpolation rate for frequency-domain HRV [Hz]

# =============================================================================
# Task Force HRV bands [Hz]
# =============================================================================
BANDS = {
    'VLF': (0.003, 0.04),
    'LF':  (0.04,  0.15),
    'HF':  (0.15,  0.40),
}

# =============================================================================
# Data paths
# =============================================================================
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = REPO_ROOT / 'data-new'
OUTPUTS_ROOT = REPO_ROOT / 'outputs'
FIGURES_DIR = OUTPUTS_ROOT / 'figures'
TABLES_DIR = OUTPUTS_ROOT / 'tables'
MANUSCRIPT_DIR = REPO_ROOT / 'manuscript'
MANUSCRIPT_NOTES_DIR = MANUSCRIPT_DIR / 'notes'
MANUSCRIPT_BUILD_DIR = MANUSCRIPT_DIR / 'build'
FIGURE_EXPORT_EXT = '.pdf'

# short key -> session folder under data-new/ (E1 folders use the same suffix as the key).
SESSION_MAP = {
    'E1A':         '20260424_165939_E1A',
    'E1B':         '20260424_170710_E1B',
    'E1C':         '20260424_171501_E1C',
    'E2A_insp_1':  '20260424_172248_E2A_insp_1',
    'E2A_insp_2':  '20260424_172917_E2A_insp_2',
    'E2B_exp_1':   '20260424_173443_E2B_exp_1',
    'E2B_exp_2':   '20260424_174141_E2B_exp_2',
    'E3_walk':     '20260424_174736_E3_walk_1',
    'E4A_12pm':    '20260424_175610_E4A_12pm',
    'E4A_9pm':     '20260424_180659_E4A_9pm',
    'E4A_6pm':     '20260424_181454_E4A_6pm',
    'E4A_5pm':     '20260424_182226_E4A_5pm',
    'E4A_3pm':     '20260424_182930_E4A_3pm',
    'E4B_sleep':   '20260424_155332_E4B',
}

# Analysis windows (start_s, end_s) relative to recording start.
# Windows drop the first ~10 s of impedance settling and then take the
# cleanest contiguous steady-state period. Durations are chosen based on
# actual recording lengths (verified 2026-04-24).
FILE_INVENTORY = {
    # Experiment 1 — E1A–C = postural ramp
    'E1A':        {'window': (10.0, 310.0), 'note': 'supine, post-sleep (repeat supine)'},
    'E1B':        {'window': (10.0, 310.0), 'note': 'sitting, 5 min (HF reference for E2/E3)'},
    'E1C':        {'window': (10.0, 310.0), 'note': 'standing, 5 min'},
    # Experiment 2 - breath holding (121 s per trial; full window)
    'E2A_insp_1': {'window': (0.0, 120.0), 'note': 'inspiratory hold trial 1'},
    'E2A_insp_2': {'window': (0.0, 120.0), 'note': 'inspiratory hold trial 2'},
    'E2B_exp_1':  {'window': (0.0, 120.0), 'note': 'expiratory hold trial 1'},
    'E2B_exp_2':  {'window': (0.0, 120.0), 'note': 'expiratory hold trial 2'},
    # Experiment 3 - seated -> walking -> seated (180 s recording)
    'E3_walk':    {'window': (0.0, 180.0), 'note': '0-60s seated, 60-120s walk, 120-180s recovery'},
    # Experiment 4A - paced breathing (240-300 s; 3/min uses longer window)
    'E4A_12pm':   {'window': (10.0, 230.0), 'note': '12/min paced breathing'},
    'E4A_9pm':    {'window': (10.0, 230.0), 'note': '9/min paced breathing'},
    'E4A_6pm':    {'window': (10.0, 230.0), 'note': '6/min paced breathing (resonance)'},
    'E4A_5pm':    {'window': (10.0, 230.0), 'note': '5/min paced breathing'},
    'E4A_3pm':    {'window': (10.0, 290.0), 'note': '3/min paced breathing (extended window, 14 cycles)'},
    # Experiment 4B - partial sleep (862 s exploratory)
    'E4B_sleep':  {'window': (0.0, 860.0), 'note': 'partial sleep-onset recording (exploratory only)'},
}

# Expected breathing rate for paced-breathing conditions, for Figure 4.3 validation.
# rate_hz = rate_per_min / 60
E4A_EXPECTED_BREATHING_HZ = {
    'E4A_12pm': 12.0 / 60.0,     # 0.200 Hz
    'E4A_9pm':   9.0 / 60.0,     # 0.150 Hz
    'E4A_6pm':   6.0 / 60.0,     # 0.100 Hz (resonance)
    'E4A_5pm':   5.0 / 60.0,     # 0.0833 Hz
    'E4A_3pm':   3.0 / 60.0,     # 0.050 Hz (below HF band)
}

# E2 segment bounds within each trial's 120 s window.
E2_SEG = {
    'pre':      (5.0,  30.0),    # skip first 5 s settling; spontaneous breathing baseline
    'hold':     (30.0, 70.0),    # breath hold (40 s)
    'recovery': (70.0, 120.0),   # post-hold recovery (50 s)
}

# E3 segment bounds within the 180 s walking recording.
E3_SEG = {
    'seated':    (0.0,   60.0),
    'walking':   (60.0,  120.0),   # HRV marked unreliable; ECG noisy from motion
    'recovery':  (120.0, 180.0),
}

# =============================================================================
# Anchor baselines (steady-state reference for transient/exploratory keys)
# =============================================================================
# Each transient / short-segment key is anchored to a posture-matched steady-state
# recording. E2 and E3 are seated -> anchor to E1B (sitting). Using E1A (supine)
# would inflate the hold HF-drop ratio because HF is higher supine than sitting, and
# would distort Finding 1 in Table 2.1. E4B is supine -> anchor to E1A
# (post-sleep supine baseline).
ANCHOR_KEYS = {
    'E2A_insp_1': 'E1B',
    'E2A_insp_2': 'E1B',
    'E2B_exp_1':  'E1B',
    'E2B_exp_2':  'E1B',
    'E3_walk':    'E1B',
    'E4B_sleep':  'E1A',
}

# =============================================================================
# Orchestrator dispatch
# =============================================================================
EXPERIMENT_TYPE = {
    'E1A': 'steady_state',  'E1B': 'steady_state',
    'E1C': 'steady_state',
    'E4A_12pm': 'steady_state', 'E4A_9pm': 'steady_state',
    'E4A_6pm':  'steady_state', 'E4A_5pm': 'steady_state',
    'E4A_3pm':  'steady_state',
    'E2A_insp_1': 'transient', 'E2A_insp_2': 'transient',
    'E2B_exp_1':  'transient', 'E2B_exp_2':  'transient',
    'E3_walk':    'transient',
    'E4B_sleep':  'exploratory',
}

# =============================================================================
# Condition order for integration notebook (06)
# =============================================================================
CONDITION_ORDER = [
    'E4A_3pm', 'E4A_6pm',               # slow paced - most parasympathetic
    'E1A',                              # supine: postural supine
    'E1B',                              # sitting baseline
    'E4A_12pm', 'E4A_9pm', 'E4A_5pm',   # other paced conditions
    'E1C',                              # standing
    'E3_walk',                          # flagged unreliable (motion)
    'E4B_sleep',                        # flagged partial
]

# =============================================================================
# Helpers
# =============================================================================
def get_session_path(key: str) -> Path:
    """Return path to the <session>/20260424/ directory (parent of hour folders).

    Example:
        get_session_path('E1A') ->
            data-new/20260424_165939_E1A/20260424/
    """
    if key not in SESSION_MAP:
        raise KeyError(f"Unknown session key: {key!r}. "
                       f"Valid keys: {sorted(SESSION_MAP)}")
    return DATA_ROOT / SESSION_MAP[key] / '20260424'


def check_freq_match(measured_hz: float, expected_hz: float,
                     rel_tol: float = 0.15, abs_tol: float = 0.015) -> bool:
    """Is `measured_hz` within tolerance of `expected_hz`?

    Used by Figure 4.3 paced-breathing validation. Relative tolerance scales
    with the expected rate so slow breathing (3/min = 0.05 Hz) is not held to
    an unachievable absolute bound; absolute floor protects against pathological
    rates near DC.

        tol = max(abs_tol, rel_tol * expected_hz)
        -> 12/min (0.200 Hz), rel=0.15: tol = 0.030 Hz
        -> 6/min  (0.100 Hz), rel=0.15: tol = 0.015 Hz (abs floor)
        -> 3/min  (0.050 Hz), rel=0.15: tol = 0.015 Hz (abs floor)
    """
    return abs(measured_hz - expected_hz) < max(abs_tol, rel_tol * expected_hz)


__all__ = [
    'FS', 'FS_GSEN', 'NOTCH_FREQ', 'NOTCH_Q', 'BANDPASS', 'FILTER_ORDER',
    'BASELINE_MED1_MS', 'BASELINE_MED2_MS',
    'REFRACTORY_MS', 'RR_MIN_MS', 'RR_MAX_MS', 'INTERP_FREQ', 'BANDS',
    'REPO_ROOT', 'DATA_ROOT', 'OUTPUTS_ROOT', 'FIGURES_DIR', 'TABLES_DIR',
    'MANUSCRIPT_DIR', 'MANUSCRIPT_NOTES_DIR', 'MANUSCRIPT_BUILD_DIR',
    'FIGURE_EXPORT_EXT', 'SESSION_MAP', 'FILE_INVENTORY',
    'E4A_EXPECTED_BREATHING_HZ', 'E2_SEG', 'E3_SEG',
    'ANCHOR_KEYS', 'EXPERIMENT_TYPE', 'CONDITION_ORDER',
    'get_session_path', 'check_freq_match',
]
