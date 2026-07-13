# GDC Lung Cancer Stage-Survival Dataset Scout

一個為醫療大數據 hackathon 設計、可在一個下午完成的 Dataset Scout。它比較 GDC 的 `TCGA-LUAD` 與 `TCGA-LUSC`，回答公開 metadata 是否足以支援後續 stage-survival 研究規劃。

> **重要聲明**
> 本工具不執行 survival analysis，不產生預後、療效、因果或臨床建議。
> 欄位存在不等於資料完整，也不等於研究設計有效。

---

## 核心目標與問題

### Demo 回答的五個問題

| # | 問題 | 答案類型 | 
|---|------|--------|
| 1 | **Problem** | LUAD 與 LUSC 是否具備 stage、survival endpoint 與清楚的 access metadata？ | 是/否/部分 |
| 2 | **Input** | GDC projects、cases、files、`_mapping` 與官方 Data Dictionary | 結構化 JSON/YAML |
| 3 | **Workflow** | 受限狀態機 Agent 執行 plan → fetch → normalize → evidence gate → check → report → review | 線性流程，無迴圈 |
| 4 | **Check** | schema、evidence coverage、access consistency，以及 normal、schema、not_found、conflict cases | 四分類統計 |
| 5 | **Limit** | 結果只代表 metadata 對研究規劃的支援程度，不能當作 survival 結果或臨床證據 | 明確範圍界定 |

---

## 安裝與環境設置

### 系統需求
- Python 3.11 以上
- pip 22.0 以上
- 網路連接（用於 GDC API 查詢）

### 快速開始

```bash
# 1. 克隆或下載項目
git clone <repo-url>
cd gdc-lung-scout

# 2. 安裝依賴
python -m pip install --upgrade pip
python -m pip install -e .

# 3. 驗證安裝
python -c "import gdc_scout; print(gdc_scout.__version__)"
```

### 配置文件

建立 `configs/task_spec.yaml`（JSON 語法，YAML 1.2 子集）：

```yaml
# configs/task_spec.yaml
projects:
  luad:
    project_id: "TCGA-LUAD"
    name: "Lung Adenocarcinoma"
    description: "TCGA-LUAD dataset for stage-survival evaluation"
    
  lusc:
    project_id: "TCGA-LUSC"
    name: "Lung Squamous Cell Carcinoma"
    description: "TCGA-LUSC dataset for stage-survival evaluation"

api:
  endpoint: "https://api.gdc.cancer.gov"
  timeout: 30
  max_retries: 3
  retry_backoff: 2.0

evidence:
  required_fields:
    - "endpoint"
    - "url"
    - "request_timestamp"
    - "http_status"
    - "response_sha256"
    - "parser_version"

output:
  dir: "outputs/latest"
  format: "csv,md,json,jsonl"
```

---

## 命令執行流程

### 流程總圖

```
開始
  ↓
[1] python -m gdc_scout run --config configs/task_spec.yaml --output outputs/latest
       ├─ 讀取配置
       ├─ 調用 GDC API
       ├─ 生成 8 個 Artifacts
       └─ 保存到 outputs/latest/
  ↓
[2] python -m gdc_scout eval --output outputs/latest
       ├─ 驗證 evidence 完整性
       ├─ 生成 eval_report.json
       └─ 檢查數據品質指標
  ↓
[3] python -m unittest discover -s tests -v
       ├─ 運行所有單元測試
       └─ 驗證 parser 正確性
  ↓
結束 → 檢查 outputs/latest/review_checklist.md
```

### 詳細命令說明

#### 1️⃣ 運行數據評估 (必須)

```bash
python -m gdc_scout run \
  --config configs/task_spec.yaml \
  --output outputs/latest \
  --verbose
```

**參數說明**：
- `--config` (必須): 配置文件路徑
- `--output` (必須): 輸出目錄
- `--verbose` (可選): 啟用詳細日誌
- `--dry-run` (可選): 只驗證配置，不執行 API 調用

**預期執行時間**: 2-5 分鐘（取決於 API 回應速度）

**成功標誌**: 輸出以下消息
```
✓ Run completed successfully
✓ Generated 8 artifacts
✓ All evidence verified
```

---

#### 2️⃣ 執行評估與驗證 (必須)

