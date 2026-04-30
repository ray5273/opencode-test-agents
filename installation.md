# Installation Guide

이 문서는 Opencode에서 `experiment-orchestrator` primary agent와 hidden `experiment-planner`, `experiment-executor` subagent를 설치하는 절차입니다.

## Prerequisites

- Bash
- Python 3
- `pyyaml` for plan validation helpers
- Opencode config directory access

Install Python dependency if needed:

```bash
python3 -m pip install pyyaml
```

## Preview Installation

Before writing files, preview the destination paths:

```bash
./install.sh --dry-run
```

Project-local preview:

```bash
./install.sh --project --dry-run
```

## Install Globally

Global install makes the agents available from any directory where Opencode runs:

```bash
./install.sh --global
```

Files are installed under:

- `${OPENCODE_CONFIG_HOME:-$HOME/.config/opencode}/agents/`
- `${OPENCODE_CONFIG_HOME:-$HOME/.config/opencode}/experiment-agents/`

## Install For One Project

Project install keeps the agents scoped to the current repository:

```bash
./install.sh --project
```

Files are installed under:

- `.opencode/agents/`
- `.opencode/experiment-agents/`

## Use In Opencode

1. Start `opencode`.
2. Press `Tab` and select `experiment-orchestrator`.
3. Ask it to create an experiment plan.
4. Review the ID-based draft plan in `.opencode-test-agents/plans/<id>.plan.yaml` and reply with `승인` or `OK`.
5. Orchestrator asks planner to freeze the approved plan to `experiments/<id>/plan.yaml` and update handoff status to `APPROVED`.
6. Orchestrator calls `experiment-executor` as a Task.
7. Executor validates the context, plan, and handoff, then asks for a second approval before running generated scripts.

If Task handoff is unavailable in your Opencode environment, keep `experiment-orchestrator` as the normal entrypoint and follow its manual fallback instructions. For troubleshooting, invoke `@experiment-executor` manually if your environment allows hidden subagent calls, or temporarily remove `hidden: true` / change `mode` for the subagent and restore it afterward. Pass both `experiments/<id>/plan.yaml` and `.opencode-test-agents/plans/<id>.md`.

## Plan Handoff Workspace

Planner stores resumable planning state under:

```bash
.opencode-test-agents/plans/
```

Each plan has:

- `<id>.md`: Markdown handoff with status, user intent, decisions, open questions, artifact paths, next action, and resume prompt.
- `<id>.plan.yaml`: ID-based draft plan before approval, for example `2026-04-30_spdk-zerocopy-qd-sweep_001.plan.yaml`.

This workspace is local-only and ignored by Git. It is not installed by `install.sh`; only agents, context, examples, and tools are installed.

After approval, Planner copies the draft to `experiments/<id>/plan.yaml`, writes `experiments/<id>/plan.yaml.sha256`, marks the handoff as `APPROVED`, and returns a structured handoff summary to Orchestrator. Orchestrator starts Executor with the final plan path and handoff path. Executor treats `experiments/<id>/plan.yaml` as the execution source of truth and uses the handoff only to confirm continuity.

## Uninstall

Preview removal:

```bash
./uninstall.sh --project --dry-run
```

Remove project-local install:

```bash
./uninstall.sh --project
```

Remove global install:

```bash
./uninstall.sh --global
```

Restore the most recent backup created by the installer:

```bash
./uninstall.sh --project --restore-bak
```
