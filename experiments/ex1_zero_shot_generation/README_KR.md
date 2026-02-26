# 실험 1: Zero-Shot BOP 생성

[English](README.md) | [한국어](README_KR.md)

## 개요

이 실험은 다양한 LLM의 zero-shot Bill of Process(BOP) 생성 능력을 평가합니다. 제품명(예: "EV Battery Cell")만 주어진 상태에서, 각 모델이 사전 예시나 파인튜닝 없이 공정 단계와 설비 배정을 포함한 완전한 BOP 구조를 생성합니다.

## 정답 데이터 (Ground Truth)

- **ex1_gt_kr.json** / **ex1_gt_en.json**: 10개 제품 카테고리에 대해 수작업으로 큐레이션한 정답 BOP (총 83개 공정 단계)
- **gt_verification.md**: 정답 검증 과정 및 참조 출처 문서

### 제품 목록

| ID | 제품 | 공정 수 |
|----|------|---------|
| P01 | EV 배터리 셀 | 14 |
| P02 | 자동차 BIW (차체) | 9 |
| P03 | 스마트폰 SMT | 7 |
| P04 | 반도체 패키징 | 9 |
| P05 | 태양광 PV 모듈 | 9 |
| P06 | EV 모터 헤어핀 스테이터 | 8 |
| P07 | OLED 디스플레이 패널 | 6 |
| P08 | 세탁기 | 8 |
| P09 | 제약 정제 | 6 |
| P10 | 타이어 제조 | 7 |

## 테스트 모델

| 모델 | 제공사 |
|------|--------|
| Gemini 2.5 Flash | Google |
| GPT-5 Mini | OpenAI |
| Claude Sonnet 4.5 | Anthropic |
| Gemini 2.5 Pro | Google |
| GPT-5.2 | OpenAI |

## 평가 지표

- **Recall (n/M)**: 매칭된 공정 수 / 전체 정답 공정 수
- **Accuracy**: 정답 공정 중 정확히 매칭된 비율
- **Sequence Match**: 매칭된 공정 쌍 중 올바른 순서를 유지하는 비율
- **N:M Coverage**: 여러 생성 공정이 하나의 정답 공정을 커버할 수 있는 다대다 매칭 평가

## 사용법

```bash
# 저장소 루트에서 실행
# 저비용 모델로 1개 제품 빠른 테스트
python experiments/ex1_zero_shot_generation/run_experiment.py --test

# 전체 모델, 전체 제품 실행
python experiments/ex1_zero_shot_generation/run_experiment.py

# 특정 모델 지정
python experiments/ex1_zero_shot_generation/run_experiment.py --models gemini-2.5-flash gpt-5-mini

# 특정 제품 지정
python experiments/ex1_zero_shot_generation/run_experiment.py --products P01 P03

# 기존 결과를 개선된 지표로 재평가
python experiments/ex1_zero_shot_generation/reevaluate.py
```

**사전 요구사항**: 저장소 루트의 `.env`에 API 키를 설정하세요 (`.env.example` 참조).

## 결과

원시 결과는 `results/` 폴더에 타임스탬프가 포함된 JSON 파일로 저장됩니다. 각 실행은 다음을 생성합니다:
- `*_detail_*.json`: 제품별, 모델별 상세 결과
- `*_summary_*.json`: 집계 요약 통계
- `*_reeval_*.json`: 1:1 및 N:M 방법론 재평가 결과