```bash
python -m gdc_scout eval \
  --output outputs/latest \
  --threshold 0.8
```

**參數說明**：
- `--output` (必須): 與 `run` 的輸出目錄一致
- `--threshold` (可選): 可採信性閾值（0.0-1.0，預設 0.8）

**驗證項目**：
- ✓ Evidence 四項元數據完整性
- ✓ Schema 匹配度
- ✓ 覆蓋率（covered rows / total rows）
- ✓ Access consistency（公開/受限一致性）

**輸出**: `eval_report.json`

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "overall_confidence": 0.92,
  "evidence_completeness": {
    "normal": 156,
    "schema": 3,
    "not_found": 2,
    "conflict": 1
  },
  "recommendations": [...]
}
```

---

#### 3️⃣ 運行測試套件 (建議)

```bash
python -m unittest discover -s tests -v 2>&1 | tee test_results.log
```

**測試涵蓋**：
- Parser 正確性 (test_parser.py)
- Evidence 驗證 (test_evidence_gate.py)
- Harness 邏輯 (test_harness_conditions.py)
- 輸出格式 (test_output_artifacts.py)

**預期**: 所有測試應通過 ✓

---

## 輸出文件格式詳細說明

所有輸出文件位於 `outputs/latest/` 目錄。

### 核心 Artifacts（8 個）

#### 1. `dataset_cards.csv`

**用途**: 快速檢視兩個 project 的元數據卡片

**格式**: CSV，帶 header

```csv
project_id,project_name,case_count,file_count,stage_field_present,survival_field_present,access_level,last_updated
TCGA-LUAD,Lung Adenocarcinoma,585,12450,TRUE,TRUE,public,2024-01-15T10:30:00Z
TCGA-LUSC,Lung Squamous Cell Carcinoma,504,10230,TRUE,FALSE,public,2024-01-15T10:31:00Z
```

**欄位說明**:
- `project_id`: GDC Project ID
- `case_count`: Cases 總數
- `file_count`: 相關檔案總數
- `stage_field_present`: Metadata 中是否有 stage 欄位
- `survival_field_present`: Metadata 中是否有 survival endpoint
- `access_level`: public / controlled / mixed
- `last_updated`: 最後更新時間（ISO 8601）

---

#### 2. `fit_for_question.md`

**用途**: 人類可讀的評估報告，回答「是否適合進行 stage-survival 研究？」

**格式**: Markdown，含章節、表格、checklist

**結構**:
```markdown
# GDC Lung Cancer Stage-Survival Fitness Report

## Executive Summary
[Yes/No/Partial] - 1-2 句結論

## Key Findings
- LUAD: 具備 stage、survival、censoring 三個必要欄位
- LUSC: 缺少 censoring information
- 推薦: LUAD 可直接進行研究規劃；LUSC 需補充外部資料

## Detailed Assessment
### TCGA-LUAD
- ✓ Stage: present (TNM staging system)
- ✓ Vital Status: present (alive/dead)
- ✓ Days to Death: present (complete for deceased)
- ✓ Access: Public

### TCGA-LUSC
- ✓ Stage: present (TNM staging system)
- ✗ Days to Death: NOT_FOUND
- ✗ Censoring: partial
- ✓ Access: Public, mixed tissue sources

## Evidence & Audit Trail
每個結論都必須含 `evidence_id`

| Claim | Evidence ID | Status |
|-------|-------------|--------|
| LUAD 具備 vital_status | ev_luad_001 | NORMAL |
| LUAD 具備 days_to_death | ev_luad_002 | NORMAL |
| LUSC 具備 vital_status | ev_lusc_001 | NORMAL |
| LUSC 具備 days_to_death | ev_lusc_002 | NOT_FOUND |

## Manual Review Checklist
- [ ] 確認 LUSC censoring 資料源
- [ ] 檢查外部 clinical trial database 中是否有 LUSC follow-up 資料
- [ ] 驗證 stage 編碼規則是否一致
```

---

#### 3. `data_dictionary.md`

**用途**: 記錄從 GDC Data Dictionary 擷取的所有欄位定義

**格式**: Markdown 表格

```markdown
# GDC Data Dictionary Snapshot

## Diagnosis Fields (Used in this analysis)

