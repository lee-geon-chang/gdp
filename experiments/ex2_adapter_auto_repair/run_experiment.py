#!/usr/bin/env python
"""
Ex2 Benchmark: Tool Adapter Auto-Repair Performance
Gen-DT (Generative Digital-twin Prototyper) Research
Target: IEEE CASE 2026

Measures Pass@1 (Baseline) vs Pass@k (Auto-Repair) for LLM-generated adapters.
Adapter generation uses gemini-2.5-flash.

Experiment scale: 10 tools x 8 BOPs x 4 conditions (k=0,1,2,3) = 320 runs

Usage:
    # Quick test: 1 tool, 1 bop, k=0
    python ex2/run_experiment.py --test

    # Full experiment: 320 runs
    python ex2/run_experiment.py

    # Baseline only (80 runs)
    python ex2/run_experiment.py --k 0

    # Specific tools
    python ex2/run_experiment.py --tools bottleneck_analyzer line_balance_calculator

    # Specific BOPs
    python ex2/run_experiment.py --bops bicycle minimal

    # Specific model
    python ex2/run_experiment.py --model gemini-2.5-flash
"""

import asyncio
import json
import os
import sys
import time
import copy
import subprocess
import argparse
import inspect
import traceback
import builtins
import math
import tempfile
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# Project setup
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.tools.synthesizer import synthesize_adapter, repair_adapter
from app.tools.tool_models import (
    ToolMetadata, AdapterCode, InputSchema, OutputSchema,
    ExecutionType, ParamDef,
)
from ex2.validators import validate_tool_output, ValidationResult

# ============================================================
# Configuration
# ============================================================

DEFAULT_MODEL = "gemini-2.5-flash"
SUBPROCESS_TIMEOUT_SEC = 60
K_VALUES = [0, 1, 2, 3]

# Delay between LLM API calls (seconds)
API_DELAY_SEC = 2.0

# Tool difficulty mapping
TOOL_DIFFICULTY = {
    "bottleneck_analyzer": "Easy",
    "line_balance_calculator": "Easy",
    "equipment_utilization": "Medium",
    "process_distance_analyzer": "Medium",
    "worker_skill_matcher": "Medium",
    "material_flow_analyzer": "Medium",
    "safety_zone_checker": "Medium",
    "takt_time_optimizer": "Hard",
    "energy_estimator": "Hard",
    "layout_compactor": "Hard",
}

log = logging.getLogger("ex2")


# ============================================================
# Standalone Executor (no registry dependency)
# ============================================================

def _safe_builtins():
    """Restricted builtins for adapter code execution."""
    allowed = [
        'abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter',
        'float', 'format', 'int', 'isinstance', 'len', 'list', 'map',
        'max', 'min', 'next', 'print', 'range', 'round', 'set', 'sorted',
        'str', 'sum', 'tuple', 'type', 'zip', 'None', 'True', 'False',
        'KeyError', 'ValueError', 'TypeError', 'IndexError', 'Exception',
    ]
    safe = {}
    for name in allowed:
        if hasattr(builtins, name):
            safe[name] = getattr(builtins, name)

    original_import = builtins.__import__
    safe_modules = {'json', 'csv', 'io', 'math', 'statistics', 'copy', 're'}

    def restricted_import(name, *args, **kwargs):
        if name not in safe_modules:
            raise ImportError(f"'{name}' module is not allowed in adapter code.")
        return original_import(name, *args, **kwargs)

    safe['__import__'] = restricted_import
    return safe


def _run_preprocessor(code: str, bop_data: dict, params: Optional[Dict[str, Any]] = None) -> str:
    """Execute pre-processor adapter code."""
    namespace = {"__builtins__": _safe_builtins()}
    import json as json_mod
    import csv as csv_mod
    import io as io_mod
    import math as math_mod
    namespace["json"] = json_mod
    namespace["csv"] = csv_mod
    namespace["io"] = io_mod
    namespace["math"] = math_mod
    exec(code, namespace)
    fn = namespace.get("convert_bop_to_input")
    if not fn:
        raise ValueError("Pre-processor missing 'convert_bop_to_input' function.")

    sig = inspect.signature(fn)
    if len(sig.parameters) < 2:
        raise ValueError("convert_bop_to_input must accept 2 parameters (bop_json, params).")

    result = fn(bop_data, params or {})
    if not isinstance(result, str):
        result = json.dumps(result, ensure_ascii=False)
    return result


