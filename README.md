# Opencode Experiment Agents

> 설치는 [installation.md](installation.md)를 참고하세요. 처음 설치 전에는 `./install.sh --dry-run`으로 대상 경로를 확인한 뒤 `./install.sh --project` 또는 `./install.sh --global`을 실행하면 됩니다.

> 시스템 실험 자동화를 위한 Opencode orchestrator와 두 hidden subagent. **계획 ≠ 실행**, **모든 실행은 스크립트 파일을 거침**, **실패 시 즉시 중단** 원칙으로 재현성과 결과 무결성을 보장합니다.

[![lint](https://github.com/USER/opencode-experiment-agents/actions/workflows/lint.yml/badge.svg)](https://github.com/USER/opencode-experiment-agents/actions/workflows/lint.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 빠른 시작

```bash
git clone https://github.com/USER/opencode-experiment-agents.git
cd opencode-experiment-agents
./install.sh                # 글로벌 설치 (~/.config/opencode/)
# 또는
./install.sh --project      # 현재 프로젝트의 .opencode/에 설치
./install.sh --dry-run      # 실제 설치 없이 미리보기
```

설치 후 `opencode`를 실행하고 Tab 키로 `experiment-orchestrator`를 선택하세요.

## 무엇인가

하나의 사용자-facing primary agent와 두 hidden subagent를 제공합니다.

- **experiment-orchestrator** — 사용자의 유일한 Tab 선택 entrypoint입니다. 대화, 승인 gate, planner/executor 호출 순서를 조율합니다.
- **experiment-planner** — hidden subagent입니다. 자연어 실험 의도를 받아 날짜와 실험명이 들어간 draft plan과 handoff를 작성하고 승인 시 final `plan.yaml`을 동결합니다. 시스템을 변경하지 않습니다.
- **experiment-executor** — hidden subagent입니다. 승인된 `plan.yaml`을 받아 환경 캡처 → 스크립트 생성 → 사용자 재확인 → 실행 → 보고서 생성까지 수행합니다. plan에 없는 행동은 절대 하지 않습니다.

## 설계 원칙

1. **계획 ≠ 실행** — orchestrator가 planner와 executor를 분리 호출. 승인 후 동결된 `experiments/<id>/plan.yaml`이 둘 사이의 계약.
2. **모든 실행은 스크립트 파일을 거침** — bash 직접 실행 금지. 히스토리가 항상 파일로 남음.
3. **실패 시 즉시 중단** — 자동 재시도/fallback/cleanup 없음. 부분 결과 보존.
4. **두 단계 사용자 승인** — ① ID 기반 draft plan 승인 ② 스크립트 실행 직전 재확인.
5. **도메인 비종속** — probe/collector를 라이브러리화. SPDK는 한 인스턴스일 뿐.
6. **약한 모델 대응** — 시스템 프롬프트는 추론보다 패턴 매칭에 의존. 단계 체크리스트, 정확한 단어 매칭, 좋은/나쁜 예시, 정확한 쉘 명령까지 명시.

## 왜 omo / OpenAgentsControl이 아닌가

[Oh My OpenAgent (omo)](https://github.com/code-yeongyu/oh-my-openagent)와 같은 큰 플러그인을 쓰지 않는 이유:

| 측면 | omo | 이 프로젝트 |
|---|---|---|
| 도메인 | 코딩 자동화 | 시스템/성능 실험 자동화 |
| 철학 | 자율 실행 (Zero intervention) | 명시적 사용자 승인 (실패 시 즉시 중단) |
| 적합 워크로드 | "8000 eslint warnings 하룻밤에 해결" | "SPDK 패치 효과를 5회 반복 측정" |
| 라이브러리 | 코딩 도구 (LSP, AST) | 시스템 probe (lscpu, nvme, hugepages...) + collector (fio, perf, iostat...) |

**두 도구는 공존 가능**합니다. omo로 코딩 자동화하면서, 실험을 계획하고 실행할 때만 `experiment-orchestrator`로 전환하면 됩니다.

OpenAgentsControl(OAC)는 철학(approval gates)이 더 가깝지만, OAC 자체가 또 하나의 프레임워크라 의존성이 늘어납니다. 이 프로젝트는 순수 Opencode 위에서 직접 동작합니다.

## 파일 구조

```
opencode-experiment-agents/
├── README.md
├── LICENSE                              # MIT
├── CHANGELOG.md
├── install.sh                           # 글로벌/프로젝트 설치 + 백업
├── uninstall.sh
├── installation.md                      # 설치 상세 가이드
├── agents/
│   ├── experiment-orchestrator.md       # primary agent (대화와 handoff 조율)
│   ├── experiment-planner.md            # hidden subagent (계획)
│   └── experiment-executor.md           # hidden subagent (실행)
├── context/
│   └── experiment-agents-context.md     # 세 에이전트 공통 컨텍스트
│                                        # (plan.yaml 스키마, probe/collector 라이브러리, 보고서 템플릿)
├── examples/
│   ├── plan-template.yaml               # 빈 템플릿
│   └── plan-spdk-example.yaml           # SPDK 완전 예시
├── tools/
│   ├── validate_plan.py                 # plan.yaml 검증
│   ├── aggregate_metrics.py             # metrics 집계
│   └── render_report.py                 # report.md 생성
└── .github/workflows/lint.yml
```

Planner는 로컬 계획 재개 상태를 Git에 커밋하지 않는 작업공간에 저장합니다.

```
.opencode-test-agents/plans/
├── <id>.md          # Plan Handoff: 사용자 의도, 결정, 질문, 승인 상태, 재개 프롬프트
└── <id>.plan.yaml   # 승인 전 ID 기반 draft plan
```

예: `.opencode-test-agents/plans/2026-04-30_spdk-zerocopy-qd-sweep_001.plan.yaml`

승인 후 source of truth는 계속 `experiments/<id>/plan.yaml`입니다. handoff는 세션이 끊기거나 자동/수동으로 executor가 이어받을 때 사용하는 보조 계약입니다.

설치 후에는 다음 위치에 배치됩니다.

| 모드 | agents/* | context.md / examples/ |
|---|---|---|
| `--global` | `~/.config/opencode/agents/` | `~/.config/opencode/experiment-agents/` |
| `--project` | `.opencode/agents/` | `.opencode/experiment-agents/` |

`tools/*.py`도 같은 `experiment-agents/tools/` 아래에 설치됩니다.

> `AGENTS.md`라는 이름을 쓰지 않습니다. Opencode/Cursor/Claude Code 등 여러 도구가 프로젝트 루트의 `AGENTS.md`를 자동 컨텍스트로 로드하므로, 사용자의 기존 `AGENTS.md`와 충돌하지 않게 `experiment-agents/context.md`로 격리합니다.

## 약한 모델 (GLM-4.7 등) 대응 설계

| 위험 | 대응 |
|---|---|
| 다단계 추론 중 단계 누락 | 단계마다 명시적 체크리스트, "단계 N을 마치기 전에 N+1 금지" |
| 모호한 logic을 발명함 | 좋은 예시 / 나쁜 예시 양쪽 명시. logic 작성 후 자기검증 질문 강제 |
| 사용자 응답을 자기 해석 | 응답 인식 단어를 표로 명시 ("승인", "go", "OK" 등). 모호 응답은 다시 질문 |
| 라이브러리에 없는 이름 발명 | 시작 시 context 파일을 반드시 읽도록 강제, 표에 없으면 사용자에게 추가 요청 |
| 쉘 명령을 발명 | probe/collector마다 정확한 쉘 명령을 context에 박아둠 |
| 실패 처리 추론 실수 | 실패 의사 코드를 그대로 명시 |

시스템 프롬프트가 다소 길어졌지만, 이는 모델이 매번 같은 절차를 따르게 하기 위한 것입니다. **약한 모델일수록 명시적 지시가 효과적입니다.**

## 사용 흐름

### 1. Orchestrator로 자연어 요청

```
Tab → experiment-orchestrator

> SPDK NVMe-oF target에 patches/zerocopy.patch를 적용하고
> queue depth 1, 4, 16, 64에서 4k randread 처리량과 p99 지연을 측정해줘.
> 각 조건당 5번 반복.
```

Orchestrator가 hidden `experiment-planner`를 호출합니다. Planner가 빠진 정보(워밍업 여부, 대상 디바이스, 성공 기준 등)를 **한 번에 모아서** 반환하면 orchestrator가 사용자에게 전달합니다.

### 2. ID 기반 draft plan 검토 + 명시적 승인

Planner가 `.opencode-test-agents/plans/<id>.plan.yaml`을 작성하고 orchestrator가 정형 요약을 보여줍니다. **명시적으로 "승인" 또는 "OK"라고 답하세요.** 모호한 응답("음... 좋아 보이네")은 승인으로 받아들이지 않습니다.

승인 전 draft는 날짜와 실험 slug가 포함된 `.opencode-test-agents/plans/<id>.plan.yaml`에 저장되고, 재개용 handoff는 `.opencode-test-agents/plans/<id>.md`에 저장됩니다. 승인 후에는 planner가 `experiments/<id>/plan.yaml`로 동결 복사하고 checksum을 생성한 뒤, handoff 상태를 `APPROVED`로 갱신합니다.

### 3. Executor 자동 handoff + 실행 승인

Orchestrator는 승인 직후 `experiment-executor` Task를 호출해 `experiments/<id>/plan.yaml` 검증부터 시작하게 합니다. Task 호출이 환경에서 지원되지 않거나 실패하면 orchestrator의 수동 fallback 안내를 따르세요.

Executor는 자동으로:
1. plan.yaml의 13개 항목과 가능한 경우 matching handoff 검증 (실패 시 즉시 중단)
2. probe로 환경 사전 캡처
3. `scripts/00_setup.sh` ~ `scripts/90_teardown.sh` 생성
4. 실행 직전 사용자에게 재확인

답변: `실행` / `dry-run` / `수정: ...` / `취소`

### 4. 결과 확인

```
experiments/<id>/
├── plan.yaml
├── env/{pre,post}/        # 환경 캡처
├── scripts/               # 실제 실행된 스크립트
├── runs/iter_NNN/         # iteration별 로그/메트릭
├── aggregated_metrics.json
├── status.json            # SUCCESS | FAILED | INCOMPLETE
└── report.md              # 최종 보고서
```

실패해도 보고서는 생성됩니다. 환경 정리는 명시 호출:
```bash
bash experiments/<id>/scripts/90_teardown.sh
```

## 권한 모델

| 항목 | Orchestrator | Planner | Executor |
|---|---|---|---|
| read / list / glob / grep | allow | allow | allow |
| edit | deny | `.opencode-test-agents/plans/**`, `**/plan.yaml` allow | `experiments/**` allow, 그 외 ask |
| bash | read-only 일부 allow, 나머지 deny | git/ls/cat 등 read-only만 일부 allow, 나머지 deny | 환경 probe 명령 + `bash experiments/*` allow, 나머지 ask |
| webfetch | ask | ask | deny |
| task (subagent 호출) | `experiment-planner`, `experiment-executor` allow, 나머지 deny | deny | deny |

이 권한은 보수적입니다. 새로운 명령이 필요하면 각 에이전트의 `permission.bash` 섹션에 패턴을 추가하세요.

## 커스터마이징

- **새로운 probe 추가**: `context/experiment-agents-context.md`의 "3. Probe 라이브러리"에 정확한 쉘 명령과 함께 등록.
- **새로운 collector 추가**: "4. Collector 라이브러리"에 파싱 로직(jq 또는 python)과 함께 등록.
- **모델 지정**: 각 에이전트 frontmatter에 `model: <provider>/<model_id>` 추가. 미지정 시 글로벌 설정을 따릅니다.
- **온도 조정**: Planner 0.1, Executor 0.0이 기본. Executor는 결정론적이어야 하므로 0 권장.

## 계획 재개

새 Opencode 세션에서 이어갈 때는 `experiment-orchestrator`로 전환한 뒤 `.opencode-test-agents/plans/<id>.md`의 `Resume Prompt`를 붙여 넣으세요. Executor로 수동 fallback할 때는 숨김 subagent 수동 호출이 가능한 환경에서 `@experiment-executor`에 `experiments/<id>/plan.yaml`과 matching handoff 경로를 함께 전달하세요. 환경이 hidden subagent 수동 호출을 막으면 임시로 해당 agent의 `hidden`/`mode`를 바꿔 troubleshooting하고 끝나면 되돌립니다.

## 알려진 한계

- 단일 머신 가정. 분산 실험은 별도 설계 필요.
- 결과 저장은 로컬 파일시스템. DB/오브젝트 스토리지 푸시 미지원.
- 실험 검색 인덱스 없음. `experiments/`를 직접 grep해야 함.
- 사용자 정의 시각화 차트는 보고서 템플릿에 자동 포함 안 됨 (collector가 PNG도 생성하면 임베드 가능).

## 라이선스

MIT — [LICENSE](LICENSE) 참조.

## 기여

PR 환영합니다. 특히 새로운 probe / collector 라이브러리 항목 추가, 다른 모델(GLM 외)에서의 동작 사례 보고가 도움됩니다.