| Field | Type | Unit | Values | Description |
|-------|------|------|--------|-------------|
| `diagnosis.primary_diagnosis` | string | - | [ICD-10 codes] | Primary cancer diagnosis code |
| `diagnosis.stage` | string | - | [Stage I, II, III, IV] | TNM staging system |
| `diagnosis.vital_status` | keyword | - | [alive, dead] | Patient vital status at last follow-up |
| `diagnosis.days_to_death` | integer | days | [0, ∞) | Days between diagnosis and death |

## Clinical Fields

| Field | Type | Unit | Values | Description |
|-------|------|------|--------|-------------|
| `clinical.gender` | keyword | - | [male, female] | Patient biological sex |
| `clinical.age_at_initial_pathological_diagnosis` | integer | years | [0, 120] | Age at diagnosis |

## MAPPING CONFLICTS DETECTED
- `stage`: expected string, but some responses return structured object with stage_event[]
```

---

#### 4. `trace.jsonl`

**用途**: 完整的審計軌跡，用於事後調查每一步決策

**格式**: JSON Lines（每行一個 JSON object）

```jsonl
{"step": 1, "action": "plan", "timestamp": "2024-01-15T10:30:00Z", "task": "fetch LUAD project card"}
{"step": 2, "action": "fetch", "timestamp": "2024-01-15T10:30:05Z", "url": "https://api.gdc.cancer.gov/projects?project_id=TCGA-LUAD", "http_status": 200, "response_size_bytes": 2450, "response_sha256": "abc123..."}
{"step": 3, "action": "normalize", "timestamp": "2024-01-15T10:30:06Z", "parsed_fields": 12, "harness_condition": "NORMAL", "evidence_id": "ev_luad_001"}
{"step": 4, "action": "evidence_gate", "timestamp": "2024-01-15T10:30:07Z", "evidence_id": "ev_luad_001", "required_metadata": ["endpoint", "url", "request_timestamp", "http_status", "response_sha256", "parser_version"], "status": "PASS"}
{"step": 5, "action": "check", "timestamp": "2024-01-15T10:30:08Z", "claim": "LUAD stage field exists", "result": "verified", "confidence": 0.99}
```

**每行欄位**:
- `step`: 序號
- `action`: plan, fetch, normalize, evidence_gate, check, report, review
- `timestamp`: ISO 8601
- `evidence_id`: (如適用) 證據編號
- `harness_condition`: NORMAL / SCHEMA / NOT_FOUND / CONFLICT
- 其他依 action 類型的元數據

---

#### 5. `run_manifest.json`

**用途**: 執行的元數據摘要，用於批次追蹤

**格式**: JSON 單一 object

```json
{
  "run_id": "run_20240115_103000",
  "timestamp": "2024-01-15T10:30:00Z",
  "config": "configs/task_spec.yaml",
  "python_version": "3.11.7",
  "gdc_scout_version": "0.2.1",
  "output_dir": "outputs/latest",
  "artifacts_generated": [
    "dataset_cards.csv",
    "fit_for_question.md",
    "data_dictionary.md",
    "trace.jsonl",
    "run_manifest.json",
    "eval_report.json",
    "review_checklist.md",
    "source_snapshot.json"
  ],
  "total_api_calls": 24,
  "total_time_seconds": 145.3,
  "harness_summary": {
    "NORMAL": 156,
    "SCHEMA": 3,
    "NOT_FOUND": 2,
    "CONFLICT": 1
  }
}
```

---

#### 6. `eval_report.json`

**用途**: 數據品質與可採信性評估報告

**格式**: JSON，結構化指標

```json
{
  "timestamp": "2024-01-15T10:35:00Z",
  "evaluation_config": {
    "confidence_threshold": 0.8,
    "evidence_required_fields": 6
  },
  "overall_confidence": 0.92,
  "confidence_breakdown": {
    "LUAD": {
      "stage": 0.99,
      "survival": 0.95,
      "access": 1.0,
      "overall": 0.98
    },
    "LUSC": {
      "stage": 0.99,
      "survival": 0.65,
      "access": 1.0,
      "overall": 0.88
    }
  },
  "evidence_completeness": {
    "total_claims": 162,
    "normal": 156,
    "schema": 3,
    "not_found": 2,
    "conflict": 1,
    "completeness_rate": 0.963
  },
  "schema_validation": {
    "mapped_fields": 18,
    "matched": 17,
    "mismatches": 1,
    "validation_rate": 0.944
  },
  "recommendations": [
    {
      "priority": "HIGH",
      "project": "LUSC",
      "issue": "Days to death field not found in API response",
      "suggested_action": "Check GDC data dictionary for alternative survival endpoint field names"
    },
    {
      "priority": "MEDIUM",
      "project": "LUAD",
      "issue": "Stage field type mismatch between mapping and response",
      "suggested_action": "Verify whether stage should be extracted from stage_event or TNM staging"
    }
  ]
}
```

---

#### 7. `review_checklist.md`

**用途**: 人工審查清單，包含所有 NOT_FOUND、SCHEMA、CONFLICT cases

**格式**: Markdown checklist

```markdown
# Manual Review Checklist

