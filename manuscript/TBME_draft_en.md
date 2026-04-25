# Cardiorespiratory Dynamics Across Posture, Voluntary Breath-Hold, Walking, and Paced Breathing: A Single-Lead ECG Multiexperiment Study

## Abstract

This study analyzed 15 repeated-measures single-lead electrocardiographic recordings from one participant across postural baselines, voluntary breath-hold, walking, paced breathing, and a partial sleep-onset segment to build a context-aware framework for heart rate variability interpretation. Electrocardiographic signals sampled at 500 Hz were processed using baseline-drift suppression, 50-Hz notch filtering, 0.5-40-Hz bandpass filtering, and dual-path R-peak detection with both a teaching scipy path and a NeuroKit2 reference path. Postural baseline data showed a physiologically coherent autonomic axis: mean heart rate increased and respiratory-linked variability decreased from supine to standing. Inspiratory breath-hold produced a larger chronotropic response than expiratory breath-hold, whereas expiratory recovery showed the strongest vagal rebound. Walking raised mean heart rate to 83.0 bpm and yielded a recovery time constant of 6.8 s, but walking-phase fine-scale variability remained motion-limited. Paced breathing was the strongest controlled manipulation: the RR spectral peak tracked imposed breathing frequency with high fidelity (R² = 0.998). However, slow breathing inflated LF/HF without parallel collapse of RMSSD, indicating spectral-band migration rather than straightforward sympathovagal reversal. Moreover, the classical inverted-U resonance peak at 6 breaths/min was not observed; RR amplitude continued to rise at 3 breaths/min. These findings show that heart rate variability metrics must be interpreted within the validity limits imposed by the physiological task, time scale, and frequency boundary assumptions.

## Index Terms

Heart rate variability, single-lead electrocardiography, paced breathing, voluntary breath-hold, walking challenge, autonomic regulation

## I. Introduction

Heart rate variability (HRV) is widely used as a surrogate marker of autonomic regulation, yet its interpretation depends critically on the physiological context, the duration of the analyzed segment, and whether the assumptions underlying time- and frequency-domain metrics remain valid. A scalar HRV index may appear portable across tasks, but the mechanism that generates variability during posture, exercise, breath-hold, and slow paced breathing is not the same. In particular, LF/HF becomes problematic when respiration is intentionally slowed, because the dominant respiratory oscillation can cross the conventional 0.15-Hz boundary and migrate from the HF band into LF.

The present study addresses this problem using a repeated-measures, single-participant dataset that spans five distinct physiological paradigms within one coherent analysis pipeline: 1) postural baseline recordings, 2) inspiratory and expiratory breath-hold trials, 3) a short walking challenge with recovery, 4) five paced-breathing conditions, and 5) a partial sleep-onset appendix recording. This design makes it possible to ask a set of linked questions rather than treating each experiment as an isolated demonstration:

1. Does posture define a stable autonomic reference axis?
2. Are breath-hold effects purely physiological, or are they materially confounded by conscious effort?
3. Which walking-derived metrics remain interpretable under motion contamination?
4. Does paced breathing accurately entrain the RR spectrum, and if so, does its main effect appear as heart-rate reduction, band redistribution, or amplitude expansion?
5. Which metrics remain robust when all experiments are synthesized into one manuscript?

The contribution of this paper is threefold. First, it provides an end-to-end ECG analysis framework that connects quality control, pipeline validation, experiment-specific readouts, and cross-experiment synthesis. Second, it shows that different tasks require different interpretive spaces: posture is best understood as a steady-state autonomic set-point shift, breath-hold and walking as challenge-recovery trajectories, and paced breathing as a manipulation of cardiorespiratory oscillation amplitude and spectral location. Third, it reports a paced-breathing finding that departs from the simplified resonance narrative: within the tested range, the largest RR oscillations occurred at 3 breaths/min rather than at a clear 6-breaths/min peak.

## II. Materials and Methods

### A. Study Design and Dataset

This was a single-participant repeated-measures physiological study comprising 15 ECG recordings. ECG was sampled at 500 Hz, and triaxial accelerometry was sampled at 25 Hz. Because all recordings came from the same acquisition chain and were processed with a unified pipeline, between-condition differences primarily reflect task-dependent physiology rather than instrumentation changes.

