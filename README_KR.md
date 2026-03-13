# GDP (Generative Digital-twin Prototyper)

[English](README.md) | [한국어](README_KR.md)

LLM 기반 제조 공정 설계 자동화 및 분석 도구 연동 프레임워크

<p align="center">
  <img src="fig1.png" alt="GDP 시스템 개요" width="100%">
</p>

## 주요 기능

- **제로-샷 BOP 생성**: 도메인 지식 없이 자연어 입력만으로 구조적으로 완결된 제조 공정 데이터(Bill of Process) 생성
- **3가지 도구 연동 모드**: 기존 스크립트 어댑터 자동 생성(모드 A), AI 기반 도구 로직 합성(모드 B), 스키마 가이드 최적화(모드 C)
- **Auto-Repair 메커니즘**: 도구 어댑터의 런타임 에러를 LLM이 자가 수정하는 자동 복구 루프 (최대 k회)
- **공정 중심 데이터 모델**: LLM 토큰 효율성과 도구 호환성을 최적화한 평탄화 BOP 구조
- **3패널 동기화 인터페이스**: BOP 테이블, 3D 레이아웃, AI 어시스턴트 간 양방향 실시간 동기화

## 빠른 시작

### 사전 요구사항

- Python 3.10+
- Node.js 18+
- LLM API 키 1개 이상 (Gemini, OpenAI, 또는 Anthropic)

### 설치

