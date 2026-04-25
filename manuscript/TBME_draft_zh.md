# 姿勢、隨意屏息、步行與節律呼吸下之心肺動態：基於單導程 ECG 的多實驗研究

## 摘要

本研究以單一受試者、重複量測的設計，分析 15 段單導程 ECG 記錄，整合姿勢基線、隨意屏息、步行挑戰、節律呼吸與部分入睡過程，建立一套可跨情境解讀的心率變異度（HRV）分析框架。訊號以 500 Hz ECG 輸入，經基線漂移去除、50 Hz notch 與 0.5–40 Hz bandpass 濾波後，分別以教學用 scipy path 與 NeuroKit2 參考 path 進行 R-peak 偵測與比較。結果顯示，姿勢改變主要改變自主神經 operating point：由仰臥到站立，平均心率上升而 RMSSD 與 HF power 單調下降。屏息實驗中，吸氣後屏息造成較大心率上升，而呼氣後屏息在恢復期呈現較強副交感反彈。步行挑戰使平均心率上升至 83.0 bpm，恢復時間常數約 6.8 s，但步行期的細緻 HRV 指標受 motion artifact 汙染。節律呼吸是全篇最強的受控操弄：RR 頻譜主峰與 imposed breathing rate 高度對應（R² = 0.998），然而在慢呼吸條件下，LF/HF 大幅上升而 RMSSD 並未同步下降，顯示 classical HF/LF 邊界在此情境下失效。更重要的是，本資料未觀察到典型 6/min inverted-U resonance peak；RR 振幅反而在 3/min 時達到最大。這些結果說明，HRV 解讀必須依操弄情境、時間尺度與頻帶有效性調整，而不能將 LF/HF 視為跨情境的萬用 summary metric。

## 關鍵詞

心率變異度，單導程 ECG，節律呼吸，隨意屏息，步行挑戰，自主神經調控

## I. 緒論

心率變異度（heart rate variability, HRV）常被用來近似自主神經調控狀態，但其解讀高度依賴操弄情境、量測長度與頻域假設是否成立。若將不同生理任務下的 HRV scalar 指標直接並列，往往容易得到表面上可比較、實際上卻混合了不同機制的結論。最典型的例子是 LF/HF：在一般靜息短時程記錄中，LF/HF 可以作為一種粗略的頻域平衡指標；但在刻意控制呼吸頻率、尤其是慢呼吸條件下，呼吸主峰本身會跨越 Task Force 定義的 0.15 Hz 邊界，使 LF/HF 不再是單純的 sympathovagal summary。

本研究的價值在於：我們不是只做一個 HRV 任務，而是在同一位受試者身上，以 repeated-measures 方式串接多個具有不同生理意義的操弄，包括：(1) 姿勢改變；(2) 吸氣後與呼氣後的隨意屏息；(3) 短時步行挑戰與恢復；(4) 五種固定節律的 paced breathing；以及 (5) 一段不完整但生理方向合理的入睡過渡記錄。這種設計使我們可以回答下列五個問題：

1. 姿勢改變是否提供一條穩定、可預測的 autonomic baseline axis？
2. 屏息時觀察到的 HF collapse 與心率變化，是純生理效應，還是 conscious effort confound 的混合？
3. 步行任務中觀察到的 HRV 改變，哪些是生理訊號，哪些受 motion artifact 限制？
4. Paced breathing 是否真的能精準地把 RR 主峰拉到目標頻率？若可以，其主要效應是改變平均心率、改變頻帶分配，還是放大振盪振幅？
5. 當所有任務被整合時，哪一類 HRV 指標可以穩健跨情境比較，哪一類必須附帶 validity caveat？

本文的主要貢獻有三。第一，我們建立一條自資料品質檢查、雙 path R-peak 驗證，到各實驗專屬指標與跨實驗綜整的完整分析鏈。第二，我們證明同一份 ECG 資料在不同操弄下，應用不同的解讀框架：姿勢適合 steady-state autonomic set point，屏息與步行適合 challenge/recovery trajectory，節律呼吸則主要揭露 respiratory entrainment 與 amplitude modulation。第三，我們在 paced breathing 中觀察到一個與經典 resonance narrative 不完全一致的結果：在本受試者資料內，RR 振幅並未在 6/min 形成清楚 inverted-U 峰值，而是在更慢的 3/min 條件持續增加。

