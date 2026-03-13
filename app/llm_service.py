import json
import os
from typing import Tuple, Optional
from dotenv import load_dotenv
from app.prompts import SYSTEM_PROMPT, MODIFY_PROMPT_TEMPLATE, UNIFIED_CHAT_PROMPT_TEMPLATE
from app.models import BOPData
from app.llm import get_provider

# .env 파일 로드
load_dotenv()


def get_resource_size(resource_type: str, equipment_type: str = None) -> dict:
    """
    리소스 타입에 따른 기본 크기를 반환합니다.
    Viewer3D.jsx의 getResourceSize()와 동일한 값.
    """
    if resource_type == "equipment":
        if equipment_type == "robot":
            return {"width": 1.4, "height": 1.7, "depth": 0.6}
        elif equipment_type == "machine":
            return {"width": 2.1, "height": 1.9, "depth": 1.0}
        elif equipment_type == "manual_station":
            return {"width": 1.6, "height": 1.0, "depth": 0.8}
        else:
            return {"width": 0.4, "height": 0.4, "depth": 0.4}
    elif resource_type == "worker":
        return {"width": 0.5, "height": 1.7, "depth": 0.3}
    elif resource_type == "material":
        return {"width": 0.4, "height": 0.25, "depth": 0.4}
    return {"width": 0.4, "height": 0.4, "depth": 0.4}


def compute_resource_sizes(bop_data: dict) -> dict:
    """
    모든 resource_assignments에 computed_size를 부여합니다.
    """
    print("[COMPUTE-SIZES] 리소스 크기 계산 시작")

    equipments = bop_data.get("equipments", [])
    equipment_type_map = {eq["equipment_id"]: eq["type"] for eq in equipments}

    computed_count = 0
    for ra in bop_data.get("resource_assignments", []):
        eq_type = None
        if ra["resource_type"] == "equipment":
            eq_type = equipment_type_map.get(ra["resource_id"])
        size = get_resource_size(ra["resource_type"], eq_type)
        ra["computed_size"] = size
        computed_count += 1

    print(f"[COMPUTE-SIZES] 완료: {computed_count}개 리소스 크기 계산")
    return bop_data


def compute_process_sizes(bop_data: dict) -> dict:
    """
    모든 process_details에 computed_size (바운딩박스)를 계산합니다.
    리소스들의 relative_location + computed_size + scale로부터 공정 전체 크기를 구합니다.
    반드시 compute_resource_sizes() 이후에 호출해야 합니다.
    """
    resource_assignments = bop_data.get("resource_assignments", [])
    computed_count = 0

    for pd in bop_data.get("process_details", []):
        pid = pd.get("process_id")
        pidx = pd.get("parallel_index", 1)

        resources = [
            ra for ra in resource_assignments
            if ra.get("process_id") == pid and ra.get("parallel_index", 1) == pidx
        ]

        if not resources:
            pd["computed_size"] = {"width": 0.5, "height": 0.5, "depth": 0.5}
            computed_count += 1
            continue

        min_x = float("inf")
        max_x = float("-inf")
        min_z = float("inf")
        max_z = float("-inf")
        max_height = 0.0

        for idx, r in enumerate(resources):
            rel_loc = r.get("relative_location") or {"x": 0, "y": 0, "z": 0}
            x = rel_loc.get("x", 0)
            z = rel_loc.get("z", 0)

            # auto-layout 폴백 (프론트엔드 bopStore.js와 동일)
            if x == 0 and z == 0 and len(resources) > 1:
                step = 0.9
                z = idx * step - (len(resources) - 1) * step / 2

            size = r.get("computed_size") or {"width": 0.4, "height": 0.4, "depth": 0.4}
            scale = r.get("scale") or {"x": 1, "y": 1, "z": 1}

            actual_w = size.get("width", 0.4) * scale.get("x", 1)
            actual_d = size.get("depth", 0.4) * scale.get("z", 1)
            actual_h = size.get("height", 0.4) * scale.get("y", 1)

            min_x = min(min_x, x - actual_w / 2)
            max_x = max(max_x, x + actual_w / 2)
            min_z = min(min_z, z - actual_d / 2)
            max_z = max(max_z, z + actual_d / 2)
            max_height = max(max_height, actual_h)

        pd["computed_size"] = {
            "width": round(max_x - min_x, 2),
            "height": round(max_height, 2),
            "depth": round(max_z - min_z, 2),
        }
        computed_count += 1

    print(f"[COMPUTE-SIZES] 공정 크기 계산 완료: {computed_count}개")
    return bop_data


