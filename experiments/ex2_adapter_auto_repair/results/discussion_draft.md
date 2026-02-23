# Ex2 Discussion Draft -- IEEE CASE 2026

## (English -- for paper)

### V. RESULTS AND DISCUSSION

#### A. Overall Execution Pass Rate

Table I summarizes the execution pass rates across all 320 experimental
runs. At the baseline ($k{=}0$, no repair), the LLM-generated adapters
achieved an execution pass rate of **80.0%** (64/80), with two distinct
failure modes affecting two tools. When the auto-repair mechanism is
enabled with $k{=}1$, the pass rate increases to **98.8%** (79/80), and
reaches **100.0%** at $k{=}2$ and $k{=}3$. This indicates that at most
two repair iterations are sufficient to resolve all observed execution
failures in our benchmark.

#### B. Effect of Adapter Difficulty

We categorize the 10 tools into three difficulty levels based on the
complexity of the required BOP-to-tool data transformation (Table II).

**Easy (2 tools)** -- adapters requiring simple field extraction --
achieved 100% execution pass rate at all $k$ values. **Medium (5 tools)**
-- adapters requiring cross-referencing of multiple BOP arrays or
coordinate transformations -- achieved 100% at $k{=}0$ for four tools,
with `worker_skill_matcher` failing at baseline due to a post-processor
type error. All Medium tools reach 100% at $k{=}1$.

**Hard (3 tools)** showed a pass rate of 66.7% (16/24) at $k{=}0$.
The failures are attributable to `layout_compactor`, which requires
converting flat BOP process data into a topological graph structure.
The other two Hard tools (`energy_estimator`, `takt_time_optimizer`)
passed at baseline. At $k{=}1$, Hard tools reach 95.8% (23/24),
with one residual `layout_compactor` failure (SyntaxError from
an improperly repaired adapter). Full resolution requires $k{=}2$.

#### C. Error Analysis

The 16 baseline failures exhibit two distinct patterns (Table IV):

1. **`ImportError` in pre-process** (8 cases, `layout_compactor`):
   The generated adapter attempted to import the `copy` module, which
   is not in the restricted sandbox allowlist. The adapter correctly
   used `copy.deepcopy()` for data transformation -- a reasonable
   programming choice. The issue is environmental constraint awareness
   rather than algorithmic understanding.

2. **`TypeError` in post-process** (8 cases, `worker_skill_matcher`):
   The generated post-processor returned an incompatible type when
   merging tool output back into BOP format. This reflects a schema
   mapping error in the adapter's understanding of the BOP data
   structure.

These two failure modes reveal complementary limitations: the first
is an environmental constraint violation (which module is allowed),
while the second is a structural mapping error (how to integrate
results). Both are amenable to auto-repair since error messages
provide explicit diagnostic information.

#### D. Repair Convergence

When auto-repair is enabled ($k \geq 1$), 47 repair events occurred
across all runs. The vast majority (44/47, 93.6%) succeeded with a
single repair attempt, and the remaining 3 cases required exactly
2 attempts. The average repair attempts for success was **1.06**,
demonstrating rapid convergence.

The repair process for `layout_compactor` follows a predictable
pattern: the repair LLM replaces the forbidden `copy` module with
`json.loads(json.dumps(...))` -- a valid deep-copy alternative.
For `worker_skill_matcher`, the repair addresses the type conversion
error in the post-processor.

#### E. Output Correctness -- Two-Tier Evaluation

A critical finding emerges when we extend evaluation beyond execution
success to **output correctness** using property-based validation
(Table VI). Each tool's output is verified against domain-specific
invariants: mathematical consistency (e.g., bottleneck process has
the maximum effective cycle time), structural integrity (e.g., no
negative coordinates in layout), and aggregation correctness
(e.g., distribution sums match totals).

The results reveal a significant gap between execution pass rate
and output correctness:

| $k$ | Exec Pass | Output Correct | Full Pass Rate |
|-----|-----------|----------------|----------------|
| 0   | 80.0%     | 98.4%          | **78.8%**      |
| 1   | 98.8%     | 84.8%          | **83.8%**      |
| 2   | 100.0%    | 83.8%          | **83.8%**      |
| 3   | 100.0%    | 83.8%          | **83.8%**      |

