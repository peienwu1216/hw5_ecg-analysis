# Revision Plan — Add the Activity/Motion Fusion Channel to the LF/HF Final Project

**For:** Claude Code agent operating in the ECG analysis repo
**Manuscript:** the *final project* paper "When Should the LF/HF Ratio Be Used as an Autonomic-Balance Metric in Wearable ECG?" (NOT the HW5 lab report — the HW5 report is the source you mine for data/code).
**Author intent:** owner is iterating on this in response to specific advisor feedback. Read the "Why" section before touching anything; the strategic framing is the point, not just the edits.

---

## 0. Why this revision exists (read first)

The advisor's email asked for two things, in increasing importance:
1. Recheck the criteria in Billman [5] and Laborde [6] against short-term recordings. **Already done** in §3–§4.
2. The "shining point": *"breathing and activities (Actigraph) can be separately estimated, so a fusion of the measurements with HRV can potentially remedy the parasympathetic link."*

§5 / §5.1 already implements **half** of point 2 — the **breathing channel**: the IMU confirms the respiratory frequency, and migrated RSA power is reassigned out of LF back to the vagal pool (`LF/HF_corr = LF_res / (HF + RSA_LF)`). This is the literal "remedy the parasympathetic link."

The **other half — the activity/Actigraph channel — already exists fully analyzed in the HW5 report (Experiment 3, walking)** but was cut from the final project as "not the main line." That cut is the thing we are reversing. The walking analysis is the only empirical instance of the Actigraph half the advisor named by name, and it completes the fusion story instead of leaving it at 50%.

**The unifying idea the new content must express** (this is the whole reason the revision is worth doing — do not lose it):

> The IMU is a **context sensor for HRV**, and IMU↔HR coherence is the **decision variable** that tells you which of two actions to take on a suspect spectral component.
>
> - **High coherence** (paced slow breathing, Cxy ≈ 0.69–0.89): the RR oscillation *is* respiration → the power is identifiable, structured RSA → **CORRECT** it (reassign LF→vagal). → §5.1, done.
> - **Low coherence + spectral overlap** (walking, Cxy ≈ 0.04–0.06, step 1.46 Hz vs cardiac f0 1.38 Hz): motion did *not* lock a clean narrowband line into the cardiac rhythm, **but** low coherence does not exclude broadband artifact, and the step/cardiac bands overlap so linear filtering cannot separate them → the power is *not* a removable, reassignable component → **GATE** it (mark fine-scale HRV motion-limited, exclude from cross-condition comparison). → new §5.2.

Same instrument, same coherence test, opposite verdict, opposite action. Both verdicts protect the parasympathetic readout: §5.1 by *reassignment*, §5.2 by *invalidation* (preventing a motion-corrupted RMSSD/HF from being reported as vagal tone).

**Precision warning for the prose:** do NOT collapse this into "high coherence = keep, low coherence = drop." In walking, low coherence at the step frequency is mildly *reassuring* (no coherent artifact line to subtract); the reason we gate anyway is the *combination* of (a) step–cardiac spectral overlap that filtering can't resolve and (b) inability to exclude broadband motion artifact. Coherence diagnoses the *type* of cross-channel coupling and therefore the right *action* — it is not a simple quality threshold. The advisor will catch a sloppy version of this.

---

## 1. Ground truth (verify against repo before using — do not trust these transcribed numbers blindly)

These are read off the PDFs and may contain transcription error. **Locate the actual computed values in the HW5 codebase/data and use those.** If any differ from below, the repo wins; flag the discrepancy in your summary.

**Activity/walking channel (the new §5.2 material):**
- Step frequency ≈ 1.46 Hz (88 steps/min); walking cardiac fundamental f0 ≈ 1.38 Hz → overlap band ~1–3 Hz, unresolvable by linear filtering.
- Magnitude-squared coherence at step peak Cxy ≈ 0.04; 1–3 Hz band-mean Cxy ≈ 0.06.
- Correlation |ΔRR| vs accelerometer magnitude r ≈ 0.26 (weak).
- Motion RMS: seated ≈ 0.036 g, walking ≈ 0.103 g, recovery ≈ 0.042 g.
- HR: seated 60.8 → walking 83.0 → recovery 70.3 bpm; recovery τ ≈ 6.8 s; HRR60 ≈ 18.5 bpm.
- Walking RMSSD ≈ 41.1 ms — reported but explicitly NOT used as a cross-condition comparator.