## II. 材料與方法

### A. 研究設計與資料集

本研究為單一受試者、跨 15 段記錄的 repeated-measures 生理實驗。ECG 取樣率為 500 Hz，三軸加速度（GSEN）取樣率為 25 Hz。所有記錄皆來自同一套裝置與同一分析流程，因此不同實驗間的差異主要來自生理操弄，而不是硬體與前處理條件改變。

整體資料可分為五類。首先，`E1PRE` 為 pre-sleep supine baseline，用於 pipeline validation 與 E4B appendix anchor。`E1A`、`E1B`、`E1C` 分別對應仰臥、坐姿、站姿，形成姿勢基線。其次，`E2A_insp_1/2` 與 `E2B_exp_1/2` 為吸氣後與呼氣後屏息，各兩次 trial；在 notebook 中，第一個 repetition 被標記為較 effortful，第二個 repetition 作為較 relaxed 的對照。第三，`E3_walk` 為 180 s 記錄，含 seated、walking、recovery 三段。第四，`E4A_12pm/9pm/6pm/5pm/3pm` 為五種 paced breathing 條件，其中 3/min 延長為較長記錄以確保足夠呼吸週期。最後，`E4B_sleep` 為不完整的入睡過渡紀錄，只作 appendix。

特別需要說明的是，E4A 五個節律呼吸條件採 **固定遞減順序**（12 → 9 → 6 → 5 → 3 breaths/min），而非 randomized order。此設計會引入 training、relaxation、fatigue 或 vigilance drift 的潛在混雜效應，因此後文會明確將其列為限制，而不將 monotonic trend 過度詮釋為純生理 resonance law。

### B. 訊號處理流程

ECG 分析統一由 `src/pipeline.py` 完成。原始訊號先經兩階段 median filter 去除 baseline drift，再施加 50 Hz notch 與 0.5–40 Hz Butterworth bandpass。R-peak 偵測採雙 path：其一為對 Pan–Tompkins [2] 精神忠實的 teaching path；其二為 NeuroKit2 參考 path，搭配 Kubios-style peak correction。主結果表格與 paced breathing 的關鍵分析以 NeuroKit2 path 為主，因其在短時程與異常 beat 修正上較穩定；但 pipeline validation 顯示兩條 path 在 steady-state 段落中幾乎完全一致。

RR interval 由相鄰 R-peak 差分得到。對 steady-state 資料，時間域指標包括 mean HR、SDNN、RMSSD、pNN50；頻域指標則依 Task Force 定義 [1] 以 4 Hz cubic interpolation 後的 RR series 進行 Welch PSD，計算 VLF、LF、HF、LF/HF 與 normalized units。對 transient 任務（E2、E3），由於單段時間過短，不直接在每一 regime 上報告標準頻域 HRV，而改以時間域指標與 trajectory slope 描述；E2 的頻域比較則以 pooled spectral averaging 的方式與 E1B seated anchor 對照。

### C. 圖表配置、位置與論證功能

為符合 IEEE TBME 的結果導向寫法，本文不讓圖表只當裝飾，而是讓每張圖與每個表各自承擔一個明確問題。

- **Fig. 1 + Table I** 放在 `III-A` 開頭。  
  目的：建立姿勢基線，回答「steady-state autonomic set point 是否隨姿勢單調改變？」  
  要證明：後續 breath-hold、walking、paced breathing 的 interpretation 需要 posture-matched anchor，而 E1A–C 正提供這條參考軸。

- **Fig. 2 + Tables II–III** 放在 `III-B`。  
  目的：回答「breath-hold 的 HF collapse 與心率變化是否受到 conscious effort confound？」  
  要證明：吸氣後屏息與呼氣後屏息的反應不同，而且 relaxed / effortful 狀態會影響結論強度。