def ensure_manual_stations(bop_data: dict) -> dict:
    """
    작업자나 로봇이 있는 공정 인스턴스에 수작업대(manual_station)가 없으면 자동으로 추가합니다.
    """
    print("[ENSURE-MANUAL-STATIONS] 수작업대 검증 시작")

    equipments = bop_data.get("equipments", [])
    process_details = bop_data.get("process_details", [])
    resource_assignments = bop_data.get("resource_assignments", [])

    # Equipment ID별 타입 매핑
    equipment_type_map = {eq["equipment_id"]: eq["type"] for eq in equipments}

    # 다음 Equipment ID 생성을 위한 카운터
    max_eq_num = 0
    for eq in equipments:
        match = __import__('re').match(r'EQ(\d+)', eq["equipment_id"])
        if match:
            max_eq_num = max(max_eq_num, int(match.group(1)))

    added_count = 0

    # 각 공정 인스턴스별로 검사
    for detail in process_details:
        pid = detail["process_id"]
        pidx = detail.get("parallel_index", 1)

        # 이 인스턴스의 리소스들
        instance_resources = [
            ra for ra in resource_assignments
            if ra["process_id"] == pid and ra.get("parallel_index", 1) == pidx
        ]

        has_worker = False
        has_robot = False
        has_manual_station = False

        for ra in instance_resources:
            if ra["resource_type"] == "worker":
                has_worker = True
            elif ra["resource_type"] == "equipment":
                eq_type = equipment_type_map.get(ra["resource_id"])
                if eq_type == "robot":
                    has_robot = True
                elif eq_type == "manual_station":
                    has_manual_station = True

        if (has_worker or has_robot) and not has_manual_station:
            max_eq_num += 1
            new_eq_id = f"EQ{max_eq_num:03d}"

            new_equipment = {
                "equipment_id": new_eq_id,
                "name": f"작업대 {max_eq_num}",
                "type": "manual_station"
            }
            equipments.append(new_equipment)
            equipment_type_map[new_eq_id] = "manual_station"

            new_ra = {
                "process_id": pid,
                "parallel_index": pidx,
                "resource_type": "equipment",
                "resource_id": new_eq_id,
                "quantity": 1
            }
            resource_assignments.append(new_ra)

            added_count += 1
            print(f"  - Process {pid}#{pidx}: manual_station 추가 ({new_eq_id})")

    if added_count > 0:
        print(f"[ENSURE-MANUAL-STATIONS] 완료: {added_count}개 수작업대 자동 추가")
    else:
        print(f"[ENSURE-MANUAL-STATIONS] 완료: 모든 공정에 수작업대 존재")

    bop_data["equipments"] = equipments
    bop_data["resource_assignments"] = resource_assignments
    return bop_data


