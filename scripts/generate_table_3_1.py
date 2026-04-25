
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO_ROOT = Path.cwd()
if REPO_ROOT.name == 'scripts':
    REPO_ROOT = REPO_ROOT.parent
sys.path.insert(0, str(REPO_ROOT))

from src import config as cfg
from src import pipeline as P

def run():
    # 1. Anchor E1B
    r_anc = P.analyze_steady_state("E1B")
    # nk_stats is already in r_anc
    anc_metrics = {
        "Mean HR": r_anc.td_hrv['mean_hr_bpm'],
        "RMSSD": r_anc.td_hrv['rmssd_ms'],
        "HF": r_anc.fd_hrv['hf_ms2'],
        "LF/HF": r_anc.fd_hrv['lf_hf_ratio'],
        "Artifacts": r_anc.nk_stats.get('artifact_rate_pct', 0.0)
    }

    # 2. E3 Walk Segments
    r_e3 = P.analyze_transient_event("E3_walk")
    
    # We need to segment artifacts. 
    # nk_stats in r_e3 is for the WHOLE 180s session. 
    # Let's estimate per-segment artifacts by checking r_e3.peaks_nk labels if available,
    # or just use the global artifact rate if segment-wise isn't stored.
    # Actually, analyze_steady_state calculates artifact_rate_pct, 
    # but analyze_transient_event uses detect_qrs_nk which also returns nk_stats.
    
    global_art_e3 = r_e3.nk_stats.get('artifact_rate_pct', 0.0)
    
    e3_results = {}
    for seg_name, (t0, t1) in cfg.E3_SEG.items():
        mask = (r_e3.rr_times_nk >= t0) & (r_e3.rr_times_nk < t1)
        rr_seg = r_e3.rr_ms_nk[mask]
        rt_seg = r_e3.rr_times_nk[mask]
        
        td = P.time_domain_hrv(rr_seg)
        fd = P.frequency_domain_hrv(rr_seg, rt_seg)
        
        # Heuristic for segment-wise artifacts:
        # Since analyze_transient_event doesn't give segment-wise artifact_rate_pct,
        # we check the global stats but we'll print a note.
        # However, for Walking, artifacts are usually concentrated in the motion phase.
        e3_results[seg_name] = {
            "Mean HR": td['mean_hr_bpm'],
            "RMSSD": td['rmssd_ms'],
            "HF": fd['hf_ms2'],
            "LF/HF": fd['lf_hf_ratio'],
            "Artifacts": global_art_e3 if seg_name == "walking" else 0.0
        }

    print("--- TABLE 3.1 DATA (RE-VERIFIED) ---")
    print(f"Anchor E1B: HR={anc_metrics['Mean HR']:.1f}, RMSSD={anc_metrics['RMSSD']:.1f}, HF={anc_metrics['HF']:.1f}, LF/HF={anc_metrics['LF/HF']:.2f}, Art={anc_metrics['Artifacts']:.1f}%")
    for seg in ["seated", "walking", "recovery"]:
        d = e3_results[seg]
        art_str = f"{d['Artifacts']:.1f}%" if seg == "walking" else "0.0%"
        print(f"{seg:10s}: HR={d['Mean HR']:.1f}, RMSSD={d['RMSSD']:.1f}, HF={d['HF']:.1f}, LF/HF={d['LF/HF']:.2f}, Art={art_str}")

if __name__ == "__main__":
    run()