Generated: 2024-01-15T10:35:00Z

## SCHEMA Issues (Harness Condition: BLOCK)
需要檢查配置或 API mapping 是否正確

- [ ] **Evidence ID: ev_luad_schema_001**
  - Field: `project_id`
  - Issue: Empty or null value
  - Severity: CRITICAL
  - Action: Update config/api_mapping.json
  - Reviewed by: _______
  - Date: _______

---

## NOT_FOUND Cases (Harness Condition: STOP)
查詢返回空結果，需人工確認是否嘗試替代資料源

- [ ] **Evidence ID: ev_lusc_notfound_001**
  - Query: GET /cases?project=TCGA-LUSC&expand=diagnoses.days_to_death
  - Result: 0 hits
  - Expected: ≥ 100 cases with days_to_death
  - Severity: HIGH
  - Action: 
    1. Check GDC data dictionary for alternative field names (e.g., `days_to_last_follow_up`)
    2. Query `/cases?project=TCGA-LUSC&expand=diagnoses.days_to_last_follow_up`
    3. If still empty, check TCIA or dbGaP for external follow-up data
  - Reviewed by: _______
  - Date: _______

---

## CONFLICT Cases (Harness Condition: REVIEW)
Mapping 或 API response 衝突，需人工判斷

- [ ] **Evidence ID: ev_luad_conflict_001**
  - Field: `stage`
  - Mapping says: string (values: "Stage I", "Stage II", "Stage III", "Stage IV")
  - API returns: object with { stage_event: [{tnm_edition: "8th", tnm_stage: "IA"}] }
  - Severity: MEDIUM
  - Action:
    1. Confirm TNM edition consistency across LUAD dataset
    2. Decide: extract `stage_event[0].tnm_stage` or stay with text description?
    3. Update parser logic and re-run evaluation
  - Reviewed by: _______
  - Date: _______

---

## Summary Table

| Category | Count | Status |
|----------|-------|--------|
| SCHEMA (BLOCK) | 3 | Requires config fix |
| NOT_FOUND (STOP) | 2 | Requires manual verification |
| CONFLICT (REVIEW) | 1 | Requires decision |
| **Total Items to Review** | **6** | **Action Required** |

## Sign-off

- [ ] All SCHEMA issues resolved
- [ ] All NOT_FOUND cases verified or flagged for external data
- [ ] All CONFLICT cases decision made & parser updated
- [ ] Re-evaluation run completed
- Reviewed by: _________________ Date: _______
- Approved by: _________________ Date: _______
```

---

#### 8. `source_snapshot.json`

**用途**: 記錄 API response 原始快照，供事後查核

**格式**: JSON，鍵值對應 evidence_id → response

```json
{
  "ev_luad_001": {
    "evidence_id": "ev_luad_001",
    "endpoint": "/projects",
    "query_parameters": {
      "project_id": "TCGA-LUAD"
    },
    "request_url": "https://api.gdc.cancer.gov/projects?project_id=TCGA-LUAD",
    "request_method": "GET",
    "request_timestamp": "2024-01-15T10:30:05Z",
    "http_status": 200,
    "response_headers": {
      "content-type": "application/json",
      "content-length": 2450
    },
    "response_sha256": "abc123def456...",
    "response_body_truncated": false,
    "parser_version": "0.2.1",
    "parsed_data": {
      "project_id": "TCGA-LUAD",
      "name": "Lung Adenocarcinoma",
      "case_count": 585,
      "file_count": 12450,
      "disease_type": "Lung Cancer",
      "primary_site": "Lung"
    }
  },
  "ev_lusc_notfound_002": {
    "evidence_id": "ev_lusc_notfound_002",
    "endpoint": "/cases",
    "query_parameters": {
      "project": "TCGA-LUSC",
      "expand": "diagnoses.days_to_death"
    },
    "request_url": "https://api.gdc.cancer.gov/cases?project=TCGA-LUSC&expand=diagnoses.days_to_death",
    "request_timestamp": "2024-01-15T10:31:15Z",
    "http_status": 200,
    "response_body": {
      "data": {
        "hits": []
      },
      "warnings": "Field 'days_to_death' may not be populated for TCGA-LUSC. Consider using 'days_to_last_follow_up' instead."
    },
    "harness_condition": "NOT_FOUND"
  }
}
```

---

## Harness 護欄條件判斷樹

### 快速決策流程圖

```
Request sent to GDC API
  ↓
