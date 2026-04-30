#!/usr/bin/env bash
# Opencode Experiment Agents - Uninstaller
#
# Usage:
#   ./uninstall.sh --global       # 글로벌 설치 제거
#   ./uninstall.sh --project      # 프로젝트 설치 제거
#   ./uninstall.sh --dry-run      # 어떤 파일이 제거될지만 미리 보기
#   ./uninstall.sh --restore-bak  # 가장 최근 백업(.bak.*)을 복원

set -euo pipefail

MODE=""
DRY_RUN=0
RESTORE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --global)       MODE="global"; shift ;;
    --project)      MODE="project"; shift ;;
    --dry-run)      DRY_RUN=1; shift ;;
    --restore-bak)  RESTORE=1; shift ;;
    --help|-h)
      sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$MODE" ]]; then
  echo "ERROR: --global 또는 --project 중 하나를 지정해주세요." >&2
  exit 1
fi

if [[ "$MODE" == "global" ]]; then
  TARGET_BASE="${OPENCODE_CONFIG_HOME:-$HOME/.config/opencode}"
else
  TARGET_BASE=".opencode"
fi

AGENTS_DIR="$TARGET_BASE/agents"
PKG_DIR="$TARGET_BASE/experiment-agents"

files_to_remove=(
  "$AGENTS_DIR/experiment-planner.md"
  "$AGENTS_DIR/experiment-executor.md"
  "$PKG_DIR/context.md"
  "$PKG_DIR/examples/plan-template.yaml"
  "$PKG_DIR/examples/plan-spdk-example.yaml"
  "$PKG_DIR/tools/validate_plan.py"
  "$PKG_DIR/tools/aggregate_metrics.py"
  "$PKG_DIR/tools/render_report.py"
)

echo "=== Opencode Experiment Agents Uninstaller ==="
echo "Mode: $MODE"
echo

# 백업 복원 모드
if [[ "$RESTORE" == "1" ]]; then
  echo "백업(.bak.*)을 찾아 복원합니다..."
  for f in "${files_to_remove[@]}"; do
    latest_bak="$(ls -t "$f".bak.* 2>/dev/null | head -1 || true)"
    if [[ -n "$latest_bak" ]]; then
      if [[ "$DRY_RUN" == "1" ]]; then
        echo "  [dry-run] 복원 예정: $latest_bak → $f"
      else
        cp "$latest_bak" "$f"
        echo "  복원: $latest_bak → $f"
      fi
    fi
  done
  exit 0
fi

# 일반 제거 모드
for f in "${files_to_remove[@]}"; do
  if [[ -f "$f" ]]; then
    if [[ "$DRY_RUN" == "1" ]]; then
      echo "  [dry-run] 제거 예정: $f"
    else
      rm "$f"
      echo "  제거: $f"
    fi
  fi
done

# 빈 디렉토리 제거 시도 (사용자의 다른 파일이 있으면 그대로 둠)
if [[ "$DRY_RUN" != "1" ]]; then
  rmdir "$PKG_DIR/examples" 2>/dev/null || true
  rmdir "$PKG_DIR/tools" 2>/dev/null || true
  rmdir "$PKG_DIR" 2>/dev/null || true
fi

echo
echo "제거 완료. 백업 파일(.bak.*)은 그대로 보존됩니다."
echo "백업도 정리하려면: find $TARGET_BASE -name '*.bak.*' -delete"
