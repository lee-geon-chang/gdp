import json
import logging
import os
from dotenv import load_dotenv
from app.tools.tool_prompts import TOOL_ANALYSIS_PROMPT
from app.llm import get_provider

load_dotenv()
log = logging.getLogger("tool_analyzer")


def _strip_markdown_block(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split('\n')
        lines = lines[1:]  # remove opening ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = '\n'.join(lines)
    return text.strip()


async def analyze_script(
    source_code: str,
    file_name: str,
    sample_input: str = None,
    model: str = None,
    input_schema_override: dict = None,
    output_schema_override: dict = None
) -> dict:
    """LLM을 사용하여 스크립트의 입출력 스키마를 분석합니다.

    Args:
        source_code: 분석할 소스 코드
        file_name: 파일명
        sample_input: 샘플 입력 데이터
        model: 사용할 LLM 모델
        input_schema_override: 입력 스키마 오버라이드 (제공 시 분석 스킵)
        output_schema_override: 출력 스키마 오버라이드 (제공 시 분석 스킵)
    """
    import time
    start_time = time.time()

    log.info("=" * 60)
    log.info("[analyze] === 스크립트 분석 시작 ===")
    log.info("[analyze] file_name=%s, source_code=%d bytes, sample_input=%s",
             file_name, len(source_code), "있음" if sample_input else "없음")
    log.info("[analyze] model=%s, 스키마 오버라이드=%s",
             model or "기본값", "있음" if (input_schema_override or output_schema_override) else "없음")

    # 스키마 오버라이드는 "참고 정보"로 활용 (완전 스킵하지 않음)
    # AI가 스키마를 검증하고 필요시 개선할 수 있도록

    # Get default tool model if not specified
    if not model:
        model = os.getenv("DEFAULT_TOOL_MODEL", "gemini-2.0-flash")

    # Get provider for the specified model
    provider = get_provider(model)

    # 샘플 입력 섹션
    sample_section = ""
    if sample_input:
        sample_section = f"## Sample Input Data (Use This as Reference)\n```\n{sample_input}\n```\n"

    # 스키마 오버라이드 섹션 (참고 정보로 제공)
    schema_hint_section = ""
    if input_schema_override or output_schema_override:
        schema_hint_section = "## User-Provided Schema Hints (Validate and Improve if Needed)\n"
        if input_schema_override:
            schema_hint_section += f"Input Schema Hint:\n```json\n{json.dumps(input_schema_override, indent=2, ensure_ascii=False)}\n```\n"
        if output_schema_override:
            schema_hint_section += f"Output Schema Hint:\n```json\n{json.dumps(output_schema_override, indent=2, ensure_ascii=False)}\n```\n"
        schema_hint_section += "**Important**: Use these as reference but analyze the code to verify and improve them.\n\n"

    prompt = TOOL_ANALYSIS_PROMPT.format(
        source_code=source_code,
        sample_input_section=sample_section + schema_hint_section,
    )
    log.info("[analyze] 프롬프트 준비 완료: %d bytes (샘플=%s, 스키마힌트=%s)",
             len(prompt),
             "있음" if sample_input else "없음",
             "있음" if (input_schema_override or output_schema_override) else "없음")

    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        log.info("[analyze] LLM 호출 시도 %d/%d (model=%s)", attempt + 1, max_retries, model)
        try:
            # LLM API 호출 (provider abstraction 사용)
            data = await provider.generate_json(prompt, max_retries=1)
            response_length = len(json.dumps(data))
            log.info("[analyze] LLM 응답 수신: %d bytes", response_length)
            text = json.dumps(data)

            # Gemini가 배열로 감싸서 반환하는 경우 첫 번째 요소 추출
            if isinstance(data, list):
                log.info("[analyze] 응답이 배열(len=%d) — 첫 번째 요소 추출", len(data))
                if len(data) == 0:
                    raise ValueError("응답 배열이 비어 있습니다.")
                data = data[0]

            log.info("[analyze] 파싱된 JSON 키: %s", list(data.keys()))

            # 필수 필드 검증
            for field in ["tool_name", "description", "input_schema", "output_schema"]:
                if field not in data:
                    log.error("[analyze] 누락 필드: '%s' — 전체 응답 키: %s", field, list(data.keys()))
                    log.error("[analyze] 전체 응답 데이터:\n%s", json.dumps(data, ensure_ascii=False, indent=2)[:2000])
                    raise ValueError(f"응답에 '{field}' 필드가 없습니다.")

            if "execution_type" not in data:
                data["execution_type"] = "python"

            # Standardize: force json type, remove args_format
            if "input_schema" in data:
                data["input_schema"]["type"] = "json"
                data["input_schema"].pop("args_format", None)

            elapsed = time.time() - start_time
            log.info("[analyze] 분석 성공 — tool_name=%s (소요 시간: %.2f초)", data.get("tool_name"), elapsed)
            log.info("[analyze] === 분석 완료 ===")
            log.info("=" * 60)
            return data

        except Exception as e:
            last_error = f"분석 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}"
            log.error("[analyze] %s", last_error)
            if attempt < max_retries - 1:
                continue

    elapsed = time.time() - start_time
    log.error("[analyze] 최종 실패: %s (소요 시간: %.2f초)", last_error, elapsed)
    log.info("=" * 60)
    raise Exception(f"스크립트 분석 실패: {last_error}")
