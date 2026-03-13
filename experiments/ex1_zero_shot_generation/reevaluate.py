#!/usr/bin/env python
"""
Re-evaluate Ex1 v2 results with improved metrics.

Changes from original evaluation:
1. N:M matching (one GT step can match multiple generated steps and vice versa)
2. Precision = # generated steps covering ≥1 GT / total generated
3. Recall = # GT steps covered by ≥1 generated / total GT  (≈ old "accuracy")
4. F1 = 2*P*R / (P+R)
5. Old 1:1 greedy metrics preserved for comparison

Usage:
    python ex1_v2/reevaluate.py
    python ex1_v2/reevaluate.py --detail-json ex1_v2/results/ex1v2_detail_20260211_164455.json
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
from typing import List

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

SIMILARITY_THRESHOLD = 0.4


# ============================================================
# Step similarity (same as original)
# ============================================================

def normalize_step(step: str) -> str:
    s = step.lower().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^a-zA-Z0-9가-힣\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_keywords(step: str) -> set:
    words = set()
    words.update(re.findall(r"[가-힣]{2,}", step))
    words.update(w.lower() for w in re.findall(r"[a-zA-Z]{3,}", step))
    return words


def step_similarity(gen_step: str, gt_step: str) -> float:
    gen_n = normalize_step(gen_step)
    gt_n = normalize_step(gt_step)
    if gen_n == gt_n:
        return 1.0
    if gen_n and gt_n and (gen_n in gt_n or gt_n in gen_n):
        return 0.9
    gen_kw = extract_keywords(gen_step)
    gt_kw = extract_keywords(gt_step)
    if gen_kw and gt_kw:
        intersection = gen_kw & gt_kw
        union = gen_kw | gt_kw
        jaccard = len(intersection) / len(union) if union else 0
        if jaccard > 0:
            seq = SequenceMatcher(None, gen_n, gt_n).ratio()
            return max(jaccard, seq)
    return SequenceMatcher(None, gen_n, gt_n).ratio()


def step_similarity_bilingual(gen_step: str, gt_step_kr: str, gt_step_en: str) -> float:
    """Compute max similarity across Korean and English GT."""
    sim_kr = step_similarity(gen_step, gt_step_kr)
    sim_en = step_similarity(gen_step, gt_step_en)
    return max(sim_kr, sim_en)


# ============================================================
# Original 1:1 Greedy Evaluation (preserved for comparison)
# ============================================================

def evaluate_greedy_1to1(
    generated_steps: List[str],
    gt_steps_kr: List[str],
    gt_steps_en: List[str],
) -> dict:
    M = len(gt_steps_kr)
    G = len(generated_steps)
    if not generated_steps:
        return {"recall": 0.0, "precision": 0.0, "f1": 0.0, "n": 0, "M": M, "G": G,
                "sequence_match": 0.0, "matches": []}

    matches = []
    used_gen = set()
    for gt_idx in range(M):
        best_sim, best_gen_idx, best_gen_step = 0.0, -1, ""
        for gen_idx, gen_step in enumerate(generated_steps):
            if gen_idx in used_gen:
                continue
            sim = step_similarity_bilingual(gen_step, gt_steps_kr[gt_idx],
                                            gt_steps_en[gt_idx] if gt_idx < len(gt_steps_en) else "")
            if sim > best_sim:
                best_sim = sim
                best_gen_idx = gen_idx
                best_gen_step = gen_step
        if best_sim >= SIMILARITY_THRESHOLD and best_gen_idx >= 0:
            matches.append({"gt_idx": gt_idx, "gen_idx": best_gen_idx,
                            "gt_step": gt_steps_kr[gt_idx], "gen_step": best_gen_step,
                            "similarity": round(best_sim, 3)})
            used_gen.add(best_gen_idx)

    n = len(matches)
    recall = n / M if M > 0 else 0.0
    precision = n / G if G > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Sequence match
    if n >= 2:
        gen_indices = [m["gen_idx"] for m in matches]
        ordered = sum(1 for i in range(len(gen_indices)) for j in range(i+1, len(gen_indices))
                      if gen_indices[i] < gen_indices[j])
        total = len(gen_indices) * (len(gen_indices) - 1) // 2
        sequence_match = ordered / total if total > 0 else 1.0
    else:
        sequence_match = 1.0 if n >= 0 else 0.0

    return {"recall": round(recall, 4), "precision": round(precision, 4),
            "f1": round(f1, 4), "n": n, "M": M, "G": G,
            "sequence_match": round(sequence_match, 4), "matches": matches}


# ============================================================
# NEW: N:M Coverage-based Evaluation
# ============================================================

def evaluate_coverage_nm(
    generated_steps: List[str],
    gt_steps_kr: List[str],
    gt_steps_en: List[str],
) -> dict:
    """
    N:M matching — each step can match multiple counterparts.

    - A GT step is "recalled" if ANY generated step matches it (sim >= threshold)
    - A generated step is "precise" if it matches ANY GT step (sim >= threshold)
    - Recall = recalled GT / total GT
    - Precision = precise generated / total generated
    - F1 = harmonic mean
    """
    M = len(gt_steps_kr)
    G = len(generated_steps)
    if not generated_steps:
        return {"recall": 0.0, "precision": 0.0, "f1": 0.0,
                "recalled_gt": 0, "precise_gen": 0, "M": M, "G": G,
                "sequence_match": 0.0, "gt_coverage": [], "gen_coverage": []}

    # Build full similarity matrix
    sim_matrix = []
    for gt_idx in range(M):
        row = []
        for gen_idx in range(G):
            sim = step_similarity_bilingual(
                generated_steps[gen_idx],
                gt_steps_kr[gt_idx],
                gt_steps_en[gt_idx] if gt_idx < len(gt_steps_en) else ""
            )
            row.append(sim)
        sim_matrix.append(row)

    # GT coverage: for each GT step, best matching generated step(s)
    gt_coverage = []
    recalled_gt_indices = set()
    for gt_idx in range(M):
        best_sim = 0.0
        best_gen_idx = -1
        matching_gens = []
        for gen_idx in range(G):
            sim = sim_matrix[gt_idx][gen_idx]
            if sim >= SIMILARITY_THRESHOLD:
                matching_gens.append({"gen_idx": gen_idx, "gen_step": generated_steps[gen_idx],
                                      "similarity": round(sim, 3)})
            if sim > best_sim:
                best_sim = sim
                best_gen_idx = gen_idx
        covered = best_sim >= SIMILARITY_THRESHOLD
        if covered:
            recalled_gt_indices.add(gt_idx)
        gt_coverage.append({
            "gt_idx": gt_idx,
            "gt_step": gt_steps_kr[gt_idx],
            "covered": covered,
            "best_sim": round(best_sim, 3),
            "best_gen_idx": best_gen_idx,
            "best_gen_step": generated_steps[best_gen_idx] if best_gen_idx >= 0 else "",
            "all_matches": matching_gens,
        })

    # Generated coverage: for each generated step, does it match any GT?
    gen_coverage = []
    precise_gen_indices = set()
    for gen_idx in range(G):
        best_sim = 0.0
        best_gt_idx = -1
        for gt_idx in range(M):
            sim = sim_matrix[gt_idx][gen_idx]
            if sim > best_sim:
                best_sim = sim
                best_gt_idx = gt_idx
        covered = best_sim >= SIMILARITY_THRESHOLD
        if covered:
            precise_gen_indices.add(gen_idx)
        gen_coverage.append({
            "gen_idx": gen_idx,
            "gen_step": generated_steps[gen_idx],
            "covered": covered,
            "best_sim": round(best_sim, 3),
            "best_gt_idx": best_gt_idx,
            "best_gt_step": gt_steps_kr[best_gt_idx] if best_gt_idx >= 0 else "",
        })

    recalled_gt = len(recalled_gt_indices)
    precise_gen = len(precise_gen_indices)

    recall = recalled_gt / M if M > 0 else 0.0
    precision = precise_gen / G if G > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Sequence: use recalled GT steps, check if their best-gen indices preserve order
    if recalled_gt >= 2:
        recalled_ordered = sorted(recalled_gt_indices)
        best_gen_for_recalled = [gt_coverage[gt_idx]["best_gen_idx"] for gt_idx in recalled_ordered]
        ordered = sum(1 for i in range(len(best_gen_for_recalled))
                      for j in range(i+1, len(best_gen_for_recalled))
                      if best_gen_for_recalled[i] < best_gen_for_recalled[j])
        total = len(best_gen_for_recalled) * (len(best_gen_for_recalled) - 1) // 2
        sequence_match = ordered / total if total > 0 else 1.0
    else:
        sequence_match = 1.0 if recalled_gt >= 0 else 0.0

    return {
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "f1": round(f1, 4),
        "recalled_gt": recalled_gt,
        "precise_gen": precise_gen,
        "M": M,
        "G": G,
        "sequence_match": round(sequence_match, 4),
        "gt_coverage": gt_coverage,
        "gen_coverage": gen_coverage,
    }


# ============================================================
# Main: Re-evaluate existing results
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Re-evaluate Ex1 v2 with improved metrics")
    parser.add_argument("--detail-json", type=str, default=None,
                        help="Path to existing detail JSON. Auto-detects latest if not specified.")
    args = parser.parse_args()

    # Find detail JSON
    if args.detail_json:
        detail_path = Path(args.detail_json)
    else:
        results_dir = SCRIPT_DIR / "results"
        candidates = sorted(results_dir.glob("ex1v2_detail_*.json"))
        if not candidates:
            print("ERROR: No detail JSON found in ex1_v2/results/")
            return
        detail_path = candidates[-1]
        print(f"Using latest: {detail_path.name}")

    # Load detail JSON
    with open(detail_path, "r", encoding="utf-8") as f:
        detail = json.load(f)

    # Load GT
    with open(SCRIPT_DIR / "ex1_gt_kr.json", "r", encoding="utf-8") as f:
        gt_kr = json.load(f)
    with open(SCRIPT_DIR / "ex1_gt_en.json", "r", encoding="utf-8") as f:
        gt_en = json.load(f)

    gt_kr_map = {p["product_id"]: p for p in gt_kr["ground_truth_bop"]}
    gt_en_map = {p["product_id"]: p for p in gt_en["ground_truth_bop"]}

    results = detail["results"]
    print(f"\nRe-evaluating {len(results)} results with two methods:\n"
          f"  (A) Original 1:1 Greedy  (B) N:M Coverage\n")

    # Re-evaluate each result
    reeval_results = []
    for r in results:
        if not r.get("success") or not r.get("generated_processes"):
            reeval_results.append({
                "product_id": r["product_id"],
                "model": r["model"],
                "success": False,
                "greedy_1to1": None,
                "coverage_nm": None,
            })
            continue

        pid = r["product_id"]
        gt_steps_kr = gt_kr_map[pid]["bop_steps"]
        gt_steps_en = gt_en_map[pid]["bop_steps"]
        gen_steps = r["generated_processes"]

        eval_greedy = evaluate_greedy_1to1(gen_steps, gt_steps_kr, gt_steps_en)
        eval_nm = evaluate_coverage_nm(gen_steps, gt_steps_kr, gt_steps_en)

        reeval_results.append({
            "product_id": pid,
            "product_name": r["product_name"],
            "model": r["model"],
            "model_id": r["model_id"],
            "success": True,
            "generated_count": len(gen_steps),
            "gt_count": len(gt_steps_kr),
            "greedy_1to1": {
                "recall": eval_greedy["recall"],
                "precision": eval_greedy["precision"],
                "f1": eval_greedy["f1"],
                "n": eval_greedy["n"],
                "sequence_match": eval_greedy["sequence_match"],
            },
            "coverage_nm": {
                "recall": eval_nm["recall"],
                "precision": eval_nm["precision"],
                "f1": eval_nm["f1"],
                "recalled_gt": eval_nm["recalled_gt"],
                "precise_gen": eval_nm["precise_gen"],
                "sequence_match": eval_nm["sequence_match"],
                "gt_coverage": eval_nm["gt_coverage"],
                "gen_coverage": eval_nm["gen_coverage"],
            },
        })

    # ============================================================
    # Aggregate by model
    # ============================================================
    models = {}
    for r in reeval_results:
        if not r["success"]:
            continue
        m = r["model"]
        if m not in models:
            models[m] = {"greedy_1to1": [], "coverage_nm": []}
        models[m]["greedy_1to1"].append(r["greedy_1to1"])
        models[m]["coverage_nm"].append(r["coverage_nm"])

    print("=" * 100)
    print(f"{'Model':<22} | {'Method':<14} | {'Recall':>7} {'Precision':>10} {'F1':>7} | {'SeqMatch':>8}")
    print("-" * 100)

    model_summary = {}
    for m_name in ["Gemini 2.5 Flash", "GPT-5 Mini", "Gemini 2.5 Pro", "GPT-5.2"]:
        if m_name not in models:
            continue
        data = models[m_name]

        # Greedy 1:1
        g = data["greedy_1to1"]
        g_recall = sum(x["recall"] for x in g) / len(g)
        g_prec = sum(x["precision"] for x in g) / len(g)
        g_f1 = sum(x["f1"] for x in g) / len(g)
        g_seq = sum(x["sequence_match"] for x in g) / len(g)

        # Coverage N:M
        c = data["coverage_nm"]
        c_recall = sum(x["recall"] for x in c) / len(c)
        c_prec = sum(x["precision"] for x in c) / len(c)
        c_f1 = sum(x["f1"] for x in c) / len(c)
        c_seq = sum(x["sequence_match"] for x in c) / len(c)

        print(f"{m_name:<22} | {'Greedy 1:1':<14} | {g_recall:>6.1%} {g_prec:>9.1%} {g_f1:>7.1%} | {g_seq:>7.1%}")
        print(f"{'':<22} | {'Coverage N:M':<14} | {c_recall:>6.1%} {c_prec:>9.1%} {c_f1:>7.1%} | {c_seq:>7.1%}")
        print("-" * 100)

        model_summary[m_name] = {
            "greedy_1to1": {
                "avg_recall": round(g_recall, 4), "avg_precision": round(g_prec, 4),
                "avg_f1": round(g_f1, 4), "avg_sequence_match": round(g_seq, 4),
            },
            "coverage_nm": {
                "avg_recall": round(c_recall, 4), "avg_precision": round(c_prec, 4),
                "avg_f1": round(c_f1, 4), "avg_sequence_match": round(c_seq, 4),
            },
        }

    # ============================================================
    # Per-product comparison for GPT-5.2
    # ============================================================
    print("\n\n=== GPT-5.2 Per-Product: Greedy 1:1 vs Coverage N:M ===\n")
    print(f"{'Product':<28} | {'GT':>3} {'Gen':>4} | {'1:1 Recall':>10} {'N:M Recall':>10} {'Delta':>7} | "
          f"{'1:1 F1':>7} {'N:M F1':>7} {'Delta':>7}")
    print("-" * 120)

    gpt52_products = [r for r in reeval_results if r.get("model") == "GPT-5.2" and r["success"]]
    for r in gpt52_products:
        g = r["greedy_1to1"]
        c = r["coverage_nm"]
        delta_r = c["recall"] - g["recall"]
        delta_f = c["f1"] - g["f1"]
        print(f"{r['product_id']} {r['product_name']:<24} | {r['gt_count']:>3} {r['generated_count']:>4} | "
              f"{g['recall']:>9.1%} {c['recall']:>9.1%} {delta_r:>+6.1%} | "
              f"{g['f1']:>6.1%} {c['f1']:>6.1%} {delta_f:>+6.1%}")

    # ============================================================
    # Save results
    # ============================================================
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = SCRIPT_DIR / "results"
    out_dir.mkdir(exist_ok=True)

    # Detailed re-evaluation
    reeval_detail = {
        "experiment": "Ex1 v2 Re-evaluation (Improved Metrics)",
        "timestamp": datetime.now().isoformat(),
        "source": str(detail_path.name),
        "methods": {
            "greedy_1to1": "Original 1:1 greedy best-match. Each step matched at most once.",
            "coverage_nm": "N:M coverage. GT recalled if ANY generated matches. Generated precise if ANY GT matches.",
        },
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "model_summary": model_summary,
        "results": reeval_results,
    }

    detail_out = out_dir / f"ex1v2_reeval_{ts}.json"
    with open(detail_out, "w", encoding="utf-8") as f:
        json.dump(reeval_detail, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {detail_out}")

    # Compact summary
    summary_out = out_dir / f"ex1v2_reeval_summary_{ts}.json"
    with open(summary_out, "w", encoding="utf-8") as f:
        json.dump({
            "experiment": "Ex1 v2 Re-evaluation Summary",
            "timestamp": datetime.now().isoformat(),
            "model_summary": model_summary,
        }, f, ensure_ascii=False, indent=2)
    print(f"Saved: {summary_out}")


if __name__ == "__main__":
    main()