At $k{=}2$ (100% execution pass), only **83.8%** of runs produce
fully correct output. This means **16.2% of adapters run without
errors but produce semantically incorrect results** -- a class of
failures invisible to execution-only evaluation.

#### F. Per-Tool Output Correctness Analysis

Table VII provides per-tool correctness breakdown:

- **7/10 tools** (all Easy + 4 Medium + `energy_estimator`) achieve
  **100% output correctness** across all validated runs.

- **`takt_time_optimizer`** (Hard, 87.5% correct): Fails on
  `large_scale` BOP (14 processes) where the adapter incorrectly
  reduces a process's parallel count from 2 to 1 -- violating the
  optimization constraint that parallelism should only increase.
  This is a logical error in the adapter's optimization mapping.

- **`layout_compactor`** (Hard, 39.1% correct): Produces **negative
  coordinates** (e.g., $z = -4.0$) and occasionally **expands** the
  layout span instead of compacting it (reduction = $-2.88\%$).
  In a 3D digital twin, this manifests as walls and equipment
  rendered in invalid positions. The adapter runs without errors
  but generates geometrically incorrect results.

- **`worker_skill_matcher`** (Medium, 12.5% correct): The
  `skill_distribution` field is inconsistent with the `matches`
  array -- the distribution sums to fewer entries than the number
  of evaluated matches. The adapter omits some workers when
  building the distribution summary.

These findings demonstrate that **auto-repair resolves execution
errors but does not guarantee semantic correctness**. The repaired
adapters may introduce subtle data transformation errors that pass
runtime checks but produce incorrect domain results.

#### G. Cost-Benefit Analysis

The auto-repair mechanism introduces a latency overhead.
Successful executions without repair complete in approximately
**0.13s** on average (adapter execution + subprocess only).
Repaired executions require **8--19s** on average, dominated by
LLM API round-trips for error diagnosis and code regeneration.

Adapter generation time shows a positive correlation with
difficulty level: Easy tools average ~28s, Medium tools ~35s,
and Hard tools ~65s. The outlier `layout_compactor` (~86s)
reflects the model's extended reasoning for the complex
bidirectional graph transformation.

From a practical standpoint, repair costs are incurred only once
per tool registration -- the repaired adapter is cached and reused.
However, the output correctness gap suggests that repair alone is
insufficient; **runtime validation** should complement auto-repair
to ensure not just executability but correctness.

#### H. BOP Scenario Independence

At $k{=}0$, execution pass rates vary by BOP scenario only to the
extent that different BOPs expose the same tool failures uniformly.
All 8 scenarios produce identical per-tool results, confirming that
adapter performance is invariant to BOP structure, scale
(2--14 processes), and manufacturing domain (bicycle, EV battery,
SMT, automobile).

Output correctness failures are also BOP-dependent for specific
tools: `layout_compactor` fails on BOPs with parallel structures
(bicycle, complex\_dag, washing\_machine) where coordinate
calculations are more complex, while passing on simpler linear
BOPs (minimal, smt\_line, tire).

#### I. Threats to Validity

1. **Single model**: Adapter generation used only `gemini-2.5-flash`.
   Different models may exhibit different failure modes.

2. **Deterministic adapter reuse**: The same adapter is tested across
   all 8 BOPs per tool. This reflects the real system's behavior
   but limits independent failure observation.

3. **Sandbox constraint**: The `ImportError` failure mode is specific
   to our restricted execution environment. In an unrestricted
   environment, this failure would not occur; however, sandboxing
   is a deliberate security measure in production systems.

4. **Validator coverage**: Property-based validators check a finite
   set of invariants. Additional invariants (e.g., topological
   ordering in layout compaction) may reveal further correctness
   issues not captured by our current validator suite.

5. **Non-determinism**: LLM-generated adapters are stochastic.
   A different random seed may produce different adapters with
   different correctness characteristics.

---

## (한국어 -- 논문용)

### V. 결과 및 고찰

#### A. 전체 실행 통과율

