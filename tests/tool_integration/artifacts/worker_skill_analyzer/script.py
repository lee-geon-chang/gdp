import json
import argparse
import sys
import os
import math


def process_data(data):
    """Analyzes worker skills and process complexity to identify mismatches and suggest reassignments.

    Input JSON format:
    {
        "project_title": "string",
        "target_uph": float,
        "processes": [
            {
                "process_id": "string",
                "parallel_count": int,
                "predecessor_ids": [],
                "successor_ids": [],
                "parallel_lines": [
                    {
                        "parallel_index": int,
                        "name": "string",
                        "description": "string",
                        "cycle_time_sec": float,
                        "location": {"x": float, "y": float, "z": float},
                        "rotation_y": float
                    }
                ],
                "resources": [
                    {
                        "resource_type": "equipment|worker|material",
                        "resource_id": "string",
                        "quantity": int,
                        "role": "string",
                        "relative_location": {"x": float, "y": float, "z": float},
                        "rotation_y": float,
                        "scale": {"x": float, "y": float, "z": float},
                        "parallel_line_index": int
                    }
                ]
            }
        ],
        "equipments": [],
        "workers": [
            {
                "worker_id": "string",
                "name": "string",
                "skill_level": "Junior|Mid|Senior"
            }
        ],
        "materials": [],
        "obstacles": []
    }

    Output JSON format:
    {
        "process_worker_assignments": {
            "process_id": [{"worker_id": "string", "skill_level": "Junior|Mid|Senior"}]
        },
        "skill_adequacy_scores": {
            "process_id": float  # Score based on cycle time and worker skill levels
        },
        "mismatch_warnings": [
            {"process_id": "string", "worker_id": "string", "reason": "string"}
        ],
        "reassignment_suggestions": [
            {"process_id": "string", "suggested_worker_id": "string", "reason": "string"}
        ]
    }
    """
    process_worker_assignments = {}
    skill_adequacy_scores = {}
    mismatch_warnings = []
    reassignment_suggestions = []

    # 1. 공정별 작업자 배치 현황
    for process in data['processes']:
        process_id = process['process_id']
        process_worker_assignments[process_id] = []
        for resource in process['resources']:
            if resource['resource_type'] == 'worker':
                worker_id = resource['resource_id']
                worker = next((w for w in data['workers'] if w['worker_id'] == worker_id), None)
                if worker:
                    process_worker_assignments[process_id].append({
                        'worker_id': worker_id,
                        'skill_level': worker['skill_level']
                    })

    # 2. 스킬 적합도 점수 (간단한 예시: cycle_time * skill_level_multiplier)
    for process in data['processes']:
        process_id = process['process_id']
        total_skill_score = 0
        total_cycle_time = 0
        worker_count = 0

        for parallel_line in process['parallel_lines']:
            total_cycle_time += parallel_line['cycle_time_sec']

        for assignment in process_worker_assignments.get(process_id, []):
            worker_count += 1
            skill_level = assignment['skill_level']
            if skill_level == 'Junior':
                skill_multiplier = 1
            elif skill_level == 'Mid':
                skill_multiplier = 2
            else:
                skill_multiplier = 3
            total_skill_score += skill_multiplier

        if worker_count > 0:
            average_skill_multiplier = total_skill_score / worker_count
            skill_adequacy_scores[process_id] = total_cycle_time * average_skill_multiplier
        else:
            skill_adequacy_scores[process_id] = 0  # No workers assigned

    # 3. 미스매치 경고 및 4. 재배치 제안 (간단한 예시: cycle_time이 길고 Junior 작업자만 있는 경우)
    for process in data['processes']:
        process_id = process['process_id']
        cycle_time_threshold = 60  # 예시: 60초 이상을 복잡한 공정으로 간주
        junior_workers_only = True
        has_workers = False

        total_cycle_time = 0
        for parallel_line in process['parallel_lines']:
            total_cycle_time += parallel_line['cycle_time_sec']

        for assignment in process_worker_assignments.get(process_id, []):
            has_workers = True
            if assignment['skill_level'] != 'Junior':
                junior_workers_only = False
                break

        if has_workers and junior_workers_only and total_cycle_time > cycle_time_threshold:
            for assignment in process_worker_assignments[process_id]:
                worker_id = assignment['worker_id']
                mismatch_warnings.append({
                    'process_id': process_id,
                    'worker_id': worker_id,
                    'reason': f'공정 {process_id}는 복잡한 공정인데 Junior 작업자 {worker_id}만 배치되었습니다.'
                })

                # 간단한 재배치 제안 (가장 높은 스킬 레벨의 작업자를 배치한다고 가정)
                available_senior_workers = [w['worker_id'] for w in data['workers'] if w['skill_level'] == 'Senior']
                if available_senior_workers:
                    suggested_worker_id = available_senior_workers[0]
                    reassignment_suggestions.append({
                        'process_id': process_id,
                        'suggested_worker_id': suggested_worker_id,
                        'reason': f'공정 {process_id}에 Senior 작업자 {suggested_worker_id}를 배치하는 것을 제안합니다.'
                    })

    result = {
        'process_worker_assignments': process_worker_assignments,
        'skill_adequacy_scores': skill_adequacy_scores,
        'mismatch_warnings': mismatch_warnings,
        'reassignment_suggestions': reassignment_suggestions
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="작업자 스킬 레벨과 공정 난이도를 분석하는 도구입니다.")
    parser.add_argument('--input', '-i', type=str, required=True, help='입력 JSON 파일 경로')
    parser.add_argument('--output', '-o', type=str, required=True, help='출력 JSON 파일 경로')
    args = parser.parse_args()

    # Read input
    if not os.path.exists(args.input):
        print(f"[Error] 입력 파일을 찾을 수 없습니다: {args.input}")
        sys.exit(1)

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[Error] 입력 파일이 JSON 형식이 아닙니다: {e}")
        sys.exit(1)

    # Process
    try:
        result = process_data(input_data)
    except Exception as e:
        print(f"[Error] 데이터 처리 중 오류가 발생했습니다: {e}")
        sys.exit(1)

    # Write output
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[Error] 출력 파일을 쓸 수 없습니다: {e}")
        sys.exit(1)

    print(f"[Success] 결과가 {args.output}에 저장되었습니다.")


if __name__ == "__main__":
    main()