"""
도구 등록 파이프라인 통합 테스트

이 스크립트는 전체 도구 생성 → 분석 → 어댑터 생성 → 실행 → 개선 파이프라인을 테스트합니다.
"""

import os
import sys
import json
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# 앱 모듈 임포트
from app.tools.tool_prompts import (
    TOOL_ANALYSIS_PROMPT,
    SCRIPT_GENERATION_PROMPT,
    ADAPTER_SYNTHESIS_PROMPT,
    TOOL_IMPROVEMENT_PROMPT
)


@dataclass
class TestResult:
    """테스트 결과 저장"""
    tool_name: str
    phase: str  # generate, analyze, synthesize, execute, improve
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ToolPipelineTester:
    """도구 파이프라인 테스터"""

    def __init__(self, bop_data_path: str):
        self.bop_data_path = Path(bop_data_path)
        self.bop_data = self._load_bop_data()
        self.results: List[TestResult] = []
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY")

        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

        # 임시 작업 디렉토리
        self.work_dir = Path(tempfile.mkdtemp(prefix="tool_test_"))
        print(f"[테스트] 작업 디렉토리: {self.work_dir}")

    def _load_bop_data(self) -> Dict[str, Any]:
        """BOP 데이터 로드"""
        with open(self.bop_data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _call_gemini(self, prompt: str, response_json: bool = True) -> Dict[str, Any]:
        """Gemini API 호출"""
        import requests
        import time

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}"

        config = {"temperature": 0.3}
        if response_json:
            config["responseMimeType"] = "application/json"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": config,
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=90,
                )

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
                    lines = text.split('\n')
                    lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    text = '\n'.join(lines)

                data = json.loads(text)

                # 배열 응답 처리
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]

                return data

            except requests.exceptions.HTTPError as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                raise
            except json.JSONDecodeError as e:
                print(f"  [JSON 파싱 오류] {str(e)[:100]}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                raise

        raise Exception("API 호출 실패")

    def generate_script(self, description: str) -> Optional[Dict[str, Any]]:
        """1단계: 스크립트 생성"""
        print(f"\n[1단계] 스크립트 생성: {description[:50]}...")

        try:
            prompt = SCRIPT_GENERATION_PROMPT.format(user_description=description)
            result = self._call_gemini(prompt)

            if "script_code" not in result:
                raise ValueError("script_code가 응답에 없습니다.")

            tool_name = result.get("tool_name", "generated_tool")
            print(f"  [성공] 도구명: {tool_name}")

            self.results.append(TestResult(
                tool_name=tool_name,
                phase="generate",
                success=True,
                message="스크립트 생성 완료",
                data=result
            ))

            return result

        except Exception as e:
            print(f"  [실패] {str(e)}")
            self.results.append(TestResult(
                tool_name="unknown",
                phase="generate",
                success=False,
                message="스크립트 생성 실패",
                error=str(e)
            ))
            return None

    def analyze_script(self, script_code: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """2단계: 스크립트 분석"""
        print(f"\n[2단계] 스크립트 분석: {tool_name}")

        try:
            prompt = TOOL_ANALYSIS_PROMPT.format(
                source_code=script_code,
                sample_input_section=""
            )
            result = self._call_gemini(prompt)

            # 필수 필드 검증
            for field in ["tool_name", "description", "input_schema", "output_schema"]:
                if field not in result:
                    raise ValueError(f"'{field}' 필드 누락")

            print(f"  [성공] 입력타입: {result['input_schema'].get('type')}, 출력타입: {result['output_schema'].get('type')}")
            print(f"  [파라미터] {len(result.get('params_schema', []))}개")

            self.results.append(TestResult(
                tool_name=tool_name,
                phase="analyze",
                success=True,
                message="스크립트 분석 완료",
                data=result
            ))

            return result

        except Exception as e:
            print(f"  [실패] {str(e)}")
            self.results.append(TestResult(
                tool_name=tool_name,
                phase="analyze",
                success=False,
                message="스크립트 분석 실패",
                error=str(e)
            ))
            return None

    def synthesize_adapter(self, tool_name: str, description: str,
                          input_schema: Dict, output_schema: Dict,
                          script_code: str, params_schema: List) -> Optional[Dict[str, Any]]:
        """3단계: 어댑터 코드 생성"""
        print(f"\n[3단계] 어댑터 생성: {tool_name}")

        try:
            # params_schema 섹션
            params_section = ""
            if params_schema:
                params_section = (
                    "## User-Provided Parameters (params dict)\n"
                    f"```json\n{json.dumps(params_schema, indent=2, ensure_ascii=False)}\n```\n"
                    "Use these values in convert_bop_to_input(bop_json, params)"
                )

            prompt = ADAPTER_SYNTHESIS_PROMPT.format(
                tool_name=tool_name,
                tool_description=description,
                input_schema_json=json.dumps(input_schema, indent=2, ensure_ascii=False),
                output_schema_json=json.dumps(output_schema, indent=2, ensure_ascii=False),
                source_code_section=f"## Tool Source Code\n```python\n{script_code}\n```",
                params_schema_section=params_section
            )

            result = self._call_gemini(prompt)

            if "pre_process_code" not in result or "post_process_code" not in result:
                raise ValueError("어댑터 코드가 응답에 없습니다.")

            print(f"  [성공] pre_process: {len(result['pre_process_code'])}자, post_process: {len(result['post_process_code'])}자")

            self.results.append(TestResult(
                tool_name=tool_name,
                phase="synthesize",
                success=True,
                message="어댑터 생성 완료",
                data=result
            ))

            return result

        except Exception as e:
            print(f"  [실패] {str(e)}")
            self.results.append(TestResult(
                tool_name=tool_name,
                phase="synthesize",
                success=False,
                message="어댑터 생성 실패",
                error=str(e)
            ))
            return None

    def execute_tool(self, tool_name: str, script_code: str,
                    pre_process_code: str, post_process_code: str,
                    params: Dict[str, Any] = None) -> Dict[str, Any]:
        """4단계: 도구 실행"""
        print(f"\n[4단계] 도구 실행: {tool_name}")

        params = params or {}
        execution_result = {
            "success": False,
            "tool_input": None,
            "tool_output": None,
            "updated_bop": None,
            "stdout": "",
            "stderr": "",
            "error": None
        }

        try:
            # 1. Pre-process: BOP → 도구 입력
            print("  [1] Pre-process 실행...")
            pre_process_func = self._compile_function(pre_process_code, "convert_bop_to_input")
            tool_input = pre_process_func(self.bop_data, params)
            execution_result["tool_input"] = tool_input
            print(f"    → 입력 데이터 생성 완료 ({len(str(tool_input))}자)")

            # 2. 스크립트 실행
            print("  [2] 스크립트 실행...")
            script_path = self.work_dir / f"{tool_name}.py"
            input_path = self.work_dir / "input.json"
            output_path = self.work_dir / "output.json"

            # 스크립트 저장
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_code)

            # 입력 파일 저장
            with open(input_path, 'w', encoding='utf-8') as f:
                if isinstance(tool_input, str):
                    f.write(tool_input)
                else:
                    json.dump(tool_input, f, ensure_ascii=False, indent=2)

            # 스크립트 실행
            result = subprocess.run(
                [sys.executable, str(script_path), "--input", str(input_path), "--output", str(output_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.work_dir)
            )

            execution_result["stdout"] = result.stdout
            execution_result["stderr"] = result.stderr

            if result.returncode != 0:
                raise RuntimeError(f"스크립트 실행 실패 (코드: {result.returncode})\n{result.stderr}")

            print(f"    → 스크립트 실행 완료")

            # 3. 출력 파일 읽기
            if output_path.exists():
                with open(output_path, 'r', encoding='utf-8') as f:
                    tool_output = f.read()
                execution_result["tool_output"] = tool_output
                print(f"    → 출력 데이터 ({len(tool_output)}자)")
            else:
                raise FileNotFoundError("출력 파일이 생성되지 않았습니다.")

            # 4. Post-process: 도구 출력 → BOP 업데이트
            print("  [3] Post-process 실행...")
            post_process_func = self._compile_function(post_process_code, "apply_result_to_bop")
            updated_bop = post_process_func(self.bop_data, tool_output)
            execution_result["updated_bop"] = updated_bop
            print(f"    → BOP 업데이트 완료")

            execution_result["success"] = True
            print(f"  [성공] 도구 실행 완료")

            self.results.append(TestResult(
                tool_name=tool_name,
                phase="execute",
                success=True,
                message="도구 실행 완료",
                data=execution_result
            ))

        except Exception as e:
            import traceback
            execution_result["error"] = str(e)
            execution_result["stderr"] += f"\n{traceback.format_exc()}"
            print(f"  [실패] {str(e)[:100]}")

            self.results.append(TestResult(
                tool_name=tool_name,
                phase="execute",
                success=False,
                message="도구 실행 실패",
                error=str(e),
                data=execution_result
            ))

        return execution_result

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

    def improve_tool(self, tool_name: str, description: str,
                    pre_process_code: str, post_process_code: str,
                    script_code: str, params_schema: List,
                    execution_result: Dict[str, Any],
                    feedback: str) -> Optional[Dict[str, Any]]:
        """5단계: AI 개선"""
        print(f"\n[5단계] AI 개선: {tool_name}")
        print(f"  피드백: {feedback[:50]}...")

        try:
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

            result = self._call_gemini(prompt, response_json=False)

            # 텍스트 응답인 경우 JSON 파싱 시도
            if isinstance(result, str):
                result = json.loads(result)

            print(f"  [성공] 변경사항: {result.get('changes_summary', [])}")

            self.results.append(TestResult(
                tool_name=tool_name,
                phase="improve",
                success=True,
                message="AI 개선 완료",
                data=result
            ))

            return result

        except Exception as e:
            print(f"  [실패] {str(e)}")
            self.results.append(TestResult(
                tool_name=tool_name,
                phase="improve",
                success=False,
                message="AI 개선 실패",
                error=str(e)
            ))
            return None

    def save_artifacts(self, tool_name: str, script_code: str,
                      pre_process_code: str, post_process_code: str,
                      tool_output: str):
        """테스트 산출물 저장"""
        artifact_dir = Path(__file__).parent / "artifacts" / tool_name
        artifact_dir.mkdir(parents=True, exist_ok=True)

        # 스크립트 저장
        with open(artifact_dir / "script.py", 'w', encoding='utf-8') as f:
            f.write(script_code)

        # 어댑터 저장
        with open(artifact_dir / "adapter_pre.py", 'w', encoding='utf-8') as f:
            f.write(pre_process_code)
        with open(artifact_dir / "adapter_post.py", 'w', encoding='utf-8') as f:
            f.write(post_process_code)

        # 출력 저장
        with open(artifact_dir / "output.json", 'w', encoding='utf-8') as f:
            f.write(tool_output)

        print(f"\n  [산출물 저장] {artifact_dir}")

    def validate_result(self, tool_name: str, tool_output: str,
                       updated_bop: Dict[str, Any]) -> Dict[str, Any]:
        """결과 검증"""
        print(f"\n[검증] {tool_name} 결과 분석")

        validation = {
            "tool_name": tool_name,
            "output_valid": False,
            "bop_changed": False,
            "changes": [],
            "issues": []
        }

        try:
            # 출력 파싱 시도
            output_data = json.loads(tool_output)
            validation["output_valid"] = True
            validation["output_keys"] = list(output_data.keys()) if isinstance(output_data, dict) else "array"
            print(f"  출력 형식: {validation['output_keys']}")
        except:
            validation["issues"].append("출력이 유효한 JSON이 아닙니다.")
            print(f"  [경고] 출력 JSON 파싱 실패")

        # BOP 변경 감지
        if updated_bop:
            # 간단한 변경 감지 (전체 비교는 복잡하므로 일부만)
            original_process_count = len(self.bop_data.get("processes", []))
            updated_process_count = len(updated_bop.get("processes", []))

            original_obstacle_count = len(self.bop_data.get("obstacles", []))
            updated_obstacle_count = len(updated_bop.get("obstacles", []))

            if original_process_count != updated_process_count:
                validation["bop_changed"] = True
                validation["changes"].append(f"공정 수: {original_process_count} → {updated_process_count}")

            if original_obstacle_count != updated_obstacle_count:
                validation["bop_changed"] = True
                validation["changes"].append(f"장애물 수: {original_obstacle_count} → {updated_obstacle_count}")

            # 위치 변경 감지
            for i, proc in enumerate(updated_bop.get("processes", [])):
                if i < len(self.bop_data.get("processes", [])):
                    orig_proc = self.bop_data["processes"][i]
                    orig_loc = orig_proc.get("parallel_lines", [{}])[0].get("location", {})
                    new_loc = proc.get("parallel_lines", [{}])[0].get("location", {})

                    if orig_loc != new_loc:
                        validation["bop_changed"] = True
                        validation["changes"].append(f"공정 {proc.get('process_id')} 위치 변경")

            if validation["bop_changed"]:
                print(f"  BOP 변경 감지: {validation['changes']}")
            else:
                print(f"  BOP 변경 없음 (정보성 도구일 수 있음)")

        return validation

    def run_full_pipeline(self, description: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """전체 파이프라인 실행"""
        print("\n" + "=" * 60)
        print(f"[파이프라인 시작] {description[:50]}...")
        print("=" * 60)

        pipeline_result = {
            "description": description,
            "success": False,
            "phases": {}
        }

        # 1. 스크립트 생성
        gen_result = self.generate_script(description)
        if not gen_result:
            return pipeline_result

        tool_name = gen_result.get("tool_name", "unknown")
        script_code = gen_result.get("script_code", "")
        suggested_params = gen_result.get("suggested_params", [])

        pipeline_result["phases"]["generate"] = gen_result

        # 2. 스크립트 분석
        analysis = self.analyze_script(script_code, tool_name)
        if not analysis:
            return pipeline_result

        pipeline_result["phases"]["analyze"] = analysis

        # 분석 결과에서 params_schema 가져오기 (suggested_params와 병합)
        params_schema = analysis.get("params_schema") or suggested_params

        # 3. 어댑터 생성
        adapter = self.synthesize_adapter(
            tool_name=tool_name,
            description=analysis.get("description", ""),
            input_schema=analysis.get("input_schema", {}),
            output_schema=analysis.get("output_schema", {}),
            script_code=script_code,
            params_schema=params_schema
        )
        if not adapter:
            return pipeline_result

        pipeline_result["phases"]["synthesize"] = adapter

        # 4. 도구 실행
        # params가 없으면 params_schema의 default 값 사용
        if params is None:
            params = {}
            for p in params_schema:
                if isinstance(p, dict) and "key" in p and "default" in p:
                    params[p["key"]] = p["default"]

        exec_result = self.execute_tool(
            tool_name=tool_name,
            script_code=script_code,
            pre_process_code=adapter.get("pre_process_code", ""),
            post_process_code=adapter.get("post_process_code", ""),
            params=params
        )

        pipeline_result["phases"]["execute"] = exec_result

        # 5. 결과 검증 및 산출물 저장
        if exec_result.get("success"):
            validation = self.validate_result(
                tool_name=tool_name,
                tool_output=exec_result.get("tool_output", ""),
                updated_bop=exec_result.get("updated_bop")
            )
            pipeline_result["validation"] = validation
            pipeline_result["success"] = True

            # 산출물 저장
            self.save_artifacts(
                tool_name=tool_name,
                script_code=script_code,
                pre_process_code=adapter.get("pre_process_code", ""),
                post_process_code=adapter.get("post_process_code", ""),
                tool_output=exec_result.get("tool_output", "")
            )

            # 출력 내용 미리보기
            print("\n  [출력 미리보기]")
            output_preview = exec_result.get("tool_output", "")[:500]
            print(f"  {output_preview}...")
            if len(exec_result.get("tool_output", "")) > 500:
                print(f"  (총 {len(exec_result.get('tool_output', ''))}자)")
        else:
            # 실패 시 개선 시도
            print("\n[자동 개선 시도]")
            improvement = self.improve_tool(
                tool_name=tool_name,
                description=analysis.get("description", ""),
                pre_process_code=adapter.get("pre_process_code", ""),
                post_process_code=adapter.get("post_process_code", ""),
                script_code=script_code,
                params_schema=params_schema,
                execution_result=exec_result,
                feedback="실행 중 오류가 발생했습니다. 오류를 분석하고 수정해주세요."
            )

            if improvement:
                pipeline_result["phases"]["improve"] = improvement

                # 개선된 코드로 재실행
                new_pre = improvement.get("pre_process_code") or adapter.get("pre_process_code", "")
                new_post = improvement.get("post_process_code") or adapter.get("post_process_code", "")
                new_script = improvement.get("script_code") or script_code

                print("\n[개선된 코드로 재실행]")
                retry_result = self.execute_tool(
                    tool_name=tool_name + "_improved",
                    script_code=new_script,
                    pre_process_code=new_pre,
                    post_process_code=new_post,
                    params=params
                )

                pipeline_result["phases"]["retry"] = retry_result

                if retry_result.get("success"):
                    validation = self.validate_result(
                        tool_name=tool_name,
                        tool_output=retry_result.get("tool_output", ""),
                        updated_bop=retry_result.get("updated_bop")
                    )
                    pipeline_result["validation"] = validation
                    pipeline_result["success"] = True

        return pipeline_result

    def print_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("테스트 결과 요약")
        print("=" * 60)

        success_count = sum(1 for r in self.results if r.success)
        total_count = len(self.results)

        print(f"\n총 {total_count}개 단계 중 {success_count}개 성공")
        print()

        for r in self.results:
            status = "[성공]" if r.success else "[실패]"
            print(f"  {status} {r.tool_name} / {r.phase}: {r.message}")
            if r.error:
                print(f"         오류: {r.error[:80]}...")


# === 테스트 기능 정의 ===

TEST_FEATURES = [
    {
        "name": "병목 공정 분석",
        "description": """
        제조 라인의 병목 공정을 분석하는 도구를 만들어주세요.

        요구사항:
        - 각 공정의 cycle_time_sec을 분석
        - 목표 UPH를 달성하기 위한 택트 타임 계산
        - 병목이 되는 공정(cycle_time이 가장 긴 공정) 식별
        - 병목 해소를 위한 필요 병렬 라인 수 계산

        출력:
        - 공정별 cycle_time 목록
        - 목표 택트 타임
        - 병목 공정 ID와 이름
        - 개선 제안 (필요 병렬 수)
        """,
        "params": {}
    },
    {
        "name": "공정 간 이동 거리 분석",
        "description": """
        공정 간 물류 이동 거리를 분석하는 도구를 만들어주세요.

        요구사항:
        - 연속된 공정 간의 거리 계산 (predecessor → successor)
        - 각 공정의 location 좌표 사용
        - 총 이동 거리 합계
        - 가장 먼 거리의 공정 쌍 식별

        출력:
        - 공정 쌍별 이동 거리
        - 총 이동 거리
        - 최대 이동 거리 구간
        - 거리 최적화 제안 (선택적)
        """,
        "params": {}
    },
    {
        "name": "작업자 스킬 기반 배치 분석",
        "description": """
        작업자 스킬 레벨과 공정 난이도를 분석하는 도구를 만들어주세요.

        요구사항:
        - 각 공정에 배치된 작업자 정보 추출
        - 작업자의 skill_level (Junior, Mid, Senior) 확인
        - 공정의 cycle_time을 기반으로 복잡도 추정 (긴 시간 = 복잡)
        - 스킬 미스매치 감지 (복잡한 공정에 Junior 배치 등)

        출력:
        - 공정별 작업자 배치 현황
        - 스킬 적합도 점수
        - 미스매치 경고
        - 재배치 제안
        """,
        "params": {}
    }
]


async def main():
    """메인 테스트 실행"""
    # BOP 데이터 경로
    bop_path = Path(__file__).parent / "test_bop_bicycle.json"

    if not bop_path.exists():
        print(f"[오류] BOP 데이터 파일이 없습니다: {bop_path}")
        return

    # 테스터 초기화
    try:
        tester = ToolPipelineTester(str(bop_path))
    except ValueError as e:
        print(f"[오류] {e}")
        return

    # 테스트할 기능 선택
    print("\n사용 가능한 테스트 기능:")
    for i, feature in enumerate(TEST_FEATURES):
        print(f"  {i + 1}. {feature['name']}")
    print(f"  {len(TEST_FEATURES) + 1}. 전체 테스트")

    try:
        choice = input("\n선택 (번호 입력): ").strip()
        choice = int(choice)
    except:
        choice = 1  # 기본값

    if choice == len(TEST_FEATURES) + 1:
        # 전체 테스트
        features_to_test = TEST_FEATURES
    elif 1 <= choice <= len(TEST_FEATURES):
        features_to_test = [TEST_FEATURES[choice - 1]]
    else:
        print("잘못된 선택입니다.")
        return

    # 테스트 실행
    all_results = []
    for feature in features_to_test:
        result = tester.run_full_pipeline(
            description=feature["description"],
            params=feature.get("params")
        )
        all_results.append({
            "feature": feature["name"],
            "result": result
        })

    # 결과 요약
    tester.print_summary()

    # 결과 저장
    results_path = tester.work_dir / "test_results.json"
    with open(results_path, 'w', encoding='utf-8') as f:
        # 간단한 직렬화 (dataclass 제외)
        serializable = []
        for r in tester.results:
            serializable.append({
                "tool_name": r.tool_name,
                "phase": r.phase,
                "success": r.success,
                "message": r.message,
                "error": r.error
            })
        json.dump(serializable, f, ensure_ascii=False, indent=2)

    print(f"\n[결과 저장] {results_path}")


if __name__ == "__main__":
    asyncio.run(main())