표 I은 총 320회 실험 실행에 대한 실행 통과율을 요약한다.
기준선($k{=}0$, 수리 없음)에서 LLM이 생성한 어댑터는 **80.0%** (64/80)의
실행 통과율을 달성하였으며, 2개의 도구에서 2가지 유형의 실패가 발생하였다.
자동 수리 메커니즘을 $k{=}1$로 활성화하면 통과율은 **98.8%** (79/80)로
상승하며, $k{=}2$ 및 $k{=}3$에서 **100.0%**에 도달한다. 이는 최대 2회의
수리 반복으로 관찰된 모든 실행 실패를 해결할 수 있음을 나타낸다.

#### B. 어댑터 난이도의 영향

BOP-도구 간 데이터 변환의 복잡도를 기준으로 10개 도구를 세 난이도 수준으로
분류하였다(표 II).

**Easy (2개 도구)** -- 단순 필드 추출 -- 는 모든 $k$ 값에서 100% 통과율을
달성하였다. **Medium (5개 도구)** 중 4개는 $k{=}0$에서 100%를 달성하였으나,
`worker_skill_matcher`는 후처리기 타입 에러로 기준선에서 실패하였다.
모든 Medium 도구는 $k{=}1$에서 100%에 도달한다.

**Hard (3개 도구)** 는 $k{=}0$에서 66.7% (16/24)의 통과율을 보였다.
실패는 `layout_compactor`에 기인하며, 나머지 두 Hard 도구는 기준선에서
통과하였다. $k{=}1$에서 Hard 도구는 95.8% (23/24)에 도달하고,
완전 해결은 $k{=}2$를 필요로 한다.

#### C. 에러 분석

16건의 기준선 실패는 두 가지 패턴을 보인다(표 IV):

1. **`ImportError` (전처리 단계, 8건, `layout_compactor`)**: 생성된
   어댑터가 샌드박스 허용 목록에 없는 `copy` 모듈을 임포트 시도.
   `copy.deepcopy()` 사용은 합리적 선택이나, 문제는 환경 제약 인식 부족.

2. **`TypeError` (후처리 단계, 8건, `worker_skill_matcher`)**: 후처리기가
   도구 출력을 BOP 형식으로 병합할 때 호환되지 않는 타입을 반환.
   BOP 데이터 구조에 대한 어댑터의 스키마 매핑 에러.

두 실패 모드는 상호보완적 한계를 드러낸다: 환경 제약 위반과 구조적 매핑 에러.
두 유형 모두 에러 메시지가 명시적 진단 정보를 제공하므로 자동 수리에 적합하다.

#### D. 수리 수렴

자동 수리 활성화 시, 47건의 수리 이벤트 중 44건(93.6%)이 1회 시도로 성공하고
나머지 3건은 정확히 2회 시도를 필요로 하였다. 평균 수리 시도 횟수는
**1.06회**로 빠른 수렴을 보여준다.

#### E. 출력 정확도 -- 2단계 평가

실행 성공을 넘어 **출력 정확도**를 속성 기반 검증(property-based validation)으로
측정하면 중요한 발견이 나타난다(표 VI). 각 도구의 출력을 도메인 특화 불변 조건으로
검증한다: 수학적 일관성(예: 병목 공정이 최대 유효 사이클 타임을 가지는가),
구조적 무결성(예: 레이아웃에 음수 좌표가 없는가), 집계 정확성(예: 분포 합계가
총계와 일치하는가).

결과는 실행 통과율과 출력 정확도 간 **유의미한 격차**를 드러낸다:

| $k$ | 실행 통과 | 출력 정확 | 완전 통과율 |
|-----|----------|----------|-----------|
| 0   | 80.0%    | 98.4%    | **78.8%** |
| 1   | 98.8%    | 84.8%    | **83.8%** |
| 2   | 100.0%   | 83.8%    | **83.8%** |
| 3   | 100.0%   | 83.8%    | **83.8%** |

$k{=}2$에서 실행 100% 통과하지만, 출력이 완전히 올바른 비율은 **83.8%**에
불과하다. 즉, **16.2%의 어댑터가 에러 없이 실행되지만 의미적으로 틀린 결과를
생성**하며, 이는 실행 전용 평가로는 발견할 수 없는 실패 유형이다.

#### F. 도구별 출력 정확도 분석

표 VII은 도구별 정확도를 제공한다:

- **7/10 도구** (Easy 전체 + Medium 4개 + `energy_estimator`)가
  검증된 모든 실행에서 **100% 출력 정확도**를 달성.