[https://anonymous.4open.science/r/gdp-0D5D](https://anonymous.4open.science/r/gdp-0D5D) 에서 소스를 다운로드한 뒤:

```bash
cd gdp
pip install -r requirements.txt
npm install
```

### 환경 설정

```bash
cp .env.example .env
# .env를 편집하여 API 키 입력
```

### 실행

```bash
# 1. 백엔드 API 서버 시작
uvicorn app.main:app --reload --port 8000

# 2. 프론트엔드 개발 서버 시작 (별도 터미널)
npm run dev
```

브라우저에서 http://localhost:5173 접속

## 사용법

인터페이스는 **데이터 테이블**(왼쪽), **3D 레이아웃**(가운데), **AI 어시스턴트**(오른쪽) 세 개의 동기화된 패널로 구성됩니다.

### 수동 워크플로우

1. **마스터 테이블을 먼저 등록** — 공정 생성 전에 장비(Equipment), 작업자(Workers), 자재(Materials) 탭에서 리소스를 등록합니다.
2. **공정 생성** — BOP 탭에서 **+ Add Process** 를 클릭하여 공정 단계를 추가하고, 이름·설명·사이클 타임을 인라인 편집합니다.
3. **리소스 매핑** — 각 공정 행의 장비/작업자/자재 드롭다운에서 등록된 마스터를 선택하여 할당합니다.
4. **레이아웃 배치** — 3D 뷰에서 공정 박스나 리소스를 드래그하여 위치를 조정합니다. 우클릭으로 회전(5도 단위)할 수 있습니다.

### 3D 레이아웃 조작

**카메라:**
- **좌클릭 드래그**: 카메라 회전
- **우클릭 드래그**: 카메라 이동
- **스크롤**: 줌 인/아웃

**오브젝트 조작** — 오브젝트를 클릭하여 선택한 뒤 키보드로 모드를 전환합니다:
- **T키** (이동 모드): 축 핸들을 드래그하여 XZ 평면 위 이동
- **R키** (회전 모드): 초록색 회전 링을 드래그하여 회전 (5도 단위 스냅)

### 도구 등록 및 실행

**Tools** 탭에서 분석 도구를 세 가지 방식으로 추가할 수 있습니다:

- **Upload** — **+ Upload** 클릭 후 Python 스크립트(`.py`)를 선택하면, 시스템이 입출력 스키마를 자동 분석하고 어댑터를 생성합니다.
- **AI Generate** — **AI Generate** 클릭 후 원하는 분석을 자연어로 설명하면, 스키마와 스크립트를 자동 생성합니다.
- **AI Improve** — 도구 실행 후 **AI Improve** 섹션에서 피드백을 입력하여 어댑터, 파라미터, 스크립트를 개선할 수 있습니다.

등록된 도구를 실행하려면 목록에서 선택하고 파라미터를 설정한 뒤 **Execute** 를 클릭합니다. 결과가 변경 사항(diff)으로 표시되며, **Apply Changes** 를 클릭하면 BOP에 반영됩니다.

### AI 어시스턴트

오른쪽 패널에서 자연어 명령을 입력합니다. 모델과 언어(KR/EN)를 선택한 뒤 지시를 입력하세요. 예시:

- `"자전거 조립 라인 5공정으로 생성해줘"`
- `"용접 공정 뒤에 검사 공정 추가해줘"`
- `"P003 공정 삭제해줘"`
- `"현재 병목 공정이 뭐야?"`

어시스턴트는 BOP 전체 생성, 기존 공정 수정, 질문 응답, 등록된 도구 호출이 가능합니다.

### 시나리오 관리

**Scenarios** 탭에서 작업을 저장, 로드, 비교, 내보내기할 수 있습니다:

- **저장/로드** — 현재 BOP를 이름을 붙여 저장하고, 이후에 다시 불러올 수 있습니다.
- **비교** — 여러 시나리오를 선택하여 공정 수, UPH, 리소스 현황을 나란히 비교합니다.
- **내보내기** — BOP를 JSON 또는 Excel로 다운로드합니다. 이전에 내보낸 파일을 업로드하여 복원할 수도 있습니다.

## 프로젝트 구조

```
gdp/
├── app/                          # FastAPI 백엔드
│   ├── main.py                   # API 엔드포인트
│   ├── llm_service.py            # LLM 오케스트레이션
│   ├── llm/                      # LLM 프로바이더 구현
│   └── tools/                    # 도구 어댑터 시스템
├── src/                          # React 프론트엔드 소스
├── dist/                         # 빌드된 프론트엔드
├── public/models/                # 3D 모델 에셋 (GLB)
├── data/tool_registry/           # 등록된 분석 도구 (12개)
├── uploads/scripts/              # 도구 스크립트
├── tests/                        # 테스트 코드
└── experiments/                  # 재현 가능한 실험 코드
    ├── ex1_zero_shot_generation/ # 실험 1: 제로-샷 BOP 생성
    ├── ex2_adapter_auto_repair/  # 실험 2: 어댑터 자동 복구
    └── ex3_design_efficiency/    # 실험 3: 설계 효율성 평가
```

## 실험

### 실험 1: 제로-샷 공정 생성 성능

**10종 제조 제품군** (GT 83스텝)에 대해 4종 LLM의 제로-샷 BOP 생성 성능을 평가. 3종 모델이 N:M 커버리지 매칭 기준 평균 **F1 88.9%** 달성.

```bash
# 빠른 테스트 (1개 제품, 저비용 모델)
python experiments/ex1_zero_shot_generation/run_experiment.py --test

# 전체 실험 (전 모델, 전 제품)
python experiments/ex1_zero_shot_generation/run_experiment.py
```

### 실험 2: 도구 어댑터 자동 생성 및 Auto-Repair 강건성

**10종 분석 도구** × **8개 BOP 시나리오** × 수리 예산 k=0..3 (총 320회 실행). Auto-Repair가 k=2에서 **실행 통과율 100%** 달성, 2단계 평가로 **16.2% 조용한 실패** 발견.

```bash
# 빠른 테스트 (1개 도구, 1개 BOP)
python experiments/ex2_adapter_auto_repair/run_experiment.py --test

# 전체 실험 (320회)
python experiments/ex2_adapter_auto_repair/run_experiment.py
```

### 실험 3: 설계 작업 효율성 평가

경력 3~15년 엔지니어 5명이 동일한 E-Bike 조립 라인 설계 과제(6공정 BOP 초기 구축 + 100 UPH 달성을 위한 병목 병렬화)를 수동 편집과 AI 보조 생성 두 조건에서 수행. AI 보조 설계가 평균 **55.2%** 시간 단축, 일관된 소요 시간(SD 0.7분) 확인.

과제 지시서 및 자세한 내용은 [experiments/ex3_design_efficiency/](experiments/ex3_design_efficiency/)를 참조.

## 사전 등록된 분석 도구

GDP에는 실험 2에서 사용된 10종의 제조 분석 도구가 사전 등록되어 웹 인터페이스에서 바로 사용 가능합니다:

| 도구 | 난이도 | 설명 |
|------|--------|------|
| Bottleneck Analyzer | Easy | 유효 사이클 타임 기준 병목 공정 식별 |
| Line Balance Calculator | Easy | 라인 밸런스율 및 택트 타임 계산 |
| Equipment Utilization | Medium | 설비 가동률 분석 및 과부하 탐지 |
| Material Flow Analyzer | Medium | 자재 흐름 추적 및 수량 집계 |
| Process Distance Analyzer | Medium | 자재 이동 거리 계산 |
| Safety Zone Checker | Medium | 공정-장애물 간 안전 거리 검증 |
| Worker Skill Matcher | Medium | 작업자-공정 간 숙련도 매칭 평가 |
| Energy Estimator | Hard | 공정별 에너지 소비량 및 비용 계산 |
| Layout Compactor | Hard | 최소 간격 유지하며 레이아웃 압축 |
| Takt Time Optimizer | Hard | 목표 UPH 달성을 위한 병렬 스테이션 최적화 |

## 3D 에셋 라이선스

본 프로젝트는 CC0 1.0 / 퍼블릭 도메인 하의 3D 모델을 사용합니다.

## 인용

```bibtex
@inproceedings{anonymous2026gdp,
  title     = {GDP (Generative Digital-twin Prototyper): An LLM-Based Framework
               for Automated Process Design and Analysis Tool Integration},
  author    = {Anonymous},
  booktitle = {Proc. IEEE Int. Conf. Autom. Sci. Eng. (CASE)},
  year      = {2026}
}
```

## 라이선스

[MIT](LICENSE)
