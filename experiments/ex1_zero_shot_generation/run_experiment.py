#!/usr/bin/env python
"""
Ex1 v2 Benchmark: Zero-shot BOP Generation Performance Measurement
Gen-DT (Generative Digital-twin Prototyper) Research
Target: IEEE CASE 2026

Dataset: ex1_v2 GT (all steps verified against accessible HTML references)

Models:
  - Gemini 2.5 Flash    (cheap, test first)
  - GPT-5 Mini           (cheap, test first)
  - Claude Sonnet 4.5    (mid)
  - Gemini 2.5 Pro       (expensive)
  - GPT-5.2              (expensive)

Usage:
    # Quick test with cheap models on 1 product
    python ex1_v2/run_experiment.py --test

    # Run all models, all products
    python ex1_v2/run_experiment.py

    # Specific models/products
    python ex1_v2/run_experiment.py --models gemini-2.5-flash gpt-5-mini
    python ex1_v2/run_experiment.py --products P01 P03
"""

import asyncio
import json
import os
import sys
import time
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from difflib import SequenceMatcher

# Project setup
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.prompts import SYSTEM_PROMPT


# ============================================================
# Configuration
# ============================================================

# Models ordered: cheap first, expensive last
EXPERIMENT_MODELS = [
    {"id": "gemini-2.5-flash",        "provider": "gemini",    "display": "Gemini 2.5 Flash",  "tier": "cheap"},
    {"id": "gpt-5-mini",              "provider": "openai",    "display": "GPT-5 Mini",        "tier": "cheap"},
    {"id": "claude-sonnet-4-5-20250929", "provider": "anthropic", "display": "Claude Sonnet 4.5", "tier": "mid"},
    {"id": "gemini-2.5-pro",          "provider": "gemini",    "display": "Gemini 2.5 Pro",    "tier": "expensive"},
    {"id": "gpt-5.2",                 "provider": "openai",    "display": "GPT-5.2",           "tier": "expensive"},
]

# Cheap models for quick testing
CHEAP_MODELS = [m for m in EXPERIMENT_MODELS if m["tier"] == "cheap"]

# Experiment protocol: Temperature = 0.0 for reproducibility
TEMPERATURE = 0.0

# Fuzzy matching threshold for step comparison
SIMILARITY_THRESHOLD = 0.4

# Delay between API calls (seconds) to respect rate limits
API_DELAY_SEC = 1.5


# ============================================================
# API Call Functions (Temperature = 0.0)
# ============================================================

async def call_gemini(api_key: str, model: str, prompt: str) -> str:
    """Call Gemini API with temperature=0.0 via REST."""
    import requests

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": TEMPERATURE},
    }

    response = requests.post(url, headers=headers, json=payload, timeout=180)
    response.raise_for_status()

    result = response.json()
    return result["candidates"][0]["content"]["parts"][0]["text"].strip()


