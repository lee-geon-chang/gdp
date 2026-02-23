from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class ExecutionType(str, Enum):
    PYTHON = "python"
    EXECUTABLE = "executable"


class SchemaType(str, Enum):
    CSV = "csv"
    JSON = "json"
    DICT = "dict"
    LIST = "list"
    STRING = "string"
    ARGS = "args"
    STDIN = "stdin"


class InputSchema(BaseModel):
    type: SchemaType = Field(default=SchemaType.JSON, description="입력 형식 타입")
    columns: Optional[List[str]] = Field(default=None, description="CSV: 컬럼명 목록")
    fields: Optional[List[str]] = Field(default=None, description="JSON: 필드명 목록")
    structure: Optional[Dict[str, Any]] = Field(default=None, description="JSON: 중첩 구조 정의")
    description: str = Field(..., description="입력 형식 설명")


class OutputSchema(BaseModel):
    type: SchemaType = Field(..., description="출력 형식 타입")
    columns: Optional[List[str]] = Field(default=None, description="CSV: 컬럼명 목록")
    fields: Optional[List[str]] = Field(default=None, description="JSON: 필드명 목록")
    structure: Optional[Dict[str, Any]] = Field(default=None, description="JSON: 중첩 구조 정의")
    return_format: Optional[Any] = Field(default=None, description="dict/list 타입의 반환 형식 설명")
    description: str = Field(..., description="출력 형식 설명")


class ParamDef(BaseModel):
    key: str = Field(..., description="파라미터 키")
    label: str = Field(..., description="표시 라벨")
    type: str = Field(default="number", description="입력 타입 (number, text, select 등)")
    default: Optional[Any] = Field(default=None, description="기본값")
    required: bool = Field(default=False, description="필수 여부")
    description: str = Field(default="", description="파라미터 설명")


class ToolMetadata(BaseModel):
    tool_id: str = Field(..., description="고유 도구 식별자 (slug)")
    tool_name: str = Field(..., description="도구 표시 이름")
    description: str = Field(..., description="도구 설명")
    execution_type: ExecutionType = Field(..., description="python 또는 executable")
    file_name: str = Field(..., description="업로드된 원본 파일명")
    input_schema: InputSchema
    output_schema: OutputSchema
    params_schema: Optional[List[ParamDef]] = Field(default=None, description="도구별 추가 파라미터 정의")
    example_input: Optional[Any] = Field(default=None, description="입력 예시 데이터")
    example_output: Optional[Any] = Field(default=None, description="출력 예시 데이터")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class AdapterCode(BaseModel):
    tool_id: str
    pre_process_code: str = Field(..., description="convert_bop_to_input(bop_json) -> str")
    post_process_code: str = Field(..., description="apply_result_to_bop(bop_json, tool_output) -> dict")


class ToolRegistryEntry(BaseModel):
    metadata: ToolMetadata
    adapter: AdapterCode
    source_code: Optional[str] = Field(default=None, description="도구 스크립트 소스 코드")


# === API Request/Response ===

class AnalyzeRequest(BaseModel):
    source_code: str = Field(..., description="분석할 소스 코드")
    file_name: str = Field(default="script.py", description="원본 파일명")
    sample_input: Optional[str] = Field(default=None, description="예제 입력 데이터")
    model: Optional[str] = Field(default=None, description="사용할 LLM 모델")
    input_schema_override: Optional[InputSchema] = Field(default=None, description="입력 스키마 오버라이드 (제공 시 LLM 분석 스킵)")
    output_schema_override: Optional[OutputSchema] = Field(default=None, description="출력 스키마 오버라이드 (제공 시 LLM 분석 스킵)")


class AnalyzeResponse(BaseModel):
    tool_name: str
    description: str
    execution_type: ExecutionType
    input_schema: InputSchema
    output_schema: OutputSchema
    params_schema: Optional[List[ParamDef]] = None


class RegisterRequest(BaseModel):
    tool_name: str
    description: str
    execution_type: ExecutionType
    file_name: str
    source_code: str
    input_schema: InputSchema
    output_schema: OutputSchema
    params_schema: Optional[List[ParamDef]] = None
    sample_input: Optional[str] = None
    example_input: Optional[Any] = Field(default=None, description="입력 예시 데이터")
    example_output: Optional[Any] = Field(default=None, description="출력 예시 데이터")
    model: Optional[str] = Field(default=None, description="사용할 LLM 모델")


class RegisterResponse(BaseModel):
    tool_id: str
    tool_name: str
    message: str
    adapter_preview: Optional[Dict[str, str]] = None


class ExecuteRequest(BaseModel):
    tool_id: str
    bop_data: Dict[str, Any] = Field(..., description="현재 BOP JSON 데이터")
    params: Optional[Dict[str, Any]] = Field(default=None, description="도구별 추가 파라미터")


class ExecuteResponse(BaseModel):
    success: bool
    message: str
    updated_bop: Optional[Dict[str, Any]] = None
    tool_input: Optional[str] = None  # 도구에 전달된 입력 데이터
    tool_output: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    execution_time_sec: Optional[float] = None
    auto_repair_attempted: Optional[bool] = None
    auto_repaired: Optional[bool] = None
    error_diagnosis: Optional[Dict[str, Any]] = None


