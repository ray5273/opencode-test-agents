#!/usr/bin/env bash
# Opencode Experiment Agents - Installer
#
# Usage:
#   ./install.sh                # 글로벌 설치 (~/.config/opencode/)
#   ./install.sh --global       # 글로벌 설치 (명시)
#   ./install.sh --project      # 현재 디렉토리에 .opencode/ 설치
#   ./install.sh --dry-run      # 어떤 파일이 어디로 갈지만 미리 보기
#   ./install.sh --force        # 기존 파일이 있어도 백업 없이 덮어쓰기
#   ./install.sh --help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MODE="global"
DRY_RUN=0
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --global)   MODE="global"; shift ;;
    --project)  MODE="project"; shift ;;
    --dry-run)  DRY_RUN=1; shift ;;
    --force)    FORCE=1; shift ;;
    --help|-h)
      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Use --help to see usage." >&2
      exit 1
      ;;
  esac
done

# 설치 위치 결정
if [[ "$MODE" == "global" ]]; then
  TARGET_BASE="${OPENCODE_CONFIG_HOME:-$HOME/.config/opencode}"
  AGENTS_DIR="$TARGET_BASE/agents"
  PKG_DIR="$TARGET_BASE/experiment-agents"
else
  TARGET_BASE=".opencode"
  AGENTS_DIR="$TARGET_BASE/agents"
  PKG_DIR="$TARGET_BASE/experiment-agents"
fi

# 소스 파일 확인
required_files=(
  "agents/experiment-orchestrator.md"
  "agents/experiment-planner.md"
  "agents/experiment-reviewer.md"
  "agents/experiment-executor.md"
  "context/experiment-agents-context.md"
  "examples/plan-template.yaml"
  "examples/plan-spdk-example.yaml"
  "tools/validate_plan.py"
  "tools/aggregate_metrics.py"
  "tools/render_report.py"
)

for f in "${required_files[@]}"; do
  if [[ ! -f "$SCRIPT_DIR/$f" ]]; then
    echo "ERROR: Missing source file: $SCRIPT_DIR/$f" >&2
    echo "이 스크립트는 레포 루트에서 실행해야 합니다." >&2
    exit 1
  fi
done

# 설치 계획 표시
echo "=== Opencode Experiment Agents Installer ==="
echo "Mode:        $MODE"
echo "Source:      $SCRIPT_DIR"
echo "Agents to:   $AGENTS_DIR/"
echo "Package to:  $PKG_DIR/"
echo

# 설치 매핑
declare -a copies
copies+=("$SCRIPT_DIR/agents/experiment-orchestrator.md|$AGENTS_DIR/experiment-orchestrator.md")
copies+=("$SCRIPT_DIR/agents/experiment-planner.md|$AGENTS_DIR/experiment-planner.md")
copies+=("$SCRIPT_DIR/agents/experiment-reviewer.md|$AGENTS_DIR/experiment-reviewer.md")
copies+=("$SCRIPT_DIR/agents/experiment-executor.md|$AGENTS_DIR/experiment-executor.md")
copies+=("$SCRIPT_DIR/context/experiment-agents-context.md|$PKG_DIR/context.md")
copies+=("$SCRIPT_DIR/examples/plan-template.yaml|$PKG_DIR/examples/plan-template.yaml")
copies+=("$SCRIPT_DIR/examples/plan-spdk-example.yaml|$PKG_DIR/examples/plan-spdk-example.yaml")
copies+=("$SCRIPT_DIR/tools/validate_plan.py|$PKG_DIR/tools/validate_plan.py")
copies+=("$SCRIPT_DIR/tools/aggregate_metrics.py|$PKG_DIR/tools/aggregate_metrics.py")
copies+=("$SCRIPT_DIR/tools/render_report.py|$PKG_DIR/tools/render_report.py")

# 충돌 검사
have_conflict=0
for entry in "${copies[@]}"; do
  src="${entry%%|*}"
  dst="${entry##*|}"
  if [[ -f "$dst" ]]; then
    if cmp -s "$src" "$dst"; then
      echo "[same]    $dst"
    else
      echo "[CONFLICT] $dst (already exists, will backup)"
      have_conflict=1
    fi
  else
    echo "[new]     $dst"
  fi
done
echo

if [[ "$DRY_RUN" == "1" ]]; then
  echo "(dry-run) 실제 설치는 하지 않았습니다. --dry-run 없이 다시 실행하세요."
  exit 0
fi

# 사용자 확인
if [[ "$have_conflict" == "1" && "$FORCE" == "0" ]]; then
  read -r -p "기존 파일이 있습니다. 백업 후 진행할까요? [y/N] " ans
  case "$ans" in
    y|Y|yes|YES) ;;
    *) echo "취소되었습니다."; exit 0 ;;
  esac
fi

# 디렉토리 생성
mkdir -p "$AGENTS_DIR" "$PKG_DIR" "$PKG_DIR/examples" "$PKG_DIR/tools"

# 복사 실행
TS="$(date +%Y%m%d-%H%M%S)"
for entry in "${copies[@]}"; do
  src="${entry%%|*}"
  dst="${entry##*|}"

  if [[ -f "$dst" ]] && ! cmp -s "$src" "$dst"; then
    cp "$dst" "$dst.bak.$TS"
    echo "  backup: $dst.bak.$TS"
  fi

  cp "$src" "$dst"
  if [[ "$dst" == *.py ]]; then
    chmod +x "$dst"
  fi
  echo "  install: $dst"
done

# 검증
echo
echo "=== 설치 검증 ==="
all_ok=1
for entry in "${copies[@]}"; do
  src="${entry%%|*}"
  dst="${entry##*|}"
  if cmp -s "$src" "$dst"; then
    echo "  OK: $dst"
  else
    echo "  FAIL: $dst"
    all_ok=0
  fi
done

if [[ "$all_ok" != "1" ]]; then
  echo
  echo "ERROR: 일부 파일 복사에 실패했습니다." >&2
  exit 1
fi

# 다음 단계 안내
echo
echo "=== 설치 완료 ==="
echo
if [[ "$MODE" == "global" ]]; then
  echo "글로벌 설치되었습니다. 어느 디렉토리에서든 opencode 실행 시 사용 가능합니다."
else
  echo "프로젝트 설치되었습니다. 이 디렉토리에서 opencode 실행 시에만 사용됩니다."
fi
echo
echo "사용 방법:"
echo "  1. opencode 실행"
echo "  2. Tab 키로 'experiment-orchestrator' 선택 (primary agent로 등록됨)"
echo "  3. 자연어로 실험 의도 전달"
echo "  4. reviewer plan 검토 결과 확인 → plan.yaml 검토 → '승인'"
echo "  5. orchestrator가 planner freeze 후 'experiment-executor'를 호출해 검증과 script 생성 시작"
echo "  6. reviewer script 검토 결과 확인 → 스크립트 검토 → '실행'"
echo "     (자동 호출 실패 시 orchestrator의 수동 fallback 안내를 따르세요)"
echo
echo "제거: ./uninstall.sh --$MODE"
