from __future__ import annotations

import csv
import json
import platform
import time
from collections import Counter
from pathlib import Path
from typing import Any

from . import __version__
from .client import GDCClient, utcnow


STAGE_FIELDS = ("diagnoses.ajcc_pathologic_stage", "diagnoses.ajcc_clinical_stage", "diagnoses.figo_stage")
SURVIVAL_FIELDS = ("demographic.vital_status", "demographic.days_to_death", "diagnoses.days_to_last_follow_up")


class Scout:
    def __init__(self, config: dict[str, Any], output: str | Path, config_path: str):
        self.config, self.output, self.config_path = config, Path(output), config_path
        api = config["api"]
        self.client = GDCClient(api["endpoint"], api["timeout"], api["max_retries"], api["retry_backoff"])
        self.required = config["evidence"]["required_fields"]
        self.snapshots: dict[str, Any] = {}
        self.trace: list[dict[str, Any]] = []
        self.issues: list[dict[str, Any]] = []
        self.step = 0

    def log(self, action: str, **fields: Any) -> None:
        self.step += 1
        self.trace.append({"step": self.step, "action": action, "timestamp": utcnow(), **fields})

    def _fetch(self, evidence_id: str, path: str, params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        body, evidence = self.client.get(path, params)
        missing = [field for field in self.required if evidence.get(field) in (None, "")]
        condition = "SCHEMA" if missing else "NORMAL"
        snapshot = {"evidence_id": evidence_id, **evidence, "response_body": body, "harness_condition": condition}
        self.snapshots[evidence_id] = snapshot
        self.log("fetch", evidence_id=evidence_id, url=evidence["url"], http_status=evidence["http_status"], response_sha256=evidence["response_sha256"])
        self.log("evidence_gate", evidence_id=evidence_id, required_metadata=self.required, status="FAIL" if missing else "PASS")
        if missing:
            self.issues.append({"evidence_id": evidence_id, "condition": "SCHEMA", "field": ", ".join(missing), "issue": "Missing evidence metadata", "severity": "CRITICAL"})
        return body, evidence

    @staticmethod
    def _hits(body: dict[str, Any]) -> list[dict[str, Any]]:
        return body.get("data", {}).get("hits", [])

    def run(self) -> list[dict[str, Any]]:
        started = time.monotonic()
        self.output.mkdir(parents=True, exist_ok=True)
        self.log("plan", task="inspect projects, cases, files, and case mapping")
        mapping_body, _ = self._fetch("ev_mapping_001", "/cases/_mapping", {})
        mapping = mapping_body.get("_mapping", mapping_body.get("fields", mapping_body.get("data", {}).get("fields", {})))
        cards = []
        for alias, spec in self.config["projects"].items():
            pid = spec["project_id"]
            def filt(field: str) -> str:
                return json.dumps({"op": "=", "content": {"field": field, "value": pid}}, separators=(",", ":"))
            project_body, _ = self._fetch(f"ev_{alias}_project", "/projects", {"filters": filt("project_id"), "format": "JSON", "size": 1})
            cases_body, _ = self._fetch(f"ev_{alias}_cases", "/cases", {"filters": filt("project.project_id"), "format": "JSON", "size": 2000, "expand": "diagnoses,demographic", "fields": "case_id"})
            file_body, _ = self._fetch(f"ev_{alias}_files", "/files", {"filters": filt("cases.project.project_id"), "format": "JSON", "size": 0, "facets": "access"})
            project_hits, case_hits = self._hits(project_body), self._hits(cases_body)
            if not project_hits:
                self._not_found(f"ev_{alias}_project", pid, "project")
            if not case_hits:
                self._not_found(f"ev_{alias}_cases", pid, "cases")
            project = project_hits[0] if project_hits else {}
            stage_count = sum(self._has_stage(case) for case in case_hits)
            vital_count = sum(bool((case.get("demographic") or {}).get("vital_status")) for case in case_hits)
            endpoint_count = sum(self._has_endpoint(case) for case in case_hits)
            access, file_count = self._file_summary(file_body)
            summary = project.get("summary", {})
            card = {
                "project_id": pid, "project_name": project.get("name") or spec.get("name", alias),
                "case_count": summary.get("case_count", len(case_hits)),
                "file_count": summary.get("file_count", file_count),
                "stage_field_present": bool(stage_count), "survival_field_present": bool(vital_count and endpoint_count),
                "access_level": access, "last_updated": utcnow(),
                "stage_coverage": self._ratio(stage_count, len(case_hits)),
                "vital_status_coverage": self._ratio(vital_count, len(case_hits)),
                "endpoint_coverage": self._ratio(endpoint_count, len(case_hits)),
                "evidence_ids": [f"ev_{alias}_project", f"ev_{alias}_cases", f"ev_{alias}_files"],
            }
            cards.append(card)
            self.log("normalize", evidence_id=f"ev_{alias}_cases", parsed_fields=len(case_hits), harness_condition="NORMAL" if case_hits else "NOT_FOUND")
            self.log("check", evidence_id=f"ev_{alias}_cases", claim=f"{pid} stage and survival metadata coverage measured", result="verified" if case_hits else "unverified")
        self.log("report", artifacts=8)
        self._write(cards, mapping, time.monotonic() - started)
        self.log("review", issue_count=len(self.issues))
        self._write_trace()
        # A run is self-contained and produces all eight promised artifacts.
        # The eval command can subsequently regenerate this with another threshold.
        from .evaluation import evaluate
        evaluate(self.output, 0.8)
        return cards

    def _not_found(self, evidence_id: str, pid: str, field: str) -> None:
        self.snapshots[evidence_id]["harness_condition"] = "NOT_FOUND"
        self.issues.append({"evidence_id": evidence_id, "condition": "NOT_FOUND", "field": field, "issue": f"No {field} hits for {pid}", "severity": "HIGH"})

    @staticmethod
    def _has_stage(case: dict[str, Any]) -> bool:
        return any(any(d.get(k) not in (None, "", "Not Reported", "Unknown") for k in ("ajcc_pathologic_stage", "ajcc_clinical_stage", "figo_stage")) for d in case.get("diagnoses", []))

    @staticmethod
    def _has_endpoint(case: dict[str, Any]) -> bool:
        demographic = case.get("demographic") or {}
        return demographic.get("days_to_death") is not None or any(
            d.get("days_to_death") is not None or d.get("days_to_last_follow_up") is not None
            for d in case.get("diagnoses", [])
        )

    @staticmethod
    def _ratio(n: int, total: int) -> float:
        return round(n / total, 4) if total else 0.0

    @staticmethod
    def _file_summary(body: dict[str, Any]) -> tuple[str, int]:
        data = body.get("data", {})
        total = data.get("pagination", {}).get("total", 0)
        buckets = data.get("aggregations", {}).get("access", {}).get("buckets", [])
        values = {str(b.get("key", "")).lower() for b in buckets if b.get("doc_count", 0)}
        access = "mixed" if len(values) > 1 else (next(iter(values)) if values else "unknown")
        return access, total

    def _write(self, cards: list[dict[str, Any]], mapping: dict[str, Any], duration: float) -> None:
        columns = ["project_id", "project_name", "case_count", "file_count", "stage_field_present", "survival_field_present", "access_level", "last_updated", "stage_coverage", "vital_status_coverage", "endpoint_coverage", "evidence_ids"]
        with (self.output / "dataset_cards.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns); writer.writeheader()
            for card in cards: writer.writerow({**card, "evidence_ids": ";".join(card["evidence_ids"])})
        (self.output / "source_snapshot.json").write_text(json.dumps(self.snapshots, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_fit(cards)
        self._write_dictionary(mapping)
        self._write_review()
        summary = Counter(s.get("harness_condition", "NORMAL") for s in self.snapshots.values())
        manifest = {"run_id": "run_" + utcnow().replace("-", "").replace(":", "").replace("T", "_").split(".")[0], "timestamp": utcnow(), "config": self.config_path, "python_version": platform.python_version(), "gdc_scout_version": __version__, "output_dir": str(self.output), "artifacts_generated": ["dataset_cards.csv", "fit_for_question.md", "data_dictionary.md", "trace.jsonl", "run_manifest.json", "eval_report.json", "review_checklist.md", "source_snapshot.json"], "total_api_calls": len(self.snapshots), "total_time_seconds": round(duration, 3), "harness_summary": dict(summary)}
        (self.output / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_fit(self, cards: list[dict[str, Any]]) -> None:
        ready = sum(c["stage_field_present"] and c["survival_field_present"] for c in cards)
        verdict = "Yes" if ready == len(cards) else ("Partial" if ready else "No")
        lines = ["# GDC Lung Cancer Stage-Survival Fitness Report", "", "## Executive Summary", "", f"**{verdict}** — {ready}/{len(cards)} projects show both stage metadata and a usable survival endpoint in the sampled public case metadata. This supports planning only, not survival inference.", "", "## Detailed Assessment", ""]
        for c in cards:
            lines += [f"### {c['project_id']}", "", f"- Stage metadata: {'present' if c['stage_field_present'] else 'not found'} ({c['stage_coverage']:.1%})", f"- Vital status: {c['vital_status_coverage']:.1%}", f"- Death/follow-up endpoint: {c['endpoint_coverage']:.1%}", f"- File access metadata: {c['access_level']}", f"- Evidence: `{c['evidence_ids'][1]}`, `{c['evidence_ids'][2]}`", ""]
        lines += ["## Limits", "", "Metadata visibility does not establish completeness, valid censoring, harmonized staging, downloadable file access, prognosis, treatment effect, causality, or clinical utility.", "", "## Evidence & Audit Trail", "", "Every assessment above links to `source_snapshot.json`; request metadata and hashes are recorded in `trace.jsonl`."]
        (self.output / "fit_for_question.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_dictionary(self, mapping: dict[str, Any]) -> None:
        fields = [*STAGE_FIELDS, *SURVIVAL_FIELDS]
        lines = ["# GDC Data Dictionary Snapshot", "", "This snapshot records relevant fields reported by the live `/cases/_mapping` endpoint.", "", "| Field | Mapping | Present |", "|---|---|---|"]
        for field in fields:
            info = mapping.get("cases." + field, {}) if isinstance(mapping, dict) else {}
            lines.append(f"| `{field}` | `{json.dumps(info, ensure_ascii=False)[:180]}` | {'yes' if info else 'no'} |")
            if not info:
                self.issues.append({"evidence_id": "ev_mapping_001", "condition": "SCHEMA", "field": field, "issue": "Field absent from live mapping", "severity": "MEDIUM"})
        (self.output / "data_dictionary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_review(self) -> None:
        lines = ["# Manual Review Checklist", "", f"Generated: {utcnow()}", ""]
        if not self.issues:
            lines += ["No SCHEMA, NOT_FOUND, or CONFLICT cases were detected.", ""]
        for condition in ("SCHEMA", "NOT_FOUND", "CONFLICT"):
            group = [x for x in self.issues if x["condition"] == condition]
            if group:
                lines += [f"## {condition} Cases", ""]
                for x in group:
                    lines += [f"- [ ] **{x['evidence_id']}** — `{x['field']}`: {x['issue']} ({x['severity']})", ""]
        lines += ["## Sign-off", "", "- [ ] All flagged cases reviewed", "- [ ] Any parser decisions documented", "- [ ] Evaluation re-run after changes"]
        (self.output / "review_checklist.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_trace(self) -> None:
        (self.output / "trace.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in self.trace), encoding="utf-8")