**Breathing channel (already in §5 — do not change, cited for the symmetry):**
- IMU–HR coherence Cxy ≈ 0.69–0.89 (excluding 12/min), peak r ≈ 0.76–0.94.
- 12/min is SNR-limited (r ≈ 0.37, Cxy ≈ 0.22): fast shallow breathing → weak chest displacement.

**Do not alter** the LF/HF headline numbers (0.22→17.46 naive; corrected ≤1.05), the postural positive control, or any §3 result.

---

## 2. Tasks

Work in order. Each task has acceptance criteria. Make atomic commits per task.

### Task A — Locate and orient (no edits yet)
- Find the final-project manuscript source (LaTeX `.tex`, likely separate from the HW5 report `.tex`). Confirm current section structure matches: §5 Multi-Sensor Respiratory Validation → §5.1 Fusion-Based Recovery → §6 Checklist (Table 3) → §7 Limitations → §8 Conclusion.
- Find the HW5 Experiment-3 (walking) analysis code and its output figures/numbers (accelerometer magnitude, step-frequency PSD, Cxy, |ΔRR|–motion correlation). Identify what is reusable as-is.
- Report back the file map and the verified walking numbers before proceeding. **Do not guess section numbers or filenames — confirm them.**

### Task B — Add §5.2 "Activity-Channel Gating of HRV Validity" (the core addition)
Insert a new subsection after §5.1, before §6. Target length: roughly half a page of prose + one figure + (optional) one or two summary rows. Keep it tight; this is a focused extension, not a new experiment write-up.

