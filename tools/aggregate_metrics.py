#!/usr/bin/env python3
"""Aggregate per-run metrics.json files for an experiment directory."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * pct
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def aggregate(exp_dir: Path) -> dict[str, Any]:
    runs_dir = exp_dir / "runs"
    by_metric: dict[str, list[float]] = {}
    per_run: list[dict[str, Any]] = []

    for metrics_path in sorted(runs_dir.glob("iter_*/metrics.json")):
        iter_name = metrics_path.parent.name
        if "warmup" in iter_name:
            continue
        metrics = load_json(metrics_path)
        per_run.append({"iter": iter_name, "metrics": metrics})
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                by_metric.setdefault(key, []).append(float(value))

    result: dict[str, Any] = {"metrics": {}, "runs": per_run}
    for key, values in sorted(by_metric.items()):
        result["metrics"][key] = {
            "n": len(values),
            "mean": statistics.fmean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "p50": percentile(values, 0.50),
            "p95": percentile(values, 0.95),
            "p99": percentile(values, 0.99),
            "min": min(values),
            "max": max(values),
            "values": values,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("exp_dir", type=Path)
    args = parser.parse_args()
    out = aggregate(args.exp_dir)
    (args.exp_dir / "aggregated_metrics.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.exp_dir / 'aggregated_metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
