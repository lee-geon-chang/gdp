// Mock BOP data for development and testing
// New flat structure: processes (routing), process_details (instances), resource_assignments (flat)

export const mockBopData = {
  "project_title": "전기 자전거 조립 라인",
  "target_uph": 120,
  "processes": [
    { "process_id": "P001", "predecessor_ids": [], "successor_ids": ["P002"] },
    { "process_id": "P002", "predecessor_ids": ["P001"], "successor_ids": ["P003"] },
    { "process_id": "P003", "predecessor_ids": ["P002"], "successor_ids": ["P004"] },
    { "process_id": "P004", "predecessor_ids": ["P003"], "successor_ids": ["P005"] },
    { "process_id": "P005", "predecessor_ids": ["P004"], "successor_ids": [] }
  ],
  "process_details": [
    // P001 - 프레임 용접 (병렬 2)
    { "process_id": "P001", "parallel_index": 1, "name": "프레임 용접", "description": "메인 프레임과 서브 프레임을 용접하여 기본 골격 제작", "cycle_time_sec": 180.0, "location": { "x": 0, "y": 0, "z": 0 }, "rotation_y": 0 },
    { "process_id": "P001", "parallel_index": 2, "name": "프레임 용접", "description": "메인 프레임과 서브 프레임을 용접하여 기본 골격 제작", "cycle_time_sec": 180.0, "location": { "x": 0, "y": 0, "z": 5 }, "rotation_y": 0 },
    // P002 - 도장 (병렬 1)
    { "process_id": "P002", "parallel_index": 1, "name": "도장", "description": "프레임 표면 전처리 후 분체 도장 실시", "cycle_time_sec": 120.0, "location": { "x": 5, "y": 0, "z": 0 }, "rotation_y": 0 },
    // P003 - 전장 조립 (병렬 2)
    { "process_id": "P003", "parallel_index": 1, "name": "전장 조립", "description": "배터리, 모터, 컨트롤러 등 전장 부품 조립", "cycle_time_sec": 240.0, "location": { "x": 10, "y": 0, "z": 0 }, "rotation_y": 0 },
    { "process_id": "P003", "parallel_index": 2, "name": "전장 조립", "description": "배터리, 모터, 컨트롤러 등 전장 부품 조립", "cycle_time_sec": 240.0, "location": { "x": 10, "y": 0, "z": 5 }, "rotation_y": 0 },
    // P004 - 프레임 및 조립 (병렬 2)
    { "process_id": "P004", "parallel_index": 1, "name": "프레임 및 조립", "description": "바퀴, 브레이크, 핸들 등 기계 부품 조립", "cycle_time_sec": 200.0, "location": { "x": 15, "y": 0, "z": 0 }, "rotation_y": 0 },
    { "process_id": "P004", "parallel_index": 2, "name": "프레임 및 조립", "description": "바퀴, 브레이크, 핸들 등 기계 부품 조립", "cycle_time_sec": 200.0, "location": { "x": 15, "y": 0, "z": 5 }, "rotation_y": 0 },
    // P005 - 최종 검사 및 포장 (병렬 1)
    { "process_id": "P005", "parallel_index": 1, "name": "최종 검사 및 포장", "description": "기능 테스트, 외관 검사 후 포장 처리", "cycle_time_sec": 150.0, "location": { "x": 20, "y": 0, "z": 0 }, "rotation_y": 0 }
  ],
  "resource_assignments": [
    // P001:1 resources
    { "process_id": "P001", "parallel_index": 1, "resource_type": "equipment", "resource_id": "EQ001", "quantity": 1, "relative_location": { "x": 0, "y": 0, "z": 0 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Main welding robot #1" },
    { "process_id": "P001", "parallel_index": 1, "resource_type": "worker", "resource_id": "W001", "quantity": 1, "relative_location": { "x": 1.0, "y": 0, "z": 0.5 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Welding operator #1" },
    { "process_id": "P001", "parallel_index": 1, "resource_type": "material", "resource_id": "M001", "quantity": 5.2, "relative_location": { "x": -1.2, "y": 0, "z": 0 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Frame material" },
    // P001:2 resources
    { "process_id": "P001", "parallel_index": 2, "resource_type": "equipment", "resource_id": "EQ002", "quantity": 1, "relative_location": { "x": 0, "y": 0, "z": 0 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Main welding robot #2" },
    { "process_id": "P001", "parallel_index": 2, "resource_type": "worker", "resource_id": "W002", "quantity": 1, "relative_location": { "x": 1.0, "y": 0, "z": 0.5 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Welding operator #2" },
    { "process_id": "P001", "parallel_index": 2, "resource_type": "material", "resource_id": "M001", "quantity": 5.2, "relative_location": { "x": -1.2, "y": 0, "z": 0 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Frame material" },
    // P002:1 resources
    { "process_id": "P002", "parallel_index": 1, "resource_type": "equipment", "resource_id": "EQ003", "quantity": 1, "relative_location": { "x": 0, "y": 0, "z": 0 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Powder coating booth" },
    { "process_id": "P002", "parallel_index": 1, "resource_type": "worker", "resource_id": "W009", "quantity": 1, "relative_location": { "x": 1.0, "y": 0, "z": 0.5 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Coating operator" },
    { "process_id": "P002", "parallel_index": 1, "resource_type": "material", "resource_id": "M002", "quantity": 0.8, "relative_location": { "x": -1.2, "y": 0, "z": 0 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Coating powder" },
    // P003:1 resources
    { "process_id": "P003", "parallel_index": 1, "resource_type": "equipment", "resource_id": "EQ004", "quantity": 1, "relative_location": { "x": 0, "y": 0, "z": 0 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Assembly workstation #1" },
    { "process_id": "P003", "parallel_index": 1, "resource_type": "worker", "resource_id": "W003", "quantity": 2, "relative_location": { "x": 0.9, "y": 0, "z": 0.5 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Electronics assembler #1" },
    { "process_id": "P003", "parallel_index": 1, "resource_type": "material", "resource_id": "M003", "quantity": 1, "relative_location": { "x": -1.0, "y": 0, "z": 0.4 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Battery pack" },
    { "process_id": "P003", "parallel_index": 1, "resource_type": "material", "resource_id": "M004", "quantity": 1, "relative_location": { "x": -1.0, "y": 0, "z": -0.4 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Hub motor" },
    // P003:2 resources
    { "process_id": "P003", "parallel_index": 2, "resource_type": "equipment", "resource_id": "EQ006", "quantity": 1, "relative_location": { "x": 0, "y": 0, "z": 0 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Assembly workstation #2" },
    { "process_id": "P003", "parallel_index": 2, "resource_type": "worker", "resource_id": "W007", "quantity": 2, "relative_location": { "x": 0.9, "y": 0, "z": 0.5 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Electronics assembler #2" },
    { "process_id": "P003", "parallel_index": 2, "resource_type": "material", "resource_id": "M003", "quantity": 1, "relative_location": { "x": -1.0, "y": 0, "z": 0.4 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Battery pack" },
    { "process_id": "P003", "parallel_index": 2, "resource_type": "material", "resource_id": "M004", "quantity": 1, "relative_location": { "x": -1.0, "y": 0, "z": -0.4 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Hub motor" },
    // P004:1 resources
    { "process_id": "P004", "parallel_index": 1, "resource_type": "equipment", "resource_id": "EQ005", "quantity": 1, "relative_location": { "x": 0, "y": 0, "z": 0 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Assembly station #1" },
    { "process_id": "P004", "parallel_index": 1, "resource_type": "worker", "resource_id": "W004", "quantity": 2, "relative_location": { "x": 0.9, "y": 0, "z": 0.5 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Mechanical assembler #1" },
    { "process_id": "P004", "parallel_index": 1, "resource_type": "material", "resource_id": "M005", "quantity": 2, "relative_location": { "x": -1.0, "y": 0, "z": 0.4 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Wheels" },
    { "process_id": "P004", "parallel_index": 1, "resource_type": "material", "resource_id": "M006", "quantity": 2, "relative_location": { "x": -1.0, "y": 0, "z": -0.4 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Brake set" },
    // P004:2 resources
    { "process_id": "P004", "parallel_index": 2, "resource_type": "equipment", "resource_id": "EQ007", "quantity": 1, "relative_location": { "x": 0, "y": 0, "z": 0 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Assembly station #2" },
    { "process_id": "P004", "parallel_index": 2, "resource_type": "worker", "resource_id": "W008", "quantity": 2, "relative_location": { "x": 0.9, "y": 0, "z": 0.5 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Mechanical assembler #2" },
    { "process_id": "P004", "parallel_index": 2, "resource_type": "material", "resource_id": "M005", "quantity": 2, "relative_location": { "x": -1.0, "y": 0, "z": 0.4 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Wheels" },
    { "process_id": "P004", "parallel_index": 2, "resource_type": "material", "resource_id": "M006", "quantity": 2, "relative_location": { "x": -1.0, "y": 0, "z": -0.4 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Brake set" },
    // P005:1 resources
    { "process_id": "P005", "parallel_index": 1, "resource_type": "equipment", "resource_id": "EQ008", "quantity": 1, "relative_location": { "x": 0, "y": 0, "z": 0 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Test equipment" },
    { "process_id": "P005", "parallel_index": 1, "resource_type": "worker", "resource_id": "W005", "quantity": 1, "relative_location": { "x": 1.0, "y": 0, "z": 0.5 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Quality inspector" },
    { "process_id": "P005", "parallel_index": 1, "resource_type": "worker", "resource_id": "W006", "quantity": 1, "relative_location": { "x": -1.0, "y": 0, "z": 0.5 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Packaging worker" },
    { "process_id": "P005", "parallel_index": 1, "resource_type": "material", "resource_id": "M007", "quantity": 1, "relative_location": { "x": 1.2, "y": 0, "z": -0.5 }, "rotation_y": 0, "scale": { "x": 1, "y": 1, "z": 1 }, "role": "Packaging box" }
  ],
  "equipments": [
    { "equipment_id": "EQ001", "name": "6축 용접 로봇 #1", "type": "robot" },
    { "equipment_id": "EQ002", "name": "6축 용접 로봇 #2", "type": "robot" },
    { "equipment_id": "EQ003", "name": "분체 도장 부스", "type": "machine" },
    { "equipment_id": "EQ004", "name": "전장 조립 워크스테이션 #1", "type": "manual_station" },
    { "equipment_id": "EQ005", "name": "기계 조립 워크스테이션 #1", "type": "manual_station" },
    { "equipment_id": "EQ006", "name": "전장 조립 워크스테이션 #2", "type": "manual_station" },
    { "equipment_id": "EQ007", "name": "기계 조립 워크스테이션 #2", "type": "manual_station" },
    { "equipment_id": "EQ008", "name": "기능 테스트 장비", "type": "machine" }
  ],
  "workers": [
    { "worker_id": "W001", "name": "김철수", "skill_level": "Senior" },
    { "worker_id": "W002", "name": "이영희", "skill_level": "Senior" },
    { "worker_id": "W003", "name": "박민수", "skill_level": "Senior" },
    { "worker_id": "W004", "name": "정수진", "skill_level": "Mid" },
    { "worker_id": "W005", "name": "최준호", "skill_level": "Senior" },
    { "worker_id": "W006", "name": "강미라", "skill_level": "Junior" },
    { "worker_id": "W007", "name": "홍길동", "skill_level": "Senior" },
    { "worker_id": "W008", "name": "윤지원", "skill_level": "Mid" },
    { "worker_id": "W009", "name": "한지민", "skill_level": "Senior" }
  ],
  "materials": [
    { "material_id": "M001", "name": "알루미늄 합금 프레임", "unit": "kg" },
    { "material_id": "M002", "name": "분체 도료", "unit": "kg" },
    { "material_id": "M003", "name": "리튬이온 배터리 팩 (48V 13Ah)", "unit": "ea" },
    { "material_id": "M004", "name": "허브 모터 (500W)", "unit": "ea" },
    { "material_id": "M005", "name": "26인치 휠 세트", "unit": "ea" },
    { "material_id": "M006", "name": "디스크 브레이크 세트", "unit": "ea" },
    { "material_id": "M007", "name": "포장 박스", "unit": "ea" }
  ],
  "obstacles": []
};