[CHECK 1] Response HTTP status = 200?
  ├─ NO → Retry (max 3 times) → Fail → harness: ERROR
  └─ YES ↓
[CHECK 2] Required fields present (project_id, evidence_ids)?
  ├─ NO → harness: SCHEMA (BLOCK) → reject output
  └─ YES ↓
[CHECK 3] Response hits > 0?
  ├─ NO → harness: NOT_FOUND (STOP) → mark unverified, add to review checklist
  └─ YES ↓
[CHECK 4] Data matches mapping/data_dictionary?
  ├─ NO → harness: CONFLICT (REVIEW) → mark unverified, add to review checklist
  └─ YES ↓
[CHECK 5] Evidence metadata complete (6 items)?
  ├─ NO → harness: SCHEMA (BLOCK)
  └─ YES ↓
✓ NORMAL (PASS) → Include in report with full audit trail
```

### 詳細條件定義

#### 1️⃣ NORMAL (PASS)
- ✓ HTTP 200
- ✓ 必要欄位完整
- ✓ API 返回 ≥1 結果
- ✓ 數據與 mapping 一致
- ✓ 證據元數據完整 (6 項)

**輸出**: evidence 納入報告，包含完整審計軌跡
**日誌級別**: INFO
**範例**: 

```
LUAD stage field
├─ Query: /cases?project=TCGA-LUAD&expand=diagnoses.stage
├─ Result: 585 hits with stage values
├─ Harness: NORMAL
├─ Evidence ID: ev_luad_001
├─ Status: ✓ VERIFIED
└─ Confidence: 0.99
```

---

#### 2️⃣ SCHEMA (BLOCK)
- ✗ 必要欄位缺失（project_id, evidence_ids 為空/null）
- ✗ 證據元數據不完整（少於 6 項必要項目）
- ✗ 欄位型態不符 (預期 string，收到 object)

**輸出**: claim 拒絕，自動標記 `unverified`
**日誌級別**: ERROR
**後續**: 需要人工檢查配置或 API mapping

**範例**:

```yaml
Error: Missing required field 'project_id' in config
  Location: configs/task_spec.yaml, line 12
  Harness: SCHEMA (BLOCK)
  Action: Fix config and re-run
```

---

#### 3️⃣ NOT_FOUND (STOP)
- API 返回 HTTP 200，但 `hits: []`
- 不進行推測補值
- 不自動切換 project
- 需要人工確認替代資料源

**輸出**: 標記 `unverified`，列入 review_checklist.md
**日誌級別**: WARNING
**後續**: 人工 review 與決策

**決策樹**:
```
Query returns 0 hits
  ├─ Reason 1: 欄位名稱錯誤
  │  └─ Action: Check data_dictionary.md for correct field name
  ├─ Reason 2: 該 project 確實無該欄位
  │  └─ Action: Use alternative field or external data source
  └─ Reason 3: API 版本變更
     └─ Action: Check GDC API changelog and update query
