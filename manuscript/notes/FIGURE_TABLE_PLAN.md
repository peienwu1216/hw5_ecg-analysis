# 圖表配置與證據鏈規劃

註記：本文件保留原本的敘事規劃內容；實際 LaTeX 載入與目前 canonical 檔名，請以 `FIGURE_INDEX.md` 與 `outputs/figures/*.pdf` 為準。

本文件不是論文本文，而是「主文 / appendix / 補充材料」的配置藍圖。目標是避免圖太多卻沒有明確任務，並確保每張圖、每個表都在回答一個明確研究問題。

## 一、建議主文圖

| 論文編號 | 來源檔案 | 建議放置章節 | 要回答的問題 | 要證明的事情 |
| --- | --- | --- | --- | --- |
| Fig. 1 | `nb01_fig01_pipeline_overview.png` | `II-B Processing Pipeline` | 整體實驗設計與分析流程為何？ | 提供研究全貌，包含四大主要實驗與訊號處理步驟。 |
| Fig. 2 | `MAIN_03_nb02_exp1_rr_psd_grid.png` | `III-A Postural Baseline` | 姿勢改變是否造成單調、可解釋的自主神經變化？ | Supine → Sitting → Standing 對 HRV 的影響具有生理一致性，建立後續實驗的 reference axis。 |
| Fig. 3 | `MAIN_06_nb03_exp2_effort_comparison.png` | `III-B Voluntary Breath-Hold` | 屏息造成的變化是純生理，還是受到 conscious effort confound？ | Inspiratory/expiratory hold 的反應不只取決於呼吸中止本身，也受到 effort / relaxation 狀態調節。 |
| Fig. 4 | `MAIN_12_nb04_exp3_multimodal_fusion.png` | `III-C Walking Challenge` | 步行時看到的 RR / HRV 變化是否可信，還是被 motion artifact 汙染？ | Walking 期間確有 HR 提升，但細緻 HRV 指標需以 motion validity 框架解讀。 |
| Fig. 5 | `MAIN_15_nb05_exp4a_psd_overlay.png` | `III-D Paced Breathing` | 呼吸節律是否真的把 RR 主峰往左推移？ | 呼吸頻率下降時，RR spectral peak 系統性左移，且振幅隨慢呼吸放大。 |
| Fig. 6 | `MAIN_16_nb05_exp4a_peak_tracking_regression.png` | `III-D Paced Breathing` | 量測到的 RR spectral peak 是否真的跟 metronome rate 對上？ | Peak tracking 幾乎沿 identity line，支持 paced-breathing manipulation 有效。 |
| Fig. 7 | `MAIN_17_nb05_exp4a_lfhf_vs_rmssd.png` | `III-D Paced Breathing` | 慢呼吸下 LF/HF 的上升是自主神經翻轉，還是頻帶遷移假象？ | LF/HF 大幅上升但 RMSSD 並未同步崩解，顯示 band migration 而非單純 sympathovagal shift。 |
| Fig. 8 | `MAIN_18_nb05_exp4a_resonance_amplitude.png` | `III-D Paced Breathing` | 是否存在 classical 6/min inverted-U resonance peak？ | 在本資料中未見清楚 6/min 峰值，RR amplitude 反而隨更慢呼吸持續增加。 |
| Fig. 9 | `MAIN_19_nb06_integration_operating_map.png` | `III-E Cross-Experiment Synthesis` | posture 與 paced breathing 改變的是同一件事嗎？ | 姿勢主要改變 autonomic operating point；paced breathing 主要放大 oscillatory amplitude，而非顯著改變 mean HR。 |
| Fig. 10 | `MAIN_20_nb06_integration_challenge_recovery_atlas.png` | `III-E Cross-Experiment Synthesis` | transient experiments 應如何和 steady-state experiments 放在同一框架下理解？ | Breath-hold、walking、partial sleep 更適合以 challenge / recovery trajectory 解讀，而非單一 steady-state HRV scalar。 |

## 二、建議主文表

| 論文編號 | 來源檔案 | 建議放置章節 | 要回答的問題 | 要證明的事情 |
| --- | --- | --- | --- | --- |
| Table I | `table_1_1_postural.csv` | `III-A` | posture baseline 的量化差異是什麼？ | HR、RMSSD、HF、LF/HF 對姿勢變化呈一致方向。 |
| Table II | `table_2_1a_trials.csv` | `III-B` | breath-hold trials 的時間域變化有多大？ | Inspiratory hold 對 HR 的上升較大；expiratory recovery 有明顯 vagal rebound。 |
| Table III | `table_2_1b_pooled.csv` | `III-B` | HF collapse / rebound 的頻域證據有多強？ | Inspiratory hold 明顯壓低 HF，expiratory recovery 超越 seated anchor。 |
| Table IV | `table_3_1_walking.csv` | `III-C` | walking challenge 的定量結果是什麼？ | Walking HR 上升、recovery tau 可估、walking RMSSD 需註記 motion unreliability。 |
| Table V | `table_4_1_paced.csv` | `III-D` | paced breathing 的操弄有效嗎？且 amplitude 與 band metrics 如何改變？ | Peak deviation 小、total power / SDNN 增加、LF/HF 在 slow breathing 下被 band migration 放大。 |
| Table VI | `table_5_cross_experiment.csv` | `III-E` | 全部實驗如何在同一框架下總結？ | 以 HR、RMSSD、total power 與 validity note 做 cross-experiment synthesis 比單看 LF/HF 更穩健。 |

