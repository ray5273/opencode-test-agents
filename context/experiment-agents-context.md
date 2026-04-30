# Experiment Agents — 공유 컨텍스트

이 문서는 `experiment-orchestrator`, `experiment-planner`, `experiment-executor` 에이전트의 공통 계약입니다. **세 에이전트는 매 세션 시작 시 이 문서를 먼저 읽어야 합니다.** 추측은 금지이며, 모든 정의는 이 문서가 진실의 원천입니다.

정상 workflow의 유일한 primary entrypoint는 `experiment-orchestrator`입니다. `experiment-planner`와 `experiment-executor`는 hidden subagent이며, orchestrator가 Task로만 호출합니다. 사용자는 일반적으로 planner/executor를 Tab으로 직접 선택하지 않습니다.

## 1. 디렉토리 구조 (절대 약속)

계획 재개 상태와 실행 결과는 분리합니다.

- `.opencode-test-agents/plans/`는 Planner가 쓰는 로컬 계획 작업공간입니다. draft plan과 Markdown handoff를 보관하며 Git에 커밋하지 않습니다.
- `experiments/`는 사용자 승인 후 동결된 plan과 Executor 실행 결과의 source of truth입니다.

### 1.1 계획 작업공간

```
.opencode-test-agents/plans/
├── <id>.md          # Planner handoff, 재개와 자동/수동 executor handoff 상태
└── <id>.plan.yaml   # 승인 전 ID 기반 draft plan
```

승인 전 draft plan 파일명은 `YYYY-MM-DD_<slug>_<seq>.plan.yaml` 형식이어야 합니다. 예: `2026-04-30_spdk-zerocopy-qd-sweep_001.plan.yaml`. 단순 `plan.yaml` 이름은 승인 후 `experiments/<id>/plan.yaml`에 동결된 실행 계약에만 사용합니다.

handoff Markdown 형식:

```markdown
# Plan Handoff: <id>

## Status
DRAFT | WAITING_FOR_USER | APPROVED | HANDED_OFF | CANCELLED

## User Intent
원 요청과 가설 요약

## Decisions
확정된 변수, 메트릭, 반복 횟수, baseline 여부, 성공 기준

## Open Questions
아직 사용자 확인이 필요한 항목. 없으면 None

## Plan Artifact
- Draft plan: .opencode-test-agents/plans/<id>.plan.yaml
- Final plan: experiments/<id>/plan.yaml 또는 None
- SHA256: <checksum 또는 None>

## Next Agent Action
planner/executor/사용자가 다음에 해야 할 한 줄 지시

## Resume Prompt
새 세션에서 그대로 붙여 넣을 재개 프롬프트
```

허용 status:

| Status | 의미 |
|---|---|
| `DRAFT` | draft plan이 있지만 아직 승인 요청 전이거나 수정 중 |
| `WAITING_FOR_USER` | planner가 사용자 답변을 기다림 |
| `APPROVED` | final `experiments/<id>/plan.yaml`이 생성되고 checksum이 기록됨 |
| `HANDED_OFF` | legacy/manual flow에서 executor handoff가 이미 확인됨 |
| `CANCELLED` | 사용자가 계획을 중단함 |

Executor는 handoff가 있으면 `APPROVED` 또는 `HANDED_OFF`만 실행 대상으로 인정합니다. 다른 status는 실행 대상으로 거부하고 스크립트 생성 전에 중단합니다.

승인 후 기본 흐름은 orchestrator가 planner에게 final plan freeze를 요청하고, planner가 handoff status를 `APPROVED`로 갱신한 structured handoff summary를 반환한 뒤, orchestrator가 `experiment-executor` Task를 호출하는 것입니다. 이 handoff는 executor가 context와 plan을 읽고 검증을 시작하는 것까지만 허용합니다. 실제 실험 스크립트 실행은 executor의 별도 실행 직전 승인 없이는 시작하지 않습니다.

