# 실험 2: 어댑터 Auto-Repair

[English](README.md) | [한국어](README_KR.md)

## 개요

이 실험은 LLM이 생성한 도구 어댑터에 대한 반복적 자동 수리 메커니즘의 효과를 측정합니다. 어댑터가 검증에 실패(스키마 오류, 런타임 오류, 잘못된 출력)하면, 시스템이 오류를 LLM에 피드백하여 최대 *k*회 반복으로 자동 수리합니다.

10개 분석 도구와 8개 BOP 시나리오에 걸쳐 **Pass@1** (베이스라인, 수리 없음)과 **Pass@k** (*k* = 1, 2, 3 수리 반복)를 비교합니다.

## 실험 규모

- **10개 도구** × **8개 BOP** × **4개 조건** (k=0,1,2,3) = **320회 실행**

## 도구

| 도구 | 난이도 | 설명 |
|------|--------|------|
| bottleneck_analyzer | Easy | 병목 공정 식별 |
| line_balance_calculator | Easy | 라인 밸런싱 지표 계산 |
| equipment_utilization | Medium | 설비 가동률 계산 |
| process_distance_analyzer | Medium | 공정 간 거리 측정 |
| worker_skill_matcher | Medium | 작업자-요구 스킬 매칭 |
| material_flow_analyzer | Medium | 자재 흐름 패턴 분석 |
| safety_zone_checker | Hard | 안전 구역 준수 검증 |
| takt_time_optimizer | Hard | 택트 타임 최적화 |
| energy_estimator | Hard | 에너지 소비량 추정 |
| layout_compactor | Hard | 공간 레이아웃 최적화 |

## BOP 시나리오

`bop_scenarios/` 폴더에 위치: bicycle, complex_dag, ev_battery, large_scale, minimal, smt_line, tire, washing_machine.

## 사용법

```bash
# 저장소 루트에서 실행
# 빠른 테스트: 1개 도구, 1개 BOP, k=0
python experiments/ex2_adapter_auto_repair/run_experiment.py --test

# 전체 실험: 320회 실행
python experiments/ex2_adapter_auto_repair/run_experiment.py

# 베이스라인만 (80회 실행, k=0)
python experiments/ex2_adapter_auto_repair/run_experiment.py --k 0

# 특정 도구 지정
python experiments/ex2_adapter_auto_repair/run_experiment.py --tools bottleneck_analyzer line_balance_calculator

# 특정 BOP 지정
python experiments/ex2_adapter_auto_repair/run_experiment.py --bops bicycle minimal

# 결과 분석 및 그래프 생성
python experiments/ex2_adapter_auto_repair/analyze_results.py
```

**사전 요구사항**: 저장소 루트의 `.env`에 API 키를 설정하세요 (`.env.example` 참조).

## 결과

원시 결과는 `results/` 폴더에 타임스탬프가 포함된 JSON 파일로 저장됩니다. 각 실행은 다음을 생성합니다:
- `*_detail_*.json`: 도구별, BOP별 상세 결과
- `*_summary_*.json`: 수리 반복별 집계 통과율

분석 산출물은 `results/figures/` 폴더에 저장됩니다:
- 출판용 차트 (PDF/PNG)
- LaTeX 테이블 (`tables.tex`, `tables_ko.tex`)
