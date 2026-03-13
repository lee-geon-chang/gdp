from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any


# ============================================
# 기본 모델
# ============================================

class Location(BaseModel):
    """3D 공간 좌표"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Size3D(BaseModel):
    """3D 크기"""
    width: float = 0.4
    height: float = 0.4
    depth: float = 0.4


# ============================================
# 마스터 데이터 모델
# ============================================

class Equipment(BaseModel):
    """설비 마스터 데이터"""
    equipment_id: str = Field(..., description="설비 고유 ID")
    name: str = Field(..., description="설비명")
    type: str = Field(..., description="설비 타입: robot, machine, manual_station")
    specifications: Optional[Dict[str, Any]] = Field(default=None, description="설비 사양 (제조사, 모델 등)")


class Worker(BaseModel):
    """작업자 마스터 데이터"""
    worker_id: str = Field(..., description="작업자 고유 ID")
    name: str = Field(..., description="작업자명")
    skill_level: Optional[str] = Field(default=None, description="숙련도 (Senior, Junior 등)")
    certifications: Optional[List[str]] = Field(default=None, description="보유 자격증")


class Material(BaseModel):
    """자재 마스터 데이터"""
    material_id: str = Field(..., description="자재 고유 ID")
    name: str = Field(..., description="자재명")
    unit: str = Field(default="ea", description="단위 (kg, ea, m 등)")
    specifications: Optional[Dict[str, Any]] = Field(default=None, description="자재 사양")


# ============================================
# 리소스 배치 모델 (top-level)
# ============================================

class ResourceAssignment(BaseModel):
    """리소스 배치 (process_id + parallel_index로 공정 인스턴스에 매핑)"""
    process_id: str = Field(..., description="소속 공정 ID")
    parallel_index: int = Field(default=1, description="병렬 인덱스 (1-based)")
    resource_type: str = Field(..., description="리소스 타입: equipment, worker, material")
    resource_id: str = Field(..., description="리소스 ID (마스터 데이터 참조)")
    quantity: float = Field(default=1.0, description="사용 수량")
    relative_location: Optional[Location] = Field(default=None, description="공정 내 상대 좌표")
    role: Optional[str] = Field(default=None, description="역할/용도 (예: 주작업자, 검사)")
    rotation_y: float = Field(default=0.0, description="Y축 회전 (라디안)")
    scale: Optional[Dict[str, float]] = Field(default=None, description="XYZ 스케일")
    computed_size: Optional[Size3D] = Field(default=None, description="계산된 기본 크기")

    @validator('resource_type')
    def validate_resource_type(cls, v):
        allowed = ['equipment', 'worker', 'material']
        if v not in allowed:
            raise ValueError(f"resource_type은 {allowed} 중 하나여야 합니다")
        return v

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("quantity는 양수여야 합니다")
        return v


# ============================================
# 공정 상세 모델 (top-level)
# ============================================

class ProcessDetail(BaseModel):
    """공정 인스턴스 상세 (process_id + parallel_index로 식별)"""
    process_id: str = Field(..., description="소속 공정 ID")
    parallel_index: int = Field(default=1, description="병렬 인덱스 (1-based)")
    name: str = Field(..., description="공정명")
    description: Optional[str] = Field(default=None, description="공정 설명")
    cycle_time_sec: float = Field(default=60.0, description="사이클 타임 (초)")
    location: Optional[Location] = Field(default=None, description="절대 좌표")
    rotation_y: float = Field(default=0.0, description="Y축 회전")
    computed_size: Optional[Size3D] = Field(default=None, description="계산된 공정 바운딩박스 크기")

    @validator('cycle_time_sec')
    def validate_cycle_time(cls, v):
        if v is not None and v <= 0:
            raise ValueError("cycle_time_sec는 양수여야 합니다")
        return v


# ============================================
# 공정 모델
# ============================================

class Process(BaseModel):
    """공정 라우팅 (연결 정보만)"""
    process_id: str = Field(..., description="공정 고유 ID")
    predecessor_ids: List[str] = Field(default_factory=list, description="선행 공정 ID 리스트")
    successor_ids: List[str] = Field(default_factory=list, description="후속 공정 ID 리스트")


# ============================================
# BOP 데이터 모델
# ============================================

class BOPData(BaseModel):
    """Bill of Process 전체 데이터"""
    project_title: str = Field(..., description="프로젝트 제목")
    target_uph: int = Field(..., description="목표 시간당 생산량")
    processes: List[Process] = Field(..., description="공정 라우팅 리스트")
    process_details: List[ProcessDetail] = Field(default_factory=list, description="공정 인스턴스 상세 리스트")
    resource_assignments: List[ResourceAssignment] = Field(default_factory=list, description="리소스 배치 리스트")
    equipments: List[Equipment] = Field(default_factory=list, description="설비 마스터 리스트")
    workers: List[Worker] = Field(default_factory=list, description="작업자 마스터 리스트")
    materials: List[Material] = Field(default_factory=list, description="자재 마스터 리스트")

    @validator('target_uph')
    def validate_target_uph(cls, v):
        if v <= 0:
            raise ValueError("target_uph는 양수여야 합니다")
        return v

    @validator('processes')
    def validate_processes_not_empty(cls, v):
        if len(v) == 0:
            raise ValueError("processes는 최소 1개 이상이어야 합니다")
        return v

    def validate_references(self) -> tuple:
        """참조 무결성 검증"""
        # Equipment IDs 수집
        equipment_ids = {eq.equipment_id for eq in self.equipments}
        # Worker IDs 수집
        worker_ids = {w.worker_id for w in self.workers}
        # Material IDs 수집
        material_ids = {m.material_id for m in self.materials}
        # Process IDs 수집
        process_ids = {p.process_id for p in self.processes}

        # Process ID 중복 검사
        process_id_list = [p.process_id for p in self.processes]
        if len(process_id_list) != len(set(process_id_list)):
            duplicates = [pid for pid in process_id_list if process_id_list.count(pid) > 1]
            return False, f"중복된 process_id가 있습니다: {set(duplicates)}"

        # resource_assignments 참조 검증
        for ra in self.resource_assignments:
            if ra.process_id not in process_ids:
                return False, f"ResourceAssignment의 process_id '{ra.process_id}'가 processes 목록에 없습니다"
            if ra.resource_type == 'equipment':
                if ra.resource_id not in equipment_ids:
                    return False, f"Process {ra.process_id}의 equipment_id '{ra.resource_id}'가 equipments 목록에 없습니다"
            elif ra.resource_type == 'worker':
                if ra.resource_id not in worker_ids:
                    return False, f"Process {ra.process_id}의 worker_id '{ra.resource_id}'가 workers 목록에 없습니다"
            elif ra.resource_type == 'material':
                if ra.resource_id not in material_ids:
                    return False, f"Process {ra.process_id}의 material_id '{ra.resource_id}'가 materials 목록에 없습니다"

        # process_details 참조 검증
        for pd in self.process_details:
            if pd.process_id not in process_ids:
                return False, f"ProcessDetail의 process_id '{pd.process_id}'가 processes 목록에 없습니다"

        # 선행/후속 공정 ID 검증
        for process in self.processes:
            for pred_id in process.predecessor_ids:
                if pred_id not in process_ids:
                    return False, f"Process {process.process_id}의 predecessor_id '{pred_id}'가 processes 목록에 없습니다"

            for succ_id in process.successor_ids:
                if succ_id not in process_ids:
                    return False, f"Process {process.process_id}의 successor_id '{succ_id}'가 processes 목록에 없습니다"

        return True, ""

    def detect_cycles(self) -> tuple:
        """공정 흐름에서 순환 참조 검증 (DAG 구조 확인)"""
        # 방문 상태: 0=미방문, 1=방문중, 2=완료
        visited = {p.process_id: 0 for p in self.processes}

        def dfs(node_id: str, path: List[str]) -> tuple:
            if visited[node_id] == 1:
                # 순환 발견
                cycle_start = path.index(node_id)
                cycle = path[cycle_start:] + [node_id]
                return False, f"순환 참조 발견: {' -> '.join(cycle)}"

            if visited[node_id] == 2:
                # 이미 완료된 노드
                return True, ""

            visited[node_id] = 1  # 방문 중

            # successor들을 탐색
            process = next(p for p in self.processes if p.process_id == node_id)
            for succ_id in process.successor_ids:
                is_valid, msg = dfs(succ_id, path + [node_id])
                if not is_valid:
                    return False, msg

            visited[node_id] = 2  # 완료
            return True, ""

        # 모든 노드에서 DFS 시작
        for process in self.processes:
            if visited[process.process_id] == 0:
                is_valid, msg = dfs(process.process_id, [])
                if not is_valid:
                    return False, msg

        return True, ""


# ============================================
# API Request/Response 모델
# ============================================

class GenerateRequest(BaseModel):
    """BOP 생성 요청"""
    user_input: str


class ChatRequest(BaseModel):
    """BOP 수정 요청"""
    message: str
    current_bop: BOPData


class UnifiedChatRequest(BaseModel):
    """통합 채팅 요청 (생성/수정/QA)"""
    message: str
    current_bop: Optional[BOPData] = None
    model: Optional[str] = None  # LLM 모델 선택 (None이면 기본 모델 사용)
    language: Optional[str] = "ko"  # 응답 언어 ("ko" 또는 "en")


class UnifiedChatResponse(BaseModel):
    """통합 채팅 응답"""
    message: str
    bop_data: Optional[BOPData] = None