class ToolListItem(BaseModel):
    tool_id: str
    tool_name: str
    description: str
    execution_type: ExecutionType
    created_at: str
    params_schema: Optional[List[ParamDef]] = None


class GenerateSchemaRequest(BaseModel):
    """스키마만 생성 요청 (AI 생성 1단계)"""
    description: str = Field(..., description="원하는 도구 기능 설명")
    model: Optional[str] = Field(default=None, description="사용할 LLM 모델")


class GenerateSchemaResponse(BaseModel):
    """스키마 생성 응답"""
    success: bool
    tool_name: Optional[str] = None
    description: Optional[str] = None
    input_schema: Optional[InputSchema] = None
    output_schema: Optional[OutputSchema] = None
    suggested_params: Optional[List[ParamDef]] = None
    example_input: Optional[Any] = Field(default=None, description="입력 예시 데이터 (AI 생성)")
    example_output: Optional[Any] = Field(default=None, description="출력 예시 데이터 (AI 생성)")
    changes_summary: Optional[List[str]] = Field(default=None, description="변경 사항 요약 (개선 시)")
    message: Optional[str] = None


class ImproveSchemaRequest(BaseModel):
    """스키마 개선 요청"""
    tool_name: str = Field(..., description="도구명")
    description: str = Field(..., description="도구 설명")
    current_input_schema: dict = Field(..., description="현재 입력 스키마")
    current_output_schema: dict = Field(..., description="현재 출력 스키마")
    current_params: Optional[List[dict]] = Field(default=None, description="현재 파라미터")
    user_feedback: str = Field(..., description="사용자 개선 요청")
    model: Optional[str] = Field(default=None, description="사용할 LLM 모델")


class GenerateScriptRequest(BaseModel):
    """스크립트 생성 요청 (AI 생성 2단계 또는 독립 실행)"""
    description: str = Field(..., description="원하는 도구 기능 설명")
    model: Optional[str] = Field(default=None, description="사용할 LLM 모델")
    input_schema: Optional[InputSchema] = Field(default=None, description="입력 스키마 (제공 시 이를 기반으로 스크립트 생성)")
    output_schema: Optional[OutputSchema] = Field(default=None, description="출력 스키마 (제공 시 이를 기반으로 스크립트 생성)")
    example_input: Optional[Any] = Field(default=None, description="입력 예시 데이터")
    example_output: Optional[Any] = Field(default=None, description="출력 예시 데이터")


class GenerateScriptResponse(BaseModel):
    success: bool
    tool_name: Optional[str] = None
    description: Optional[str] = None
    script_code: Optional[str] = None
    suggested_params: Optional[List[ParamDef]] = None
    message: Optional[str] = None


class ExecutionContext(BaseModel):
    success: bool = False
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    tool_output: Optional[str] = None


class ImproveRequest(BaseModel):
    user_feedback: str = Field(..., description="사용자의 개선 요청 내용")
    execution_context: Optional[ExecutionContext] = None
    modify_adapter: bool = Field(default=True, description="어댑터 코드 수정 여부")
    modify_params: bool = Field(default=True, description="파라미터 스키마 수정 여부")
    modify_script: bool = Field(default=False, description="스크립트 코드 수정 여부")
    model: Optional[str] = Field(default=None, description="사용할 LLM 모델")


class ImproveResponse(BaseModel):
    success: bool
    message: str
    explanation: Optional[str] = None
    changes_summary: Optional[List[str]] = None
    preview: Optional[Dict[str, Any]] = None  # pre_process_code, post_process_code, params_schema, script_code


class ApplyImprovementRequest(BaseModel):
    pre_process_code: Optional[str] = None
    post_process_code: Optional[str] = None
    params_schema: Optional[List[ParamDef]] = None
    script_code: Optional[str] = None
    create_new_version: bool = Field(default=True, description="새 버전으로 등록할지 여부")


class RegisterSchemaOnlyRequest(BaseModel):
    """스키마만으로 도구를 등록 (스크립트는 나중에 업로드)"""
    tool_name: str = Field(..., description="도구 이름")
    description: str = Field(..., description="도구 설명")
    execution_type: ExecutionType = Field(default=ExecutionType.PYTHON, description="실행 타입")
    input_schema: InputSchema = Field(..., description="입력 스키마")
    output_schema: OutputSchema = Field(..., description="출력 스키마")
    params_schema: Optional[List[ParamDef]] = Field(default=None, description="파라미터 스키마")
    example_input: Optional[Any] = Field(default=None, description="입력 예시 데이터")
    example_output: Optional[Any] = Field(default=None, description="출력 예시 데이터")
    model: Optional[str] = Field(default=None, description="사용할 LLM 모델")


class RegisterSchemaOnlyResponse(BaseModel):
    success: bool
    tool_id: str
    tool_name: str
    message: str
    adapter_preview: Optional[Dict[str, str]] = None


class UpdateScriptRequest(BaseModel):
    """등록된 도구의 스크립트 업데이트"""
    source_code: str = Field(..., description="스크립트 소스 코드")
    file_name: str = Field(..., description="스크립트 파일명")


class UpdateScriptResponse(BaseModel):
    success: bool
    message: str
    tool_id: str
    file_name: str