def _run_postprocessor(code: str, bop_data: dict, tool_output: str) -> dict:
    """Execute post-processor adapter code."""
    namespace = {"__builtins__": _safe_builtins()}
    import json as json_mod
    import csv as csv_mod
    import io as io_mod
    import math as math_mod
    namespace["json"] = json_mod
    namespace["csv"] = csv_mod
    namespace["io"] = io_mod
    namespace["math"] = math_mod
    exec(code, namespace)
    fn = namespace.get("apply_result_to_bop")
    if not fn:
        raise ValueError("Post-processor missing 'apply_result_to_bop' function.")

    parsed_output = tool_output
    if isinstance(tool_output, str):
        try:
            parsed_output = json_mod.loads(tool_output)
        except json_mod.JSONDecodeError:
            parsed_output = {"raw_output": tool_output}

    result = fn(bop_data, parsed_output)
    if not isinstance(result, dict):
        raise ValueError("Post-processor must return a dict.")
    return result


def _capture_error_info(e: Exception) -> Dict[str, Any]:
    """Extract detailed error info from exception."""
    return {
        "type": type(e).__name__,
        "message": str(e),
        "traceback": traceback.format_exc(),
    }


async def run_single_execution(
    script_path: Path,
    pre_code: str,
    post_code: str,
    bop_data: dict,
    params: Optional[Dict[str, Any]],
    max_repair: int = 0,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """
    Execute a single tool with adapter, with optional auto-repair.

    Returns:
        {
            "success": bool,
            "error_type": str or None,
            "error_phase": str or None,  # "pre_process", "subprocess", "post_process"
            "repair_attempts_used": int,
            "execution_time_sec": float,
        }
    """
    start_time = time.time()
    bop_data = copy.deepcopy(bop_data)

    current_pre_code = pre_code
    current_post_code = post_code
    repair_attempts_used = 0

    work_dir = Path(tempfile.mkdtemp(prefix="ex2_"))

    try:
        # === Phase 1: Pre-processor ===
        tool_input = None
        pre_error = None

        for attempt in range(max_repair + 1):
            try:
                tool_input = _run_preprocessor(current_pre_code, bop_data, params)
                break
            except Exception as e:
                pre_error = e
                if attempt < max_repair:
                    repair_attempts_used += 1
                    error_info = _capture_error_info(e)
                    bop_json_str = json.dumps(bop_data, ensure_ascii=False, indent=2)

                    fixed_code = await repair_adapter(
                        failed_function="pre_process",
                        failed_code=current_pre_code,
                        error_info=error_info,
                        input_data=bop_json_str,
                        model=model,
                    )

                    if fixed_code:
                        current_pre_code = fixed_code
                    else:
                        break

        if tool_input is None:
            return {
                "success": False,
                "error_type": type(pre_error).__name__ if pre_error else "Unknown",
                "error_phase": "pre_process",
                "error_message": str(pre_error) if pre_error else "",
                "repair_attempts_used": repair_attempts_used,
                "execution_time_sec": round(time.time() - start_time, 3),
            }

        # === Phase 2: Subprocess ===
        input_file = work_dir / "input_data.json"
        output_file = work_dir / "output_data.json"

        with open(input_file, "w", encoding="utf-8") as f:
            f.write(tool_input)

        cmd = [sys.executable, str(script_path), "--input", str(input_file), "--output", str(output_file)]
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": "",
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        }

        try:
            result = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT_SEC,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error_type": "TimeoutError",
                "error_phase": "subprocess",
                "error_message": f"Script timed out after {SUBPROCESS_TIMEOUT_SEC}s",
                "repair_attempts_used": repair_attempts_used,
                "execution_time_sec": round(time.time() - start_time, 3),
            }

        if result.returncode != 0:
            return {
                "success": False,
                "error_type": "SubprocessError",
                "error_phase": "subprocess",
                "error_message": (result.stderr or result.stdout or "")[:500],
                "repair_attempts_used": repair_attempts_used,
                "execution_time_sec": round(time.time() - start_time, 3),
            }

        # Read tool output
        tool_output = None
        if output_file.exists():
            with open(output_file, "r", encoding="utf-8") as f:
                tool_output = f.read()

        if not tool_output:
            tool_output = result.stdout

        if not tool_output:
            return {
                "success": False,
                "error_type": "NoOutput",
                "error_phase": "subprocess",
                "error_message": "Script produced no output",
                "repair_attempts_used": repair_attempts_used,
                "execution_time_sec": round(time.time() - start_time, 3),
            }

        # Parse tool output as JSON for validation
        tool_output_parsed = None
        try:
            tool_output_parsed = json.loads(tool_output)
        except (json.JSONDecodeError, TypeError):
            tool_output_parsed = {"raw_output": tool_output}

        # Parse tool input as JSON for validation
        tool_input_parsed = None
        try:
            tool_input_parsed = json.loads(tool_input)
        except (json.JSONDecodeError, TypeError):
            tool_input_parsed = {"raw_input": tool_input}

        # === Phase 3: Post-processor ===
        post_error = None

        for attempt in range(max_repair + 1):
            try:
                updated_bop = _run_postprocessor(current_post_code, bop_data, tool_output)
                # Verify JSON serializable
                json.dumps(updated_bop)
                return {
                    "success": True,
                    "error_type": None,
                    "error_phase": None,
                    "error_message": None,
                    "repair_attempts_used": repair_attempts_used,
                    "execution_time_sec": round(time.time() - start_time, 3),
                    "tool_output": tool_output_parsed,
                    "tool_input": tool_input_parsed,
                }
            except Exception as e:
                post_error = e
                if attempt < max_repair:
                    repair_attempts_used += 1
                    error_info = _capture_error_info(e)

                    fixed_code = await repair_adapter(
                        failed_function="post_process",
                        failed_code=current_post_code,
                        error_info=error_info,
                        input_data=tool_output[:5000] if tool_output else "",
                        model=model,
                    )

                    if fixed_code:
                        current_post_code = fixed_code
                    else:
                        break

        return {
            "success": False,
            "error_type": type(post_error).__name__ if post_error else "Unknown",
            "error_phase": "post_process",
            "error_message": str(post_error) if post_error else "",
            "repair_attempts_used": repair_attempts_used,
            "execution_time_sec": round(time.time() - start_time, 3),
        }

    except Exception as e:
        return {
            "success": False,
            "error_type": type(e).__name__,
            "error_phase": "unknown",
            "error_message": str(e),
            "repair_attempts_used": repair_attempts_used,
            "execution_time_sec": round(time.time() - start_time, 3),
        }
    finally:
        try:
            shutil.rmtree(work_dir)
        except Exception:
            pass


