#!/usr/bin/env python3
"""Render a deterministic Markdown report for an experiment directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by runtime users.
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc


def read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_variables(plan: dict[str, Any]) -> str:
    variables = plan.get("variables") or []
    if not variables:
        return "none"
    return ", ".join(f"{v.get('name')}={v.get('values')}" for v in variables)


def render_table(metrics: dict[str, Any]) -> str:
    if not metrics:
        return "| Metric | n | mean | std | p50 | p95 | p99 | min | max |\n|---|---|---|---|---|---|---|---|---|\n"
    lines = ["| Metric | n | mean | std | p50 | p95 | p99 | min | max |", "|---|---|---|---|---|---|---|---|---|"]
    for name, row in sorted(metrics.items()):
        lines.append(
            "| {name} | {n} | {mean:.4g} | {std:.4g} | {p50:.4g} | {p95:.4g} | {p99:.4g} | {min:.4g} | {max:.4g} |".format(
                name=name,
                n=row.get("n", 0),
                mean=row.get("mean", 0),
                std=row.get("std", 0),
                p50=row.get("p50", 0),
                p95=row.get("p95", 0),
                p99=row.get("p99", 0),
                min=row.get("min", 0),
                max=row.get("max", 0),
            )
        )
    return "\n".join(lines) + "\n"


def render(exp_dir: Path) -> str:
    plan_path = exp_dir / "plan.yaml"
    if not plan_path.is_file():
        raise SystemExit(f"missing {plan_path}")
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    status = read_json(exp_dir / "status.json", {"state": "UNKNOWN", "failure": None})
    aggregated = read_json(exp_dir / "aggregated_metrics.json", {"metrics": {}, "runs": []})
    exp = plan.get("experiment", {})
    target = plan.get("target", {})
    metrics = plan.get("metrics") or []
    failure = status.get("failure")

    conclusion = "성공 기준을 수동 검토하세요."
    if status.get("state") == "FAILED" and failure:
        conclusion = f"실험이 실패했습니다: {failure}"
    elif status.get("state") == "SUCCESS":
        conclusion = f"성공 기준 검토 필요: {plan.get('success_criteria', 'N/A')}"

    return f"""# Experiment {exp.get('id', exp_dir.name)}

## Summary
- **Status**: {status.get('state', 'UNKNOWN')}
- **Hypothesis**: {exp.get('hypothesis', 'N/A')}
- **결론 한 줄**: {conclusion}
- **주요 수치**: `aggregated_metrics.json` 참조

## Hypothesis & Plan
- 가설: {exp.get('hypothesis', 'N/A')}
- 성공 기준: {plan.get('success_criteria', 'N/A')}
- 변수: {summarize_variables(plan)}
- 측정 메트릭: {', '.join(m.get('name', '') for m in metrics)}
- 반복: {plan.get('iterations', 'N/A')}회 (warmup {plan.get('warmup_runs', 0)}회)

## Environment
- 대상 레포: {target.get('repo_path')} @ {target.get('commit')}
- 적용 패치: {target.get('patches') or []}

전체 환경: [`env/pre/`](./env/pre/), [`env/post/`](./env/post/)

## Results

### Aggregated (warmup 제외)
{render_table(aggregated.get('metrics', {}))}
## Anomalies & Warnings
- 실패 정보: {failure or '없음'}
- sanity_range 이탈: status.json 및 run logs 참조
- env pre/post 차이: env 디렉토리 비교 필요

## Conclusion
{conclusion}

## Artifacts
- plan.yaml: [`./plan.yaml`](./plan.yaml)
- 환경: [`./env/pre/`](./env/pre/), [`./env/post/`](./env/post/)
- 스크립트: [`./scripts/`](./scripts/)
- 원시 로그: [`./runs/`](./runs/)
- 집계 메트릭: [`./aggregated_metrics.json`](./aggregated_metrics.json)
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("exp_dir", type=Path)
    args = parser.parse_args()
    report = render(args.exp_dir)
    (args.exp_dir / "report.md").write_text(report, encoding="utf-8")
    print(f"wrote {args.exp_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