Task 호출이 Opencode 환경에서 지원되지 않거나 실패하면 수동 fallback을 사용합니다. 정상 사용자는 Tab에서 `experiment-orchestrator`만 선택합니다. troubleshooting이 필요하면 숨김 subagent를 수동 호출할 수 있는 환경에서 `@experiment-planner` 또는 `@experiment-executor`를 직접 호출합니다. 환경이 hidden subagent 수동 호출을 막으면 임시로 해당 agent 파일의 `hidden: true`를 제거하거나 `mode: primary`로 바꾼 뒤, 작업이 끝나면 되돌립니다. executor fallback에는 반드시 `experiments/<id>/plan.yaml`과 `.opencode-test-agents/plans/<id>.md`를 함께 전달합니다.

### 1.2 실행 결과 디렉토리

```
experiments/<id>/
├── plan.yaml              # Planner 작성, 사용자 승인 후 동결
├── plan.yaml.sha256
├── env/
│   ├── pre/               # 실험 시작 전 환경
│   │   ├── <probe>.txt
│   │   └── hashes.txt
│   └── post/              # 실험 종료 후 환경
│       └── ...
├── scripts/
│   ├── 00_setup.sh
│   ├── 10_baseline.sh     # 선택 (plan에 baseline step이 있을 때만)
│   ├── 20_run.sh
│   ├── 30_collect.sh
│   ├── 90_teardown.sh     # 자동 실행 금지
│   └── hashes.txt
├── runs/
│   ├── iter_000_warmup_<n>/   # 통계에서 제외
│   ├── iter_001__queue_depth-4/
│   │   ├── 20_run.stdout.log
│   │   ├── 20_run.stderr.log
│   │   ├── 30_collect.stdout.log
│   │   ├── 30_collect.stderr.log
│   │   ├── timing.json        # {start_iso, end_iso, duration_sec, exit_code}
│   │   ├── metrics.json       # {metric_name: value, ...}
│   │   ├── <원시출력>.json    # 예: fio.json
│   │   └── failure_snapshot/  # 실패 시에만
│   ├── iter_002/
│   └── iter_NNN/
├── aggregated_metrics.json
├── status.json            # SUCCESS | FAILED | INCOMPLETE
├── progress.json
├── heartbeat.txt          # 5초마다 갱신 (실행 중 표시)
└── report.md              # 최종 보고서
```

변수가 있는 run 디렉토리는 `iter_001__<name>-<value>` 형식을 사용합니다.
변수가 둘 이상이면 `iter_001__queue_depth-4__block_size-4k`처럼 이어 붙입니다.

**실험 ID 형식**: `YYYY-MM-DD_<slug>_<seq>`
- slug: 영문 lowercase, 하이픈 구분, 2~3 단어
- seq: 3자리 (001, 002, ...)
- 예: `2026-04-30_spdk-zerocopy-qd-sweep_001`

## 2. plan.yaml 스키마

**[REQUIRED]** 표시 필드는 누락 시 Executor 검증에서 실패. 임의 필드 추가 금지.

```yaml
experiment:
  id: <string>                    # [REQUIRED] 실험 ID (위 형식)
  hypothesis: <string>            # [REQUIRED] 한 줄 가설
  description: <string>           # 선택, 추가 설명

success_criteria: <string>        # [REQUIRED] 가설 검증 기준

target:
  repo_path: <path|null>          # [REQUIRED] null이면 시스템 레벨 실험
  commit: <git_sha|null>          # repo_path가 null이 아니면 필수
  patches: [<path>, ...]          # 선택, plan.yaml과 같은 디렉토리 기준 상대 경로
  build_command: <string|null>    # 선택, 재빌드가 필요한 경우

variables:                        # [REQUIRED] 변수 없으면 빈 리스트 []
  - name: <string>                # 영문 lowercase + underscore (스크립트에서 VAR_<UPPER>로 변환)
    values: [<any>, ...]

metrics:                          # [REQUIRED] 최소 1개
  - name: <string>
    unit: <string>
    collector: <collector_name>   # 4번 라이브러리에 등록된 이름이어야 함
    sanity_range: [<num>, <num>]  # [min, max], 이 범위 밖이면 실패

probes:                           # [REQUIRED]
  base: [<probe_name>, ...]       # 권장: [os, cpu, mem, disk, git, env, time]
  extra: [<probe_name>, ...]      # 도메인별

steps:                            # [REQUIRED] 최소 1개
  - name: <string>
    type: setup | baseline | run | collect | teardown
    logic: <string>               # Executor가 그대로 명령으로 옮길 수 있을 만큼 구체적
    timeout_sec: <int>            # > 0

iterations: <int>                 # [REQUIRED] >= 1
warmup_runs: <int>                # 기본값 0
parallel: false                   # [REQUIRED] 단일 머신 가정, 항상 false

failure_policy:                   # [REQUIRED]
  on_step_fail: stop_and_preserve
  on_metric_out_of_range: stop_and_preserve
  on_timeout: stop_and_preserve
  auto_teardown: false            # [REQUIRED] 항상 false (다른 값이면 Executor 거부)
```

