#!/usr/bin/env python3
"""Validate an experiment plan before executor script generation."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by runtime users.
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc


ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-z0-9-]+_\d{3}$")
VAR_RE = re.compile(r"^[a-z][a-z0-9_]*$")
STEP_TYPES = {"setup", "baseline", "run", "collect", "teardown"}
POLICY = {
    "on_step_fail": "stop_and_preserve",
    "on_metric_out_of_range": "stop_and_preserve",
    "on_timeout": "stop_and_preserve",
    "auto_teardown": False,
}


class PlanError(Exception):
    def __init__(self, item: str, reason: str, value: Any = None, expected: str = ""):
        self.item = item
        self.reason = reason
        self.value = value
        self.expected = expected
        super().__init__(reason)


def fail(item: str, reason: str, value: Any = None, expected: str = "") -> None:
    raise PlanError(item, reason, value, expected)


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        fail("1. file exists", "plan.yaml file does not exist", str(path), "existing YAML file")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail("2. YAML parse", str(exc), str(path), "valid YAML")
    if not isinstance(data, dict):
        fail("2. YAML parse", "top-level YAML is not a mapping", type(data).__name__, "mapping")
    return data


def names_from_context(context: Path, section: str) -> set[str]:
    text = context.read_text(encoding="utf-8")
    if section == "probe":
        return set(re.findall(r"^#### probe: ([a-zA-Z0-9_]+)$", text, re.MULTILINE))
    if section == "collector":
        return set(re.findall(r"^#### collector: ([a-zA-Z0-9_]+)$", text, re.MULTILINE))
    raise ValueError(section)


def require_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        fail("3. required fields", f"missing or invalid mapping: {key}", value, "mapping")
    return value


def require_list(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        fail("3. required fields", f"missing or invalid list: {key}", value, "list")
    return value


def git_commit_exists(repo_path: str, commit: str) -> bool:
    result = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", f"{commit}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def validate(plan: dict[str, Any], plan_path: Path, context_path: Path, skip_local_checks: bool = False) -> None:
    if not context_path.is_file():
        fail("0. context file", "context file does not exist", str(context_path), "existing context file")

    probes = names_from_context(context_path, "probe")
    collectors = names_from_context(context_path, "collector")

    experiment = require_mapping(plan, "experiment")
    target = require_mapping(plan, "target")
    variables = require_list(plan, "variables")
    metrics = require_list(plan, "metrics")
    probe_cfg = require_mapping(plan, "probes")
    steps = require_list(plan, "steps")
    failure_policy = require_mapping(plan, "failure_policy")

    exp_id = experiment.get("id")
    if not isinstance(exp_id, str) or not ID_RE.match(exp_id):
        fail("4. id format", "invalid experiment.id", exp_id, r"YYYY-MM-DD_slug_001")
    if not experiment.get("hypothesis"):
        fail("3. required fields", "missing experiment.hypothesis", experiment.get("hypothesis"), "non-empty string")
    if not plan.get("success_criteria"):
        fail("3. required fields", "missing success_criteria", plan.get("success_criteria"), "non-empty string")

    repo_path = target.get("repo_path")
    commit = target.get("commit")
    if repo_path is not None and not skip_local_checks:
        if not isinstance(repo_path, str) or not os.path.isdir(repo_path):
            fail("5. target.repo_path", "repo_path is not a directory", repo_path, "existing directory or null")
        if not isinstance(commit, str) or not git_commit_exists(repo_path, commit):
            fail("6. target.commit", "commit does not resolve in repo_path", commit, "existing git commit")

    if not skip_local_checks:
        for patch in target.get("patches") or []:
            patch_path = Path(patch)
            if not patch_path.is_absolute():
                patch_path = plan_path.parent / patch_path
            if not patch_path.is_file():
                fail("7. patches", "patch file does not exist", patch, "existing file")

    for var in variables:
        if not isinstance(var, dict) or not VAR_RE.match(str(var.get("name", ""))):
            fail("3. required fields", "invalid variable name", var, "lowercase snake_case mapping")
        if "values" not in var or not isinstance(var["values"], list):
            fail("3. required fields", "variable.values must be a list", var, "list")

    if not metrics:
        fail("3. required fields", "metrics must contain at least one metric", metrics, "non-empty list")
    for metric in metrics:
        if not isinstance(metric, dict):
            fail("3. required fields", "metric must be a mapping", metric, "mapping")
        collector = metric.get("collector")
        if collector not in collectors:
            fail("8. collector names", "collector is not registered", collector, sorted(collectors))
        sanity = metric.get("sanity_range")
        if not isinstance(sanity, list) or len(sanity) != 2:
            fail("3. required fields", "metric.sanity_range must have two values", sanity, "[min, max]")

    for probe in (probe_cfg.get("base") or []) + (probe_cfg.get("extra") or []):
        if probe not in probes:
            fail("9. probe names", "probe is not registered", probe, sorted(probes))

    if not steps:
        fail("3. required fields", "steps must contain at least one step", steps, "non-empty list")
    for step in steps:
        if not isinstance(step, dict):
            fail("10. step.type", "step must be a mapping", step, "mapping")
        if step.get("type") not in STEP_TYPES:
            fail("10. step.type", "invalid step type", step.get("type"), sorted(STEP_TYPES))
        timeout = step.get("timeout_sec")
        if not isinstance(timeout, int) or timeout <= 0:
            fail("12. timeout_sec", "timeout_sec must be > 0", timeout, "positive integer")

    iterations = plan.get("iterations")
    if not isinstance(iterations, int) or iterations < 1:
        fail("11. iterations", "iterations must be >= 1", iterations, "positive integer")
    if plan.get("parallel") is not False:
        fail("3. required fields", "parallel must be false", plan.get("parallel"), "false")
    for key, expected in POLICY.items():
        if failure_policy.get(key) != expected:
            fail("13. failure_policy", f"invalid failure_policy.{key}", failure_policy.get(key), expected)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--skip-local-checks", action="store_true", help="Skip repo_path, commit, and patch existence checks.")
    args = parser.parse_args()

    try:
        validate(load_yaml(args.plan), args.plan, args.context, skip_local_checks=args.skip_local_checks)
    except PlanError as exc:
        print("plan.yaml validation failed")
        print(f"- item: {exc.item}")
        print(f"- reason: {exc.reason}")
        print(f"- actual: {exc.value}")
        print(f"- expected: {exc.expected}")
        return 1

    print("plan.yaml validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
