# Changelog

본 프로젝트는 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

## [Unreleased]

### Added
- `installation.md` 설치 가이드와 README 상단 설치 안내
- `tools/validate_plan.py`, `tools/aggregate_metrics.py`, `tools/render_report.py` helper 도구
- `experiment-orchestrator` primary agent entrypoint

### Changed
- 저장소 파일 배치를 `agents/`, `context/`, `examples/`, `.github/workflows/` 표준 구조로 정리
- Executor가 plan 검증, metrics 집계, report 생성을 helper 도구로 수행하도록 지침 강화
- `plan.yaml`에 top-level `success_criteria` 필드 추가
- `experiment-planner`와 `experiment-executor`를 hidden subagent로 전환하고 orchestrator가 handoff를 조율하도록 변경

## [0.1.0] - 2026-04-30

### Added
- 두 개의 primary 에이전트: `experiment-planner`, `experiment-executor`
- 공통 컨텍스트 파일: `context/experiment-agents-context.md` (plan.yaml 스키마, probe/collector 라이브러리, 보고서 템플릿 정의)
- 예시 plan.yaml: `examples/plan-template.yaml` (빈 템플릿), `examples/plan-spdk-example.yaml` (SPDK 완전 예시)
- 한 줄 설치/제거 스크립트: `install.sh`, `uninstall.sh` (글로벌/프로젝트, dry-run, 백업 자동화)
- GitHub Actions: markdown/YAML lint workflow

### Design
- 약한 모델(GLM-4.7 등) 대응: 단계별 체크리스트, 좋은/나쁜 logic 양쪽 예시, 사용자 응답 인식 단어 표, probe/collector를 실제 쉘 명령 수준까지 명시
- 사용자 충돌 회피: 프로젝트 루트에 `AGENTS.md`를 두지 않고 `experiment-agents/context.md`로 격리 (Opencode/Cursor 등이 자동 로드하는 `AGENTS.md`와 충돌 없음)
- Probe / Collector 라이브러리: 13개 probe (os, cpu, mem, disk, git, env, ulimit, time, nvme, hugepages, numa, pci, iommu, irq, network, gpu, kernel_modules, sysctl), 6개 collector (parse_fio_json, parse_perf_stat, parse_iostat, parse_time, parse_json_file, parse_regex)

[Unreleased]: https://github.com/USER/opencode-experiment-agents/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/USER/opencode-experiment-agents/releases/tag/v0.1.0
