from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def _iso_to_utc(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _request_json(url: str, token: str) -> dict[str, Any]:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310 - GitHub API only
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("invalid API payload root")
    return payload


def select_successful_run(
    *,
    workflow_runs: list[dict[str, Any]],
    head_sha: str,
    max_age_hours: float,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    sha = str(head_sha).strip()
    items = [item for item in workflow_runs if str(item.get("head_sha") or "") == sha]
    items = [item for item in items if str(item.get("conclusion") or "") == "success"]
    if not items:
        return None
    items.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
    selected = items[0]
    if max_age_hours <= 0:
        return selected
    ref_time = now or datetime.now(timezone.utc)
    updated = _iso_to_utc(str(selected.get("updated_at") or selected.get("created_at") or ""))
    if updated is None:
        return None
    age_h = (ref_time - updated).total_seconds() / 3600.0
    if age_h > float(max_age_hours):
        return None
    return selected


def evaluate_gate(
    *,
    api_payload: dict[str, Any],
    head_sha: str,
    max_age_hours: float,
    now: datetime | None = None,
) -> dict[str, Any]:
    runs = [item for item in (api_payload.get("workflow_runs") or []) if isinstance(item, dict)]
    selected = select_successful_run(
        workflow_runs=runs,
        head_sha=head_sha,
        max_age_hours=max_age_hours,
        now=now,
    )
    if selected is None:
        return {
            "passed": False,
            "head_sha": str(head_sha),
            "reason": "no_recent_successful_stage2_quality_gate_run",
            "workflow_runs_checked": len(runs),
        }
    return {
        "passed": True,
        "head_sha": str(head_sha),
        "reason": "ok",
        "workflow_runs_checked": len(runs),
        "selected_run": {
            "id": selected.get("id"),
            "html_url": selected.get("html_url"),
            "event": selected.get("event"),
            "status": selected.get("status"),
            "conclusion": selected.get("conclusion"),
            "created_at": selected.get("created_at"),
            "updated_at": selected.get("updated_at"),
        },
    }


def _build_runs_url(repo: str, workflow_file: str, head_sha: str) -> str:
    owner_repo = str(repo).strip()
    if "/" not in owner_repo:
        raise ValueError(f"invalid repo format: {owner_repo}")
    workflow = urllib.parse.quote(str(workflow_file).strip(), safe="")
    sha = urllib.parse.quote(str(head_sha).strip(), safe="")
    return (
        f"https://api.github.com/repos/{owner_repo}/actions/workflows/{workflow}/runs"
        f"?head_sha={sha}&status=completed&per_page=100"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check stage2-quality-gate success for a target commit SHA")
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--sha", required=True, help="target commit SHA")
    parser.add_argument("--workflow-file", default="stage2-quality-gate.yml")
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    parser.add_argument("--max-age-hours", type=float, default=168.0)
    parser.add_argument("--output")
    args = parser.parse_args()

    token = str(os.getenv(str(args.token_env)) or "").strip()
    if not token:
        raise RuntimeError(f"missing token in env: {args.token_env}")

    url = _build_runs_url(str(args.repo), str(args.workflow_file), str(args.sha))
    try:
        payload = _request_json(url, token)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"github api error: status={exc.code}, detail={detail}") from exc

    result = evaluate_gate(
        api_payload=payload,
        head_sha=str(args.sha),
        max_age_hours=float(args.max_age_hours),
    )
    result["repo"] = str(args.repo)
    result["workflow_file"] = str(args.workflow_file)
    result["max_age_hours"] = float(args.max_age_hours)
    result["queried_at"] = datetime.now(timezone.utc).isoformat()

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if bool(result.get("passed")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