- **Fig. 3 + Table IV** 放在 `III-C`。  
  目的：回答「walking 的 HRV 改變是否可信，以及 motion artifact 在哪裡變成主要限制？」  
  要證明：walking 的平均心率上升是真實生理訊號，但 walking-phase 的細緻 HRV 需加 validity caveat。

- **Figs. 4–7 + Table V** 放在 `III-D`，作為全文主軸。  
  目的：依序回答：(1) paced breathing 是否有效 entrain RR spectrum；(2) peak 是否精準追蹤 metronome；(3) LF/HF 在 slow breathing 下是否仍可當主要 autonomic index；(4) classical 6/min resonance peak 是否存在。  
  要證明：本研究最重要的發現不是「6/min 最佳」，而是「慢呼吸會改變頻帶歸屬與振幅尺度，因此 LF/HF 的跨條件解讀必須非常謹慎」。

- **Figs. 8–9 + Table VI** 放在 `III-E`。  
  目的：回答「如何把 posture、breath-hold、walking 與 paced breathing 放進同一篇論文，而不把它們誤當成同一種任務？」  
  要證明：steady-state 與 transient challenge 應用不同的 summary space 才有意義；HR、RMSSD、total power 與 validity note 是跨實驗整合的核心。

- **Fig. S1、Fig. S2、Fig. A1 與其餘 supporting figures** 放在 supplement 或 appendix。  
  目的：支持方法穩健性、資料品質與附錄觀察，但不與主結果競爭版面。

### D. 統計與報告策略

姿勢與 paced breathing 為 steady-state 條件，報告完整 HRV scalar；E2 與 E3 則以 regime-based mean HR、RMSSD、min/max HR 與 HR slope 描述。Paced breathing 的 frequency-tracking 以 `linregress` 報告 slope、intercept、95% confidence interval、residual standard deviation 與對 `slope = 1`、`intercept = 0` 的檢定。由於 E4A 僅有五個 paced conditions，故 CI 必然偏寬；本研究將重點放在 effect size、visual agreement 與理論一致性，而不做超出資料支持範圍的過度推論。

## III. 結果

### A. 姿勢基線建立了可預測的 autonomic reference axis

姿勢實驗的角色，是為後續所有 transient 與 respiratory manipulation 提供「可解釋的生理參照」。仰臥（E1A）時平均心率為 54.0 bpm，RMSSD 為 99.1 ms，HF power 為 3252.8 ms²；坐姿（E1B）時平均心率上升至 56.1 bpm，RMSSD 降至 61.1 ms，HF power 降至 1122.6 ms²；站姿（E1C）時平均心率進一步升至 79.7 bpm，RMSSD 僅剩 25.2 ms，HF power 降至 310.7 ms²，而 LF/HF 升至 1.44。此結果顯示，orthostatic loading 對本受試者造成非常典型的 vagal withdrawal 與 chronotropic increase。

Fig. 1 應放在本小節開頭，因其同時展示 time-domain RR pattern 與 frequency-domain distribution，直接回答「姿勢改變是否產生單調且一致的 HRV 重分布」。Table I 緊接其後，用量化指標支持同一件事。這組結果的重要性不只在於 Exp. 1 成功，更在於它說明後續 E2 與 E3 應採用 E1B 作 posture-matched seated anchor，而不是用 supine baseline 去誤導比較。

`[建議在此放置 Fig. 1 與 Table I]`

### B. 屏息效應同時受到呼吸型態與 conscious effort 調節

Exp. 2 的核心問題不是「屏息會不會改變 HRV」這麼簡單，而是「觀察到的變化到底有多少是純生理反應，有多少混入了 conscious effort」。兩組吸氣後屏息 trial 的 pre-hold HR 分別為 62.9 與 59.2 bpm，但 hold mean HR 升至 66.9 與 73.5 bpm，對應的 ΔHR 為 +4.0 與 +14.3 bpm；相對地，呼氣後屏息的 hold mean HR 分別為 57.8 與 60.8 bpm，變化幅度顯著較小。這表示 inspiratory hold 的 chronotropic burden 更重，且試次間差異不能忽略。