전체 예시는 `examples/plan-spdk-example.yaml` 참조.

## 3. Probe 라이브러리 (정확한 쉘 명령)

각 probe는 환경 정보를 캡처해 `env/{pre,post}/<name>.txt`에 저장합니다. **명령을 발명하지 말고 아래에 적힌 그대로 사용하세요.**

### 3.1 Base probes

#### probe: os
```bash
{
  echo "=== uname -a ==="
  uname -a
  echo "=== /etc/os-release ==="
  cat /etc/os-release 2>/dev/null || echo "N/A"
  echo "=== /proc/cmdline ==="
  cat /proc/cmdline
  echo "=== uptime ==="
  uptime
} > "$OUT_DIR/os.txt"
```

#### probe: cpu
```bash
{
  echo "=== lscpu ==="
  lscpu
  echo "=== /proc/cpuinfo (head -50) ==="
  head -50 /proc/cpuinfo
  echo "=== governor ==="
  for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    [ -f "$f" ] && echo "$f: $(cat "$f")"
  done 2>/dev/null
  echo "=== current freq ==="
  for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq; do
    [ -f "$f" ] && echo "$f: $(cat "$f")"
  done 2>/dev/null
} > "$OUT_DIR/cpu.txt"
```

#### probe: mem
```bash
{
  echo "=== free -h ==="
  free -h
  echo "=== /proc/meminfo ==="
  cat /proc/meminfo
} > "$OUT_DIR/mem.txt"
```

#### probe: disk
```bash
{
  echo "=== lsblk -O ==="
  lsblk -O 2>/dev/null || lsblk
  echo "=== df -h ==="
  df -h
  echo "=== mount ==="
  mount
} > "$OUT_DIR/disk.txt"
```

#### probe: git
대상 레포(`plan.target.repo_path`)에 대해 실행. repo_path가 null이면 이 probe는 건너뜀.
```bash
cd "$REPO_PATH" || exit 1
{
  echo "=== git rev-parse HEAD ==="
  git rev-parse HEAD
  echo "=== git status ==="
  git status
  echo "=== git log --oneline -10 ==="
  git log --oneline -10
} > "$OUT_DIR/git_status.txt"
git diff > "$OUT_DIR/git_diff.patch"
git diff --cached > "$OUT_DIR/git_diff_cached.patch"
```

#### probe: env
**시크릿 자동 마스킹 필수**.
```bash
printenv | sed -E 's/^([^=]*(_KEY|_TOKEN|_PASSWORD|_SECRET|_CREDENTIAL))=.*$/\1=<MASKED>/' \
        | sed -E 's/^(AWS_[^=]*)=.*$/\1=<MASKED>/' \
        | sed -E 's/^(GCP_[^=]*)=.*$/\1=<MASKED>/' \
        | sed -E 's/^(AZURE_[^=]*)=.*$/\1=<MASKED>/' \
        > "$OUT_DIR/env.txt"
```

#### probe: ulimit
```bash
ulimit -a > "$OUT_DIR/ulimit.txt"
```

#### probe: time
```bash
{
  echo "=== date -Iseconds ==="
  date -Iseconds
  echo "=== timedatectl status ==="
  timedatectl status 2>/dev/null || echo "N/A"
  echo "=== /etc/timezone ==="
  cat /etc/timezone 2>/dev/null || echo "N/A"
} > "$OUT_DIR/time.txt"
```

