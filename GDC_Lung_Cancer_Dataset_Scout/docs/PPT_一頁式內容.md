# GDC Lung Cancer Stage-Survival Dataset Scout

**目的**｜比較 GDC 的 TCGA-LUAD 與 TCGA-LUSC，判斷公開 metadata 是否足以支援後續 stage-survival 研究規劃。

| Demo 問題 | 可重複驗證內容 |
|---|---|
| **Problem** | 是否具備 stage、survival endpoint 與清楚的 access metadata？ |
| **Input** | GDC projects、cases、files、`_mapping` 與官方 Data Dictionary |
| **Workflow** | `plan → fetch → normalize → evidence gate → check → report → review` |
| **Check** | 驗證 schema、evidence coverage、access consistency，並分類 NORMAL／SCHEMA／NOT_FOUND／CONFLICT |
| **Output** | 產生 dataset cards、API 快照、trace、manifest、evaluation report 與 review checklist |

**重現指令**

```powershell
python -m gdc_scout run --config configs/task_spec.yaml --output outputs/latest
python -m gdc_scout eval --output outputs/latest --threshold 0.8
python -m unittest discover -s tests -v
```

**驗證原則**｜每個結論均連結 evidence ID，並記錄 API URL、時間、HTTP status、response SHA-256 與 parser version，使整個 workflow 可重跑、可追溯、可獨立查核。

> **Limit**：本工具只評估 metadata 對研究規劃的支援程度；不執行 survival analysis，也不產生預後、療效、因果或臨床建議。欄位存在不等於資料完整或研究設計有效。