The dataset contained five experiment families. `E1PRE` was a pre-sleep supine recording used for pipeline validation and as an exploratory anchor for the sleep appendix. `E1A`, `E1B`, and `E1C` formed the postural baseline sequence (supine, sitting, standing). `E2A_insp_1/2` and `E2B_exp_1/2` were inspiratory and expiratory breath-hold trials, each repeated twice; in the notebook workflow, the first repetition was treated as relatively effortful and the second as relatively relaxed. `E3_walk` was a 180-s record segmented into seated, walking, and recovery periods. `E4A_12pm/9pm/6pm/5pm/3pm` were five fixed paced-breathing conditions, with the 3-breaths/min condition extended to ensure sufficient cycles. `E4B_sleep` was incomplete and was kept for appendix use only.

An important design limitation is that the paced-breathing conditions were presented in a fixed descending order (12 → 9 → 6 → 5 → 3 breaths/min) rather than in randomized order. Any progressive training, relaxation, fatigue, or vigilance drift is therefore inseparable from the slow-breathing manipulation and must be acknowledged explicitly in the interpretation.

### B. Signal Processing Pipeline

All ECG analysis was performed through `src/pipeline.py`. Raw ECG was first corrected for baseline drift with a two-stage median filter, then filtered with a 50-Hz notch and a 0.5-40-Hz Butterworth bandpass. R-peaks were detected with two paths: a teaching scipy implementation broadly faithful to the Pan-Tompkins logic [2], and a NeuroKit2-based reference path with Kubios-style peak correction. The main results emphasized the NeuroKit2 path because of its more stable artifact correction, whereas the validation notebook demonstrated near-complete agreement between paths on the steady-state recordings.

RR intervals were computed from successive R-peaks. For steady-state recordings, time-domain indices included mean HR, SDNN, RMSSD, and pNN50. Frequency-domain HRV was obtained from linearly detrended, cubically interpolated RR series resampled at 4 Hz and analyzed with Welch power spectral density using Task Force bands [1]. For transient tasks (`E2`, `E3`), the individual phases were too short for conventional frequency-domain reporting; therefore, the main transient readouts were mean HR, RMSSD, min/max HR, and the slope of the HR trajectory. Frequency-domain comparison in `E2` was instead performed through pooled spectral averaging against the seated `E1B` anchor.

### C. Figure and Table Logic, Placement, and Evidentiary Role

The manuscript is intentionally organized so that each figure and table answers a specific question instead of merely illustrating the text.

- **Fig. 1 + Table I** belong at the start of Section III-A.  
  Question: Does orthostatic loading create a coherent autonomic baseline axis?  
  Claim: The supine-to-standing sequence provides the physiological reference needed for later seated and respiratory comparisons.

- **Fig. 2 + Tables II–III** belong in Section III-B.  
  Question: Are breath-hold findings purely physiological, or are they materially shaped by conscious effort?  
  Claim: Inspiratory and expiratory breath-hold differ, and trial state (effortful versus relaxed) changes the observed response.

- **Fig. 3 + Table IV** belong in Section III-C.  
  Question: Which walking-induced changes are physiologically meaningful and which are motion-limited?  
  Claim: Mean HR and recovery kinetics remain informative, whereas walking-phase fine-scale HRV requires an explicit validity caveat.

- **Figs. 4–7 + Table V** belong in Section III-D and carry the main paper narrative.  
  Questions: Does paced breathing entrain the RR spectrum? Do measured peaks track the metronome? Does LF/HF remain interpretable under slow breathing? Is there a classical 6-breaths/min resonance peak?  
  Claim: The manipulation is real, the frequency tracking is precise, LF/HF becomes band-shifted under slow breathing, and no clear inverted-U resonance maximum is observed within the tested range.

- **Figs. 8–9 + Table VI** belong in Section III-E.  
  Question: How should steady-state, transient, and respiratory-control experiments be integrated without forcing them into one invalid summary metric?  
  Claim: Cross-experiment synthesis is stronger when it uses mean HR, RMSSD, total power, and validity notes rather than treating LF/HF as a universal axis.

- **Supplementary and appendix figures** remain important but should not dominate the main text.  
  These include data-quality overview, pipeline validation, extended signal-processing visuals, and the partial sleep trajectory.

### D. Statistical and Reporting Strategy