### 3.2 도메인 probes

#### probe: nvme
```bash
{
  echo "=== nvme list ==="
  nvme list 2>/dev/null || echo "nvme-cli not installed"
  echo "=== smartctl per device ==="
  for dev in /dev/nvme[0-9]n[0-9]; do
    [ -e "$dev" ] || continue
    echo "--- $dev ---"
    smartctl -a "$dev" 2>/dev/null || echo "smartctl failed for $dev"
  done
} > "$OUT_DIR/nvme.txt"
```

#### probe: hugepages
```bash
{
  echo "=== /proc/meminfo huge entries ==="
  grep -i huge /proc/meminfo
  echo "=== /sys/kernel/mm/hugepages/ ==="
  for d in /sys/kernel/mm/hugepages/hugepages-*; do
    echo "--- $d ---"
    for f in "$d"/*; do
      echo "$(basename "$f"): $(cat "$f")"
    done
  done
} > "$OUT_DIR/hugepages.txt"
```

#### probe: numa
```bash
{
  echo "=== numactl -H ==="
  numactl -H 2>/dev/null || echo "numactl not installed"
  echo "=== lscpu -e ==="
  lscpu -e 2>/dev/null
} > "$OUT_DIR/numa.txt"
```

#### probe: pci
```bash
lspci -vvv > "$OUT_DIR/pci.txt" 2>&1
```

#### probe: iommu
```bash
{
  echo "=== /sys/class/iommu ==="
  ls -la /sys/class/iommu/ 2>/dev/null
  echo "=== dmesg | grep -i iommu ==="
  dmesg 2>/dev/null | grep -i iommu | tail -50
} > "$OUT_DIR/iommu.txt"
```

#### probe: irq
```bash
{
  echo "=== /proc/interrupts ==="
  cat /proc/interrupts
  echo "=== /proc/irq/*/smp_affinity ==="
  for f in /proc/irq/*/smp_affinity; do
    echo "$f: $(cat "$f" 2>/dev/null)"
  done
} > "$OUT_DIR/irq.txt"
```

#### probe: network
```bash
{
  echo "=== ip a ==="
  ip a
  echo "=== ip r ==="
  ip r
  echo "=== ethtool per interface ==="
  for iface in $(ls /sys/class/net/); do
    [ "$iface" == "lo" ] && continue
    echo "--- $iface ---"
    ethtool "$iface" 2>/dev/null
  done
} > "$OUT_DIR/network.txt"
```

#### probe: gpu
```bash
{
  nvidia-smi -q 2>/dev/null || echo "nvidia-smi not available"
} > "$OUT_DIR/gpu.txt"
```

#### probe: kernel_modules
```bash
lsmod > "$OUT_DIR/modules.txt"
```

#### probe: sysctl
```bash
sysctl -a 2>/dev/null > "$OUT_DIR/sysctl.txt"
```

새 probe가 필요하면 이 표에 먼저 추가한 후 사용.

## 4. Collector 라이브러리 (정확한 파싱 로직)

각 collector는 원시 출력 파일을 받아 `metrics.json`을 생성합니다.

#### collector: parse_fio_json
입력: fio JSON 출력 파일. 출력 키:
```bash
# Usage: parse_fio_json <fio.json> <out.json>
jq '
  (.jobs[0].read.iops // 0) + (.jobs[0].write.iops // 0) as $iops |
  (.jobs[0].read.bw // 0) + (.jobs[0].write.bw // 0) as $bw_kib |
  (.jobs[0].read.clat_ns.percentile["50.000000"] // .jobs[0].write.clat_ns.percentile["50.000000"] // 0) as $p50 |
  (.jobs[0].read.clat_ns.percentile["95.000000"] // .jobs[0].write.clat_ns.percentile["95.000000"] // 0) as $p95 |
  (.jobs[0].read.clat_ns.percentile["99.000000"] // .jobs[0].write.clat_ns.percentile["99.000000"] // 0) as $p99 |
  (.jobs[0].read.clat_ns.mean // .jobs[0].write.clat_ns.mean // 0) as $mean |
  {
    iops: $iops,
    bw_mb: ($bw_kib / 1024),
    lat_us_p50: ($p50 / 1000),
    lat_us_p95: ($p95 / 1000),
    lat_us_p99: ($p99 / 1000),
    lat_us_mean: ($mean / 1000)
  }
' "$1" > "$2"
```