頻域 pooled 結果則讓這個故事更完整。相對於 E1B seated anchor 的 HF = 1124.0 ms²，吸氣後屏息的 pooled HF 僅 94.0 ms²，約下降 12.0 倍；呼氣後屏息的 pooled HF 為 391.3 ms²，下降幅度較小。更關鍵的是恢復期：吸氣後屏息 recovery 的 pooled HF 回升至 1551.3 ms²，呼氣後屏息 recovery 更上升至 1951.6 ms²，分別約為 E1B 的 1.38 與 1.74 倍。此結果說明 breath-hold 不是單一方向的 vagal suppression 任務，而是包含 suppression 與 rebound 的動態系統。

在論文配置上，Fig. 2 應放在這裡，因為它回答的是「effort confound 是否會改變 breath-hold interpretation」。Table II 提供 time-domain trial summary，Table III 則負責 pooled frequency-domain evidence。如果版面足夠，HF collapse verification 圖可作 supplement 強化 Methods-to-Results 的橋接，但主結果不應把所有篇幅都花在重複說明 HF 下降，而應聚焦於「不同呼吸型態與 effort level 對 response shape 的影響」。

`[建議在此放置 Fig. 2、Table II 與 Table III]`

### C. 步行挑戰揭露真實心率負荷，但 walking-phase HRV 必須附帶 validity caveat

Exp. 3 的價值在於：它不是一個漂亮的 HRV steady-state 實驗，而是一個 deliberately messy 的 ambulatory challenge。資料顯示，seated phase 的 mean HR 為 60.8 bpm、RMSSD 為 54.4 ms；walking phase 的 mean HR 升至 83.0 bpm，RMSSD 降至 41.1 ms；recovery phase 的 mean HR 回落至 70.3 bpm，且 recovery time constant 約為 6.8 s。這些數值本身支持「步行造成急性心血管負荷，並在停止後快速恢復」。

然而，walking 期並不適合被當成與靜息姿勢或 paced breathing 完全同類的 HRV condition。GSEN 與 RR 的 multimodal fusion 顯示，walking 階段存在可辨認的 motion component；表格也明確將 walking-phase HRV 標記為 **UNRELIABLE (motion)**。因此，本節真正要證明的不是「walking 的 RMSSD 有多低」，而是「在 ambulatory context 中，平均心率與 recovery kinetics 比精細頻域 HRV 更穩健，而 motion validity 必須被公開標示」。

Fig. 3 應放在此處，因為它最直接地把生理變化與量測限制畫在同一張圖中。Table IV 則補上 mean HR、RMSSD、recovery tau 與 motion note。其餘 signal snapshots、ECG PSD 與 RR PSD contrast 比較適合轉入 supplement 作 supporting evidence。

`[建議在此放置 Fig. 3 與 Table IV]`

### D. 節律呼吸精準移動 RR 主峰，但未支持經典 6/min resonance peak 假說

Exp. 4A 是全篇最強的 controlled dose-response 設計，也是本文最重要的發現來源。首先，paced breathing manipulation 的有效性非常清楚。五個條件下的 measured RR spectral peak 分別為 0.2031、0.1484、0.1016、0.0859 與 0.0469 Hz，與目標呼吸頻率高度一致；線性迴歸的 slope 為 1.022（95% CI: 0.947–1.097），intercept 為 −0.0020（95% CI: −0.0116 至 0.0076），R² = 0.998，residual SD 僅 0.0028 Hz。換言之，Fig. 4 與 Fig. 5 要證明的第一件事，是「你看到的 peak migration 不是視覺錯覺，而是定量可驗證的 entrainment」。