Postural and paced-breathing conditions were treated as steady-state tasks and were reported with full HRV scalar summaries. `E2` and `E3` were described as transient trajectories using regime-based mean HR, RMSSD, extrema, and HR slope. Paced-breathing frequency tracking was summarized with linear regression, 95% confidence intervals, residual standard deviation, and tests of the null hypotheses `slope = 1` and `intercept = 0`. Because only five paced conditions were available, confidence intervals are necessarily wide; the interpretation therefore emphasizes effect size, visual agreement, and physiological coherence rather than overconfident formal inference.

## III. Results

### A. Postural Baseline Established a Physiologically Coherent Autonomic Reference Axis

The postural experiment served as the anchor for the rest of the manuscript. In the supine condition (`E1A`), mean HR was 54.0 bpm, RMSSD was 99.1 ms, and HF power was 3252.8 ms². In the sitting condition (`E1B`), mean HR increased to 56.1 bpm while RMSSD dropped to 61.1 ms and HF power to 1122.6 ms². In the standing condition (`E1C`), mean HR rose further to 79.7 bpm, RMSSD fell to 25.2 ms, HF power fell to 310.7 ms², and LF/HF increased to 1.44. The direction of change was internally consistent and physiologically plausible, indicating vagal withdrawal with progressive orthostatic loading.

Fig. 1 should be placed at the beginning of this subsection because it answers the first experimental question directly: whether posture creates a monotonic redistribution of RR dynamics in both the time and frequency domains. Table I should follow immediately as the quantitative summary. The importance of this section is not only that Experiment 1 worked as expected, but also that it justifies the use of the seated `E1B` recording as the posture-matched anchor for the breath-hold and walking experiments.

`[Place Fig. 1 and Table I near here]`

### B. Breath-Hold Effects Reflected Both Respiratory Physiology and Conscious Effort

The central question in Experiment 2 was not merely whether breath-hold perturbs HRV, but whether the observed perturbation is confounded by voluntary effort. Across the inspiratory breath-hold trials, pre-hold HR was 62.9 and 59.2 bpm, whereas hold-phase mean HR rose to 66.9 and 73.5 bpm, corresponding to ΔHR values of +4.0 and +14.3 bpm. In contrast, expiratory breath-hold trials showed smaller hold-phase shifts, with mean HR of 57.8 and 60.8 bpm. This already suggested that inspiratory hold imposed a stronger chronotropic challenge and that trial state mattered.

The pooled frequency-domain comparison completed the picture. Relative to the seated `E1B` anchor HF value of 1124.0 ms², inspiratory hold pooled HF fell to 94.0 ms², an approximately 12-fold reduction. Expiratory hold pooled HF was 391.3 ms², indicating a smaller suppression. Recovery was not symmetric: inspiratory recovery pooled HF increased to 1551.3 ms², whereas expiratory recovery rose to 1951.6 ms², corresponding to 1.38× and 1.74× the seated anchor, respectively. Thus, the breath-hold experiment should be interpreted as a suppression-plus-rebound system rather than a one-way vagal reduction.

Fig. 2 belongs here because it addresses the key interpretive question of this section: whether effort changes the shape of the breath-hold response. Table II provides the trial-level time-domain comparison, and Table III carries the pooled spectral evidence. If space permits, the isolated HF-collapse verification figure may be retained as supplementary support, but the main text should emphasize the interaction between respiratory mode and effort rather than repeating the fact of HF reduction alone.

`[Place Fig. 2, Table II, and Table III near here]`

### C. Walking Revealed a Real Cardiovascular Load but Required a Motion-Aware Validity Framework

Experiment 3 was intentionally not a clean steady-state HRV task. Its value lies in combining physiological challenge with explicit motion contamination. During the seated phase, mean HR was 60.8 bpm and RMSSD was 54.4 ms. During walking, mean HR rose to 83.0 bpm and RMSSD fell to 41.1 ms. During recovery, mean HR fell back to 70.3 bpm, and the fitted recovery time constant was 6.8 s. These values clearly support an acute exercise-load interpretation.

However, the walking phase should not be treated as directly equivalent to posture or paced breathing. The multimodal fusion between accelerometry and RR behavior showed that walking contained identifiable motion-driven signal contamination; accordingly, the walking-phase HRV estimate was explicitly marked as unreliable in the summary table. The correct conclusion is therefore not that walking simply “reduced HRV,” but that walking produced a genuine HR rise while limiting the interpretability of fine beat-to-beat variability metrics.