def sort_resources_order(bop_data: dict) -> dict:
    """
    resource_assignments를 정렬합니다.
    정렬 순서: Equipment-robot → machine → manual_station → Worker → Material
    """
    print("[SORT-RESOURCES] 리소스 정렬 시작")

    equipments = bop_data.get("equipments", [])
    equipment_type_map = {eq["equipment_id"]: eq["type"] for eq in equipments}

    def get_sort_key(ra):
        resource_type = ra["resource_type"]
        if resource_type == "equipment":
            eq_type = equipment_type_map.get(ra["resource_id"], "unknown")
            if eq_type == "robot":
                return (0, ra["process_id"], ra.get("parallel_index", 1), 1, ra["resource_id"])
            elif eq_type == "machine":
                return (0, ra["process_id"], ra.get("parallel_index", 1), 2, ra["resource_id"])
            elif eq_type == "manual_station":
                return (0, ra["process_id"], ra.get("parallel_index", 1), 3, ra["resource_id"])
            else:
                return (0, ra["process_id"], ra.get("parallel_index", 1), 4, ra["resource_id"])
        elif resource_type == "worker":
            return (0, ra["process_id"], ra.get("parallel_index", 1), 5, ra["resource_id"])
        elif resource_type == "material":
            return (0, ra["process_id"], ra.get("parallel_index", 1), 6, ra["resource_id"])
        return (0, ra["process_id"], ra.get("parallel_index", 1), 7, ra.get("resource_id", ""))

    resource_assignments = bop_data.get("resource_assignments", [])
    resource_assignments.sort(key=get_sort_key)
    bop_data["resource_assignments"] = resource_assignments

    print(f"[SORT-RESOURCES] 완료: {len(resource_assignments)}개 리소스 정렬")
    return bop_data


def apply_automatic_layout(bop_data: dict) -> dict:
    """
    BOP 데이터에 자동 좌표 배치를 적용합니다 (DAG 구조 지원).
    process_details에 location, resource_assignments에 relative_location 할당.
    """
    print("[AUTO-LAYOUT] 자동 좌표 배치 시작 (DAG 모드)")

    processes = bop_data.get("processes", [])
    process_details = bop_data.get("process_details", [])
    resource_assignments = bop_data.get("resource_assignments", [])

    if not processes:
        return bop_data

    # 1. DAG 레벨 계산
    levels = _calculate_dag_levels(processes)
    print(f"[AUTO-LAYOUT] DAG 레벨 계산 완료: {levels}")

    # 2. 레벨별로 공정 그룹화
    level_groups = {}
    for process_id, level in levels.items():
        if level not in level_groups:
            level_groups[level] = []
        level_groups[level].append(process_id)

    # 3. 좌표 배치
    x_spacing = 3.0
    z_spacing = 3.0

    for level in sorted(level_groups.keys()):
        group = level_groups[level]
        group_size = len(group)

        for idx, process_id in enumerate(group):
            x = level * x_spacing
            z = (idx - (group_size - 1) / 2) * z_spacing

            # 이 공정의 모든 process_details에 location 할당
            details_for_process = [
                d for d in process_details if d["process_id"] == process_id
            ]

            for detail_idx, detail in enumerate(details_for_process):
                detail["location"] = {
                    "x": x,
                    "y": 0,
                    "z": z + detail_idx * 5  # 병렬 인스턴스는 Z축 5m 간격
                }

                # 이 인스턴스의 리소스에 relative_location 할당
                pidx = detail.get("parallel_index", 1)
                instance_resources = [
                    ra for ra in resource_assignments
                    if ra["process_id"] == process_id and ra.get("parallel_index", 1) == pidx
                ]

                total_resources = len(instance_resources)
                if total_resources > 0:
                    step = 0.9
                    for j, ra in enumerate(instance_resources):
                        rz = j * step - (total_resources - 1) * step / 2
                        ra["relative_location"] = {"x": 0, "y": 0, "z": rz}

            print(f"  - Process {process_id}: level={level}, details={len(details_for_process)}개")

    print(f"[AUTO-LAYOUT] 완료: {len(processes)}개 공정 배치 ({len(level_groups)}개 레벨)")
    return bop_data


def _calculate_dag_levels(processes: list) -> dict:
    """
    DAG 구조에서 각 공정의 레벨(깊이)을 계산합니다.
    """
    all_ids = {p["process_id"] for p in processes}

    predecessors = {}
    for p in processes:
        pid = p["process_id"]
        preds = p.get("predecessor_ids", [])
        predecessors[pid] = [pred for pred in preds if pred in all_ids]

    levels = {}

    def get_level(pid):
        if pid in levels:
            return levels[pid]

        preds = predecessors.get(pid, [])
        if not preds:
            levels[pid] = 0
            return 0

        max_pred_level = max(get_level(pred) for pred in preds)
        levels[pid] = max_pred_level + 1
        return levels[pid]

    for p in processes:
        get_level(p["process_id"])

    return levels