- **`takt_time_optimizer`** (Hard, 87.5% 정확): `large_scale` BOP
  (14공정)에서 어댑터가 공정의 병렬 수를 2에서 1로 잘못 감소시킴 --
  병렬성은 증가만 해야 한다는 최적화 제약 위반. 논리적 매핑 에러.

- **`layout_compactor`** (Hard, 39.1% 정확): **음수 좌표** 생성
  (예: $z = -4.0$) 및 레이아웃 span을 압축하는 대신 **확장**하는 경우 발생
  (reduction = $-2.88\%$). 3D 디지털 트윈에서 이는 벽과 장비가 잘못된
  위치에 렌더링되는 것으로 나타남. 어댑터가 에러 없이 실행되지만
  기하학적으로 부정확한 결과를 생성.

- **`worker_skill_matcher`** (Medium, 12.5% 정확): `skill_distribution`
  필드가 `matches` 배열과 불일치 -- 분포 합계가 평가된 매칭 수보다 적음.
  어댑터가 분포 요약 구성 시 일부 작업자를 누락.

이 발견은 **자동 수리가 실행 에러는 해결하지만 의미적 정확성은 보장하지
않음**을 입증한다. 수리된 어댑터는 런타임 검사를 통과하지만 잘못된 도메인
결과를 생성하는 미묘한 데이터 변환 에러를 도입할 수 있다.

#### G. 비용-편익 분석

자동 수리 메커니즘은 지연 시간 오버헤드를 수반한다.
수리 없이 성공한 실행은 평균 약 **0.13초**에 완료된다.
수리된 실행은 평균 **8--19초**를 요구하며, LLM API 왕복 호출이 지배적이다.

어댑터 생성 시간은 난이도와 양의 상관관계를 보인다: Easy 평균 ~28초,
Medium ~35초, Hard ~65초. 이상치 `layout_compactor` (~86초)는 복잡한
양방향 그래프 변환에 대한 모델의 확장된 추론을 반영한다.

실용적 관점에서, 수리 비용은 도구 등록 시 1회만 발생하나, 출력 정확도 격차는
수리만으로는 불충분함을 시사한다. **런타임 검증**이 자동 수리를 보완하여
실행 가능성뿐 아니라 정확성도 보장해야 한다.

#### H. BOP 시나리오 독립성

$k{=}0$에서의 실행 통과율은 동일한 도구 실패를 균일하게 노출하는 범위
내에서만 BOP 시나리오에 따라 다르다. 8개 시나리오 모두 동일한 도구별 결과를
산출하여, 어댑터 성능이 BOP 구조, 규모(2-14공정), 제조 도메인에 불변임을
확인한다.

출력 정확도 실패는 특정 도구에 대해 BOP 의존적이다: `layout_compactor`는
병렬 구조를 가진 BOP(bicycle, complex\_dag, washing\_machine)에서 좌표
계산이 더 복잡하여 실패하는 반면, 단순한 선형 BOP(minimal, smt\_line,
tire)에서는 통과한다.

#### I. 타당성 위협

1. **단일 모델**: `gemini-2.5-flash`만 사용. 다른 모델은 상이한 실패 모드를
   보일 수 있다.

2. **결정론적 어댑터 재사용**: 동일 어댑터가 도구당 8개 BOP에서 테스트됨.
   실제 시스템 동작을 반영하나 독립적 실패 관찰을 제한.

3. **샌드박스 제약**: `ImportError` 실패는 제한된 실행 환경에 특유하다.
   비제한 환경에서는 발생하지 않으나, 샌드박싱은 프로덕션의 보안 조치이다.

4. **검증기 범위**: 속성 기반 검증기는 유한한 불변 조건 집합을 확인한다.
   추가 불변 조건이 현재 검증기가 포착하지 못한 정확도 문제를 드러낼 수 있다.

5. **비결정성**: LLM 생성 어댑터는 확률적이다. 다른 실행에서 다른 어댑터가
   생성되어 다른 정확도 특성을 보일 수 있다.

---

## (한국어 -- 핵심 요약 및 해설)

### 실험 결과 핵심 요약

**실험 규모**: 10개 도구 x 8개 BOP 시나리오 x 4개 k값 = 총 320회 실행

#### 1. 핵심 발견: 실행 성공 != 결과 정확

