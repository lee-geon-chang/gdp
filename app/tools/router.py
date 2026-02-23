from fastapi import APIRouter, HTTPException
from typing import List
import traceback
import logging

log = logging.getLogger("tool_router")

from app.tools.tool_models import (
    AnalyzeRequest, AnalyzeResponse,
    RegisterRequest, RegisterResponse,
    ExecuteRequest, ExecuteResponse,
    ToolListItem, ToolRegistryEntry,
    ToolMetadata, AdapterCode, ParamDef,
    GenerateSchemaRequest, GenerateSchemaResponse,
    ImproveSchemaRequest,
    GenerateScriptRequest, GenerateScriptResponse,
    ImproveRequest, ImproveResponse, ApplyImprovementRequest,
    RegisterSchemaOnlyRequest, RegisterSchemaOnlyResponse,
    UpdateScriptRequest, UpdateScriptResponse,
)
from app.tools.analyzer import analyze_script
from app.tools.synthesizer import synthesize_adapter, generate_schema_from_description, improve_schema_from_feedback, generate_tool_script, improve_tool
from app.tools.registry import list_tools, get_tool, delete_tool, save_tool, generate_tool_id, find_existing_tool_id, get_script_content, update_tool_script
from app.tools.executor import execute_tool

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_tool(req: AnalyzeRequest):
    """FR-1: 업로드된 스크립트의 입출력 스키마를 분석합니다."""
    log.info("[analyze] 스크립트 분석 시작: %s (코드 길이: %d), model=%s", req.file_name, len(req.source_code), req.model or "기본값")
    try:
        result = await analyze_script(
            source_code=req.source_code,
            file_name=req.file_name,
            sample_input=req.sample_input,
            model=req.model,
            input_schema_override=req.input_schema_override.model_dump() if req.input_schema_override else None,
            output_schema_override=req.output_schema_override.model_dump() if req.output_schema_override else None,
        )
        log.info("[analyze] 분석 완료: tool_name=%s, input_type=%s, params=%d개",
                 result.get("tool_name"),
                 result.get("input_schema", {}).get("type"),
                 len(result.get("params_schema") or []))
        return AnalyzeResponse(**result)
    except Exception as e:
        log.error("[analyze] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


@router.post("/register", response_model=RegisterResponse)
async def register_tool(req: RegisterRequest):
    """FR-2 + FR-3: 어댑터 코드를 생성하고 도구를 등록합니다.

    같은 이름의 도구가 이미 존재하면 업데이트합니다.
    """
    try:
        log.info("[register] 시작 - tool_name=%s", req.tool_name)

        # 기존 도구 확인 (같은 이름이면 업데이트)
        existing_id = find_existing_tool_id(req.tool_name)
        is_update = existing_id is not None
        tool_id = existing_id if is_update else generate_tool_id(req.tool_name)

        if is_update:
            log.info("[register] 기존 도구 발견 - 업데이트 모드: %s", tool_id)
        else:
            log.info("[register] 새 도구 등록: %s", tool_id)

        metadata = ToolMetadata(
            tool_id=tool_id,
            tool_name=req.tool_name,
            description=req.description,
            execution_type=req.execution_type,
            file_name=req.file_name,
            input_schema=req.input_schema,
            output_schema=req.output_schema,
            params_schema=req.params_schema,
            example_input=req.example_input,
            example_output=req.example_output,
        )
        log.info("[register] metadata 생성 완료")

        # LLM으로 어댑터 코드 자동 생성
        log.info("[register] synthesize_adapter 호출, model=%s", req.model or "기본값")
        adapter = await synthesize_adapter(metadata, source_code=req.source_code, model=req.model)
        log.info("[register] adapter 생성 완료")

        # 레지스트리에 저장 (기존 도구가 있으면 덮어씀)
        save_tool(metadata, adapter, req.source_code)
        log.info("[register] 저장 완료")

        action = "업데이트" if is_update else "등록"
        return RegisterResponse(
            tool_id=tool_id,
            tool_name=req.tool_name,
            message=f"도구 '{req.tool_name}'이(가) {action}되었습니다.",
            adapter_preview={
                "pre_process_code": adapter.pre_process_code[:500],
                "post_process_code": adapter.post_process_code[:500],
            },
        )
    except Exception as e:
        log.error("[register] 오류 발생:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"등록 실패: {str(e)}")


@router.post("/register-schema-only", response_model=RegisterSchemaOnlyResponse)
async def register_schema_only(req: RegisterSchemaOnlyRequest):
    """스키마만으로 도구를 등록합니다 (스크립트는 나중에 업로드).

    같은 이름의 도구가 이미 존재하면 업데이트합니다.
    """
    try:
        log.info("=" * 60)
        log.info("[register-schema-only] === 스키마 우선 등록 시작 ===")
        log.info("[register-schema-only] tool_name=%s", req.tool_name)
        log.info("[register-schema-only] input_type=%s, output_type=%s",
                 req.input_schema.type, req.output_schema.type)

        # 기존 도구 확인 (같은 이름이면 업데이트)
        existing_id = find_existing_tool_id(req.tool_name)
        is_update = existing_id is not None
        tool_id = existing_id if is_update else generate_tool_id(req.tool_name)

        if is_update:
            log.info("[register-schema-only] 기존 도구 발견 - 업데이트 모드: %s", tool_id)
        else:
            log.info("[register-schema-only] 새 도구 등록: %s", tool_id)

        # 임시 파일명 생성 (나중에 실제 스크립트 업로드 시 변경 가능)
        temp_file_name = f"{tool_id}_placeholder.py"

        metadata = ToolMetadata(
            tool_id=tool_id,
            tool_name=req.tool_name,
            description=req.description,
            execution_type=req.execution_type,
            file_name=temp_file_name,
            input_schema=req.input_schema,
            output_schema=req.output_schema,
            params_schema=req.params_schema,
            example_input=req.example_input,
            example_output=req.example_output,
        )
        log.info("[register-schema-only] metadata 생성 완료")

        # 어댑터 코드 생성 (스크립트 없이)
        log.info("[register-schema-only] synthesize_adapter 호출 (source_code=None), model=%s", req.model or "기본값")
        adapter = await synthesize_adapter(metadata, source_code=None, model=req.model)
        log.info("[register-schema-only] adapter 생성 완료")

        # 플레이스홀더 스크립트 생성
        placeholder_script = f"""# Placeholder script for {req.tool_name}
# This script should be replaced with actual implementation

def main():
    raise NotImplementedError("스크립트가 아직 업로드되지 않았습니다. /api/tools/{tool_id}/script 엔드포인트를 통해 업로드하세요.")

if __name__ == "__main__":
    main()
"""

        # 레지스트리에 저장 (기존 도구가 있으면 덮어씀)
        save_tool(metadata, adapter, placeholder_script)
        action = "업데이트" if is_update else "등록"
        log.info("[register-schema-only] 저장 완료: %s (%s)", tool_id, action)
        log.info("[register-schema-only] === 등록 완료 ===")
        log.info("=" * 60)

        return RegisterSchemaOnlyResponse(
            success=True,
            tool_id=tool_id,
            tool_name=req.tool_name,
            message=f"도구 '{req.tool_name}'의 스키마와 어댑터가 {action}되었습니다. 스크립트는 나중에 업로드하세요.",
            adapter_preview={
                "pre_process_code": adapter.pre_process_code[:500],
                "post_process_code": adapter.post_process_code[:500],
            },
        )
    except Exception as e:
        log.error("[register-schema-only] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"등록 실패: {str(e)}")


@router.get("/", response_model=List[ToolListItem])
async def list_all_tools():
    """FR-3: 등록된 모든 도구를 조회합니다."""
    return list_tools()


@router.get("/{tool_id}", response_model=ToolRegistryEntry)
async def get_tool_detail(tool_id: str):
    """FR-3: 특정 도구의 상세 정보를 조회합니다."""
    entry = get_tool(tool_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"도구 '{tool_id}'를 찾을 수 없습니다.")
    return entry


@router.delete("/{tool_id}")
async def delete_tool_endpoint(tool_id: str):
    """FR-3: 등록된 도구를 삭제합니다."""
    deleted = delete_tool(tool_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"도구 '{tool_id}'를 찾을 수 없습니다.")
    return {"message": f"도구 '{tool_id}'가 삭제되었습니다."}


@router.put("/{tool_id}/script", response_model=UpdateScriptResponse)
async def update_tool_script_endpoint(tool_id: str, req: UpdateScriptRequest):
    """등록된 도구의 스크립트를 업데이트합니다 (스키마 우선 등록 후 사용)."""
    log.info("=" * 60)
    log.info("[update-script] === 스크립트 업데이트 ===")
    log.info("[update-script] tool_id=%s, file_name=%s, code_length=%d",
             tool_id, req.file_name, len(req.source_code))

    try:
        # 도구 존재 확인
        entry = get_tool(tool_id)
        if not entry:
            raise HTTPException(status_code=404, detail=f"도구 '{tool_id}'를 찾을 수 없습니다.")

        # 스크립트 업데이트
        success = update_tool_script(tool_id, req.file_name, req.source_code)
        if not success:
            raise HTTPException(status_code=500, detail="스크립트 업데이트에 실패했습니다.")

        log.info("[update-script] 스크립트 업데이트 완료")
        log.info("=" * 60)

        return UpdateScriptResponse(
            success=True,
            message=f"도구 '{tool_id}'의 스크립트가 업데이트되었습니다.",
            tool_id=tool_id,
            file_name=req.file_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("[update-script] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"업데이트 실패: {str(e)}")


@router.post("/execute", response_model=ExecuteResponse)
async def execute_tool_endpoint(req: ExecuteRequest):
    """FR-4: 등록된 도구를 BOP 데이터에 대해 실행합니다."""
    import json
    log.info("[execute API] 도구 실행 요청: tool_id=%s", req.tool_id)
    log.info("[execute API] params=%s", json.dumps(req.params, ensure_ascii=False) if req.params else "None")
    log.info("[execute API] BOP 데이터: processes=%d, obstacles=%d",
             len(req.bop_data.get("processes", [])),
             len(req.bop_data.get("obstacles", [])))
    try:
        result = await execute_tool(req.tool_id, req.bop_data, req.params)
        log.info("[execute API] 실행 결과: success=%s, message=%s",
                 result.get("success"), result.get("message", "")[:100])
        return ExecuteResponse(**result)
    except Exception as e:
        log.error("[execute API] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"실행 실패: {str(e)}")


@router.post("/generate-schema", response_model=GenerateSchemaResponse)
async def generate_schema_endpoint(req: GenerateSchemaRequest):
    """AI로 도구 스키마를 생성합니다 (AI 생성 1단계)."""
    try:
        log.info("[generate-schema] AI 스키마 생성 시작, model=%s", req.model or "기본값")
        result = await generate_schema_from_description(req.description, model=req.model)
        if result is None:
            return GenerateSchemaResponse(
                success=False,
                message="스키마 생성에 실패했습니다. 다시 시도해 주세요."
            )

        # suggested_params를 ParamDef 모델로 변환
        suggested_params = None
        if result.get("suggested_params"):
            suggested_params = [
                ParamDef(**p) for p in result["suggested_params"]
            ]

        from app.tools.tool_models import InputSchema, OutputSchema
        return GenerateSchemaResponse(
            success=True,
            tool_name=result.get("tool_name"),
            description=result.get("description"),
            input_schema=InputSchema(**result["input_schema"]),
            output_schema=OutputSchema(**result["output_schema"]),
            suggested_params=suggested_params,
            example_input=result.get("example_input"),
            example_output=result.get("example_output"),
            message="스키마가 생성되었습니다."
        )
    except Exception as e:
        log.error("[generate-schema] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"생성 실패: {str(e)}")


@router.post("/improve-schema", response_model=GenerateSchemaResponse)
async def improve_schema_endpoint(req: ImproveSchemaRequest):
    """생성된 스키마를 사용자 피드백으로 개선합니다."""
    try:
        log.info("[improve-schema] tool_name=%s, feedback=%s", req.tool_name, req.user_feedback[:50])

        result = await improve_schema_from_feedback(
            tool_name=req.tool_name,
            description=req.description,
            current_input_schema=req.current_input_schema,
            current_output_schema=req.current_output_schema,
            current_params=req.current_params,
            user_feedback=req.user_feedback,
            model=req.model
        )

        if result is None:
            raise HTTPException(status_code=500, detail="스키마 개선에 실패했습니다.")

        from app.tools.tool_models import InputSchema, OutputSchema
        suggested_params = [ParamDef(**p) for p in result.get("suggested_params", [])] if result.get("suggested_params") else None

        log.info("[improve-schema] 개선 완료: 변경사항=%d개", len(result.get("changes_summary", [])))
        return GenerateSchemaResponse(
            success=True,
            tool_name=result["tool_name"],
            description=result["description"],
            input_schema=InputSchema(**result["input_schema"]),
            output_schema=OutputSchema(**result["output_schema"]),
            suggested_params=suggested_params,
            example_input=result.get("example_input"),
            example_output=result.get("example_output"),
            changes_summary=result.get("changes_summary"),
            message="스키마가 개선되었습니다."
        )
    except Exception as e:
        log.error("[improve-schema] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"개선 실패: {str(e)}")


@router.post("/generate-script", response_model=GenerateScriptResponse)
async def generate_script_endpoint(req: GenerateScriptRequest):
    """AI로 도구 스크립트를 생성합니다 (AI 생성 2단계 또는 독립 실행)."""
    try:
        log.info("[generate-script] model=%s, 스키마 제공=%s",
                 req.model or "기본값", "있음" if (req.input_schema and req.output_schema) else "없음")

        # 스키마가 제공된 경우 dict로 변환
        input_schema_dict = req.input_schema.model_dump() if req.input_schema else None
        output_schema_dict = req.output_schema.model_dump() if req.output_schema else None

        result = await generate_tool_script(
            req.description,
            model=req.model,
            input_schema=input_schema_dict,
            output_schema=output_schema_dict,
            example_input=req.example_input,
            example_output=req.example_output,
        )
        if result is None:
            return GenerateScriptResponse(
                success=False,
                message="스크립트 생성에 실패했습니다. 다시 시도해 주세요."
            )

        # suggested_params를 ParamDef 모델로 변환
        suggested_params = None
        if result.get("suggested_params"):
            suggested_params = [
                ParamDef(**p) for p in result["suggested_params"]
            ]

        return GenerateScriptResponse(
            success=True,
            tool_name=result.get("tool_name"),
            description=result.get("description"),
            script_code=result.get("script_code"),
            suggested_params=suggested_params,
            message="스크립트가 생성되었습니다."
        )
    except Exception as e:
        log.error("[generate-script] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"생성 실패: {str(e)}")


@router.post("/{tool_id}/improve", response_model=ImproveResponse)
async def improve_tool_endpoint(tool_id: str, req: ImproveRequest):
    """사용자 피드백을 기반으로 도구를 개선합니다."""
    log.info("=" * 60)
    log.info("[improve] === AI 개선 요청 ===")
    log.info("[improve] tool_id=%s", tool_id)
    log.info("[improve] 피드백: %s", req.user_feedback)
    log.info("[improve] 수정 범위: adapter=%s, params=%s, script=%s",
             req.modify_adapter, req.modify_params, req.modify_script)
    if req.execution_context:
        log.info("[improve] 실행 컨텍스트: success=%s", req.execution_context.success)

    try:
        # 도구 정보 로드
        entry = get_tool(tool_id)
        if not entry:
            raise HTTPException(status_code=404, detail=f"도구 '{tool_id}'를 찾을 수 없습니다.")

        metadata = entry.metadata
        adapter = entry.adapter

        # 스크립트 코드 로드 (필요시)
        script_code = None
        if req.modify_script:
            script_code = get_script_content(tool_id, metadata.file_name)

        # 실행 컨텍스트 준비
        exec_context = {}
        if req.execution_context:
            exec_context = {
                "success": req.execution_context.success,
                "stdout": req.execution_context.stdout,
                "stderr": req.execution_context.stderr,
                "tool_output": req.execution_context.tool_output,
            }

        # AI 개선 호출
        log.info("[improve] model=%s", req.model or "기본값")
        result = await improve_tool(
            tool_name=metadata.tool_name,
            tool_description=metadata.description,
            pre_process_code=adapter.pre_process_code,
            post_process_code=adapter.post_process_code,
            script_code=script_code,
            params_schema=[p.model_dump() for p in metadata.params_schema] if metadata.params_schema else [],
            user_feedback=req.user_feedback,
            execution_context=exec_context,
            modify_adapter=req.modify_adapter,
            modify_params=req.modify_params,
            modify_script=req.modify_script,
            model=req.model,
        )

        if result is None:
            return ImproveResponse(
                success=False,
                message="개선 생성에 실패했습니다. 다시 시도해 주세요."
            )

        log.info("[improve] === AI 개선 완료 ===")
        log.info("[improve] 설명: %s", result.get("explanation", "")[:300])
        log.info("[improve] 변경 사항: %s", result.get("changes_summary", []))
        if result.get("pre_process_code"):
            log.info("[improve] pre_process_code 변경됨 (길이: %d)", len(result.get("pre_process_code", "")))
        if result.get("post_process_code"):
            log.info("[improve] post_process_code 변경됨 (길이: %d)", len(result.get("post_process_code", "")))
        if result.get("params_schema"):
            log.info("[improve] params_schema 변경됨: %s", result.get("params_schema"))
        log.info("=" * 60)

        return ImproveResponse(
            success=True,
            message="개선 사항이 생성되었습니다.",
            explanation=result.get("explanation"),
            changes_summary=result.get("changes_summary"),
            preview={
                "pre_process_code": result.get("pre_process_code"),
                "post_process_code": result.get("post_process_code"),
                "params_schema": result.get("params_schema"),
                "script_code": result.get("script_code"),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("[improve] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"개선 실패: {str(e)}")


@router.post("/{tool_id}/apply-improvement")
async def apply_improvement_endpoint(tool_id: str, req: ApplyImprovementRequest):
    """개선된 코드를 적용합니다 (새 버전 생성 또는 덮어쓰기)."""
    log.info("=" * 60)
    log.info("[apply] === 개선 적용 요청 ===")
    log.info("[apply] tool_id=%s, create_new_version=%s", tool_id, req.create_new_version)
    log.info("[apply] pre_process 변경: %s", "Yes" if req.pre_process_code else "No")
    log.info("[apply] post_process 변경: %s", "Yes" if req.post_process_code else "No")
    log.info("[apply] params_schema 변경: %s", "Yes" if req.params_schema else "No")
    log.info("[apply] script 변경: %s", "Yes" if req.script_code else "No")

    try:
        # 기존 도구 정보 로드
        entry = get_tool(tool_id)
        if not entry:
            raise HTTPException(status_code=404, detail=f"도구 '{tool_id}'를 찾을 수 없습니다.")

        old_metadata = entry.metadata
        old_adapter = entry.adapter

        # 새 버전 생성 시 tool_id 결정
        if req.create_new_version:
            # wall_generator -> wall_generator_v2 -> wall_generator_v3 ...
            import re
            # 기존 버전 번호 추출 (예: tool_name_v2 → 2)
            version_match = re.search(r'_v(\d+)$', tool_id)
            if version_match:
                # 이미 버전이 있으면 증가
                current_version = int(version_match.group(1))
                base_name = tool_id[:version_match.start()]
                next_version = current_version + 1
                new_tool_id = generate_tool_id(f"{base_name}_v{next_version}")
                new_tool_name = f"{old_metadata.tool_name.rsplit('_v', 1)[0]}_v{next_version}"
            else:
                # 버전이 없으면 _v2 추가
                new_tool_id = generate_tool_id(f"{tool_id}_v2")
                new_tool_name = f"{old_metadata.tool_name}_v2"
        else:
            new_tool_id = tool_id
            new_tool_name = old_metadata.tool_name

        # 파라미터 스키마 처리
        new_params_schema = old_metadata.params_schema
        if req.params_schema is not None:
            new_params_schema = req.params_schema

        # 새 메타데이터 생성
        new_metadata = ToolMetadata(
            tool_id=new_tool_id,
            tool_name=new_tool_name,
            description=old_metadata.description,
            execution_type=old_metadata.execution_type,
            file_name=old_metadata.file_name,
            input_schema=old_metadata.input_schema,
            output_schema=old_metadata.output_schema,
            params_schema=new_params_schema,
        )

        # 어댑터 코드 처리
        new_adapter = AdapterCode(
            tool_id=new_tool_id,
            pre_process_code=req.pre_process_code if req.pre_process_code else old_adapter.pre_process_code,
            post_process_code=req.post_process_code if req.post_process_code else old_adapter.post_process_code,
        )

        # 스크립트 코드
        script_code = req.script_code
        if script_code is None:
            # 기존 스크립트 복사
            script_code = get_script_content(tool_id, old_metadata.file_name) or ""

        # 저장
        save_tool(new_metadata, new_adapter, script_code)
        log.info("[apply] 저장 완료: %s", new_tool_id)

        return {
            "success": True,
            "tool_id": new_tool_id,
            "tool_name": new_tool_name,
            "message": f"도구가 {'새 버전으로' if req.create_new_version else ''} 저장되었습니다.",
            "is_new_version": req.create_new_version,
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error("[apply] 오류:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"적용 실패: {str(e)}")
