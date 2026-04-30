# Installation Guide

이 문서는 Opencode에서 `experiment-planner`와 `experiment-executor` primary agent를 설치하는 절차입니다.

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
2. Press `Tab` and select `experiment-planner`.
3. Ask it to create an experiment plan.
4. Review `plan.yaml` and reply with `승인` or `OK`.
5. Press `Tab` and switch to `experiment-executor`.
6. Pass the approved `experiments/<id>/plan.yaml` path and approve execution.

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