```

**範例**:

```
NOT_FOUND: LUSC days_to_death
  ├─ Query: GET /cases?project=TCGA-LUSC&expand=diagnoses.days_to_death
  ├─ Result: 0 hits (expected ≥ 100)
  ├─ Evidence ID: ev_lusc_notfound_002
  ├─ Status: ✗ UNVERIFIED
  ├─ Harness: NOT_FOUND (STOP)
  └─ Review action: 
      1. Query alternative: days_to_last_follow_up
      2. Check TCIA database
      3. Verify GDC data dictionary version
```

---

#### 4️⃣ CONFLICT (REVIEW)
- Claim 不在 mapping 中 **OR**
- API response 與 mapping/data_dictionary 衝突
  - 型態衝突 (mapping: keyword, response: object)
  - 值域衝突 (mapping: ["Stage I", "II", "III", "IV"], response: ["0", "1", "2", "3"])
  - 欄位名稱衝突 (mapping: "stage", response: "stage_event[].tnm_stage")

**輸出**: claim 標記 `unverified`，詳細衝突記錄進 review_checklist.md
**日誌級別**: WARNING
**後續**: 人工決策後更新 parser

**必須檢查**:
- Mapping 是否過時
- API 文件是否已更新
- 是否為已知 ETL 問題
- 是否需要修改 parser 邏輯

**範例**:

```
CONFLICT: LUAD stage data type
  ├─ Field: diagnosis.stage
  ├─ Mapping expects: keyword (string)
  ├─ API response: object
  │  {
  │    "stage_event": [
  │      {
  │        "tnm_edition": "8th",
  │        "tnm_stage": "IA",
  │        "tnm_m": "0",
  │        "tnm_n": "0",
  │        "tnm_t": "1"
  │      }
  │    ]
  │  }
  ├─ Evidence ID: ev_luad_conflict_001
  ├─ Status: ✗ UNVERIFIED
  ├─ Harness: CONFLICT (REVIEW)
  └─ Review action:
      1. Verify TNM edition consistency (all "8th"?)
      2. Decide extraction rule: use tnm_stage or reconstruct "Stage I"?
      3. Update parser at gdc_scout/parsers/stage_parser.py
      4. Re-run evaluation and confirm
```

---

## Harness 運作流程時序圖

```
Time →

T0: Start
  ├─ Read config
  └─ Prepare API calls

T1: Plan Phase
  ├─ Generate query list
  └─ Log [step=1, action=plan]

T2: Fetch Phase (for each query)
  ├─ HTTP GET to GDC API
  ├─ Store response (SHA-256 hash)
  └─ Log [step=2, action=fetch, evidence_id=?, harness=?]
      ├─ HTTP 200 → proceed
      ├─ HTTP 4xx/5xx + retry < 3 → retry
      └─ retry ≥ 3 → harness: ERROR

T3: Normalize Phase
  ├─ Parse response JSON
  ├─ Extract fields
  └─ Check for missing fields
      ├─ Missing required → harness: SCHEMA (BLOCK)
      ├─ hits = 0 → harness: NOT_FOUND (STOP)
      └─ Otherwise → proceed

T4: Evidence Gate Phase
  ├─ Check evidence metadata completeness
  │  (endpoint, url, timestamp, http_status, sha256, parser_version)
  ├─ Missing any → harness: SCHEMA (BLOCK)
  └─ Complete → attach evidence_id, proceed

T5: Check Phase
  ├─ Validate against mapping
  ├─ Validate against data_dictionary
  └─ Type/value conflict → harness: CONFLICT (REVIEW)

T6: Report Phase
  ├─ NORMAL evidence → include with full trail
  ├─ SCHEMA/NOT_FOUND/CONFLICT → mark unverified
  └─ Generate fit_for_question.md

T7: Review Phase
  ├─ Extract all non-NORMAL cases
  ├─ Generate review_checklist.md
  └─ Output source_snapshot.json (raw responses)

T8: End
  └─ All 8 artifacts saved to outputs/latest/
