"""
Fix 5 issues in 03_experiment_2.ipynb spectrogram visualization:

1. Move annotation boxes inside the plot to avoid overlapping the panel title
2. Fix colorbar unit typo in fallback path (m² → ms²) 
3. Pass vmin=1, vmax=4.5 to plot_spectrogram_rr() for better color contrast
4. Reduce annotation font size to prevent overlap
5. Add printed note about spectrogram parameters and 15s time-shift
"""

import json
import pathlib
import sys

nb_path = pathlib.Path(__file__).resolve().parent.parent / "notebooks" / "03_experiment_2.ipynb"

with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Find the cell that contains the spectrogram plotting code
target_cell = None
target_idx = None
for idx, cell in enumerate(nb["cells"]):
    if cell["cell_type"] != "code":
        continue
    src = "".join(cell["source"])
    if "PL.plot_spectrogram_rr(" in src and "Panel C:" in src:
        target_cell = cell
        target_idx = idx
        break

if target_cell is None:
    print("ERROR: Could not find the target cell with spectrogram plotting code")
    sys.exit(1)

print(f"Found target cell at index {target_idx}")

new_source = []
changes_made = []

for line in target_cell["source"]:
    original_line = line

    # Fix 5: Add vmin/vmax to PL.plot_spectrogram_rr call
    if "f_spec, t_spec, Sxx, ax=ax_spec, log_scale='log10'" in line:
        line = line.replace(
            "f_spec, t_spec, Sxx, ax=ax_spec, log_scale='log10'",
            "f_spec, t_spec, Sxx, ax=ax_spec, log_scale='log10',\n        vmin=1, vmax=4.5,"
        )
        changes_made.append("Issue #5: Added vmin=1, vmax=4.5 to plot_spectrogram_rr()")

    # Fix 2: Fix colorbar unit typo in fallback path
    if "_cb.set_label('log10(PSD)  (m\u00b2/Hz)')" in line:
        line = line.replace("(m\u00b2/Hz)", "(ms\u00b2/Hz)")
        changes_made.append("Issue #2: Fixed colorbar unit typo m²→ms² in fallback path")

    # Fix 1: Move annotations inside the plot (change y from 1.01 to 0.93)
    # and change va from 'bottom' to 'top'
    if "fontsize=6.5, ha='center', va='bottom'" in line:
        line = line.replace("fontsize=6.5, ha='center', va='bottom'", 
                           "fontsize=6, ha='center', va='top'")
        changes_made.append("Issue #1: Reduced annotation font size and changed va to 'top'")

    if "1.01, 'Onset (30 s)'" in line:
        line = line.replace("1.01, 'Onset (30 s)'", "0.93, 'Onset (30 s)'")
        changes_made.append("Issue #1: Moved Onset annotation inside plot area (y=0.93)")

    if "1.01, 'Release (70 s)'" in line:
        line = line.replace("1.01, 'Release (70 s)'", "0.93, 'Release (70 s)'")
        changes_made.append("Issue #1: Moved Release annotation inside plot area (y=0.93)")

    new_source.append(line)

# Fix 3 & 4: Add printed note about spectrogram parameters after the last print statement
# Find the last line (the print with verification summary) and add notes after it
final_source = []
for i, line in enumerate(new_source):
    final_source.append(line)
    if 'print(f"Verification Summary: HF dropped to' in line:
        # Add note about spectrogram window parameters (Issue #4) and 15s start (Issue #3)
        final_source.append('print()\n')
        final_source.append('print("Note: Spectrogram (Panel C) computed with Hann window, 30 s length, ")\n')
        final_source.append('print("83.3% overlap (noverlap = 25 s). The spectrogram starts at t ≈ 15 s ")\n')
        final_source.append('print("due to the half-width of the first window; color scale clipped to ")\n')
        final_source.append('print("log10(PSD) ∈ [1, 4.5] for improved LF/HF band contrast.")\n')
        changes_made.append("Issue #3: Added note about 15s spectrogram start time")
        changes_made.append("Issue #4: Added window parameter documentation (Hann, 30s, 83.3% overlap)")

target_cell["source"] = final_source

# Clear outputs since cell source changed
target_cell["outputs"] = []
target_cell["execution_count"] = None

# Write back
with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\nApplied {len(changes_made)} changes:")
for c in changes_made:
    print(f"  ✓ {c}")
print(f"\nNotebook saved to {nb_path}")