## 三、建議放入補充材料或方法 appendix 的圖

| 補充編號 | 來源檔案 | 建議用途 | 原因 |
| --- | --- | --- | --- |
| Fig. S1 | `APP_A01_nb00_data_quality_overview.png` | Data quality appendix | 證明資料完整、各 session 原始波形合理，但不宜佔用主文篇幅。 |
| Fig. S2 | `APP_A02_nb01_pipeline_validation_e1a.png` | Methods appendix | 證明 scipy teaching path 與 NK2 reference path 一致。 |
| Fig. S3 | `MAIN_01_nb02_exp1_postural_tachograms.png` | Supplement to Exp. 1 | 視覺上直觀，但與 Fig. 1 的資訊有部分重疊。 |
| Fig. S4 | `MAIN_02_nb02_exp1_ecg_psd_by_posture.png` | Supplement to Exp. 1 | 側重 ECG morphology / harmonic structure，較偏 supporting evidence。 |
| Fig. S5 | `MAIN_04_nb02_exp1_duration_sweep.png` | Methods / robustness appendix | 用來說明 window-length sensitivity，屬方法穩健性。 |
| Fig. S6 | `MAIN_05_nb03_exp2_hf_collapse_verification.png` | Supplement to Exp. 2 | 若主文已用 effort comparison 和 pooled table，這張可退到 supplement。 |
| Fig. S7 | `MAIN_07_nb03_exp2_pure_physiology.png` | Supplement to Exp. 2 | 與主文 Fig. 2 有敘事重疊，可依篇幅決定。 |
| Fig. S8 | `MAIN_08_nb04_exp3_walking_tachogram.png` | Supplement to Exp. 3 | 全程 tachogram 直觀，但資訊密度較低。 |
| Fig. S9 | `MAIN_09_nb04_exp3_signal_processing_snapshots.png` | Supplement to Exp. 3 | 很適合說明 motion artifact，但比較像 supporting methodological visual. |
| Fig. S10 | `MAIN_10_nb04_exp3_recovery_tau_fit.png` | Supplement to Exp. 3 | 若主文篇幅不足，可將 tau 單獨圖移到 supplement，但在文字保留數值。 |
| Fig. S11 | `MAIN_11_nb04_exp3_ecg_psd_rest_vs_walk.png` | Supplement to Exp. 3 | 幫助解釋步行噪音來源。 |
| Fig. S12 | `MAIN_13_nb04_exp3_rr_psd_contrast.png` | Supplement to Exp. 3 | 頻域對比有用，但主文未必要再加一張。 |
| Fig. S13 | `MAIN_14_nb05_exp4a_tachograms.png` | Supplement to Exp. 4 | 有助於展示時域振幅變大，但主文核心論點已由 Fig. 4–7 承擔。 |
| Fig. S14 | `MAIN_21_nb06_integration_pipeline_reliability.png` | Supplement / methods appendix | 是品質保證圖，不是主要生理發現。 |

## 四、建議放 Appendix 的圖

| Appendix 編號 | 來源檔案 | 建議用途 | 原因 |
| --- | --- | --- | --- |
| Fig. A1 | `APP_A03_nb06_partial_sleep_trajectory.png` | Appendix A | E4B 僅為 partial recording，適合作附錄而非主結果。 |

## 五、建議不直接當論文正式圖表的輸出

這些檔案很重要，但更像 analysis artifact、full export、或供你自己查核：

- `quality_check.csv`
- `e1a_pipeline_comparison.csv`
- `e1a_hrv_full.csv`
- `e1a_duration_sweep.csv`
- `e1_hrv_full.csv`
- `analysis_log.csv`

它們適合作為：

1. 補充材料資料表  
2. Methods / robustness 補充證據  
3. 回覆審稿人時的 supporting evidence

## 六、論文主線一句話版本

如果要把整篇稿件收斂成一句話，主線應該是：

> 單導程 ECG 的跨情境 repeated-measures 實驗顯示，姿勢主要改變 autonomic set point，屏息與步行主要揭露 transient challenge / recovery dynamics，而節律呼吸主要改變 oscillatory amplitude；因此 HRV 指標必須依操弄情境與頻帶有效性被解讀，而不能把 LF/HF 當成萬用 summary metric。