```

---

## Safety Rules（安全規則）

1. **公開數據僅取 Metadata**
   - ✓ 允許: 查詢欄位存在性、型態、覆蓋率
   - ✗ 禁止: 下載 controlled files、病人隱私資訊

2. **分開判定**
   - `metadata visible` vs `file downloadable` 分開追蹤
   - 結果明確標示 access level

3. **禁止推測補值**
   - NOT_FOUND 時不自動改查其他欄位名
   - 不自動替換 project (LUAD 無 field 時，不自動轉查 LUSC)
   - 需要人工確認與決策

4. **Mapping 衝突時停止**
   - 不進行類型轉換
   - 不進行值域映射
   - 標記 CONFLICT，要求人工 review

5. **重試策略**
   - HTTP 3 次重試，指數退避
   - Agent 不允許無限迴圈
   - 超時後標記 ERROR

6. **審計軌跡完整性**
   - 每個 claim 必須含 evidence_id
   - evidence_id 必須指向 source_snapshot.json
   - 不可追蹤的結論自動標記 unverified

---

## 典型執行場景

### 場景 1: 完整順利執行

```bash
# 1. 驗證安裝
python -m gdc_scout --version
# Output: gdc_scout 0.2.1

# 2. 執行評估
python -m gdc_scout run --config configs/task_spec.yaml --output outputs/latest

# 預期: 約 2-3 分鐘，所有 API 調用成功

# 3. 查看結果
cat outputs/latest/fit_for_question.md
# Output: Yes - LUAD 與 LUSC 都適合進行初步 stage-survival 研究規劃

# 4. 人工審查
cat outputs/latest/review_checklist.md
# Output: 6 items requiring review (3 SCHEMA, 2 NOT_FOUND, 1 CONFLICT)

# 5. 評估數據品質
python -m gdc_scout eval --output outputs/latest

# 輸出: overall_confidence = 0.92 (high)
```

---

### 場景 2: 遇到 CONFLICT 衝突

```bash
# 1. 執行評估
python -m gdc_scout run --config configs/task_spec.yaml --output outputs/latest

# 2. 發現 CONFLICT
# > WARNING: stage field type mismatch (ev_luad_conflict_001)
# > Expected: keyword (string)
# > Got: object { stage_event: [...] }

# 3. 查看詳情
jq '.ev_luad_conflict_001' outputs/latest/source_snapshot.json

# 4. 人工決策
# > Decision: Extract tnm_stage from stage_event[0]

# 5. 更新 parser
# 編輯: gdc_scout/parsers/stage_parser.py
# 邏輯: response.stage_event[0].tnm_stage if response.stage_event else null

# 6. 重新執行
python -m gdc_scout run --config configs/task_spec.yaml --output outputs/latest

# 7. 驗證修正
python -m gdc_scout eval --output outputs/latest
```

---

## 官方來源

- [GDC Search and Retrieval API](https://docs.gdc.cancer.gov/API/Users_Guide/Search_and_Retrieval/)
- [GDC Data Dictionary](https://docs.gdc.cancer.gov/Data_Dictionary/)
- [GDC API documentation](https://docs.gdc.cancer.gov/API/)
- [GDC Data Portal](https://portal.gdc.cancer.gov/)
- [TCGA-LUAD 專案頁面](https://portal.gdc.cancer.gov/projects/TCGA-LUAD)
- [TCGA-LUSC 專案頁面](https://portal.gdc.cancer.gov/projects/TCGA-LUSC)

---

## 常見問題 (FAQ)

**Q: 執行時出現 timeout 怎麼辦？**
A: 在 `task_spec.yaml` 增加 `api.timeout` 值（預設 30 秒）

```yaml
api:
  timeout: 60
  max_retries: 5
```

**Q: 如何只執行乾跑 (dry-run)？**
A: 加上 `--dry-run` 旗標

```bash
python -m gdc_scout run --config configs/task_spec.yaml --dry-run
```

**Q: 如何重新運行評估而不重新調用 API？**
A: 使用已存在的 `source_snapshot.json`

```bash
python -m gdc_scout eval --output outputs/latest --use-cache
```

**Q: 如何並行執行多個 projects？**
A: 在 `task_spec.yaml` 增加更多 project 條目，系統會自動並行化

```yaml
projects:
  luad: ...
  lusc: ...
  brca: ...  # 新增其他癌症類型
  coad: ...
```

---

## License

MIT

---

## 版本歷史

| 版本 | 日期 | 主要變更 |
|------|------|--------|
| 0.2.1 | 2024-01-15 | 完整 Harness 護欄邏輯、改進文檔清晰度 |
| 0.2.0 | 2024-01-10 | 添加 evidence gate、review checklist |
| 0.1.0 | 2024-01-01 | 初始發版 |