def preserve_existing_layout(new_bop: dict, current_bop: dict) -> dict:
    """
    기존 BOP의 좌표를 새 BOP에 보존합니다.
    """
    # 기존 process_details 좌표를 (process_id, parallel_index)로 매핑
    existing_detail_locations = {}
    for detail in current_bop.get("process_details", []):
        key = (detail["process_id"], detail.get("parallel_index", 1))
        if "location" in detail:
            existing_detail_locations[key] = detail["location"]

    # 기존 resource_assignments 좌표를 (process_id, parallel_index, resource_id)로 매핑
    existing_resource_locations = {}
    for ra in current_bop.get("resource_assignments", []):
        if "relative_location" in ra:
            key = (ra["process_id"], ra.get("parallel_index", 1), ra["resource_id"])
            existing_resource_locations[key] = ra["relative_location"]

    # 새 BOP에 기존 좌표 적용
    for detail in new_bop.get("process_details", []):
        key = (detail["process_id"], detail.get("parallel_index", 1))
        if key in existing_detail_locations:
            detail["location"] = existing_detail_locations[key]

    for ra in new_bop.get("resource_assignments", []):
        key = (ra["process_id"], ra.get("parallel_index", 1), ra["resource_id"])
        if key in existing_resource_locations:
            ra["relative_location"] = existing_resource_locations[key]

    return new_bop


def validate_bop_data(bop_data: dict) -> Tuple[bool, str]:
    """
    BOP 데이터의 유효성을 검증합니다.
    """
    try:
        bop = BOPData(**bop_data)

        is_valid, error_msg = bop.validate_references()
        if not is_valid:
            return False, error_msg

        is_valid, error_msg = bop.detect_cycles()
        if not is_valid:
            return False, error_msg

        return True, ""

    except Exception as e:
        return False, f"검증 중 오류 발생: {str(e)}"


async def generate_bop_from_text(user_input: str, model: str = None) -> dict:
    """
    사용자 입력을 받아 LLM을 통해 BOP JSON을 생성합니다.
    """
    if not model:
        model = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")

    provider = get_provider(model)
    full_prompt = f"{SYSTEM_PROMPT}\n\nUser request: {user_input}"

    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            bop_data = await provider.generate_json(full_prompt, max_retries=1)

            # 수작업대 보장
            bop_data = ensure_manual_stations(bop_data)
            # 리소스 정렬
            bop_data = sort_resources_order(bop_data)
            # 리소스 크기 계산
            bop_data = compute_resource_sizes(bop_data)
            bop_data = compute_process_sizes(bop_data)
            # 자동 좌표 배치
            bop_data = apply_automatic_layout(bop_data)

            # BOP 검증
            is_valid, error_msg = validate_bop_data(bop_data)
            if not is_valid:
                raise ValueError(f"BOP 검증 실패: {error_msg}")

            if len(bop_data["processes"]) == 0:
                raise ValueError("processes는 비어있지 않아야 합니다.")

            return bop_data

        except Exception as e:
            last_error = f"BOP 생성 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}"
            print(last_error)
            if attempt < max_retries - 1:
                continue

    raise Exception(f"BOP 생성 실패: {last_error}")


