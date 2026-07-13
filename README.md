# GDC Lung Cancer Stage-Survival Dataset Scout

以可追溯證據比較 GDC `TCGA-LUAD` 與 `TCGA-LUSC` 的公開 metadata，判斷其是否足以支援 stage-survival **研究規劃**。本工具不執行 survival analysis，也不產生臨床建議。

## 快速開始

```powershell
python -m pip install -e .
python -m gdc_scout run --config configs/task_spec.yaml --output outputs/latest --verbose
python -m gdc_scout eval --output outputs/latest --threshold 0.8
python -m unittest discover -s tests -v
```

離線檢查設定：

```powershell
python -m gdc_scout run --config configs/task_spec.yaml --output outputs/latest --dry-run
```

輸出包含 `dataset_cards.csv`、`fit_for_question.md`、`data_dictionary.md`、`trace.jsonl`、`run_manifest.json`、`eval_report.json`、`review_checklist.md`、`source_snapshot.json`。

## 安全範圍

只查詢公開 metadata；不下載 controlled files、不推測補值。欄位存在不代表完整，也不代表研究設計有效。