async def call_openai(api_key: str, model: str, prompt: str) -> str:
    """Call OpenAI API with temperature=0.0 via SDK."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)

    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    # Try with temperature first; some models may not support it
    try:
        kwargs["temperature"] = TEMPERATURE
        response = await client.chat.completions.create(**kwargs)
    except Exception as e:
        if "temperature" in str(e).lower():
            del kwargs["temperature"]
            response = await client.chat.completions.create(**kwargs)
        else:
            raise

    return response.choices[0].message.content.strip()


async def call_anthropic(api_key: str, model: str, prompt: str) -> str:
    """Call Anthropic API with temperature=0.0 via SDK."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)

    response = await client.messages.create(
        model=model,
        max_tokens=8192,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text.strip()


async def call_model(model_config: dict, prompt: str) -> Tuple[Optional[str], Optional[str]]:
    """Call a model and return (response_text, error)."""
    provider = model_config["provider"]
    model_id = model_config["id"]

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY")
        if not api_key:
            return None, "GEMINI_API_KEY not configured"
        text = await call_gemini(api_key, model_id, prompt)
        return text, None

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None, "OPENAI_API_KEY not configured"
        text = await call_openai(api_key, model_id, prompt)
        return text, None

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None, "ANTHROPIC_API_KEY not configured"
        text = await call_anthropic(api_key, model_id, prompt)
        return text, None

    return None, f"Unknown provider: {provider}"


# ============================================================
# BOP Response Parsing
# ============================================================

def parse_bop_response(response_text: str) -> Optional[dict]:
    """
    Parse LLM response to extract BOP JSON.
    Expects the project's BOP format with 'processes' array.
    """
    if not response_text:
        return None

    def _is_valid_bop(data):
        """Check if data looks like a valid BOP (supports flat and legacy formats)."""
        if not isinstance(data, dict):
            return False
        has_processes = "processes" in data and isinstance(data["processes"], list) and len(data["processes"]) > 0
        has_details = "process_details" in data and isinstance(data["process_details"], list) and len(data["process_details"]) > 0
        return has_processes or has_details

    # 1) Direct JSON parse
    try:
        data = json.loads(response_text)
        if _is_valid_bop(data):
            return data
    except json.JSONDecodeError:
        pass

    # 2) Extract from markdown code block (handle various whitespace patterns)
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", response_text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            if _is_valid_bop(data):
                return data
        except json.JSONDecodeError:
            pass

    # 3) Find outermost JSON object
    start = response_text.find("{")
    end = response_text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(response_text[start : end + 1])
            if _is_valid_bop(data):
                return data
        except json.JSONDecodeError:
            pass

    return None


def extract_process_names(bop_data: dict) -> List[str]:
    """
    Extract ordered process names from BOP data.
    Supports both flat BOP (process_details[].name) and legacy (processes[].name).
    Follows predecessor/successor ordering if available, otherwise uses list order.
    """
    processes = bop_data.get("processes", [])
    if not processes:
        return []

    # Build name lookup: prefer process_details[].name (flat BOP), fallback to processes[].name
    detail_names = {}
    for d in bop_data.get("process_details", []):
        pid = d.get("process_id")
        if pid and pid not in detail_names:
            detail_names[pid] = d.get("name", pid)

    def get_name(proc):
        pid = proc.get("process_id", "unknown")
        # 1) process_details (flat BOP)
        if pid in detail_names:
            return detail_names[pid]
        # 2) processes[].name (legacy BOP)
        return proc.get("name", pid)

    # Try to order by predecessor chain
    proc_map = {p["process_id"]: p for p in processes if "process_id" in p}

    # Find root processes (no predecessors)
    roots = []
    for p in processes:
        preds = p.get("predecessor_ids", [])
        if not preds or all(pid not in proc_map for pid in preds):
            roots.append(p["process_id"])

    if roots and len(proc_map) == len(processes):
        # BFS ordering from roots
        ordered = []
        visited = set()
        queue = list(roots)
        while queue:
            pid = queue.pop(0)
            if pid in visited or pid not in proc_map:
                continue
            visited.add(pid)
            ordered.append(get_name(proc_map[pid]))
            for succ in proc_map[pid].get("successor_ids", []):
                if succ not in visited:
                    queue.append(succ)

        # Add any unvisited processes
        for p in processes:
            if p["process_id"] not in visited:
                ordered.append(get_name(p))

        return ordered

    # Fallback: use list order
    return [get_name(p) for p in processes]


def extract_equipment_names(bop_data: dict) -> List[str]:
    """Extract equipment names from BOP data."""
    equipments = bop_data.get("equipments", [])
    return [eq.get("name", eq.get("equipment_id", "")) for eq in equipments]


# ============================================================
# Evaluation
# ============================================================

def normalize_step(step: str) -> str:
    """Normalize a BOP step for comparison."""
    s = step.lower().strip()
    s = re.sub(r"\([^)]*\)", "", s)             # remove parenthesized content
    s = re.sub(r"[^a-zA-Z0-9가-힣\s]", "", s)  # keep letters, digits, Korean, spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_keywords(step: str) -> set:
    """Extract keywords from a BOP step (Korean + English)."""
    words = set()
    words.update(re.findall(r"[가-힣]{2,}", step))
    words.update(w.lower() for w in re.findall(r"[a-zA-Z]{3,}", step))
    return words


def step_similarity(gen_step: str, gt_step: str) -> float:
    """Calculate similarity between a generated step and a ground truth step."""
    gen_n = normalize_step(gen_step)
    gt_n = normalize_step(gt_step)

    # Exact match
    if gen_n == gt_n:
        return 1.0

    # Substring containment
    if gen_n and gt_n and (gen_n in gt_n or gt_n in gen_n):
        return 0.9

    # Keyword overlap (Jaccard)
    gen_kw = extract_keywords(gen_step)
    gt_kw = extract_keywords(gt_step)
    if gen_kw and gt_kw:
        intersection = gen_kw & gt_kw
        union = gen_kw | gt_kw
        jaccard = len(intersection) / len(union) if union else 0
        if jaccard > 0:
            seq = SequenceMatcher(None, gen_n, gt_n).ratio()
            return max(jaccard, seq)

    # Character-level similarity
    return SequenceMatcher(None, gen_n, gt_n).ratio()


def evaluate_bop(
    generated_steps: List[str],
    gt_steps_kr: List[str],
    gt_steps_en: List[str],
) -> dict:
    """
    Evaluate generated BOP process names against ground truth.

    Returns:
        n: number of matched steps
        M: total ground truth steps
        accuracy: n / M
        sequence_match: pairwise ordering consistency of matched steps
        matches: detailed match info
    """
    M = len(gt_steps_kr)

    if not generated_steps:
        return {"n": 0, "M": M, "accuracy": 0.0, "sequence_match": 0.0, "matches": []}

    # Greedy best-match: for each GT step, find best unmatched generated step
    matches = []
    used_gen = set()

    for gt_idx in range(M):
        best_sim = 0.0
        best_gen_idx = -1
        best_gen_step = ""

        for gen_idx, gen_step in enumerate(generated_steps):
            if gen_idx in used_gen:
                continue

            sim_kr = step_similarity(gen_step, gt_steps_kr[gt_idx])
            sim_en = step_similarity(gen_step, gt_steps_en[gt_idx]) if gt_idx < len(gt_steps_en) else 0
            sim = max(sim_kr, sim_en)

            if sim > best_sim:
                best_sim = sim
                best_gen_idx = gen_idx
                best_gen_step = gen_step

        if best_sim >= SIMILARITY_THRESHOLD and best_gen_idx >= 0:
            matches.append({
                "gt_idx": gt_idx,
                "gen_idx": best_gen_idx,
                "gt_step": gt_steps_kr[gt_idx],
                "gen_step": best_gen_step,
                "similarity": round(best_sim, 3),
            })
            used_gen.add(best_gen_idx)

    n = len(matches)
    accuracy = n / M if M > 0 else 0.0

    # Sequence match: ratio of correctly-ordered pairs among matched steps
    if n >= 2:
        gen_indices = [m["gen_idx"] for m in matches]
        ordered_pairs = 0
        total_pairs = 0
        for i in range(len(gen_indices)):
            for j in range(i + 1, len(gen_indices)):
                total_pairs += 1
                if gen_indices[i] < gen_indices[j]:
                    ordered_pairs += 1
        sequence_match = ordered_pairs / total_pairs if total_pairs > 0 else 1.0
    elif n == 1:
        sequence_match = 1.0
    else:
        sequence_match = 0.0

    return {
        "n": n,
        "M": M,
        "accuracy": round(accuracy, 4),
        "sequence_match": round(sequence_match, 4),
        "generated_count": len(generated_steps),
        "matches": matches,
    }


# ============================================================
# Main Experiment
# ============================================================

async def run_single(model_config: dict, product_kr: dict, product_en: dict) -> dict:
    """Run a single model x product experiment using the project's BOP generation prompt."""
    # Build prompt: SYSTEM_PROMPT + user request (same as the actual app)
    user_request = f"{product_kr['product_name']} 제조 라인"
    full_prompt = f"{SYSTEM_PROMPT}\n\nUser request: {user_request}"

    result = {
        "product_id": product_kr["product_id"],
        "product_name": product_kr["product_name"],
        "model": model_config["display"],
        "model_id": model_config["id"],
        "success": False,
        "generated_processes": None,
        "generated_equipments": None,
        "process_count": None,
        "evaluation": None,
        "error": None,
        "latency_sec": None,
    }

    start = time.time()
    try:
        response_text, err = await call_model(model_config, full_prompt)
        result["latency_sec"] = round(time.time() - start, 2)

        if err:
            result["error"] = err
            return result

        # Parse BOP JSON
        bop_data = parse_bop_response(response_text)
        if not bop_data:
            result["error"] = f"BOP parse failed. Raw (first 300 chars): {(response_text or '')[:300]}"
            return result

        # Extract process names in order
        process_names = extract_process_names(bop_data)
        equipment_names = extract_equipment_names(bop_data)

        result["generated_processes"] = process_names
        result["generated_equipments"] = equipment_names
        result["process_count"] = len(process_names)

        # Evaluate: compare process names against ground truth bop_steps
        result["evaluation"] = evaluate_bop(
            process_names,
            product_kr["bop_steps"],
            product_en["bop_steps"],
        )
        result["success"] = True

    except Exception as e:
        result["latency_sec"] = round(time.time() - start, 2)
        result["error"] = f"{type(e).__name__}: {str(e)}"

    return result


async def run_quick_test(products_kr, products_en):
    """
    Quick test: run cheap models on first product only.
    Returns True if at least one model succeeds.
    """
    print("=" * 80)
    print(" QUICK TEST: cheap models x 1 product")
    print("=" * 80)

    test_product = products_kr[0]
    test_en = products_en.get(test_product["product_id"], test_product)

    success_count = 0
    for model_config in CHEAP_MODELS:
        pid = test_product["product_id"]
        pname = test_product["product_name"]
        label = f"  [{model_config['display']}] {pid} {pname[:20]}"
        print(f"{label:<50}", end="", flush=True)

        result = await run_single(model_config, test_product, test_en)

        if result["success"]:
            ev = result["evaluation"]
            print(
                f" => {ev['n']:>2}/{ev['M']:<2} ({ev['accuracy']:>5.1%})  "
                f"Seq:{ev['sequence_match']:>5.1%}  "
                f"Gen:{ev.get('generated_count', '?')} procs  "
                f"[{result['latency_sec']}s]"
            )
            success_count += 1
        else:
            err_short = (result.get("error") or "unknown")[:60]
            print(f" => FAIL  [{result.get('latency_sec', '?')}s]  {err_short}")

        await asyncio.sleep(API_DELAY_SEC)

    print()
    if success_count > 0:
        print(f" Quick test PASSED ({success_count}/{len(CHEAP_MODELS)} models OK)")
    else:
        print(" Quick test FAILED (no models succeeded)")
    print()

    return success_count > 0


async def main():
    parser = argparse.ArgumentParser(description="Ex1 v2 BOP Zero-shot Benchmark")
    parser.add_argument("--models", nargs="*", help="Model IDs to test (default: all 4)")
    parser.add_argument("--products", nargs="*", help="Product IDs to test (default: all 10)")
    parser.add_argument("--test", action="store_true", help="Quick test: cheap models x 1 product only")
    parser.add_argument("--cheap-only", action="store_true", help="Run only cheap models (Flash, Mini)")
    args = parser.parse_args()

    print("=" * 80)
    print(" Ex1 v2 Benchmark: Zero-shot BOP Generation")
    print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Dataset: ex1_v2 (GT v2.0, verified HTML references)")
    print(f" Temperature: {TEMPERATURE}")
    print(f" Similarity Threshold: {SIMILARITY_THRESHOLD}")
    print(f" Prompt: app/prompts.py SYSTEM_PROMPT + user request")
    print("=" * 80)

    # Load ground truth
    with open(SCRIPT_DIR / "ex1_gt_kr.json", "r", encoding="utf-8") as f:
        gt_kr = json.load(f)
    with open(SCRIPT_DIR / "ex1_gt_en.json", "r", encoding="utf-8") as f:
        gt_en = json.load(f)

    products_kr = gt_kr["ground_truth_bop"]
    products_en = {p["product_id"]: p for p in gt_en["ground_truth_bop"]}

    # Quick test mode
    if args.test:
        ok = await run_quick_test(products_kr, products_en)
        if not ok:
            print(" Aborting. Fix API keys or model access before running full experiment.")
            sys.exit(1)
        print(" To run full experiment: python ex1_v2/run_experiment.py")
        return

    # Filter products if specified
    if args.products:
        products_kr = [p for p in products_kr if p["product_id"] in args.products]

    # Select models
    if args.models:
        models = [m for m in EXPERIMENT_MODELS if m["id"] in args.models]
    elif args.cheap_only:
        models = CHEAP_MODELS
    else:
        models = EXPERIMENT_MODELS

    print(f"\n Products: {len(products_kr)}")
    for p in products_kr:
        print(f"   {p['product_id']}: {p['product_name']} (GT steps: {len(p['bop_steps'])})")

    print(f"\n Models: {len(models)}")
    for m in models:
        tier_tag = f" [{m['tier']}]" if "tier" in m else ""
        print(f"   {m['display']} ({m['id']}){tier_tag}")

    total_calls = len(models) * len(products_kr)
    print(f"\n Total API calls: {total_calls}")
    print()

    # Run experiments
    all_results = []

    for mi, model_config in enumerate(models):
        print(f"[{mi+1}/{len(models)}] {model_config['display']} ({model_config.get('tier', '')})")
        print("-" * 60)

        for pi, product in enumerate(products_kr):
            pid = product["product_id"]
            pname = product["product_name"]
            en_product = products_en.get(pid, product)

            label = f"  {pid} {pname[:22]}"
            print(f"{label:<30}", end="", flush=True)

            result = await run_single(model_config, product, en_product)
            all_results.append(result)

            if result["success"]:
                ev = result["evaluation"]
                gen_cnt = ev.get("generated_count", "?")
                print(
                    f" => {ev['n']:>2}/{ev['M']:<2} ({ev['accuracy']:>5.1%})  "
                    f"Seq:{ev['sequence_match']:>5.1%}  "
                    f"Gen:{gen_cnt} procs  "
                    f"[{result['latency_sec']}s]"
                )
            else:
                err_short = (result.get("error") or "unknown")[:50]
                print(f" => FAIL  [{result.get('latency_sec', '?')}s]  {err_short}")

            await asyncio.sleep(API_DELAY_SEC)

        print()

    # ============================
    # Save results
    # ============================
    results_dir = SCRIPT_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Detailed results
    detail_file = results_dir / f"ex1v2_detail_{timestamp}.json"
    with open(detail_file, "w", encoding="utf-8") as f:
        json.dump({
            "experiment": "Ex1 v2 Zero-shot BOP Generation",
            "dataset_version": "2.0",
            "timestamp": datetime.now().isoformat(),
            "config": {
                "temperature": TEMPERATURE,
                "similarity_threshold": SIMILARITY_THRESHOLD,
                "prompt_source": "app/prompts.py SYSTEM_PROMPT",
                "models": [m["id"] for m in models],
                "products": [p["product_id"] for p in products_kr],
            },
            "results": all_results,
        }, f, indent=2, ensure_ascii=False)

    # ============================
    # Summary Table
    # ============================
    print("=" * 110)
    print(" RESULTS SUMMARY")
    print("=" * 110)
    print(
        f"{'제품ID':<7} {'제품명':<28} {'모델명':<22} "
        f"{'n/M':<8} {'정확도':<8} {'순서일치':<8} {'생성수':<7} {'비고'}"
    )
    print("-" * 110)

    for r in all_results:
        pname = r["product_name"]
        if len(pname) > 26:
            pname = pname[:24] + ".."
        model = r["model"]
        if len(model) > 20:
            model = model[:18] + ".."

        if r["success"]:
            ev = r["evaluation"]
            score = f"{ev['n']}/{ev['M']}"
            acc = f"{ev['accuracy']:.1%}"
            seq = f"{ev['sequence_match']:.1%}"
            gen = str(ev.get("generated_count", "?"))
            note = ""
        else:
            score = "-"
            acc = "-"
            seq = "-"
            gen = "-"
            note = (r.get("error") or "")[:25]

        print(f"{r['product_id']:<7} {pname:<28} {model:<22} {score:<8} {acc:<8} {seq:<8} {gen:<7} {note}")

    # ============================
    # Model Averages
    # ============================
    print()
    print("=" * 90)
    print(" MODEL AVERAGES")
    print("=" * 90)

    model_stats: Dict[str, dict] = {}
    for r in all_results:
        m = r["model"]
        if m not in model_stats:
            model_stats[m] = {"accs": [], "seqs": [], "latencies": [], "gen_counts": [], "ok": 0, "total": 0}
        model_stats[m]["total"] += 1
        if r["success"]:
            model_stats[m]["ok"] += 1
            model_stats[m]["accs"].append(r["evaluation"]["accuracy"])
            model_stats[m]["seqs"].append(r["evaluation"]["sequence_match"])
            model_stats[m]["gen_counts"].append(r["evaluation"].get("generated_count", 0))
        if r.get("latency_sec"):
            model_stats[m]["latencies"].append(r["latency_sec"])

    print(f"{'모델명':<22} {'평균정확도':<12} {'평균순서일치':<12} {'평균생성수':<10} {'평균지연(s)':<12} {'성공률'}")
    print("-" * 90)

    summary_models = {}
    for model, st in model_stats.items():
        if st["accs"]:
            avg_acc = sum(st["accs"]) / len(st["accs"])
            avg_seq = sum(st["seqs"]) / len(st["seqs"])
            avg_gen = sum(st["gen_counts"]) / len(st["gen_counts"]) if st["gen_counts"] else 0
            avg_lat = sum(st["latencies"]) / len(st["latencies"]) if st["latencies"] else 0
            rate = st["ok"] / st["total"]
            print(f"{model:<22} {avg_acc:<12.1%} {avg_seq:<12.1%} {avg_gen:<10.1f} {avg_lat:<12.1f} {rate:.0%}")
            summary_models[model] = {
                "avg_accuracy": round(avg_acc, 4),
                "avg_sequence_match": round(avg_seq, 4),
                "avg_generated_count": round(avg_gen, 1),
                "avg_latency_sec": round(avg_lat, 2),
                "success_rate": round(rate, 4),
                "products_tested": st["total"],
            }
        else:
            print(f"{model:<22} {'N/A':<12} {'N/A':<12} {'N/A':<10} {'N/A':<12} 0%")
            summary_models[model] = {
                "avg_accuracy": None,
                "avg_sequence_match": None,
                "avg_generated_count": None,
                "avg_latency_sec": None,
                "success_rate": 0,
                "products_tested": st["total"],
            }

    # Save summary
    summary_file = results_dir / f"ex1v2_summary_{timestamp}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "experiment": "Ex1 v2 Zero-shot BOP Generation",
            "dataset_version": "2.0",
            "timestamp": datetime.now().isoformat(),
            "config": {
                "temperature": TEMPERATURE,
                "similarity_threshold": SIMILARITY_THRESHOLD,
                "prompt_source": "app/prompts.py SYSTEM_PROMPT",
            },
            "model_averages": summary_models,
        }, f, indent=2, ensure_ascii=False)

    print()
    print(f" Detail: {detail_file}")
    print(f" Summary: {summary_file}")
    print(f" Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