이전 실험에서는 "실행이 에러 없이 완료되는가"만 평가했다면, 이번에는
**속성 기반 검증(property-based validation)**을 추가하여 "결과가 올바른가"도 평가.

| 지표 | k=0 | k=1 | k=2 | k=3 |
|------|-----|-----|-----|-----|
| 실행 통과율 | 80% | 98.8% | **100%** | **100%** |
| 출력 정확도 | 98.4% | 84.8% | 83.8% | 83.8% |
| **완전 통과율** | **78.8%** | **83.8%** | **83.8%** | **83.8%** |

**핵심 인사이트**: k=2에서 실행은 100% 통과하지만, 완전히 올바른 출력은
**83.8%**에 불과. **16.2%의 어댑터가 에러 없이 돌지만 틀린 결과를 낸다.**

#### 2. 에러 분석: 2가지 실패 모드

이번 실행에서는 이전과 달리 **2개 도구**가 기준선에서 실패:

| 도구 | 에러 타입 | 에러 단계 | 원인 |
|------|----------|----------|------|
| `layout_compactor` | ImportError | pre_process | `copy` 모듈 임포트 (샌드박스 차단) |
| `worker_skill_matcher` | TypeError | post_process | 반환 타입 불일치 (스키마 매핑 에러) |

#### 3. 도구별 출력 정확도 (이번 실험의 핵심 새 지표)

| 도구 | Correct Rate | Avg Score | 주요 에러 |
|------|-------------|-----------|---------|
| bottleneck_analyzer | **100%** | 100% | - |
| line_balance_calculator | **100%** | 100% | - |
| equipment_utilization | **100%** | 100% | - |
| material_flow_analyzer | **100%** | 100% | - |
| process_distance_analyzer | **100%** | 100% | - |
| safety_zone_checker | **100%** | 100% | - |
| energy_estimator | **100%** | 100% | - |
| takt_time_optimizer | **88%** | 99.7% | 병렬 수 감소 (large_scale) |
| layout_compactor | **39%** | 95.2% | 음수 좌표, span 확장 |
| worker_skill_matcher | **13%** | 95.1% | skill_distribution 합계 불일치 |

**3개 도구가 실행은 되지만 틀린 결과를 생성**:
- `layout_compactor`: z=-4.0 같은 음수 좌표 -> 3D에서 벽이 바닥 아래로
- `worker_skill_matcher`: 분포 요약에서 작업자 누락
- `takt_time_optimizer`: 최적화가 오히려 병렬성 줄임

#### 4. 논문에서 강조할 포인트

1. **"실행 성공 != 결과 정확"**: 가장 중요한 발견. 기존 Pass@k 평가의 한계 지적
2. **2단계 평가 프레임워크**: Execution Pass + Output Correctness = Full Pass
3. **Auto-repair의 한계**: 실행 에러는 잡지만 semantic correctness는 보장 못함
4. **실용적 시사점**: 런타임 검증(property-based validation)이 auto-repair를 보완해야 함
5. **도구 복잡도와 정확도 상관관계**: Hard 도구일수록 출력 정확도가 낮아짐

#### 5. 이전 실험 대비 변화

| 항목 | 이전 실행 | 이번 실행 |
|------|----------|----------|
| k=0 실행 통과 | 90% (72/80) | 80% (64/80) |
| k=1 실행 통과 | 100% | 98.8% |
| k=2 실행 통과 | 100% | 100% |
| 실패 도구 수 (k=0) | 1개 | 2개 |
| 에러 유형 | ImportError만 | ImportError + TypeError |
| **출력 정확도** | 미측정 | **83.8%** (k=2 기준) |

LLM의 확률적 특성으로 인해 매 실행마다 생성되는 어댑터가 다르므로 결과도 다름.
이는 논문의 "Threats to Validity"에서 비결정성(non-determinism)으로 언급.

### 향후 연구 제안

- **멀티 모델 비교**: GPT-4o, Claude Sonnet 등으로 확장 -- 정확도 차이 비교
- **검증기 강화**: topological ordering, AABB overlap 등 추가 불변 조건
- **자동 검증 + 수리 루프**: 출력이 틀리면 검증 에러를 피드백으로 2차 수리
- **확률적 분석**: 동일 조건 N회 반복하여 정확도의 분포 및 신뢰구간 측정