Fig. 3 should be placed here because it directly visualizes both the physiological response and its measurement limitation. Table IV then supplements the figure with mean HR, RMSSD, and the recovery tau. Signal-processing snapshots, ECG PSD comparisons, and RR spectral contrasts are valuable support, but they are better suited to supplementary material.

`[Place Fig. 3 and Table IV near here]`

### D. Paced Breathing Precisely Shifted the RR Spectral Peak but Did Not Support a Classical 6-Breaths/Min Resonance Maximum

Experiment 4A was the strongest controlled dose-response component of the study and the central result of the paper. First, the paced-breathing manipulation was demonstrably effective. The measured RR spectral peaks were 0.2031, 0.1484, 0.1016, 0.0859, and 0.0469 Hz for the 12, 9, 6, 5, and 3 breaths/min conditions, respectively. Linear regression yielded a slope of 1.022 (95% CI: 0.947–1.097), an intercept of -0.0020 (95% CI: -0.0116 to 0.0076), an R² of 0.998, and a residual standard deviation of 0.0028 Hz. Figs. 4 and 5 therefore establish that the visual peak migration is quantitatively real rather than a display artifact.

Second, the principal effect of slow breathing was amplitude expansion rather than strong heart-rate reduction. Mean HR remained in a narrow range from 57.0 to 60.1 bpm across all paced conditions. In contrast, SDNN rose from 48.7 ms at 12 breaths/min to 131.4 ms at 3 breaths/min, total power rose from 1754.3 to 10493.1 ms², and RR amplitude (`p95-p5`) increased from 156.5 to 405.5 ms. Thus, slow breathing in this dataset primarily altered the magnitude of the oscillation, not the mean chronotropic operating point.

Third, LF/HF was not interpretable as a direct sympathovagal summary under slow breathing. LF/HF increased from 0.22 at 12 breaths/min to 11.54 at 6 breaths/min and remained near 17.45–17.47 at 5 and 3 breaths/min. Yet RMSSD did not collapse in parallel; it stayed in the range of approximately 48–65 ms. This dissociation indicates that slow breathing relocated the respiratory peak into LF and thereby inflated LF/HF through spectral-band migration. Fig. 6 should therefore be framed explicitly as a demonstration of metric failure under a violated frequency-boundary assumption, not as evidence of autonomic reversal.

Finally, Fig. 7 answers the most easily overinterpreted question in the manuscript: whether a classical 6-breaths/min resonance peak was present. In this participant, the answer is no. RR amplitude and SDNN continued to increase down to 3 breaths/min rather than forming a clear inverted-U shape centered at 6 breaths/min. Although the NeuroKit2 P2T measure showed an earlier local maximum, that metric likely underestimates very slow breathing and should not override the directly observed RR-amplitude trend. The correct statement for the draft is therefore explicit: the classical inverted-U resonance peak was not observed within the tested range.

`[Place Figs. 4–7 and Table V near here]`

### E. Cross-Experiment Synthesis Showed That Different Tasks Require Different Summary Spaces

The integration section answered a methodological question that the individual experiments alone could not resolve: how should posture, breath-hold, walking, and paced breathing coexist in one coherent manuscript? The revised synthesis rejected the idea that every experiment should be ranked on a single frequency-domain axis. Fig. 8 showed that posture primarily moved the autonomic system along a trajectory of higher HR and lower RMSSD, whereas paced breathing maintained nearly stable mean HR while strongly expanding total power and SDNN. These are fundamentally different types of physiological change.

Fig. 9 then placed `E2`, `E3`, and the exploratory `E4B` appendix into a challenge-recovery space. Inspiratory breath-hold showed the stronger HR rise from pre-hold to hold. Expiratory recovery showed the largest RMSSD rebound. Walking pushed mean HR to 83.0 bpm and was followed by a recovery tau of 6.8 s. The partial sleep segment showed a smoothed HR decrease of 2.6 bpm over 14.3 min, ending close to the `E1PRE` anchor; this pattern was directionally plausible but remained too incomplete for main inferential use. Table VI served as the manuscript-level synthesis because it summarized family, phase, HR, RMSSD, total power, validity notes, and synthesis notes in one unified structure.