# ============================================================
# Tool & BOP Loading
# ============================================================

def load_tool_meta(tool_name: str) -> Tuple[ToolMetadata, str]:
    """Load tool metadata and source code."""
    tools_dir = SCRIPT_DIR / "tools"
    meta_path = tools_dir / f"{tool_name}_meta.json"
    script_path = tools_dir / f"{tool_name}.py"

    if not meta_path.exists():
        raise FileNotFoundError(f"Meta file not found: {meta_path}")
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta_dict = json.load(f)

    with open(script_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    # Normalize params_schema: some metas use "name" instead of "key"
    def _normalize_param(p: dict) -> dict:
        d = dict(p)
        if "key" not in d and "name" in d:
            d["key"] = d.pop("name")
        if "label" not in d:
            d["label"] = d.get("key", "")
        return d

    # Normalize schema fields: if fields are dicts, extract just the names
    def _normalize_schema(schema_dict: dict) -> dict:
        s = dict(schema_dict)
        if "fields" in s and isinstance(s["fields"], list):
            normalized = []
            for f in s["fields"]:
                if isinstance(f, dict):
                    normalized.append(f.get("name", str(f)))
                else:
                    normalized.append(str(f))
            s["fields"] = normalized
        return s

    input_schema_dict = _normalize_schema(meta_dict.get("input_schema", {"type": "json", "description": ""}))
    output_schema_dict = _normalize_schema(meta_dict.get("output_schema", {"type": "json", "description": ""}))

    # Build ToolMetadata from JSON
    metadata = ToolMetadata(
        tool_id=meta_dict.get("tool_id", tool_name),
        tool_name=meta_dict.get("tool_name", tool_name),
        description=meta_dict.get("description", ""),
        execution_type=ExecutionType(meta_dict.get("execution_type", "python")),
        file_name=meta_dict.get("file_name", f"{tool_name}.py"),
        input_schema=InputSchema(**input_schema_dict),
        output_schema=OutputSchema(**output_schema_dict),
        params_schema=[ParamDef(**_normalize_param(p)) for p in meta_dict.get("params_schema", [])] if meta_dict.get("params_schema") else None,
        example_input=meta_dict.get("example_input"),
        example_output=meta_dict.get("example_output"),
    )

    return metadata, source_code


def load_bop(bop_name: str) -> dict:
    """Load a BOP scenario."""
    bop_path = SCRIPT_DIR / "bop_scenarios" / f"{bop_name}.json"
    if not bop_path.exists():
        raise FileNotFoundError(f"BOP file not found: {bop_path}")

    with open(bop_path, "r", encoding="utf-8") as f:
        return json.load(f)


def discover_tools() -> List[str]:
    """Discover available tool names from meta files."""
    tools_dir = SCRIPT_DIR / "tools"
    tools = []
    for meta_file in sorted(tools_dir.glob("*_meta.json")):
        tool_name = meta_file.stem.replace("_meta", "")
        script_file = tools_dir / f"{tool_name}.py"
        if script_file.exists():
            tools.append(tool_name)
    return tools


def discover_bops() -> List[str]:
    """Discover available BOP scenario names."""
    bop_dir = SCRIPT_DIR / "bop_scenarios"
    return sorted([f.stem for f in bop_dir.glob("*.json")])


# ============================================================
# Adapter Generation (with caching)
# ============================================================

async def generate_adapter(
    tool_name: str,
    metadata: ToolMetadata,
    source_code: str,
    model: str = DEFAULT_MODEL,
) -> Tuple[Optional[AdapterCode], float]:
    """
    Generate adapter code for a tool.

    Returns:
        (AdapterCode or None, generation_time_sec)
    """
    start = time.time()
    try:
        adapter = await synthesize_adapter(metadata, source_code, model=model)
        elapsed = round(time.time() - start, 3)
        return adapter, elapsed
    except Exception as e:
        elapsed = round(time.time() - start, 3)
        print(f"    [ERROR] Adapter generation failed for {tool_name}: {e}")
        return None, elapsed


# ============================================================
# Main Experiment
# ============================================================

async def run_experiment(
    tools: List[str],
    bops: List[str],
    k_values: List[int],
    model: str = DEFAULT_MODEL,
    verbose: bool = False,
) -> List[dict]:
    """Run the full experiment."""
    all_results = []
    tools_dir = SCRIPT_DIR / "tools"

    total_combinations = len(tools) * len(bops) * len(k_values)
    current = 0

    for tool_name in tools:
        print(f"\n{'='*60}")
        print(f"  Tool: {tool_name} ({TOOL_DIFFICULTY.get(tool_name, '?')})")
        print(f"{'='*60}")

        # Load tool
        try:
            metadata, source_code = load_tool_meta(tool_name)
        except Exception as e:
            print(f"  [ERROR] Failed to load tool: {e}")
            for bop_name in bops:
                for k in k_values:
                    current += 1
                    all_results.append({
                        "tool": tool_name,
                        "tool_difficulty": TOOL_DIFFICULTY.get(tool_name, "Unknown"),
                        "bop": bop_name,
                        "k": k,
                        "success": False,
                        "error_type": "LoadError",
                        "error_phase": "setup",
                        "error_message": str(e),
                        "repair_attempts_used": 0,
                        "execution_time_sec": 0,
                        "adapter_gen_time_sec": 0,
                    })
            continue

        script_path = tools_dir / f"{tool_name}.py"

        # Generate adapter once per tool
        print(f"  Generating adapter (model={model})...", end="", flush=True)
        adapter, gen_time = await generate_adapter(tool_name, metadata, source_code, model)

        if adapter is None:
            print(f" FAILED ({gen_time}s)")
            for bop_name in bops:
                for k in k_values:
                    current += 1
                    all_results.append({
                        "tool": tool_name,
                        "tool_difficulty": TOOL_DIFFICULTY.get(tool_name, "Unknown"),
                        "bop": bop_name,
                        "k": k,
                        "success": False,
                        "error_type": "AdapterGenError",
                        "error_phase": "adapter_generation",
                        "error_message": "Adapter generation failed",
                        "repair_attempts_used": 0,
                        "execution_time_sec": 0,
                        "adapter_gen_time_sec": gen_time,
                    })
            await asyncio.sleep(API_DELAY_SEC)
            continue

        print(f" OK ({gen_time}s)")

        if verbose:
            print(f"  Pre-process code: {len(adapter.pre_process_code)} bytes")
            print(f"  Post-process code: {len(adapter.post_process_code)} bytes")

        # Save original adapter
        adapter_save_dir = SCRIPT_DIR / "results" / "adapters"
        adapter_save_dir.mkdir(parents=True, exist_ok=True)
        adapter_file = adapter_save_dir / f"{tool_name}_adapter.json"
        with open(adapter_file, "w", encoding="utf-8") as f:
            json.dump({
                "tool_id": tool_name,
                "pre_process_code": adapter.pre_process_code,
                "post_process_code": adapter.post_process_code,
                "model": model,
                "generated_at": datetime.now().isoformat(),
            }, f, indent=2, ensure_ascii=False)

        await asyncio.sleep(API_DELAY_SEC)

        # Run for each BOP and k value
        for bop_name in bops:
            try:
                bop_data = load_bop(bop_name)
            except Exception as e:
                print(f"  [ERROR] Failed to load BOP {bop_name}: {e}")
                for k in k_values:
                    current += 1
                    all_results.append({
                        "tool": tool_name,
                        "tool_difficulty": TOOL_DIFFICULTY.get(tool_name, "Unknown"),
                        "bop": bop_name,
                        "k": k,
                        "success": False,
                        "error_type": "BOPLoadError",
                        "error_phase": "setup",
                        "error_message": str(e),
                        "repair_attempts_used": 0,
                        "execution_time_sec": 0,
                        "adapter_gen_time_sec": gen_time,
                    })
                continue

            for k in k_values:
                current += 1
                label = f"  [{current}/{total_combinations}] {bop_name} k={k}"
                print(f"{label:<40}", end="", flush=True)

                exec_result = await run_single_execution(
                    script_path=script_path,
                    pre_code=adapter.pre_process_code,
                    post_code=adapter.post_process_code,
                    bop_data=bop_data,
                    params={},
                    max_repair=k,
                    model=model,
                )

                # Run property-based validation on successful executions
                validation = None
                if exec_result["success"]:
                    tool_output_data = exec_result.get("tool_output", {})
                    tool_input_data = exec_result.get("tool_input", {})
                    validation = validate_tool_output(
                        tool_name, tool_output_data, bop_data, tool_input_data
                    )

                record = {
                    "tool": tool_name,
                    "tool_difficulty": TOOL_DIFFICULTY.get(tool_name, "Unknown"),
                    "bop": bop_name,
                    "k": k,
                    "success": exec_result["success"],
                    "error_type": exec_result.get("error_type"),
                    "error_phase": exec_result.get("error_phase"),
                    "error_message": exec_result.get("error_message"),
                    "repair_attempts_used": exec_result.get("repair_attempts_used", 0),
                    "execution_time_sec": exec_result.get("execution_time_sec", 0),
                    "adapter_gen_time_sec": gen_time,
                    # Validation results
                    "output_correct": validation.passed if validation else None,
                    "validation_score": validation.score if validation else None,
                    "validation_checks_total": validation.checks_total if validation else 0,
                    "validation_checks_passed": validation.checks_passed if validation else 0,
                    "validation_errors": validation.errors if validation else [],
                }
                all_results.append(record)

                # Print result
                if exec_result["success"]:
                    repairs = exec_result.get("repair_attempts_used", 0)
                    repair_info = f" (repairs={repairs})" if repairs > 0 else ""
                    if validation and validation.passed:
                        val_info = f" V:{validation.checks_passed}/{validation.checks_total}"
                        print(f" PASS{repair_info}{val_info}  [{exec_result['execution_time_sec']}s]")
                    elif validation:
                        val_info = f" V:{validation.checks_passed}/{validation.checks_total}"
                        print(f" PASS{repair_info} OUTPUT_WRONG{val_info}  [{exec_result['execution_time_sec']}s]")
                        if verbose:
                            for err in validation.errors[:3]:
                                print(f"      {err}")
                    else:
                        print(f" PASS{repair_info}  [{exec_result['execution_time_sec']}s]")
                else:
                    phase = exec_result.get("error_phase", "?")
                    etype = exec_result.get("error_type", "?")
                    print(f" FAIL [{phase}:{etype}]  [{exec_result['execution_time_sec']}s]")

                # Delay between LLM calls only if repair was attempted
                if k > 0 and exec_result.get("repair_attempts_used", 0) > 0:
                    await asyncio.sleep(API_DELAY_SEC)

    return all_results


# ============================================================
# Results Analysis & Printing
# ============================================================

def print_summary(results: List[dict]):
    """Print experiment summary tables."""
    if not results:
        print("No results to summarize.")
        return

    # === Pass@k by k ===
    print("\n" + "=" * 70)
    print("  PASS RATE BY k")
    print("=" * 70)
    print(f"  {'k':<5} {'Total':<8} {'Pass':<8} {'Fail':<8} {'Pass Rate':<12}")
    print("-" * 70)

    for k in sorted(set(r["k"] for r in results)):
        k_results = [r for r in results if r["k"] == k]
        total = len(k_results)
        passed = sum(1 for r in k_results if r["success"])
        failed = total - passed
        rate = passed / total if total > 0 else 0
        print(f"  {k:<5} {total:<8} {passed:<8} {failed:<8} {rate:<12.1%}")

    # === Pass@k by difficulty ===
    print("\n" + "=" * 70)
    print("  PASS RATE BY DIFFICULTY x k")
    print("=" * 70)

    difficulties = ["Easy", "Medium", "Hard"]
    header = f"  {'Difficulty':<12}"
    for k in sorted(set(r["k"] for r in results)):
        header += f" {'k=' + str(k):<10}"
    print(header)
    print("-" * 70)

    for diff in difficulties:
        row = f"  {diff:<12}"
        for k in sorted(set(r["k"] for r in results)):
            dk_results = [r for r in results if r["tool_difficulty"] == diff and r["k"] == k]
            if dk_results:
                passed = sum(1 for r in dk_results if r["success"])
                rate = passed / len(dk_results)
                row += f" {passed}/{len(dk_results)} ({rate:.0%}){'':<2}"
            else:
                row += f" {'N/A':<10}"
        print(row)

    # === Error type distribution ===
    print("\n" + "=" * 70)
    print("  ERROR TYPE DISTRIBUTION (k=0 baseline)")
    print("=" * 70)

    baseline_fails = [r for r in results if r["k"] == 0 and not r["success"]]
    if baseline_fails:
        error_counts: Dict[str, int] = {}
        for r in baseline_fails:
            et = r.get("error_type", "Unknown")
            error_counts[et] = error_counts.get(et, 0) + 1

        print(f"  {'Error Type':<25} {'Count':<8} {'%':<8}")
        print("-" * 50)
        total_fails = len(baseline_fails)
        for et, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            pct = count / total_fails * 100
            print(f"  {et:<25} {count:<8} {pct:<8.1f}")
    else:
        print("  No failures at k=0 (all passed baseline!)")

    # === Error phase distribution ===
    print("\n" + "=" * 70)
    print("  ERROR PHASE DISTRIBUTION (k=0 baseline)")
    print("=" * 70)

    if baseline_fails:
        phase_counts: Dict[str, int] = {}
        for r in baseline_fails:
            ep = r.get("error_phase", "unknown")
            phase_counts[ep] = phase_counts.get(ep, 0) + 1

        print(f"  {'Phase':<20} {'Count':<8} {'%':<8}")
        print("-" * 50)
        for ep, count in sorted(phase_counts.items(), key=lambda x: -x[1]):
            pct = count / len(baseline_fails) * 100
            print(f"  {ep:<20} {count:<8} {pct:<8.1f}")

    # === Repair convergence ===
    print("\n" + "=" * 70)
    print("  REPAIR CONVERGENCE (k>0 runs that succeeded)")
    print("=" * 70)

    repair_successes = [r for r in results if r["k"] > 0 and r["success"] and r["repair_attempts_used"] > 0]
    if repair_successes:
        avg_repairs = sum(r["repair_attempts_used"] for r in repair_successes) / len(repair_successes)
        print(f"  Successful repairs: {len(repair_successes)}")
        print(f"  Avg repair attempts for success: {avg_repairs:.2f}")

        # Distribution
        for attempts in range(1, max(r["repair_attempts_used"] for r in repair_successes) + 1):
            count = sum(1 for r in repair_successes if r["repair_attempts_used"] == attempts)
            if count > 0:
                print(f"    {attempts} attempt(s): {count} cases")
    else:
        print("  No successful repairs found.")

    # === Per-tool results ===
    print("\n" + "=" * 70)
    print("  PER-TOOL RESULTS")
    print("=" * 70)

    tool_names = sorted(set(r["tool"] for r in results))
    header = f"  {'Tool':<28} {'Diff':<8}"
    for k in sorted(set(r["k"] for r in results)):
        header += f" {'k=' + str(k):<8}"
    print(header)
    print("-" * 70)

    for tool in tool_names:
        diff = TOOL_DIFFICULTY.get(tool, "?")
        row = f"  {tool:<28} {diff:<8}"
        for k in sorted(set(r["k"] for r in results)):
            tk_results = [r for r in results if r["tool"] == tool and r["k"] == k]
            if tk_results:
                passed = sum(1 for r in tk_results if r["success"])
                total = len(tk_results)
                row += f" {passed}/{total:<6}"
            else:
                row += f" {'N/A':<8}"
        print(row)

    # === Output Correctness (Validation) ===
    validated = [r for r in results if r.get("output_correct") is not None]
    if validated:
        print("\n" + "=" * 70)
        print("  OUTPUT CORRECTNESS (Property-based Validation)")
        print("=" * 70)

        # Overall by k
        print(f"\n  {'k':<5} {'Exec Pass':<12} {'Output OK':<12} {'Output Wrong':<14} {'Correct Rate':<12}")
        print("-" * 70)
        for k in sorted(set(r["k"] for r in results)):
            k_exec_pass = [r for r in results if r["k"] == k and r["success"]]
            k_valid = [r for r in k_exec_pass if r.get("output_correct") is not None]
            k_correct = sum(1 for r in k_valid if r["output_correct"])
            k_wrong = len(k_valid) - k_correct
            rate = k_correct / len(k_valid) * 100 if k_valid else 0
            print(f"  {k:<5} {len(k_exec_pass):<12} {k_correct:<12} {k_wrong:<14} {rate:.1f}%")

        # Per-tool validation
        print(f"\n  {'Tool':<28} {'Diff':<8} {'Avg Score':<12} {'Errors'}")
        print("-" * 70)
        for tool in tool_names:
            diff = TOOL_DIFFICULTY.get(tool, "?")
            tool_validated = [r for r in validated if r["tool"] == tool]
            if tool_validated:
                avg_score = sum(r.get("validation_score", 0) for r in tool_validated) / len(tool_validated)
                total_errors = sum(1 for r in tool_validated if not r["output_correct"])
                # Collect unique error messages
                err_msgs = set()
                for r in tool_validated:
                    for e in r.get("validation_errors", []):
                        err_msgs.add(e)
                err_preview = "; ".join(list(err_msgs)[:2]) if err_msgs else "-"
                if len(err_preview) > 50:
                    err_preview = err_preview[:50] + "..."
                print(f"  {tool:<28} {diff:<8} {avg_score:<12.1%} {err_preview}")
            else:
                print(f"  {tool:<28} {diff:<8} {'N/A':<12} -")


def save_results(results: List[dict], model: str):
    """Save results to JSON files."""
    results_dir = SCRIPT_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Detailed results
    detail_file = results_dir / f"ex2_detail_{timestamp}.json"
    with open(detail_file, "w", encoding="utf-8") as f:
        json.dump({
            "experiment": "Ex2 Tool Adapter Auto-Repair Benchmark",
            "timestamp": datetime.now().isoformat(),
            "config": {
                "model": model,
                "k_values": sorted(set(r["k"] for r in results)),
                "tools": sorted(set(r["tool"] for r in results)),
                "bops": sorted(set(r["bop"] for r in results)),
                "subprocess_timeout_sec": SUBPROCESS_TIMEOUT_SEC,
            },
            "results": results,
        }, f, indent=2, ensure_ascii=False)

    # Summary
    summary = {
        "experiment": "Ex2 Tool Adapter Auto-Repair Benchmark",
        "timestamp": datetime.now().isoformat(),
        "model": model,
    }

    # Pass rate by k
    pass_by_k = {}
    for k in sorted(set(r["k"] for r in results)):
        k_results = [r for r in results if r["k"] == k]
        total = len(k_results)
        passed = sum(1 for r in k_results if r["success"])
        pass_by_k[f"k={k}"] = {
            "total": total,
            "passed": passed,
            "pass_rate": round(passed / total, 4) if total > 0 else 0,
        }
    summary["pass_by_k"] = pass_by_k

    # Pass rate by difficulty x k
    pass_by_diff = {}
    for diff in ["Easy", "Medium", "Hard"]:
        pass_by_diff[diff] = {}
        for k in sorted(set(r["k"] for r in results)):
            dk = [r for r in results if r["tool_difficulty"] == diff and r["k"] == k]
            if dk:
                passed = sum(1 for r in dk if r["success"])
                pass_by_diff[diff][f"k={k}"] = round(passed / len(dk), 4)
    summary["pass_by_difficulty"] = pass_by_diff

    # Error distribution at k=0
    baseline_fails = [r for r in results if r["k"] == 0 and not r["success"]]
    error_dist = {}
    for r in baseline_fails:
        et = r.get("error_type", "Unknown")
        error_dist[et] = error_dist.get(et, 0) + 1
    summary["baseline_error_distribution"] = error_dist

    # Validation summary
    validated = [r for r in results if r.get("output_correct") is not None]
    if validated:
        val_summary = {}
        for k in sorted(set(r["k"] for r in results)):
            k_validated = [r for r in validated if r["k"] == k]
            if k_validated:
                correct = sum(1 for r in k_validated if r["output_correct"])
                val_summary[f"k={k}"] = {
                    "validated": len(k_validated),
                    "correct": correct,
                    "correct_rate": round(correct / len(k_validated), 4),
                    "avg_score": round(sum(r.get("validation_score", 0) for r in k_validated) / len(k_validated), 4),
                }
        summary["validation_by_k"] = val_summary

        # Per-tool validation
        tool_val = {}
        for tool in sorted(set(r["tool"] for r in validated)):
            t_validated = [r for r in validated if r["tool"] == tool]
            correct = sum(1 for r in t_validated if r["output_correct"])
            avg_score = sum(r.get("validation_score", 0) for r in t_validated) / len(t_validated)
            err_msgs = []
            for r in t_validated:
                err_msgs.extend(r.get("validation_errors", []))
            tool_val[tool] = {
                "validated": len(t_validated),
                "correct": correct,
                "correct_rate": round(correct / len(t_validated), 4),
                "avg_score": round(avg_score, 4),
                "unique_errors": list(set(err_msgs))[:10],
            }
        summary["validation_by_tool"] = tool_val

    summary_file = results_dir / f"ex2_summary_{timestamp}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n  Detail: {detail_file}")
    print(f"  Summary: {summary_file}")

    return detail_file, summary_file


