"""Small, dependency-free loader for the YAML subset used by the scout."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


def _scalar(text: str) -> Any:
    text = text.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if text.lower() in {"true", "false"}:
            return text.lower() == "true"
        try:
            return float(text) if "." in text else int(text)
        except ValueError:
            return text


def _simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        while stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if content.startswith("- "):
            if not isinstance(parent, list):
                raise ConfigError(f"line {number}: list item has no list parent")
            parent.append(_scalar(content[2:]))
            continue
        if ":" not in content:
            raise ConfigError(f"line {number}: expected key: value")
        key, value = content.split(":", 1)
        key, value = key.strip(), value.strip()
        if value:
            parent[key] = _scalar(value)
        else:
            # Look ahead only to decide list vs mapping.
            following = text.splitlines()[number:]
            is_list = any(x.strip() and not x.lstrip().startswith("#") and x.strip().startswith("- ")
                          for x in following[:1])
            child: Any = [] if is_list else {}
            parent[key] = child
            stack.append((indent, child))
    return root


def load_config(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"config not found: {path}")
    text = path.read_text(encoding="utf-8-sig")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = _simple_yaml(text)
    projects = data.get("projects")
    if not isinstance(projects, dict) or not projects:
        raise ConfigError("projects must be a non-empty mapping")
    for key, project in projects.items():
        if not isinstance(project, dict) or not project.get("project_id"):
            raise ConfigError(f"projects.{key}.project_id is required")
    api = data.setdefault("api", {})
    api.setdefault("endpoint", "https://api.gdc.cancer.gov")
    api.setdefault("timeout", 30)
    api.setdefault("max_retries", 3)
    api.setdefault("retry_backoff", 2.0)
    evidence = data.setdefault("evidence", {})
    evidence.setdefault("required_fields", ["endpoint", "url", "request_timestamp", "http_status", "response_sha256", "parser_version"])
    return data