async def modify_bop(current_bop: dict, user_message: str, model: str = None) -> dict:
    """
    현재 BOP와 사용자 수정 요청을 받아 업데이트된 BOP를 생성합니다.
    """
    if not model:
        model = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")

    provider = get_provider(model)
    current_bop_json = json.dumps(current_bop, indent=2, ensure_ascii=False)

    full_prompt = MODIFY_PROMPT_TEMPLATE.format(
        current_bop_json=current_bop_json,
        user_message=user_message
    )

    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            updated_bop = await provider.generate_json(full_prompt, max_retries=1)

            updated_bop = ensure_manual_stations(updated_bop)
            updated_bop = sort_resources_order(updated_bop)
            updated_bop = compute_resource_sizes(updated_bop)
            updated_bop = compute_process_sizes(updated_bop)

            # 기존 좌표 보존
            updated_bop = preserve_existing_layout(updated_bop, current_bop)

            # 좌표가 없는 새 요소가 있으면 자동 배치
            needs_layout = False
            for detail in updated_bop.get("process_details", []):
                if "location" not in detail:
                    needs_layout = True
                    break
            if not needs_layout:
                for ra in updated_bop.get("resource_assignments", []):
                    if "relative_location" not in ra:
                        needs_layout = True
                        break

            if needs_layout:
                print("[MODIFY] 새 요소 발견, 자동 좌표 배치 적용")
                updated_bop = apply_automatic_layout(updated_bop)

            is_valid, error_msg = validate_bop_data(updated_bop)
            if not is_valid:
                raise ValueError(f"BOP 검증 실패: {error_msg}")

            return updated_bop

        except Exception as e:
            last_error = f"BOP 수정 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}"
            print(last_error)
            if attempt < max_retries - 1:
                continue

    raise Exception(f"BOP 수정 실패: {last_error}")


async def unified_chat(user_message: str, current_bop: dict = None, model: str = None, language: str = "ko") -> dict:
    """
    통합 채팅 엔드포인트: BOP 생성, 수정, QA를 모두 처리합니다.
    """
    if not model:
        model = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")

    provider = get_provider(model)

    if current_bop:
        current_bop_json = json.dumps(current_bop, indent=2, ensure_ascii=False)
        context = f"Current BOP:\n{current_bop_json}"
    else:
        context = "No current BOP exists yet."

    # 언어 지시사항 추가
    if language == "en":
        language_instruction = "\n\nIMPORTANT: You MUST respond in English. The \"message\" field must be in English."
    else:
        language_instruction = "\n\nIMPORTANT: You MUST respond in Korean (한국어). The \"message\" field must be in Korean."

    full_prompt = UNIFIED_CHAT_PROMPT_TEMPLATE.format(
        context=context,
        user_message=user_message
    ) + language_instruction

    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            response_data = await provider.generate_json(full_prompt, max_retries=1)

            print(f"[DEBUG] LLM Response: {json.dumps(response_data, indent=2, ensure_ascii=False)[:500]}...")

            if "message" not in response_data:
                raise ValueError("응답에 'message' 필드가 없습니다.")

            if "bop_data" in response_data:
                bop_data = response_data["bop_data"]

                bop_data = ensure_manual_stations(bop_data)
                bop_data = sort_resources_order(bop_data)
                bop_data = compute_resource_sizes(bop_data)
                bop_data = compute_process_sizes(bop_data)

                if current_bop:
                    bop_data = preserve_existing_layout(bop_data, current_bop)

                    needs_layout = False
                    for detail in bop_data.get("process_details", []):
                        if "location" not in detail:
                            needs_layout = True
                            break
                    if not needs_layout:
                        for ra in bop_data.get("resource_assignments", []):
                            if "relative_location" not in ra:
                                needs_layout = True
                                break

                    if needs_layout:
                        print("[UNIFIED] 새 요소 발견, 자동 좌표 배치 적용")
                        bop_data = apply_automatic_layout(bop_data)
                else:
                    bop_data = apply_automatic_layout(bop_data)

                response_data["bop_data"] = bop_data

                is_valid, error_msg = validate_bop_data(bop_data)
                if not is_valid:
                    print(f"[ERROR] BOP 검증 실패: {error_msg}")
                    print(f"[ERROR] 받은 BOP 데이터: {json.dumps(bop_data, indent=2, ensure_ascii=False)[:1000]}...")
                    raise ValueError(f"BOP 검증 실패: {error_msg}")

                print(f"[DEBUG] BOP 검증 성공")

            return response_data

        except Exception as e:
            last_error = f"Unified chat 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}"
            print(last_error)
            if attempt < max_retries - 1:
                continue

    raise Exception(f"Unified chat 실패: {last_error}")
