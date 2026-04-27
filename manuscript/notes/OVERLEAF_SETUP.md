# Overleaf / Shareable Copy Notes

本地寫作現在以 `manuscript/` 為主，不再依賴 `manuscript/figures/` 內的重複 PNG。

## 本地優先做法

- 直接在 `manuscript/main.tex` 寫作
- 圖片由 `../outputs/figures/` 載入
- 新圖請從 notebook 重新輸出成 PDF

## 若要搬到 Overleaf

1. 建立 Overleaf 專案並上傳 `manuscript/main.tex`
2. 上傳 `outputs/figures/` 中論文需要的 PDF 圖檔
3. 保持原始檔名，不需要再手動改成 `fig_posture.png` 這類別名
4. 若 Overleaf 專案結構不同，只要同步調整 `\graphicspath{...}` 即可

## 建議上傳的主要圖

| 論文圖號 | 檔名 |
| --- | --- |
| Fig. 1 | `nb02_fig03_rr_psd_postural.pdf` |
| Fig. 2 | `nb03_fig02_e2_effort_comparison.pdf` |
| Fig. 3 | `nb04_fig01_e3_tachogram.pdf` |
| Fig. 4 | `nb05_fig02_e4a_psd_overlay.pdf` |
| Fig. 5 | `nb05_fig03_e4a_peak_freq.pdf` |
| Fig. 6 | `nb05_fig04_e4a_lfhf_crossover.pdf` |
| Fig. 7 | `nb06_fig01_autonomic_spectrum.pdf` |
| Fig. A1 | `nb06_fig04_e4b_sleep_trajectory.pdf` |
| Fig. A2 | `nb06_fig03_pipeline_validation.pdf` |

完整對照請看 `FIGURE_INDEX.md`。