Content requirements (express in the author's own prose — the §0 idea, made precise):
- State the dual role: the IMU's respiratory channel (§5.1) recovers migrated RSA; its **activity channel** does the complementary job — flags when a segment's HRV is motion-corrupted and should not be read autonomically.
- Present the walking evidence: motion RMS rises ~3× seated→walking; step frequency 1.46 Hz sits ~6% from cardiac f0 1.38 Hz (overlap, filtering can't separate); coherence at the step peak is low (Cxy ≈ 0.04), and |ΔRR|–motion correlation is weak (r ≈ 0.26).
- Make the verdict precise (per the precision warning in §0): low step-band coherence rules out a coherent narrowband artifact line, but does **not** exclude broadband artifact; combined with the step–cardiac overlap, walking-phase fine-scale HRV (RMSSD, HF) is treated as **motion-limited** and excluded from cross-condition comparison, while mean HR and recovery kinetics (τ) remain interpretable.
- Close with the synthesis: IMU↔HR coherence is the shared decision variable — high coherence licenses *reassignment* (§5.1), low coherence + band overlap licenses *gating* (§5.2). Together this is the respiration-aware **and** motion-aware HRV pipeline the fusion was aiming at.

**Figure for §5.2** — reuse HW5 walking-analysis plotting code; do not recompute from raw unless necessary. Minimum content:
- (a) accelerometer magnitude across seated/walk/recovery with the RMS envelope, and
- (b) the step-vs-cardiac spectral overlap (ECG PSD with f0 marked + accelerometer PSD with the 1.46 Hz step peak), annotated with Cxy.
Match the visual style of the existing figures in the final project. Renumber subsequent figures/refs as needed and update all `\ref`/`\label`.

Acceptance: §5.2 reads as the symmetric partner to §5.1; the coherence-as-decision-variable framing is explicit and correctly nuanced; numbers match the repo; figure renders and is referenced; the paper still compiles.

### Task C — Upgrade the Context-Aware Checklist (Table 3, §6) to dual-channel
The current table has columns roughly: Context | Preferred metrics | LF/HF use | Respiratory sensing. Restructure so it carries **both gating functions** — the respiratory channel (reassignment) and the activity channel (invalidation). Concretely:
- Add/relabel a column so each row shows whether **activity/motion gating** applies, alongside the existing respiratory-sensing column.
- The Walking row must change from a near-empty "Recommended" cell into a worked example of activity-channel gating: primary metrics = mean HR, recovery τ; fine-scale HRV = motion-gated/invalid; motion sensing = required.
- Keep the existing breathing rows; ensure the slow-breathing rows still point to RMSSD / resp.-centered power and "no standalone LF/HF."
- Breath-hold: a single row is fine (optional note: IMU during a hold should register *absence* of respiratory motion, which could distinguish true apnea from shallow breathing — mark as nice-to-have, do not build it out).

Acceptance: the checklist visibly encodes two gating axes; walking is no longer an unsupported orphan row; table compiles and fits the column layout.

### Task D — Tone / epistemic calibration (small but important)
The advisor explicitly framed this as "limited samples → cannot derive strong conclusion → interesting observations." Single-subject results cannot carry prescriptive "should/guidance" language. Apply, lightly, throughout abstract / §6 / conclusion:
- Reframe the checklist as *a proposed reporting framework motivated by this single-subject case and the literature*, not established guidance. Soften categorical "should" by one notch where it reads as a directive to the field.
- Fix the abstract oversell: "near-flat corrected ratio" is inaccurate (corrected spans 0.22–1.04, ~5× spread). Reword to something like "the corrected ratio no longer crosses unity" / "removes the cross-boundary inflation." Keep the ≤1.05 fact.

Acceptance: no remaining claim implies population-level guidance from n=1; the corrected-ratio description is numerically honest.

### Task E — Three targeted argument upgrades (cheap, high-value)
1. **9/min boundary rationale.** Add one explicit sentence in §5.1 (or wherever the 9/min case is handled): the band assignment is decided by the RR-PSD argmax within the IMU-anchored window, **not** by the IMU peak directly, *because the quantity being reassigned is RR power* — the IMU's role is only to anchor the search window, so the RR spectrum itself must adjudicate which band the power belongs to. This pre-empts the obvious viva question ("why hand the final call back to RR-PSD after going to the trouble of an independent respiratory reference?").
2. **Phase → mechanism.** The monotonic phase decrease (+84°→−6° across 9→3/min) and the ~1.4 s mean lag are currently presented as two separate observations. Connect them: phase = lag/T, so a roughly *fixed* reflex lag (~1.4 s, within the 1–3 s RSA latency range) *necessarily* produces a falling phase as the breathing period grows. State this so the monotonic phase trend becomes mechanistic evidence of genuine RSA coupling rather than a descriptive curiosity. Verify the arithmetic (lag/period → phase) against the actual per-rate numbers before asserting it.
3. **Criterion 2 ceiling.** Where the paper concedes it cannot isolate the baroreflex/sympathetic contribution to LF, add one sentence stating that fully resolving Billman's second criterion requires an independent sympathetic measure (e.g., blood pressure for baroreflex, or pre-ejection period), which is beyond a single-lead ECG + IMU setup. This shows awareness of the method ceiling rather than evading it.

Acceptance: all three are single-sentence-scale additions, factually checked, integrated into existing paragraphs (not bolted on as a list).

---

## 3. Non-goals / scope guard (do not do these)
- Do **not** re-expand the postural (E1) analysis beyond its current positive-control role.
- Do **not** import the full breath-hold (E2) experimental section into the final project. One checklist row only.
- Do **not** touch §3 LF/HF results or any headline number.
- Do **not** balloon the paper. Net addition target: ~half page of prose + one figure + the table upgrade + ~3 sentences from Task E. If a change makes the main line longer without strengthening it, drop it.
- Do **not** invent data. If a number isn't in the repo, say so; don't fill it from the PDF transcription in §1.

---

## 4. Order of operations
1. Task A (orient + verify numbers) → report file map and verified values.
2. Task B (§5.2 + figure).
3. Task C (checklist).
4. Tasks D and E (wording + argument upgrades) — can batch.
5. Build the PDF; fix any cross-reference / float / numbering breakage.
6. Final pass: re-read §5→§6→conclusion end-to-end to confirm the two-channel narrative is coherent and the epistemic level matches "interesting observations from a single-subject case."

## 5. Deliverable on completion
- The updated manuscript source + compiled PDF.
- A short changelog: what was added/changed per task, which numbers were verified against the repo, and any discrepancies found vs the §1 transcription.
- A flag list of anything you were unsure about or had to assume.