The scientific message of this section is direct: posture, breath-hold, walking, and paced breathing do not measure the same kind of “HRV magnitude.” A robust cross-experiment manuscript should allow different physiological tasks to be interpreted in the summary space that best preserves validity rather than forcing all conditions into one invalid scalar ranking.

`[Place Figs. 8–9 and Table VI near here]`

## IV. Discussion

The central message of this paper is that HRV interpretation must be coupled to the experimental manipulation. Experiment 1 mapped an autonomic set-point axis: posture changed HR and vagally linked metrics in the expected direction. Experiment 2 exposed the interaction between respiratory perturbation and conscious effort: inspiratory and expiratory breath-hold did not produce the same response, and trial state altered the apparent magnitude of the effect. Experiment 3 demonstrated that ambulatory recordings can still yield valid mean-HR and recovery information even when fine HRV metrics are motion-limited. Experiment 4A showed that paced breathing changes spectral location and oscillation amplitude more than mean heart rate, and that conventional LF/HF interpretation becomes unreliable once breathing is slowed below the HF boundary.

Accordingly, this manuscript is not merely a report of several HRV tasks; it is an argument about how HRV should be read. LF/HF can still serve as a secondary descriptor under ordinary short-term resting conditions, but it should not remain the dominant cross-experiment thesis metric once the respiratory peak is deliberately displaced. This is why the integration notebook was redesigned around mean HR, RMSSD, total power, and explicit validity notes rather than around a global LF/HF ranking.

The paced-breathing results deserve particular emphasis. Classical resonance-biofeedback narratives often imply that ~6 breaths/min should maximize oscillation amplitude. That simplified picture was not supported here. The largest RR oscillations were observed at 3 breaths/min, not at a sharply defined 6-breaths/min maximum. This does not invalidate the resonance concept, but it does show that “maximum amplitude,” “maximum HF power,” and “maximum within-band metric value” are not interchangeable statements.

## V. Limitations

This study has at least four limitations. First, it is a single-participant repeated-measures study; therefore, the paper is strongest as a mechanism-oriented and methods-oriented case study rather than a population-level inference. Second, the paced-breathing sequence was fixed in descending order and not randomized, so training, relaxation, fatigue, or vigilance drift may partly contribute to the monotonic slow-breathing trend. Third, the walking segment was motion-contaminated, and the walking-phase HRV metrics must be interpreted with an explicit validity caveat. Fourth, the sleep recording was incomplete and can support only an appendix-level trend statement.

Future work should expand the sample size, randomize or counterbalance paced-breathing order, and include a direct respiratory belt signal to validate ECG-derived respiration and RSA metrics under very slow breathing.

## VI. Conclusion

Using a unified ECG analysis pipeline across posture, voluntary breath-hold, walking, paced breathing, and a partial sleep-onset recording, this study shows that different physiological tasks modulate different aspects of cardiorespiratory regulation. Posture primarily changes the autonomic operating point. Breath-hold and walking reveal transient challenge and recovery dynamics. Paced breathing primarily alters oscillatory amplitude and spectral location. The most important methodological conclusion is therefore that HRV metrics cannot be interpreted independently of the physiological task. Under slow paced breathing, LF/HF is not the most robust cross-condition summary metric; mean HR, RMSSD, total power, and validity annotations provide a stronger integrative framework. For this participant, the strongest paced-breathing finding was not a classical 6-breaths/min resonance maximum, but precise frequency entrainment combined with continued amplitude growth at 3 breaths/min.

## Appendix Planning Note

- Appendix A: `E4B_sleep` partial trajectory (Fig. A1)
- Supplementary Methods: data quality and pipeline validation (Figs. S1 and S2)
- Supplementary Results: postural tachograms, walking signal snapshots, recovery tau, and additional breath-hold / walking support figures

## References (Draft Placeholder Set)

[1] Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, “Heart rate variability: Standards of measurement, physiological interpretation and clinical use,” *Circulation*, vol. 93, no. 5, pp. 1043–1065, 1996.

[2] J. Pan and W. J. Tompkins, “A real-time QRS detection algorithm,” *IEEE Transactions on Biomedical Engineering*, vol. BME-32, no. 3, pp. 230–236, 1985.

> Note: before submission, the manuscript will still require a formal literature pass and a full IEEE-style reference list. The present draft is intended to finalize structure, figure logic, evidentiary flow, and the main narrative first.
