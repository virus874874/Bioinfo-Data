# GDC Lung Cancer Stage-Survival Dataset Scout

一個為醫療大數據 Hackathon 設計、可在一個下午完成的 Dataset Scout。它比較 GDC 的 `TCGA-LUAD` 與 `TCGA-LUSC`，回答公開 metadata 是否足以支援後續 stage-survival 研究規劃。

> **重要聲明**
> 本工具不執行 survival analysis，不產生預後、療效、因果或臨床建議。欄位存在不等於資料完整，也不等於研究設計有效。

## Demo 回答的五個問題

| # | 問題 | 驗證內容 |
|---|---|---|
| 1 | **Problem** | LUAD 與 LUSC 是否具備 stage、survival endpoint 與清楚的 access metadata？ |
| 2 | **Input** | GDC projects、cases、files、`_mapping` 與官方 Data Dictionary |
| 3 | **Workflow** | 受限狀態機依序執行 plan → fetch → normalize → evidence gate → check → report → review |
| 4 | **Check** | Schema、evidence coverage、access consistency，以及 NORMAL、SCHEMA、NOT_FOUND、CONFLICT cases |
| 5 | **Limit** | 結果只代表 metadata 對研究規劃的支援程度，不能當作 survival 結果或臨床證據 |

## 重複驗證

需求：Python 3.11 以上，以及可連線至 GDC API 的網路環境。

```powershell
python -m pip install -e .
python -m gdc_scout run --config configs/task_spec.yaml --output outputs/latest --verbose
python -m gdc_scout eval --output outputs/latest --threshold 0.8
python -m unittest discover -s tests -v
```

只驗證設定、不呼叫 API：

```powershell
python -m gdc_scout run --config configs/task_spec.yaml --output outputs/latest --dry-run
```

## 通過條件

- 固定的線性 workflow 完整執行。
- 8 個 artifacts 全部產生。
- 每筆 evidence 具備 endpoint、URL、時間、HTTP status、SHA-256 與 parser version。
- `overall_confidence` 達到設定門檻。
- 所有測試通過。
- 非正常狀態被分類為 SCHEMA、NOT_FOUND 或 CONFLICT，並列入人工審查。

## 輸出

| Artifact | 用途 |
|---|---|
| `dataset_cards.csv` | 專案規模、欄位與覆蓋率 |
| `fit_for_question.md` | 是否足以支援研究規劃 |
| `data_dictionary.md` | 使用欄位與 live mapping |
| `trace.jsonl` | 完整執行軌跡 |
| `run_manifest.json` | 執行環境與摘要 |
| `eval_report.json` | Evidence 與信心評估 |
| `review_checklist.md` | 人工審查項目 |
| `source_snapshot.json` | API response 與證據快照 |