其次，慢呼吸的主要效應不是把平均心率大幅降低，而是擴大振盪振幅。E4A_12pm 時 mean HR 為 59.4 bpm、SDNN 為 48.7 ms、total power 為 1754.3 ms²；到 E4A_3pm 時 mean HR 仍僅 58.1 bpm，但 SDNN 升至 131.4 ms，total power 升至 10493.1 ms²，RR p95-p5 幅度由 156.5 ms 增至 405.5 ms。這代表 slow breathing 在本受試者上主要改變的是 oscillatory amplitude，而不是 mean chronotropic set point。

第三，也是方法學上最關鍵的一點：LF/HF 在這個實驗中不能被直讀為 sympathovagal balance。LF/HF 從 12/min 的 0.22 上升到 6/min 的 11.54，再在 5/min 與 3/min 維持約 17.45–17.47；然而 RMSSD 並未同步崩潰，反而維持在 48–65 ms 左右。這說明呼吸主峰在慢呼吸條件下跨越了 0.15 Hz 邊界，使 spectral power 被重新分配到 LF，因此 Fig. 6 的真正功能是「拆解 LF/HF inflation 與 vagal proxy 的分離」。

最後，Fig. 7 要回答的是全文最容易被誤解的問題：是否存在 classical 6/min resonance peak？在本資料中，答案是否定的。RR amplitude 與 SDNN 都隨慢呼吸持續增加，並未在 6/min 出現清楚 inverted-U 峰值。雖然 NK2 的 P2T 指標在 6/min 附近似乎較高，但其後在 5/min 與 3/min 出現下降；考量該指標在極慢呼吸下可能低估振幅，本研究不將其視為否定 RR amplitude monotonic rise 的更高階證據，而是如實報告兩種 amplitude metric 的分歧。對初稿而言，最重要的結論必須寫清楚：**the classical inverted-U resonance was not observed within the tested range**。

`[建議在此依序放置 Fig. 4、Fig. 5、Fig. 6、Fig. 7 與 Table V]`

### E. 跨實驗整合顯示：不同任務應用不同 summary space 解讀

當所有實驗被放進同一篇論文時，最危險的做法就是把它們全部壓成同一個頻域 scalar 排名。新版 integration 的主張相反：steady-state 任務應優先用 mean HR、RMSSD 與 total power 描述 operating point；transient 任務則應以 challenge / recovery trajectory 呈現。Fig. 8 顯示，posture manipulation 主要沿著「HR 上升、RMSSD 下降」方向移動；paced breathing 則在 mean HR 幾乎不變的情況下大幅放大 total power 與 SDNN。這兩條軌跡的生理意義根本不同，因此不能用同一條 LF/HF 軸去排名。

Fig. 9 則把 E2、E3 與 E4B 放進 challenge/recovery atlas。吸氣後屏息由 pre 到 hold 呈現更強的 HR 上升；呼氣後屏息在 recovery 的 RMSSD 反彈最為明顯；walking 的 mean HR 升高到 83.0 bpm，而 recovery tau 為 6.8 s；partial sleep 的 appendix 軌跡僅顯示約 2.6 bpm 的 HR 下滑，方向合理但資料不完整。Table VI 在此扮演總結角色：它不是再把所有任務重新量一次 LF/HF，而是把 **Family、Phase、Mean HR、RMSSD、Total Power、Validity note 與 Synthesis note** 放進同一張 cross-experiment summary 表。

此處的科學訊息非常明確：姿勢、屏息、步行與節律呼吸不是在測量同一種「HRV 大小」，而是在揭露不同層次的 cardiorespiratory regulation。穩健的跨實驗寫法，應該允許不同任務在不同 summary space 中被解讀，而不是強迫它們共用一個不恰當的單一指標。

`[建議在此放置 Fig. 8、Fig. 9 與 Table VI]`

## IV. 討論

