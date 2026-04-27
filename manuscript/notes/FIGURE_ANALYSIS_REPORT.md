# 論文圖表視覺分析報告 (Final Figure Analysis Report)

註記：本報告的分析結論仍可直接使用；若檔名與目前專案不一致，請以 `outputs/figures/` 內的 PDF 匯出檔與 `FIGURE_INDEX.md` 為準。

本報告基於對 `outputs/figures/` 中 24 張 PNG 檔案的逐一檢視。報告不僅包含實驗意義，更精確提取了圖像中的關鍵數值與視覺證據，旨在為論文撰寫提供最堅實的敘事支撐。

---

## 1. 演算法驗證與數據品質 (Algorithm & Quality)

| 檔案名稱 | 視覺觀察到的關鍵特徵 | 科學意義 |
| :--- | :--- | :--- |
| `nb00_fig01_quality_overview.png` | 展示 14 個 Session 的 ECG 全景與 5-15s 縮放。E3 (Walking) 原始波形有明顯基線漂移與 2-3Hz 噪音，但 R-peak 標記點位精確。 | 證明單導程 ECG 穿戴裝置在動態環境下仍具備 R-peak 提取能力，確保數據源頭可靠。 |
| `nb01_fig02_e1a_validation.png` | Scipy (紅三角) 與 NK2 (綠三角) 在 R-peak 偵測上高度重合。PSD 顯示 LF (0.141 Hz) 與 HF (0.203 Hz) 峰值清晰。 | 驗證自研 Pipeline 的時域與頻域計算與國際標準 (NeuroKit2) 具有同等效力。 |
| `nb06_fig03_pipeline_validation.png` | Artifact rate 散點圖顯示所有 session 均 < 2.5%；Detector agreement 直條圖顯示各組均 > 99.5%。 | 以量化數據證明數據清理 (Cleaning) 與特徵提取 (Feature Extraction) 的高品質。 |

---

## 2. 姿勢改變：自主神經基準線 (Postural Baseline)

| 檔案名稱 | 視覺觀察到的數據/趨勢 | 核心生理意義 |
| :--- | :--- | :--- |
| `nb02_fig01_postural_tachograms.png` | Supine (RMSSD 99.1ms) -> Sitting (61.1ms) -> Standing (25.2ms)。 | **量化基準**：直立姿勢導致迷走神經活動 (RMSSD) 發生了約 75.4% 的斷崖式下降。 |
| `nb02_fig02_ecg_psd_harmonics.png` | 基本頻率 $f_0$ 隨心率從 0.90Hz (Supine) 移至 1.33Hz (Standing)；諧波分佈符合 ECG 波形特徵。 | 證明頻譜分析能精準捕捉心臟機械活動的頻率位移。 |
| `nb02_fig03_rr_psd_postural.png` | PSD 圖中，Standing 狀態下的 0.15-0.40 Hz (HF 帶) 能量幾乎完全消失，且 Tachogram 波動幅度明顯變小。 | 展示重力挑戰造成的迷走神經撤退 (Vagal Withdrawal) 與頻譜特徵。 |

---

## 3. 屏息與步行：暫態與動態挑戰 (Challenge & Recovery)

| 檔案名稱 | 視覺觀察到的數據/趨勢 | 核心生理意義 |
| :--- | :--- | :--- |
| `nb03_fig01_e2_hf_collapse.png` | 屏息期間 HF 功率下降 **96.5%**。Spectrogram 在 30s (Onset) 後顯著變暗。 | 證明呼吸中止會強行終止 RSA，導致頻域迷走指標在暫態下完全失效。 |
| `nb03_fig03_e2_pure_physiology.png` | 吸氣後屏息 HR 峰值為 82 bpm (+27)；吐氣後屏息為 70 bpm (+12)。 | 展示胸內壓變化 (Valsalva-like effect) 對心率的調控強度高於單純缺氧反應。 |
| `nb04_fig03_e3_recovery_tau.png` | 步行後 HR 恢復曲線擬合良好，$\tau = 6.8s$，HRR60 = 18.5 bpm。 | 量體能健康度的關鍵指標：反映了迷走神經重新激活 (Reactivation) 的速度。 |
| `nb04_fig04_e3_ecg_psd.png` | 步行期間在 1-3 Hz 出現明顯紅標區域 (Walking Cadence Artifact)。 | 識別運動偽影的頻譜位置，為動態環境下的 HRV 解讀提供限制依據。 |
| `nb04_fig06_e3_rr_psd_contrast.png` | 步行時 (Red line) RR-PSD 呈現 "Locked-in" 狀態，所有生理波動峰值均被壓抑至接近底噪。 | 揭示了運動對 HRV 的全面抑制效應。 |

---

## 4. 節律呼吸：頻譜遷移與共振 (Paced Breathing)

| 檔案名稱 | 視覺觀察到的關鍵數據 | **最重要科學發現** |
| :--- | :--- | :--- |
| `nb05_fig01_e4a_tachograms.png` | 呼吸頻率變慢 (12->3/min)，SDNN 從 48.7ms 單調上升至 131.4ms。 | 證明慢呼吸能極大化心率變異度。 |
| `nb05_fig04_e4a_lfhf_crossover.png` | **LF/HF 從 0.22 暴漲至 17.47**；但 RMSSD 穩定在 47.7-64.9ms 之間。 | **核心論點**：LF/HF 的增加是頻譜遷移 (Band Migration) 的假象，並非交感神經活性增加。 |
| `nb05_fig05_e4a_resonance.png` | RR 振幅隨頻率降低持續上升，未在 0.1Hz 觀察到傳統定義的共振峰。 | 挑戰傳統 6次/分 共振模型，顯示振幅可能隨呼吸周期延長持續增加。 |

---

## 5. 跨實驗綜合圖 (Synthesis Map)

| 檔案名稱 | 圖像內容描述 | 論文結論價值 |
| :--- | :--- | :--- |
| `nb06_fig01_autonomic_spectrum.png` | X 軸 Mean HR, Y 軸 RMSSD。姿勢序列形成一條向右下的曲線；節律呼吸序列在左側垂直跳動。 | 總結：姿勢改變 ANS **Set-point**，而呼吸改變 ANS **Oscillatory Amplitude**。 |
| `nb06_fig02_hf_vs_hr_scatter.png` | 包含屏息、步行與睡眠的三個軌跡圖。 | 將暫態挑戰 (Challenge-Recovery) 納入統一的自主神經狀態空間 (State Space) 描述。 |
