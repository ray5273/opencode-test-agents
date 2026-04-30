# Repository Guidelines

## Project Structure & Module Organization

This repository packages two Opencode primary agents for experiment planning and execution:

- `agents/experiment-planner.md` and `agents/experiment-executor.md` define the two agents.
- `context/experiment-agents-context.md` is the shared source of truth for plan schema, probes, collectors, and report structure.
- `examples/plan-template.yaml` and `examples/plan-spdk-example.yaml` provide reusable plan examples.
- `tools/*.py` contains deterministic helpers for plan validation, metric aggregation, and report rendering.
- `install.sh` and `uninstall.sh` install or remove the agents from Opencode config locations.
- `.github/workflows/lint.yml` defines the intended GitHub Actions lint workflow.

Keep installer paths, README examples, and this layout in sync when adding packaged files.

## Build, Test, and Development Commands

- `./install.sh --dry-run` previews global installation without writing files.
- `./install.sh --project` installs into the local `.opencode/` directory.
- `./install.sh --global` installs into `${OPENCODE_CONFIG_HOME:-$HOME/.config/opencode}`.
- `./uninstall.sh --project --dry-run` previews local removal.
- `yamllint -d '{extends: relaxed, rules: {line-length: disable}}' .` checks YAML.
- `shellcheck install.sh uninstall.sh` checks shell scripts.
- `python3 tools/validate_plan.py examples/plan-spdk-example.yaml --context context/experiment-agents-context.md` validates the complete example plan.

## Coding Style & Naming Conventions

Use Markdown for agent prompts and documentation, Bash for installer scripts, and YAML for plans/workflows. Keep Bash scripts strict with `set -euo pipefail`, quote variable expansions, and prefer long option names such as `--dry-run`. Plan fields use `snake_case`; experiment IDs should follow the template pattern `YYYY-MM-DD_slug_NNN`. Agent markdown should keep YAML frontmatter valid and permissions explicit.

## Testing Guidelines

There is no application test suite. Treat linting and parse checks as the minimum validation before submitting changes. For installer changes, run dry-run modes for both scopes:

```bash
./install.sh --dry-run
./install.sh --project --dry-run
./uninstall.sh --project --dry-run
```

For plan examples, ensure every `*.yaml` file parses with Python/PyYAML or an equivalent YAML parser.

## Commit & Pull Request Guidelines

This branch has no existing commits, so no project-specific commit convention is established. Use short imperative subjects, for example `Add SPDK collector example` or `Fix project install paths`. Pull requests should describe the affected agent, context, or script; list validation commands run; and link related issues. Include screenshots only when documenting Opencode UI behavior.

## Agent-Specific Instructions

Preserve the core contract: planner writes plans only, executor runs only approved plans, and all execution must go through generated script files. Do not add probes or collectors without updating `context/experiment-agents-context.md` and at least one example plan.
