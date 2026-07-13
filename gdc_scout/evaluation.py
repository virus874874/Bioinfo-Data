from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from .client import utcnow


def evaluate(output: str | Path, threshold: float = 0.8) -> dict:
    output = Path(output)
    snapshot_path, cards_path = output / "source_snapshot.json", output / "dataset_cards.csv"
    if not snapshot_path.is_file() or not cards_path.is_file():
        raise FileNotFoundError("run artifacts missing; expected source_snapshot.json and dataset_cards.csv")
    snapshots = json.loads(snapshot_path.read_text(encoding="utf-8"))
    with cards_path.open(encoding="utf-8-sig", newline="") as f:
        cards = list(csv.DictReader(f))
    required = ["endpoint", "url", "request_timestamp", "http_status", "response_sha256", "parser_version"]
    complete = sum(all(item.get(k) not in (None, "") for k in required) for item in snapshots.values())
    conditions = Counter(item.get("harness_condition", "NORMAL").lower() for item in snapshots.values())
    breakdown = {}
    for card in cards:
        stage, vital, endpoint = (float(card[k]) for k in ("stage_coverage", "vital_status_coverage", "endpoint_coverage"))
        access = 1.0 if card["access_level"] in {"public", "controlled", "mixed"} else 0.5
        overall = round((stage + vital + endpoint + access) / 4, 3)
        breakdown[card["project_id"]] = {"stage": stage, "survival": round((vital + endpoint) / 2, 3), "access": access, "overall": overall}
    confidence = round(sum(x["overall"] for x in breakdown.values()) / len(breakdown), 3) if breakdown else 0.0
    total = len(snapshots)
    report = {"timestamp": utcnow(), "evaluation_config": {"confidence_threshold": threshold, "evidence_required_fields": len(required)}, "overall_confidence": confidence, "passes_threshold": confidence >= threshold, "confidence_breakdown": breakdown, "evidence_completeness": {"total_claims": total, **conditions, "complete_evidence": complete, "completeness_rate": round(complete / total, 3) if total else 0.0}, "recommendations": []}
    if confidence < threshold:
        report["recommendations"].append({"priority": "HIGH", "issue": "Overall confidence is below threshold", "suggested_action": "Review coverage and harness issues before study planning"})
    if conditions.get("schema") or conditions.get("not_found") or conditions.get("conflict"):
        report["recommendations"].append({"priority": "HIGH", "issue": "Non-NORMAL evidence exists", "suggested_action": "Complete review_checklist.md and rerun"})
    (output / "eval_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report