# ============================================================
# CLI Entry Point
# ============================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Ex2 Benchmark: Tool Adapter Auto-Repair Performance"
    )
    parser.add_argument("--test", action="store_true",
                        help="Quick test: 1 tool, 1 bop, k=0")
    parser.add_argument("--tools", nargs="*",
                        help="Tool names to test (default: all)")
    parser.add_argument("--bops", nargs="*",
                        help="BOP scenario names to test (default: all)")
    parser.add_argument("--k", type=int, nargs="*",
                        help="k values to test (default: 0 1 2 3)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help=f"LLM model for adapter generation (default: {DEFAULT_MODEL})")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    print("=" * 70)
    print("  Ex2 Benchmark: Tool Adapter Auto-Repair")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Model: {args.model}")
    print("=" * 70)

    # Discover available tools and BOPs
    available_tools = discover_tools()
    available_bops = discover_bops()

    if not available_tools:
        print("ERROR: No tools found in ex2/tools/")
        sys.exit(1)
    if not available_bops:
        print("ERROR: No BOP scenarios found in ex2/bop_scenarios/")
        sys.exit(1)

    # Select tools
    if args.test:
        tools = [available_tools[0]]
        bops = [available_bops[0]]
        k_values = [0]
    else:
        tools = args.tools if args.tools else available_tools
        bops = args.bops if args.bops else available_bops
        k_values = args.k if args.k is not None else K_VALUES

    # Validate selections
    for t in tools:
        if t not in available_tools:
            print(f"ERROR: Tool '{t}' not found. Available: {available_tools}")
            sys.exit(1)
    for b in bops:
        if b not in available_bops:
            print(f"ERROR: BOP '{b}' not found. Available: {available_bops}")
            sys.exit(1)

    total = len(tools) * len(bops) * len(k_values)
    print(f"\n  Tools ({len(tools)}): {', '.join(tools)}")
    print(f"  BOPs ({len(bops)}): {', '.join(bops)}")
    print(f"  k values: {k_values}")
    print(f"  Total runs: {total}")
    print()

    # Run experiment
    results = await run_experiment(
        tools=tools,
        bops=bops,
        k_values=k_values,
        model=args.model,
        verbose=args.verbose,
    )

    # Print summary
    print_summary(results)

    # Save results
    save_results(results, args.model)

    print(f"\n  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    # Fix Windows asyncio event loop issue
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
