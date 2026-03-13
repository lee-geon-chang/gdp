"""
AI 개선 기능 테스트

의도적으로 실패 케이스를 만들어 AI 개선 기능이 동작하는지 검증합니다.
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.tools.tool_prompts import (
    TOOL_ANALYSIS_PROMPT,
    SCRIPT_GENERATION_PROMPT,
    ADAPTER_SYNTHESIS_PROMPT,
    TOOL_IMPROVEMENT_PROMPT
)


class ImprovementTester:
    """AI 개선 기능 테스터"""

    def __init__(self, bop_data_path: str):
        self.bop_data_path = Path(bop_data_path)
        with open(self.bop_data_path, 'r', encoding='utf-8') as f:
            self.bop_data = json.load(f)

        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

        self.work_dir = Path(tempfile.mkdtemp(prefix="improve_test_"))
        self.artifact_dir = Path(__file__).parent / "artifacts" / "improvement_tests"
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

        print(f"[테스트] 작업 디렉토리: {self.work_dir}")

    def _call_gemini(self, prompt: str, response_json: bool = True) -> Dict[str, Any]:
        """Gemini API 호출"""
        import requests
        import time
        import re

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}"

        config = {"temperature": 0.2}
        if response_json:
            config["responseMimeType"] = "application/json"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": config,
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, timeout=90)

                if response.status_code == 429:
                    wait_time = (2 ** attempt) * 2
                    print(f"  [Rate Limit] {wait_time}초 대기...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                result = response.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"].strip()

                # Markdown 블록 제거
                if text.startswith("```"):
                    lines = text.split('\n')[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    text = '\n'.join(lines)

                if not response_json:
                    # 텍스트 응답에서 JSON 추출 시도
                    try:
                        return json.loads(text)
                    except:
                        # JSON 블록 찾기
                        json_match = re.search(r'\{[\s\S]*\}', text)
                        if json_match:
                            return json.loads(json_match.group())
                        return {"raw_text": text}

                return json.loads(text)

            except json.JSONDecodeError as e:
                print(f"  [JSON 오류] {str(e)[:50]}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                # 마지막 시도에서 raw 텍스트 반환
                return {"raw_text": text if 'text' in dir() else "", "parse_error": str(e)}

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                raise

        raise Exception("API 호출 실패")

    def _compile_function(self, code: str, func_name: str):
        """코드 문자열에서 함수 추출"""
        namespace = {"json": __import__("json"), "math": __import__("math"),
                     "copy": __import__("copy"), "io": __import__("io"),
                     "csv": __import__("csv"), "re": __import__("re"),
                     "statistics": __import__("statistics")}
        exec(code, namespace)
        if func_name not in namespace:
            raise ValueError(f"함수 '{func_name}'를 찾을 수 없습니다.")
        return namespace[func_name]

    def execute_tool(self, tool_name: str, script_code: str,
                    pre_process_code: str, post_process_code: str,
                    params: Dict = None) -> Dict[str, Any]:
        """도구 실행"""
        params = params or {}
        result = {
            "success": False,
            "tool_input": None,
            "tool_output": None,
            "updated_bop": None,
            "stdout": "",
            "stderr": "",
            "error": None
        }

        try:
            # Pre-process
            pre_func = self._compile_function(pre_process_code, "convert_bop_to_input")
            tool_input = pre_func(self.bop_data, params)
            result["tool_input"] = tool_input

            # 스크립트 실행
            script_path = self.work_dir / f"{tool_name}.py"
            input_path = self.work_dir / "input.json"
            output_path = self.work_dir / "output.json"

            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_code)

            with open(input_path, 'w', encoding='utf-8') as f:
                if isinstance(tool_input, str):
                    f.write(tool_input)
                else:
                    json.dump(tool_input, f, ensure_ascii=False, indent=2)

            proc = subprocess.run(
                [sys.executable, str(script_path), "--input", str(input_path), "--output", str(output_path)],
                capture_output=True, text=True, timeout=60, cwd=str(self.work_dir)
            )

            result["stdout"] = proc.stdout
            result["stderr"] = proc.stderr

            if proc.returncode != 0:
                raise RuntimeError(f"스크립트 실패 (코드: {proc.returncode})\n{proc.stderr}")

            if output_path.exists():
                with open(output_path, 'r', encoding='utf-8') as f:
                    result["tool_output"] = f.read()

            # Post-process
            post_func = self._compile_function(post_process_code, "apply_result_to_bop")
            result["updated_bop"] = post_func(self.bop_data, result["tool_output"])
            result["success"] = True

        except Exception as e:
            import traceback
            result["error"] = str(e)
            result["stderr"] += f"\n{traceback.format_exc()}"

        return result

    def improve_tool(self, tool_name: str, description: str,
                    pre_process_code: str, post_process_code: str,
                    script_code: str, params_schema: list,
                    execution_result: Dict, feedback: str) -> Optional[Dict]:
        """AI 개선 요청"""
        print(f"\n[AI 개선 요청]")
        print(f"  피드백: {feedback[:80]}...")

        current_code_section = (
            f"### Pre-process Code\n```python\n{pre_process_code}\n```\n\n"
            f"### Post-process Code\n```python\n{post_process_code}\n```\n\n"
            f"### Script Code\n```python\n{script_code}\n```"
        )

        prompt = TOOL_IMPROVEMENT_PROMPT.format(
            tool_name=tool_name,
            tool_description=description,
            current_code_section=current_code_section,
            params_schema_json=json.dumps(params_schema, indent=2, ensure_ascii=False) if params_schema else "[]",
            execution_success=execution_result.get("success", False),
            stdout=execution_result.get("stdout", "")[:2000] or "(empty)",
            stderr=execution_result.get("stderr", "")[:2000] or "(empty)",
            tool_output=execution_result.get("tool_output", "")[:2000] or "(empty)",
            user_feedback=feedback,
            modify_adapter="Yes",
            modify_params="Yes",
            modify_script="Yes"
        )

        try:
            # response_json=False로 시도 (코드 필드가 복잡해서)
            result = self._call_gemini(prompt, response_json=False)

            # 결과 검증
            if not isinstance(result, dict):
                print(f"  [경고] 응답이 dict가 아님: {type(result)}")
                return None

            if "raw_text" in result and "parse_error" in result:
                print(f"  [경고] JSON 파싱 실패, raw 텍스트에서 코드 추출 시도")
                # raw_text에서 코드 블록 추출 시도
                import re
                raw = result.get("raw_text", "")

                extracted = {}
                # pre_process_code 추출
                pre_match = re.search(r'def convert_bop_to_input\(.*?\n(?:.*?\n)*?(?=\ndef |$)', raw, re.MULTILINE)
                if pre_match:
                    extracted["pre_process_code"] = pre_match.group(0).strip()

                # post_process_code 추출
                post_match = re.search(r'def apply_result_to_bop\(.*?\n(?:.*?\n)*?(?=\ndef |$)', raw, re.MULTILINE)
                if post_match:
                    extracted["post_process_code"] = post_match.group(0).strip()

                if extracted:
                    result = extracted
                else:
                    return None

            print(f"  [성공] 변경사항: {result.get('changes_summary', ['코드 수정됨'])}")
            return result
        except Exception as e:
            import traceback
            print(f"  [실패] {str(e)[:100]}")
            print(f"  {traceback.format_exc()[:200]}")
            return None


# === 테스트 케이스 정의 ===

def test_case_1_broken_adapter(tester: ImprovementTester):
    """
    테스트 케이스 1: 잘못된 어댑터 코드
    - 의도적으로 BOP 구조를 잘못 접근하는 어댑터 생성
    - AI가 오류를 수정하는지 확인
    """
    print("\n" + "=" * 60)
    print("[테스트 1] 잘못된 어댑터 코드 수정")
    print("=" * 60)

    tool_name = "cycle_time_reporter"
    description = "공정별 사이클 타임을 출력하는 도구"

    # 정상 스크립트
    script_code = '''"""Cycle Time Reporter"""
import json
import argparse
import os
import sys

def process_data(data):
    result = {"cycle_times": {}}
    for proc in data.get("processes", []):
        process_id = proc["process_id"]
        cycle_time = proc["cycle_time_sec"]  # 입력에서 이미 추출된 값
        result["cycle_times"][process_id] = cycle_time
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', required=True)
    parser.add_argument('--output', '-o', required=True)
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    result = process_data(input_data)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[Success] Saved to {args.output}")

if __name__ == "__main__":
    main()
'''

    # 의도적으로 잘못된 어댑터 (process 레벨에서 cycle_time을 찾으려 함)
    # BOP 구조에서 cycle_time_sec은 process_details 안에 있음
    broken_pre_process = '''def convert_bop_to_input(bop_json, params):
    import json
    result = {"processes": []}
    for proc in bop_json.get("processes", []):
        # 오류: process 레벨에는 cycle_time_sec이 없음!
        result["processes"].append({
            "process_id": proc["process_id"],
            "cycle_time_sec": proc["cycle_time_sec"]  # KeyError 발생
        })
    return json.dumps(result, ensure_ascii=False)
'''

    # 정상 post-process
    post_process_code = '''def apply_result_to_bop(bop_json, tool_output):
    import json
    import copy
    result = copy.deepcopy(bop_json)
    # 정보성 도구이므로 BOP 변경 없음
    return result
'''

    # 1. 실행 (실패 예상)
    print("\n[1단계] 잘못된 어댑터로 실행 (실패 예상)")
    exec_result = tester.execute_tool(
        tool_name=tool_name,
        script_code=script_code,
        pre_process_code=broken_pre_process,
        post_process_code=post_process_code
    )

    if exec_result["success"]:
        print("  [예상 외] 실행 성공?! 테스트 케이스 검토 필요")
        return False

    print(f"  [예상대로 실패] {exec_result['error'][:80]}...")

    # 2. AI 개선 요청
    print("\n[2단계] AI에게 개선 요청")
    try:
        improvement = tester.improve_tool(
            tool_name=tool_name,
            description=description,
            pre_process_code=broken_pre_process,
            post_process_code=post_process_code,
            script_code=script_code,
            params_schema=[],
            execution_result=exec_result,
            feedback="pre_process에서 KeyError('cycle_time_sec')가 발생합니다. BOP에서 cycle_time_sec은 processes[] 안이 아니라 process_details[] 안에 있습니다. bop_json['process_details']에서 process_id별로 cycle_time_sec을 조회하도록 수정해주세요."
        )
    except Exception as e:
        print(f"  [예외] {str(e)[:100]}")
        improvement = None

    if not improvement:
        print("  [실패] AI 개선 응답 없음")
        return False

    print(f"  [응답 키] {list(improvement.keys())}")

    # 3. 개선된 코드로 재실행
    print("\n[3단계] 개선된 코드로 재실행")

    # 개선된 코드 추출 (None 체크)
    new_pre = improvement.get("pre_process_code") if improvement else None
    new_post = improvement.get("post_process_code") if improvement else None
    new_script = improvement.get("script_code") if improvement else None

    # pre_process가 수정되지 않았으면 실패
    if not new_pre:
        print("  [실패] pre_process_code가 개선되지 않음")
        # 응답 내용 출력
        print(f"  [디버그] 개선 응답 키: {list(improvement.keys()) if improvement else 'None'}")
        return False

    new_pre = new_pre or broken_pre_process
    new_post = new_post or post_process_code
    new_script = new_script or script_code

    retry_result = tester.execute_tool(
        tool_name=tool_name + "_fixed",
        script_code=new_script,
        pre_process_code=new_pre,
        post_process_code=new_post
    )

    if retry_result["success"]:
        print(f"  [성공] 개선 후 실행 성공!")
        print(f"  출력: {retry_result['tool_output'][:200]}...")

        # 산출물 저장
        test_dir = tester.artifact_dir / "test_case_1"
        test_dir.mkdir(parents=True, exist_ok=True)

        with open(test_dir / "original_pre_process.py", 'w', encoding='utf-8') as f:
            f.write(broken_pre_process)
        with open(test_dir / "fixed_pre_process.py", 'w', encoding='utf-8') as f:
            f.write(new_pre)
        with open(test_dir / "output.json", 'w', encoding='utf-8') as f:
            f.write(retry_result["tool_output"])
        with open(test_dir / "improvement_result.json", 'w', encoding='utf-8') as f:
            json.dump(improvement, f, ensure_ascii=False, indent=2)

        print(f"  [산출물 저장] {test_dir}")
        return True
    else:
        print(f"  [실패] 개선 후에도 실행 실패: {retry_result['error'][:80]}...")
        return False


def test_case_2_wrong_output_format(tester: ImprovementTester):
    """
    테스트 케이스 2: 잘못된 출력 형식
    - 스크립트가 예상과 다른 출력 형식 생성
    - AI가 post-process를 수정하는지 확인
    """
    print("\n" + "=" * 60)
    print("[테스트 2] 잘못된 출력 형식 수정")
    print("=" * 60)

    tool_name = "resource_counter"
    description = "공정별 리소스 수를 계산하는 도구"

    # 스크립트는 배열로 출력
    script_code = '''"""Resource Counter - outputs as array"""
import json
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', required=True)
    parser.add_argument('--output', '-o', required=True)
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 결과를 배열로 출력 (예상: 객체)
    result = []
    for proc in data.get("processes", []):
        result.append({
            "id": proc["process_id"],
            "count": len(proc.get("resources", []))
        })

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print("[Success]")

if __name__ == "__main__":
    main()
'''

    # 정상 pre-process
    pre_process_code = '''def convert_bop_to_input(bop_json, params):
    import json
    return json.dumps(bop_json, ensure_ascii=False)
'''

    # 잘못된 post-process (객체 형식을 기대하지만 배열이 옴)
    broken_post_process = '''def apply_result_to_bop(bop_json, tool_output):
    import json
    import copy
    result = copy.deepcopy(bop_json)

    output = json.loads(tool_output)
    # 오류: output이 배열인데 객체처럼 접근
    for process_id, count in output["resource_counts"].items():
        print(f"Process {process_id}: {count} resources")

    return result
'''

    # 1. 실행 (실패 예상)
    print("\n[1단계] 잘못된 post-process로 실행 (실패 예상)")
    exec_result = tester.execute_tool(
        tool_name=tool_name,
        script_code=script_code,
        pre_process_code=pre_process_code,
        post_process_code=broken_post_process
    )

    if exec_result["success"]:
        print("  [예상 외] 실행 성공?!")
        return False

    print(f"  [예상대로 실패] {exec_result['error'][:80]}...")

    # 2. AI 개선 요청
    print("\n[2단계] AI에게 개선 요청")
    improvement = tester.improve_tool(
        tool_name=tool_name,
        description=description,
        pre_process_code=pre_process_code,
        post_process_code=broken_post_process,
        script_code=script_code,
        params_schema=[],
        execution_result=exec_result,
        feedback="post_process에서 오류가 발생합니다. 스크립트 출력 형식을 확인하고 post_process를 수정해주세요. 스크립트는 배열 형태로 결과를 출력합니다."
    )

    if not improvement:
        print("  [실패] AI 개선 응답 없음")
        return False

    # 3. 개선된 코드로 재실행
    print("\n[3단계] 개선된 코드로 재실행")
    new_pre = improvement.get("pre_process_code") or pre_process_code
    new_post = improvement.get("post_process_code") or broken_post_process
    new_script = improvement.get("script_code") or script_code

    retry_result = tester.execute_tool(
        tool_name=tool_name + "_fixed",
        script_code=new_script,
        pre_process_code=new_pre,
        post_process_code=new_post
    )

    if retry_result["success"]:
        print(f"  [성공] 개선 후 실행 성공!")
        print(f"  출력: {retry_result['tool_output'][:200]}...")

        # 산출물 저장
        test_dir = tester.artifact_dir / "test_case_2"
        test_dir.mkdir(parents=True, exist_ok=True)

        with open(test_dir / "original_post_process.py", 'w', encoding='utf-8') as f:
            f.write(broken_post_process)
        with open(test_dir / "fixed_post_process.py", 'w', encoding='utf-8') as f:
            f.write(new_post)
        with open(test_dir / "improvement_result.json", 'w', encoding='utf-8') as f:
            json.dump(improvement, f, ensure_ascii=False, indent=2)

        print(f"  [산출물 저장] {test_dir}")
        return True
    else:
        print(f"  [실패] 개선 후에도 실행 실패: {retry_result['error'][:80]}...")
        return False


def test_case_3_script_logic_error(tester: ImprovementTester):
    """
    테스트 케이스 3: 스크립트 로직 오류
    - 스크립트에 버그가 있어서 결과가 잘못됨
    - AI가 스크립트를 수정하는지 확인
    """
    print("\n" + "=" * 60)
    print("[테스트 3] 스크립트 로직 오류 수정")
    print("=" * 60)

    tool_name = "total_cycle_calculator"
    description = "모든 공정 인스턴스의 총 사이클 타임을 계산하는 도구"

    # 버그 있는 스크립트 (합계가 아니라 마지막 값만 반환)
    broken_script = '''"""Total Cycle Calculator - HAS BUG"""
import json
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', required=True)
    parser.add_argument('--output', '-o', required=True)
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 버그: total에 누적하지 않고 덮어씀
    total = 0
    for detail in data.get("process_details", []):
        total = detail.get("cycle_time_sec", 0)  # 버그! += 이어야 함

    result = {
        "total_cycle_time": total,
        "process_count": len(data.get("process_details", []))
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"[Success] Total: {total}")

if __name__ == "__main__":
    main()
'''

    pre_process_code = '''def convert_bop_to_input(bop_json, params):
    import json
    return json.dumps(bop_json, ensure_ascii=False)
'''

    post_process_code = '''def apply_result_to_bop(bop_json, tool_output):
    import json
    import copy
    return copy.deepcopy(bop_json)
'''

    # 1. 실행 (성공하지만 결과가 틀림)
    print("\n[1단계] 버그 있는 스크립트로 실행")
    exec_result = tester.execute_tool(
        tool_name=tool_name,
        script_code=broken_script,
        pre_process_code=pre_process_code,
        post_process_code=post_process_code
    )

    if not exec_result["success"]:
        print(f"  [실패] 예상치 못한 실행 오류: {exec_result['error']}")
        return False

    output = json.loads(exec_result["tool_output"])
    wrong_total = output.get("total_cycle_time", 0)
    print(f"  [실행 성공] 출력: {output}")
    print(f"  [문제] total_cycle_time이 {wrong_total}로 잘못 계산됨 (마지막 라인 값만)")

    # 2. AI 개선 요청
    # BOP 데이터: P001(45), P002-0(90), P002-1(95), P003(120), P004(60), P005(75)
    # 모든 process_details 합계 = 45 + 90 + 95 + 120 + 60 + 75 = 485
    expected_total = 45 + 90 + 95 + 120 + 60 + 75  # 485

    print("\n[2단계] AI에게 로직 수정 요청")
    improvement = tester.improve_tool(
        tool_name=tool_name,
        description=description,
        pre_process_code=pre_process_code,
        post_process_code=post_process_code,
        script_code=broken_script,
        params_schema=[],
        execution_result=exec_result,
        feedback=f"스크립트에 버그가 있습니다. total_cycle_time이 {wrong_total}로 나오는데, 모든 process_details의 cycle_time을 합산해야 합니다. += 연산자를 사용해야 하는데 = 연산자를 사용하고 있습니다."
    )

    if not improvement:
        print("  [실패] AI 개선 응답 없음")
        return False

    # 3. 개선된 코드로 재실행
    print("\n[3단계] 개선된 스크립트로 재실행")
    new_script = improvement.get("script_code") or broken_script

    retry_result = tester.execute_tool(
        tool_name=tool_name + "_fixed",
        script_code=new_script,
        pre_process_code=pre_process_code,
        post_process_code=post_process_code
    )

    if retry_result["success"]:
        new_output = json.loads(retry_result["tool_output"])
        actual_total = new_output.get("total_cycle_time", 0)
        print(f"  [실행 성공] 출력: {new_output}")

        # 결과 검증: 마지막 값(75)보다 훨씬 크면 누적이 된 것
        if actual_total > wrong_total * 2:
            print(f"  [성공] 누적 로직 수정됨: {wrong_total} → {actual_total}")

            # 산출물 저장
            test_dir = tester.artifact_dir / "test_case_3"
            test_dir.mkdir(parents=True, exist_ok=True)

            with open(test_dir / "original_script.py", 'w', encoding='utf-8') as f:
                f.write(broken_script)
            with open(test_dir / "fixed_script.py", 'w', encoding='utf-8') as f:
                f.write(new_script)
            with open(test_dir / "improvement_result.json", 'w', encoding='utf-8') as f:
                json.dump(improvement, f, ensure_ascii=False, indent=2)

            print(f"  [산출물 저장] {test_dir}")
            return True
        else:
            print(f"  [실패] 누적 로직이 수정되지 않음: {actual_total}")
            return False
    else:
        print(f"  [실패] 재실행 오류: {retry_result['error'][:80]}...")
        return False


def main():
    """메인 테스트 실행"""
    bop_path = Path(__file__).parent / "test_bop_bicycle.json"

    if not bop_path.exists():
        print(f"[오류] BOP 데이터 파일이 없습니다: {bop_path}")
        return

    try:
        tester = ImprovementTester(str(bop_path))
    except ValueError as e:
        print(f"[오류] {e}")
        return

    print("\n" + "=" * 60)
    print("AI 개선 기능 테스트")
    print("=" * 60)

    results = {}

    # 테스트 케이스 실행
    test_cases = [
        ("테스트 1: 잘못된 어댑터 코드", test_case_1_broken_adapter),
        ("테스트 2: 잘못된 출력 형식", test_case_2_wrong_output_format),
        ("테스트 3: 스크립트 로직 오류", test_case_3_script_logic_error),
    ]

    for name, test_func in test_cases:
        try:
            results[name] = test_func(tester)
        except Exception as e:
            print(f"\n[예외 발생] {name}: {e}")
            results[name] = False

    # 최종 결과
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    for name, success in results.items():
        status = "[성공]" if success else "[실패]"
        print(f"  {status} {name}")

    print(f"\n총 {total_count}개 테스트 중 {success_count}개 성공")


if __name__ == "__main__":
    main()