本文最核心的訊息，是 HRV interpretation 必須跟著操弄情境走。Exp. 1 建立的是 autonomic set-point axis：姿勢改變對 HR 與 vagal-linked metrics 的影響具一致方向。Exp. 2 揭露的是 respiratory perturbation 與 conscious effort 的交互作用：同樣是 breath-hold，吸氣後與呼氣後的生理負荷、恢復樣態與副交感反彈強度並不相同。Exp. 3 告訴我們，ambulatory challenge 中最穩健的是 mean HR 與 recovery kinetics，而 walking-phase 的細緻 HRV 必須公開承認 motion limitation。Exp. 4A 則進一步指出，在刻意控制呼吸且頻率慢到跨越 LF/HF 邊界時，頻域指標本身的解釋框架就會改變。

因此，本文不是單純報告一串 HRV 數值，而是在提出一個解讀原則：**steady-state posture、transient challenge 與 respiratory entrainment 不應被同一種 summary metric 粗暴統一**。這也是新版 integration 將 LF/HF 降級為「conditional metric」的原因。對一般靜息姿勢資料，它仍可作輔助指標；但在 slow paced breathing 中，LF/HF inflation 大多反映 band migration，而不是 autonomic dominance reversal。

Exp. 4A 的結果尤其值得強調。經典 resonance biofeedback 敘事通常預期 6/min 左右會產生最大振幅，但本研究並未觀察到清楚的 6/min inverted-U peak；RR amplitude 與 SDNN 反而隨更慢的呼吸條件持續增加。這並不表示 resonance 概念完全錯誤，而是說明「振幅最大化」與「單一標準頻帶內的能量最大化」並不是同一件事。若未把 frequency boundary 與 metric validity 一起考慮，就很容易把 method-dependent peak 誤讀為 physiology。

## V. 研究限制

本研究至少有四項限制。第一，這是單一受試者的 repeated-measures 研究，因此本文更適合作為機制導向、方法論導向的 case study，而非群體推論。第二，E4A paced breathing 的順序固定遞減，未 randomize，因此 training、fatigue、relaxation drift 可能部分解釋 slow-rate 條件下持續增加的 SDNN 與振幅。第三，E3 walking 段落明顯受 motion artifact 影響，因此 walking-phase 的 HRV 指標必須保留 validity caveat。第四，E4B sleep 只是 partial recording，只能作 appendix trend，不能與完整 steady-state 條件同等解讀。

未來工作可從三個方向擴展：增加受試者數以檢驗 monotonic slow-breathing effect 的可重現性；將 paced breathing 順序 randomize 或 counterbalance；以及加入直接呼吸帶訊號，以進一步驗證極慢呼吸下 ECG-derived respiration 與 RSA metric 的有效性。

## VI. 結論

本研究以同一位受試者的多實驗 ECG 資料顯示：姿勢主要改變 autonomic operating point；屏息與步行主要揭露 transient challenge/recovery dynamics；而 paced breathing 主要改變 oscillatory amplitude 與 spectral location。最重要的方法學結論是，HRV 指標不能脫離操弄情境被解讀。特別是在 slow paced breathing 下，LF/HF 並非跨條件最穩健的 summary metric；RMSSD、mean HR、total power 與 validity annotation 更適合作為跨實驗綜整的主軸。對本受試者而言，節律呼吸的 strongest finding 並不是 classical 6/min resonance peak，而是呼吸主峰可被高精度追蹤，且 RR 振幅在更慢的 3/min 條件下仍持續增加。

## 附錄規劃說明

- Appendix A：`E4B_sleep` partial trajectory（Fig. A1）
- Supplementary Methods：資料品質總覽與 pipeline validation（Fig. S1, Fig. S2）
- Supplementary Results：姿勢 tachogram、walking signal snapshots、recovery tau、E2 HF verification 等 supporting figures

## 參考文獻（初稿占位版）

[1] Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, “Heart rate variability: Standards of measurement, physiological interpretation and clinical use,” *Circulation*, vol. 93, no. 5, pp. 1043–1065, 1996.

[2] J. Pan and W. J. Tompkins, “A real-time QRS detection algorithm,” *IEEE Transactions on Biomedical Engineering*, vol. BME-32, no. 3, pp. 230–236, 1985.

> 註：正式投稿前仍需補完整文獻回顧與相關工作引用；本初稿先將內容、章節、圖表證據鏈與主結論寫完整。
