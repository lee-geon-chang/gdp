"""
BOP 생성 프롬프트 테스트
- Gemini API를 직접 호출하여 BOP 생성 결과 검증
"""
import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트 경로 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv(project_root / ".env")

from app.prompts import UNIFIED_CHAT_PROMPT_TEMPLATE

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def call_gemini(prompt: str) -> dict:
    """Gemini API 호출"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()

    result = response.json()
    response_text = result['candidates'][0]['content']['parts'][0]['text'].strip()

    # 마크다운 코드 블록 제거
    if response_text.startswith("```"):
        lines = response_text.split('\n')
        response_text = '\n'.join(lines[1:-1])

    return json.loads(response_text)

def validate_bop(bop_data: dict) -> list:
    """BOP 데이터 검증 - 문제점 리스트 반환"""
    issues = []

    if not bop_data:
        return ["bop_data가 없습니다"]

    processes = bop_data.get("processes", [])
    equipments = bop_data.get("equipments", [])
    workers = bop_data.get("workers", [])
    materials = bop_data.get("materials", [])

    # 1. 공정 수 검증
    if len(processes) < 5:
        issues.append(f"공정 수가 너무 적음: {len(processes)}개 (최소 5개 권장)")

    # 2. 각 공정의 리소스 검증
    for proc in processes:
        proc_id = proc.get("process_id", "unknown")
        resources = proc.get("resources", [])

        if not resources:
            issues.append(f"{proc_id}: resources 배열이 비어있음!")
            continue

        # 리소스 타입별 분류
        eq_resources = [r for r in resources if r.get("resource_type") == "equipment"]
        worker_resources = [r for r in resources if r.get("resource_type") == "worker"]
        material_resources = [r for r in resources if r.get("resource_type") == "material"]

        # 장비 없이 자재만 있는 경우
        if material_resources and not eq_resources:
            issues.append(f"{proc_id}: 자재만 있고 장비 없음 (무효)")

        # 장비 있는데 작업자/로봇 없는 경우
        if eq_resources and not worker_resources:
            # robot 타입 장비가 있는지 확인
            has_robot = False
            for eq_res in eq_resources:
                eq_id = eq_res.get("resource_id")
                eq_info = next((e for e in equipments if e.get("equipment_id") == eq_id), None)
                if eq_info and eq_info.get("type") == "robot":
                    has_robot = True
                    break

            if not has_robot:
                issues.append(f"{proc_id}: 장비는 있지만 작업자/로봇 없음 (누가 작동?)")

        # 수작업대 확인 (machine 공정은 예외 허용)
        has_manual_station = False
        has_machine = False
        for eq_res in eq_resources:
            eq_id = eq_res.get("resource_id")
            eq_info = next((e for e in equipments if e.get("equipment_id") == eq_id), None)
            if eq_info:
                if eq_info.get("type") == "manual_station":
                    has_manual_station = True
                if eq_info.get("type") == "machine":
                    has_machine = True

        # machine 공정이 아닌데 수작업대가 없으면 경고 (에러가 아닌 경고)
        if not has_manual_station and eq_resources and not has_machine:
            issues.append(f"{proc_id}: 수작업대(manual_station) 없음 (권장)")

    # 3. 장비 정의 검증
    if not equipments:
        issues.append("equipments 배열이 비어있음!")

    # 4. 작업자 정의 검증
    if not workers:
        issues.append("workers 배열이 비어있음!")

    return issues

def test_bop_generation(product_name: str):
    """BOP 생성 테스트"""
    print(f"\n{'='*60}")
    print(f"테스트: {product_name} 제조 라인 BOP 생성")
    print(f"{'='*60}")

    # 프롬프트 구성
    user_message = f"{product_name} 제조 라인 BOP를 생성해줘"
    context = "No current BOP exists yet."

    full_prompt = UNIFIED_CHAT_PROMPT_TEMPLATE.format(
        context=context,
        user_message=user_message
    )

    print(f"\n[요청] {user_message}")

    try:
        response = call_gemini(full_prompt)

        print(f"\n[응답 메시지] {response.get('message', 'N/A')[:200]}...")

        bop_data = response.get("bop_data")

        if not bop_data:
            print("\n❌ bop_data가 응답에 없습니다!")
            return False

        # BOP 구조 출력
        processes = bop_data.get("processes", [])
        equipments = bop_data.get("equipments", [])
        workers = bop_data.get("workers", [])
        materials = bop_data.get("materials", [])

        print(f"\n[BOP 구조]")
        print(f"  - 공정 수: {len(processes)}")
        print(f"  - 장비 수: {len(equipments)}")
        print(f"  - 작업자 수: {len(workers)}")
        print(f"  - 자재 수: {len(materials)}")

        # 각 공정의 리소스 매핑 확인
        print(f"\n[공정별 리소스 매핑]")
        for proc in processes:
            proc_id = proc.get("process_id")
            proc_name = proc.get("name")
            resources = proc.get("resources", [])

            eq_count = len([r for r in resources if r.get("resource_type") == "equipment"])
            worker_count = len([r for r in resources if r.get("resource_type") == "worker"])
            material_count = len([r for r in resources if r.get("resource_type") == "material"])

            status = "✓" if resources else "❌ EMPTY"
            print(f"  {proc_id} ({proc_name}): 장비={eq_count}, 작업자={worker_count}, 자재={material_count} {status}")

        # 장비 타입 확인
        print(f"\n[장비 목록]")
        for eq in equipments:
            print(f"  - {eq.get('equipment_id')}: {eq.get('name')} ({eq.get('type')})")

        # 검증
        issues = validate_bop(bop_data)

        if issues:
            print(f"\n⚠️ 발견된 문제점 ({len(issues)}개):")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print(f"\n✅ BOP 검증 통과!")
            return True

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY가 설정되지 않았습니다.")
        return

    print("=" * 60)
    print("BOP 생성 프롬프트 검증 테스트")
    print("=" * 60)

    # 다양한 제품으로 테스트
    test_cases = [
        "자전거",
        "선풍기",
    ]

    results = {}
    for product in test_cases:
        results[product] = test_bop_generation(product)

    # 최종 결과
    print(f"\n{'='*60}")
    print("최종 결과")
    print(f"{'='*60}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for product, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {product}: {status}")

    print(f"\n통과율: {passed}/{total}")

if __name__ == "__main__":
    main()