#### collector: parse_perf_stat
입력: `perf stat -x,` 출력 (CSV 형식). 출력 키: 카운터별로 키.
```bash
# Usage: parse_perf_stat <perf_output> <out.json>
awk -F',' '
  BEGIN { print "{" }
  NR>1 { gsub(/-/, "_", $3); printf "%s\"%s\": %s", (NR>2?",":""), $3, $1 }
  END { print "}" }
' "$1" > "$2"
```

#### collector: parse_iostat
입력: `iostat -x` 출력. 출력 키: 디바이스별 await, util, r_iops, w_iops.
구현은 awk 또는 python으로. 디바이스 이름은 키 앞에 prefix.

#### collector: parse_time
입력: `/usr/bin/time -v` 출력. 출력 키: real_sec, user_sec, sys_sec, max_rss_kb.
```bash
# Usage: parse_time <time_output> <out.json>
python3 - "$1" "$2" <<'PY'
import sys, json, re
src = open(sys.argv[1]).read()
def get(pat, default=0, t=float):
    m = re.search(pat, src)
    return t(m.group(1)) if m else default
def elapsed_to_sec(value):
    parts = value.strip().split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(parts[0])
elapsed = re.search(r"Elapsed \(wall clock\) time.*?: ([0-9:.]+)", src)
out = {
    "real_sec": elapsed_to_sec(elapsed.group(1)) if elapsed else 0,
    "user_sec": get(r"User time \(seconds\): ([\d.]+)"),
    "sys_sec":  get(r"System time \(seconds\): ([\d.]+)"),
    "max_rss_kb": get(r"Maximum resident set size \(kbytes\): (\d+)", t=int),
}
json.dump(out, open(sys.argv[2], "w"))
PY
```

#### collector: parse_json_file
입력: 임의 JSON 파일. 추가 인자로 `jsonpath` 필요. 단일 메트릭에 사용.
```bash
# Usage: parse_json_file <input.json> <out.json> <jq_expr> <metric_name>
echo "{\"$4\": $(jq "$3" "$1")}" > "$2"
```

#### collector: parse_regex
입력: 임의 텍스트. 추가 인자로 `regex` 필요.
```bash
# Usage: parse_regex <input.txt> <out.json> <regex> <metric_name>
val=$(grep -oP "$3" "$1" | head -1)
echo "{\"$4\": ${val:-null}}" > "$2"
```

새 collector도 사용 전 이 표에 등록.

## 5. 스크립트 표준 헤더 (그대로 복사 사용)

모든 `scripts/*.sh`는 다음 헤더로 시작합니다.

```bash
#!/usr/bin/env bash
set -euo pipefail

EXP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ITER="${ITER:-default}"
ITER_DIR="${EXP_DIR}/runs/${ITER}"
mkdir -p "${ITER_DIR}"

SCRIPT_NAME="$(basename "$0" .sh)"
exec > >(tee -a "${ITER_DIR}/${SCRIPT_NAME}.stdout.log") \
    2> >(tee -a "${ITER_DIR}/${SCRIPT_NAME}.stderr.log" >&2)

ts() { date -Iseconds; }
echo "[$(ts)] START ${SCRIPT_NAME} ITER=${ITER}"
trap 'rc=$?; echo "[$(ts)] END ${SCRIPT_NAME} rc=${rc}"; exit $rc' EXIT

# ===== 여기 아래에 step의 logic을 명령으로 옮기기 =====
```

## 6. 시크릿 마스킹

env probe 외에도 logs / 보고서에 환경변수 값을 노출할 때 다음 패턴은 항상 마스킹.

마스킹 대상 변수명 패턴:
- `*_KEY`, `*_TOKEN`, `*_PASSWORD`, `*_SECRET`, `*_CREDENTIAL`
- `AWS_*`, `GCP_*`, `AZURE_*` (값에 인증 정보가 들어갈 가능성)

