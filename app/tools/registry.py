import json
import re
import shutil
from pathlib import Path
from typing import List, Optional

from app.tools.tool_models import ToolMetadata, AdapterCode, ToolRegistryEntry, ToolListItem

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root
REGISTRY_DIR = BASE_DIR / "data" / "tool_registry"
UPLOADS_DIR = BASE_DIR / "uploads" / "scripts"
WORKDIR_BASE = BASE_DIR / "uploads" / "workdir"
LOGS_DIR = BASE_DIR / "data" / "tool_logs"


def _ensure_dirs():
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    WORKDIR_BASE.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def generate_tool_id(tool_name: str, allow_existing: bool = True) -> str:
    """
    도구 이름으로부터 ID를 생성합니다.

    Args:
        tool_name: 도구 이름
        allow_existing: True면 기존 ID가 있어도 그대로 반환 (업데이트용)
                       False면 기존 ID가 있으면 카운터를 붙여 새 ID 생성

    Returns:
        tool_id 문자열
    """
    slug = re.sub(r'[^a-zA-Z0-9_]', '_', tool_name.lower()).strip('_')
    slug = re.sub(r'_+', '_', slug)
    if not slug:
        slug = "tool"

    # allow_existing=True면 기존 ID가 있어도 그대로 반환 (덮어쓰기/업데이트 용도)
    if allow_existing:
        return slug

    # allow_existing=False면 충돌 시 카운터 추가
    base_slug = slug
    counter = 1
    while (REGISTRY_DIR / slug).exists():
        slug = f"{base_slug}_{counter}"
        counter += 1
    return slug


def find_existing_tool_id(tool_name: str) -> Optional[str]:
    """
    도구 이름과 일치하는 기존 tool_id를 찾습니다.

    Args:
        tool_name: 검색할 도구 이름

    Returns:
        기존 tool_id 또는 None
    """
    _ensure_dirs()
    slug = re.sub(r'[^a-zA-Z0-9_]', '_', tool_name.lower()).strip('_')
    slug = re.sub(r'_+', '_', slug)
    if not slug:
        slug = "tool"

    # 정확히 일치하는 ID가 있는지 확인
    if (REGISTRY_DIR / slug).exists():
        return slug

    return None


def save_tool(metadata: ToolMetadata, adapter: AdapterCode, source_code: str) -> str:
    _ensure_dirs()
    tool_dir = REGISTRY_DIR / metadata.tool_id
    tool_dir.mkdir(parents=True, exist_ok=True)

    with open(tool_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata.model_dump(), f, indent=2, ensure_ascii=False)

    with open(tool_dir / "adapter.json", "w", encoding="utf-8") as f:
        json.dump(adapter.model_dump(), f, indent=2, ensure_ascii=False)

    script_dir = UPLOADS_DIR / metadata.tool_id
    script_dir.mkdir(parents=True, exist_ok=True)

    # 줄바꿈 정규화: \r\n, \r을 모두 \n으로 통일
    normalized_code = source_code.replace('\r\n', '\n').replace('\r', '\n')

    # newline='' 사용: 줄바꿈 자동 변환 비활성화 (원본 그대로 저장)
    with open(script_dir / metadata.file_name, "w", encoding="utf-8", newline='') as f:
        f.write(normalized_code)

    return metadata.tool_id


def list_tools() -> List[ToolListItem]:
    _ensure_dirs()
    tools = []
    if not REGISTRY_DIR.exists():
        return tools
    for tool_dir in sorted(REGISTRY_DIR.iterdir()):
        if tool_dir.is_dir():
            meta_file = tool_dir / "metadata.json"
            if meta_file.exists():
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                tools.append(ToolListItem(
                    tool_id=meta["tool_id"],
                    tool_name=meta["tool_name"],
                    description=meta["description"],
                    execution_type=meta["execution_type"],
                    created_at=meta.get("created_at", ""),
                    params_schema=meta.get("params_schema"),
                ))
    return tools


def get_tool(tool_id: str) -> Optional[ToolRegistryEntry]:
    tool_dir = REGISTRY_DIR / tool_id
    meta_file = tool_dir / "metadata.json"
    adapter_file = tool_dir / "adapter.json"

    if not meta_file.exists() or not adapter_file.exists():
        return None

    with open(meta_file, "r", encoding="utf-8") as f:
        metadata = ToolMetadata(**json.load(f))
    with open(adapter_file, "r", encoding="utf-8") as f:
        adapter = AdapterCode(**json.load(f))

    # 스크립트 소스 코드 읽기
    source_code = get_script_content(tool_id, metadata.file_name)

    return ToolRegistryEntry(metadata=metadata, adapter=adapter, source_code=source_code)


def delete_tool(tool_id: str) -> bool:
    tool_dir = REGISTRY_DIR / tool_id
    script_dir = UPLOADS_DIR / tool_id

    deleted = False
    if tool_dir.exists():
        shutil.rmtree(tool_dir)
        deleted = True
    if script_dir.exists():
        shutil.rmtree(script_dir)
        deleted = True
    return deleted


def get_script_path(tool_id: str, file_name: str) -> Optional[Path]:
    path = UPLOADS_DIR / tool_id / file_name
    return path if path.exists() else None


def update_tool_adapter(tool_id: str, adapter: AdapterCode) -> bool:
    """
    도구의 어댑터 코드만 업데이트합니다 (자동 복구용).

    Args:
        tool_id: 도구 ID
        adapter: 업데이트할 어댑터 코드

    Returns:
        성공 여부
    """
    tool_dir = REGISTRY_DIR / tool_id
    adapter_file = tool_dir / "adapter.json"

    if not tool_dir.exists():
        return False

    try:
        with open(adapter_file, "w", encoding="utf-8") as f:
            json.dump(adapter.model_dump(), f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def get_script_content(tool_id: str, file_name: str) -> Optional[str]:
    """스크립트 파일의 내용을 읽어 반환합니다."""
    path = UPLOADS_DIR / tool_id / file_name
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def update_tool_metadata(tool_id: str, metadata: ToolMetadata) -> bool:
    """
    도구의 메타데이터만 업데이트합니다 (자동 복구용).

    Args:
        tool_id: 도구 ID
        metadata: 업데이트할 메타데이터

    Returns:
        성공 여부
    """
    tool_dir = REGISTRY_DIR / tool_id
    meta_file = tool_dir / "metadata.json"

    if not tool_dir.exists():
        return False

    try:
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def update_tool_script(tool_id: str, file_name: str, source_code: str) -> bool:
    """
    도구의 스크립트 파일을 업데이트합니다.

    Args:
        tool_id: 도구 ID
        file_name: 파일명
        source_code: 소스 코드

    Returns:
        성공 여부
    """
    tool_dir = REGISTRY_DIR / tool_id
    if not tool_dir.exists():
        return False

    script_dir = UPLOADS_DIR / tool_id
    script_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 줄바꿈 정규화
        normalized_code = source_code.replace('\r\n', '\n').replace('\r', '\n')

        with open(script_dir / file_name, "w", encoding="utf-8", newline='') as f:
            f.write(normalized_code)

        # 메타데이터에서 file_name 업데이트
        meta_file = tool_dir / "metadata.json"
        with open(meta_file, "r", encoding="utf-8") as f:
            metadata_dict = json.load(f)

        metadata_dict["file_name"] = file_name

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata_dict, f, indent=2, ensure_ascii=False)

        return True
    except Exception:
        return False