이름은 그대로, 값만 `<MASKED>`로 치환.

## 7. status.json / progress.json 스키마

### status.json
```json
{
  "state": "INITIALIZING|RUNNING|SUCCESS|FAILED|INCOMPLETE",
  "started_at": "<iso8601>",
  "ended_at": "<iso8601|null>",
  "failure": {
    "step": "<step_name>",
    "iteration": "<iter_id|null>",
    "reason": "<short string>",
    "exit_code": "<int|null>"
  }
}
```

상태 전이:
- `INITIALIZING` → 디렉토리 생성, env/pre 캡처, 스크립트 생성, 사용자 승인 대기까지
- `RUNNING` → 사용자 "실행" 응답 후 단계 5 시작 시
- `SUCCESS` → 모든 step 정상 완료
- `FAILED` → 어느 단계든 실패 시
- `INCOMPLETE` → SIGINT, dry-run 종료

### progress.json
```json
{
  "current_step": "<step_name>",
  "current_iteration": "<iter_id|null>",
  "completed_iterations": <int>,
  "total_iterations": <int>,
  "current_variables": {"<var_name>": <value>, ...},
  "updated_at": "<iso8601>"
}
```

매 step 시작/종료, 매 iteration 시작 시 갱신.

## 8. timing.json / metrics.json 스키마

### `runs/<iter>/timing.json`
```json
{
  "iter": "<iter_id>",
  "variables": {"<name>": <value>, ...},
  "start_iso": "<iso8601>",
  "end_iso": "<iso8601>",
  "duration_sec": <number>,
  "exit_code": <int>
}
```

### `runs/<iter>/metrics.json`
collector가 생성. 각 metric.name을 키로:
```json
{
  "iops": 123456,
  "lat_us_p99": 234,
  ...
}
```

### `aggregated_metrics.json`
모든 iteration의 metrics.json을 집계 (warmup 제외):
```json
{
  "<metric_name>": {
    "n": <int>,
    "mean": <num>,
    "std": <num>,
    "p50": <num>,
    "p95": <num>,
    "p99": <num>,
    "min": <num>,
    "max": <num>,
    "values": [<num>, ...]
  }
}
```

## 9. Helper tools

Executor는 검증, 집계, 보고서 생성을 직접 추론하지 말고 설치된 helper를 호출합니다.

설치 후 위치:
- 프로젝트 설치: `./.opencode/experiment-agents/tools/`
- 글로벌 설치: `~/.config/opencode/experiment-agents/tools/`

개발 중인 레포에서 직접 실행할 때는 `./tools/`를 사용합니다.

명령:
```bash
python3 <TOOLS_DIR>/validate_plan.py <plan.yaml> --context <context.md>
python3 <TOOLS_DIR>/aggregate_metrics.py <experiments/id>
python3 <TOOLS_DIR>/render_report.py <experiments/id>
```

`validate_plan.py`가 실패하면 실험을 시작하지 않습니다.
문서/CI 예시 검증에서는 `--skip-local-checks`로 repo_path, commit, patch 존재 검사를 건너뛸 수 있지만, 실제 Executor 실행 전에는 사용하지 않습니다.
`aggregate_metrics.py`는 warmup run을 제외하고 `aggregated_metrics.json`을 생성합니다.
`render_report.py`는 `plan.yaml`, `status.json`, `aggregated_metrics.json`을 읽어 `report.md`를 생성합니다.

## 10. 보고서 템플릿 (`report.md`)

**섹션 순서, 제목, 테이블 헤더는 변경 금지**. Executor는 이 템플릿을 그대로 채워서 사용:

```markdown
# Experiment <id>

## Summary
- **Status**: <SUCCESS|FAILED|INCOMPLETE>
- **Hypothesis**: <plan.experiment.hypothesis>
- **결론 한 줄**: <성공 기준 충족 여부 한 줄>
- **주요 수치**: <핵심 metric의 mean/p99 등>

## Hypothesis & Plan
- 가설: <hypothesis>
- 변수: <variables 요약>
- 측정 메트릭: <metrics 요약>
- 반복: <iterations>회 (warmup <warmup_runs>회)
- 성공 기준: <success_criteria>

## Environment
- OS: <env/pre/os.txt에서 발췌>
- CPU: <env/pre/cpu.txt에서 발췌>
- Memory: <env/pre/mem.txt에서 발췌>
- 대상 레포: <repo_path> @ <commit>
- 적용 패치: <patches 목록>

전체 환경: [`env/pre/`](./env/pre/), [`env/post/`](./env/post/)

**환경 변화 (pre vs post)**: <변화 있음/없음. 있으면 어떤 파일에 차이가 있는지>

## Execution Timeline
| Step | Iter | Start | End | Duration (s) | Exit |
|---|---|---|---|---|---|
| setup | - | ... | ... | ... | 0 |
| run | iter_001 | ... | ... | ... | 0 |
| ... | ... | ... | ... | ... | ... |

## Results

### Per-iteration metrics
| Iter | <var_1> | <var_2> | <metric_1> | <metric_2> | ... |
|---|---|---|---|---|---|
| iter_001 | 4 | 4k | 123456 | 234 | ... |
| ... | | | | | |

### Aggregated (warmup 제외)
| Metric | n | mean | std | p50 | p95 | p99 | min | max |
|---|---|---|---|---|---|---|---|---|
| iops | 5 | ... | ... | ... | ... | ... | ... | ... |
| lat_us_p99 | 5 | ... | ... | ... | ... | ... | ... | ... |

### Baseline comparison
(plan에 baseline step이 있는 경우만 작성. 없으면 "N/A".)

| Metric | Baseline | Treatment | Δ | Δ% |
|---|---|---|---|---|
| iops | ... | ... | ... | ...% |

## Anomalies & Warnings
- dmesg 에러: <있으면 발췌, 없으면 "없음">
- CPU throttling: <있음/없음>
- sanity_range 이탈: <있음/없음 + 어느 metric>
- env pre/post 차이: <있음/없음 + 어떤 차이>

## Conclusion
<성공 기준 충족 여부, 가설 검증 결과를 짧게>

## Artifacts
- plan.yaml: [`./plan.yaml`](./plan.yaml)
- 환경: [`./env/pre/`](./env/pre/), [`./env/post/`](./env/post/)
- 스크립트: [`./scripts/`](./scripts/)
- 원시 로그: [`./runs/`](./runs/)
- 집계 메트릭: [`./aggregated_metrics.json`](./aggregated_metrics.json)
```

## 11. 사용자 응답 인식 (양 에이전트 공통)

### 승인을 의미하는 응답
다음 단어 중 하나라도 응답에 포함되면 "승인":
- 한국어: "승인", "진행", "좋아", "오케이", "응", "예"
- 영어: "OK", "ok", "okay", "go", "GO", "run", "RUN", "yes", "YES", "approve", "approved", "proceed"

### 중단을 의미하는 응답
- 한국어: "취소", "중단", "그만", "안 할래", "멈춰"
- 영어: "cancel", "stop", "abort", "no", "NO"

### Dry-run을 의미하는 응답 (Executor 전용)
- "dry-run", "dryrun", "dry run", "건너뛰", "skip", "preview"

### 모호 응답
"음...", "글쎄", "잠깐", "흠" 등은 **승인 아님**. 다시 명확히 질문.

## 12. 일반 원칙 (양 에이전트 공통)

- **언어**: 사용자와의 대화는 한국어. 파일/스크립트/명령은 영어 (이식성/재현성).
- **추측 금지**: 의심스러우면 사용자에게 질문. plan에 없는 행동은 절대 하지 말 것.
- **부분 결과 보존**: 어떤 상황에서도 이미 만들어진 파일은 지우지 않음. teardown은 명시 호출만.
- **재현성 우선**: 같은 plan.yaml로 다시 돌렸을 때 동일 결과를 낼 수 있도록 노력.
- **한 번에 하나씩**: 단계 건너뛰지 말기. 약식 추론이 오류의 원인.
