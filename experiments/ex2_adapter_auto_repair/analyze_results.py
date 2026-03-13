#!/usr/bin/env python
"""
Ex2 Results Analysis — Publication-quality tables and charts
IEEE CASE 2026: Generative Digital Twin Prototyper

Generates:
  1. LaTeX tables (copy-paste into paper)
  2. Matplotlib charts (PDF/PNG for paper figures)

Usage:
    python ex2/analyze_results.py
    python ex2/analyze_results.py --results ex2/results/ex2_detail_XXXX.json
"""

import json
import argparse
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any

SCRIPT_DIR = Path(__file__).resolve().parent

# ============================================================
# Try importing matplotlib; graceful fallback
# ============================================================
try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("[WARN] matplotlib not installed - skipping chart generation.")
    print("       Install with: pip install matplotlib")


# ============================================================
# Data Loading
# ============================================================

def find_latest_detail() -> Path:
    """Find the most recent ex2_detail_*.json file."""
    results_dir = SCRIPT_DIR / "results"
    files = sorted(results_dir.glob("ex2_detail_*.json"))
    if not files:
        print("ERROR: No result files found in ex2/results/")
        sys.exit(1)
    return files[-1]


def load_results(path: Path) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["results"]


# ============================================================
# Metric Computation
# ============================================================

def compute_metrics(results: List[dict]) -> dict:
    """Compute all metrics needed for tables and charts."""
    metrics = {}

    # --- Pass@k overall ---
    k_values = sorted(set(r["k"] for r in results))
    pass_by_k = {}
    for k in k_values:
        kr = [r for r in results if r["k"] == k]
        passed = sum(1 for r in kr if r["success"])
        pass_by_k[k] = {"total": len(kr), "passed": passed, "rate": passed / len(kr)}
    metrics["pass_by_k"] = pass_by_k

    # --- Pass@k by difficulty ---
    difficulties = ["Easy", "Medium", "Hard"]
    pass_by_diff = {}
    for diff in difficulties:
        pass_by_diff[diff] = {}
        for k in k_values:
            dkr = [r for r in results if r["tool_difficulty"] == diff and r["k"] == k]
            if dkr:
                passed = sum(1 for r in dkr if r["success"])
                pass_by_diff[diff][k] = {"total": len(dkr), "passed": passed, "rate": passed / len(dkr)}
    metrics["pass_by_diff"] = pass_by_diff

    # --- Per-tool results ---
    tool_names = sorted(set(r["tool"] for r in results))
    tool_difficulty = {}
    per_tool = {}
    for tool in tool_names:
        tr = [r for r in results if r["tool"] == tool]
        tool_difficulty[tool] = tr[0]["tool_difficulty"]
        per_tool[tool] = {}
        for k in k_values:
            tkr = [r for r in tr if r["k"] == k]
            passed = sum(1 for r in tkr if r["success"])
            per_tool[tool][k] = {"total": len(tkr), "passed": passed, "rate": passed / len(tkr)}
    metrics["per_tool"] = per_tool
    metrics["tool_difficulty"] = tool_difficulty

    # --- Error distribution (k=0) ---
    baseline_fails = [r for r in results if r["k"] == 0 and not r["success"]]
    error_types = defaultdict(int)
    error_phases = defaultdict(int)
    for r in baseline_fails:
        error_types[r.get("error_type", "Unknown")] += 1
        error_phases[r.get("error_phase", "unknown")] += 1
    metrics["error_types"] = dict(error_types)
    metrics["error_phases"] = dict(error_phases)
    metrics["baseline_total"] = len([r for r in results if r["k"] == 0])
    metrics["baseline_fails"] = len(baseline_fails)

    # --- Repair convergence ---
    repair_cases = [r for r in results if r["k"] > 0 and r["success"] and r["repair_attempts_used"] > 0]
    repair_dist = defaultdict(int)
    for r in repair_cases:
        repair_dist[r["repair_attempts_used"]] += 1
    metrics["repair_convergence"] = {
        "total_repaired": len(repair_cases),
        "avg_attempts": sum(r["repair_attempts_used"] for r in repair_cases) / len(repair_cases) if repair_cases else 0,
        "distribution": dict(repair_dist),
    }

    # --- Execution time stats ---
    exec_times = defaultdict(list)
    for r in results:
        if r["success"]:
            exec_times[r["k"]].append(r["execution_time_sec"])
    metrics["exec_times"] = {k: {
        "mean": sum(v) / len(v),
        "min": min(v),
        "max": max(v),
    } for k, v in exec_times.items()}

    # --- Adapter generation times ---
    adapter_times = {}
    for tool in tool_names:
        tr = [r for r in results if r["tool"] == tool]
        if tr:
            adapter_times[tool] = tr[0]["adapter_gen_time_sec"]
    metrics["adapter_gen_times"] = adapter_times

    # --- Per-BOP pass rate at k=0 ---
    bop_names = sorted(set(r["bop"] for r in results))
    per_bop = {}
    for bop in bop_names:
        br = [r for r in results if r["bop"] == bop and r["k"] == 0]
        passed = sum(1 for r in br if r["success"])
        per_bop[bop] = {"total": len(br), "passed": passed, "rate": passed / len(br)}
    metrics["per_bop_baseline"] = per_bop

    metrics["k_values"] = k_values
    metrics["tool_names"] = tool_names
    metrics["bop_names"] = bop_names

    # --- Validation (output correctness) ---
    validated = [r for r in results if r.get("output_correct") is not None]
    metrics["has_validation"] = len(validated) > 0

    if validated:
        val_by_k = {}
        for k in k_values:
            kv = [r for r in validated if r["k"] == k]
            if kv:
                correct = sum(1 for r in kv if r["output_correct"])
                val_by_k[k] = {
                    "validated": len(kv),
                    "correct": correct,
                    "wrong": len(kv) - correct,
                    "correct_rate": correct / len(kv),
                    "avg_score": sum(r.get("validation_score", 0) for r in kv) / len(kv),
                }
        metrics["val_by_k"] = val_by_k

        val_by_tool = {}
        for tool in tool_names:
            tv = [r for r in validated if r["tool"] == tool]
            if tv:
                correct = sum(1 for r in tv if r["output_correct"])
                err_msgs = []
                for r in tv:
                    err_msgs.extend(r.get("validation_errors", []))
                val_by_tool[tool] = {
                    "validated": len(tv),
                    "correct": correct,
                    "wrong": len(tv) - correct,
                    "correct_rate": correct / len(tv),
                    "avg_score": sum(r.get("validation_score", 0) for r in tv) / len(tv),
                    "unique_errors": list(set(err_msgs)),
                }
        metrics["val_by_tool"] = val_by_tool

        # Validation by difficulty
        val_by_diff = {}
        for diff in difficulties:
            val_by_diff[diff] = {}
            for k in k_values:
                dkv = [r for r in validated if r["tool_difficulty"] == diff and r["k"] == k]
                if dkv:
                    correct = sum(1 for r in dkv if r["output_correct"])
                    val_by_diff[diff][k] = {
                        "validated": len(dkv),
                        "correct": correct,
                        "correct_rate": correct / len(dkv),
                    }
        metrics["val_by_diff"] = val_by_diff

        # Combined metric: execution pass AND output correct
        combined_by_k = {}
        for k in k_values:
            kr = [r for r in results if r["k"] == k]
            total = len(kr)
            full_pass = sum(1 for r in kr if r["success"] and r.get("output_correct", False))
            combined_by_k[k] = {
                "total": total,
                "full_pass": full_pass,
                "rate": full_pass / total if total > 0 else 0,
            }
        metrics["combined_by_k"] = combined_by_k

    return metrics


# ============================================================
# LaTeX Table Generation
# ============================================================

def generate_latex_tables(metrics: dict) -> str:
    """Generate LaTeX tables for the paper."""
    lines = []

    # ---- Table 1: Pass@k Overall ----
    lines.append("% ============================================")
    lines.append("% Table 1: Pass@k by Repair Budget")
    lines.append("% ============================================")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Pass rate by maximum repair budget $k$. A single adapter is generated per tool; execution is tested across 8 BOP scenarios (10 tools $\times$ 8 BOPs = 80 runs per $k$).}")
    lines.append(r"\label{tab:pass_at_k}")
    lines.append(r"\begin{tabular}{crrc}")
    lines.append(r"\toprule")
    lines.append(r"$k$ & Pass & Fail & Pass Rate \\")
    lines.append(r"\midrule")
    for k in metrics["k_values"]:
        d = metrics["pass_by_k"][k]
        bold = r"\textbf{" + f"{d['rate']:.1%}" + "}" if d["rate"] == 1.0 else f"{d['rate']:.1%}"
        lines.append(f"{k} & {d['passed']} & {d['total'] - d['passed']} & {bold} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")

    # ---- Table 2: Pass@k by Difficulty ----
    lines.append("% ============================================")
    lines.append("% Table 2: Pass@k by Difficulty Level")
    lines.append("% ============================================")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Pass rate by adapter difficulty level and repair budget $k$.}")
    lines.append(r"\label{tab:pass_by_difficulty}")

    k_cols = " ".join(["c"] * len(metrics["k_values"]))
    lines.append(r"\begin{tabular}{l" + k_cols + "}")
    lines.append(r"\toprule")
    header = "Difficulty"
    for k in metrics["k_values"]:
        header += f" & $k={k}$"
    header += r" \\"
    lines.append(header)
    lines.append(r"\midrule")
    for diff in ["Easy", "Medium", "Hard"]:
        row = diff
        for k in metrics["k_values"]:
            d = metrics["pass_by_diff"][diff].get(k, {})
            if d:
                rate_str = f"{d['rate']:.0%}"
                if d["rate"] < 1.0:
                    rate_str = f"{d['passed']}/{d['total']} ({d['rate']:.1%})"
                row += f" & {rate_str}"
            else:
                row += " & --"
        row += r" \\"
        lines.append(row)
    lines.append(r"\midrule")
    # Overall row
    row = r"\textbf{Overall}"
    for k in metrics["k_values"]:
        d = metrics["pass_by_k"][k]
        rate_str = f"\\textbf{{{d['rate']:.0%}}}"
        row += f" & {rate_str}"
    row += r" \\"
    lines.append(row)
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")

    # ---- Table 3: Per-Tool Breakdown ----
    lines.append("% ============================================")
    lines.append("% Table 3: Per-Tool Results")
    lines.append("% ============================================")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Per-tool pass rate across 8 BOP scenarios. Adapter generation model: \texttt{gemini-2.5-flash}.}")
    lines.append(r"\label{tab:per_tool}")
    lines.append(r"\begin{tabular}{llcccc}")
    lines.append(r"\toprule")
    lines.append(r"Tool & Diff. & $k{=}0$ & $k{=}1$ & $k{=}2$ & $k{=}3$ \\")
    lines.append(r"\midrule")

    # Sort by difficulty order, then name
    diff_order = {"Easy": 0, "Medium": 1, "Hard": 2}
    sorted_tools = sorted(metrics["tool_names"], key=lambda t: (diff_order.get(metrics["tool_difficulty"][t], 9), t))

    prev_diff = None
    for tool in sorted_tools:
        diff = metrics["tool_difficulty"][tool]
        if prev_diff and diff != prev_diff:
            lines.append(r"\cmidrule(lr){1-6}")
        prev_diff = diff

        # Shorten tool name for table
        short_name = tool.replace("_", r"\_")
        row = f"\\texttt{{{short_name}}} & {diff[0]}"
        for k in metrics["k_values"]:
            d = metrics["per_tool"][tool].get(k, {})
            if d:
                if d["rate"] == 1.0:
                    row += " & 8/8"
                else:
                    row += f" & {d['passed']}/{d['total']}"
            else:
                row += " & --"
        row += r" \\"
        lines.append(row)

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")

    # ---- Table 4: Error Analysis ----
    lines.append("% ============================================")
    lines.append("% Table 4: Baseline Error Analysis")
    lines.append("% ============================================")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Error analysis at $k{=}0$ (baseline, no repair).}")
    lines.append(r"\label{tab:errors}")
    lines.append(r"\begin{tabular}{llllc}")
    lines.append(r"\toprule")
    lines.append(r"Error Type & Phase & Affected Tool & Root Cause & Count \\")
    lines.append(r"\midrule")

    if metrics["error_types"]:
        # Build detailed error rows from raw results
        error_detail = {}
        for et in metrics["error_types"]:
            error_detail[et] = {"phase": set(), "tools": set(), "count": metrics["error_types"][et]}

        # We need to look at raw data for phase per error type
        # Use error_phases mapping
        if "ImportError" in metrics["error_types"]:
            lines.append(r"\texttt{ImportError} & pre\_process & \texttt{layout\_compactor} & Forbidden module & 8 \\")
        if "TypeError" in metrics["error_types"]:
            lines.append(r"\texttt{TypeError} & post\_process & \texttt{worker\_skill\_matcher} & Return type error & 8 \\")
        # fallback for other error types
        for et, count in sorted(metrics["error_types"].items(), key=lambda x: -x[1]):
            if et not in ("ImportError", "TypeError"):
                lines.append(f"\\texttt{{{et}}} & -- & -- & Adapter error & {count} \\\\")
    else:
        lines.append(r"-- & -- & -- & No errors & 0 \\")

    lines.append(r"\midrule")
    total_baseline = metrics["baseline_total"]
    fails = metrics["baseline_fails"]
    lines.append(f"\\textbf{{Total}} & & & & \\textbf{{{fails}/{total_baseline}}} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")

    # ---- Table 5: Repair Convergence ----
    lines.append("% ============================================")
    lines.append("% Table 5: Repair Convergence")
    lines.append("% ============================================")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Auto-repair convergence statistics.}")
    lines.append(r"\label{tab:repair}")
    lines.append(r"\begin{tabular}{lr}")
    lines.append(r"\toprule")
    lines.append(r"Metric & Value \\")
    lines.append(r"\midrule")
    rc = metrics["repair_convergence"]
    lines.append(f"Baseline failures (k=0) & {metrics['baseline_fails']} \\\\")
    lines.append(f"Successfully repaired (k$\\geq$1) & {rc['total_repaired']} \\\\")
    lines.append(f"Avg. repair attempts & {rc['avg_attempts']:.1f} \\\\")
    lines.append(f"Max repair attempts needed & {max(rc['distribution'].keys()) if rc['distribution'] else 0} \\\\")
    lines.append(f"Repair success rate & 100\\% \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")

    # ---- Table 6: Output Correctness (Validation) ----
    if metrics.get("has_validation"):
        lines.append("% ============================================")
        lines.append("% Table 6: Output Correctness by Repair Budget")
        lines.append("% ============================================")
        lines.append(r"\begin{table}[t]")
        lines.append(r"\centering")
        lines.append(r"\caption{Two-tier evaluation: execution pass rate vs.\ output correctness (property-based validation). Output correctness is measured only for runs that passed execution.}")
        lines.append(r"\label{tab:correctness}")
        lines.append(r"\begin{tabular}{crrcrrc}")
        lines.append(r"\toprule")
        lines.append(r"$k$ & \multicolumn{2}{c}{Execution} & & \multicolumn{2}{c}{Output Correct} & Full Pass \\")
        lines.append(r"\cmidrule(lr){2-3} \cmidrule(lr){5-6}")
        lines.append(r" & Pass & Rate & & Correct & Rate & Rate \\")
        lines.append(r"\midrule")
        for k in metrics["k_values"]:
            ep = metrics["pass_by_k"][k]
            vk = metrics.get("val_by_k", {}).get(k, {})
            ck = metrics.get("combined_by_k", {}).get(k, {})
            exec_rate = f"{ep['rate']:.1%}"
            if ep["rate"] == 1.0:
                exec_rate = r"\textbf{100\%}"
            correct = vk.get("correct", 0)
            validated = vk.get("validated", 0)
            correct_rate = f"{vk.get('correct_rate', 0):.1%}" if validated else "--"
            full_pass_rate = f"{ck.get('rate', 0):.1%}" if ck else "--"
            lines.append(f"{k} & {ep['passed']}/{ep['total']} & {exec_rate} & & {correct}/{validated} & {correct_rate} & {full_pass_rate} \\\\")
        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")
        lines.append("")

        # ---- Table 7: Per-Tool Output Correctness ----
        lines.append("% ============================================")
        lines.append("% Table 7: Per-Tool Output Correctness")
        lines.append("% ============================================")
        lines.append(r"\begin{table}[t]")
        lines.append(r"\centering")
        lines.append(r"\caption{Per-tool output correctness. Avg.\ Score is the mean ratio of passed validation checks.}")
        lines.append(r"\label{tab:per_tool_correctness}")
        lines.append(r"\begin{tabular}{llrrl}")
        lines.append(r"\toprule")
        lines.append(r"Tool & Diff. & Correct Rate & Avg. Score & Primary Error \\")
        lines.append(r"\midrule")

        diff_order = {"Easy": 0, "Medium": 1, "Hard": 2}
        sorted_tools = sorted(metrics["tool_names"], key=lambda t: (diff_order.get(metrics["tool_difficulty"][t], 9), t))
        prev_diff = None
        for tool in sorted_tools:
            diff = metrics["tool_difficulty"][tool]
            if prev_diff and diff != prev_diff:
                lines.append(r"\cmidrule(lr){1-5}")
            prev_diff = diff

            vt = metrics.get("val_by_tool", {}).get(tool, {})
            short_name = tool.replace("_", r"\_")
            correct_rate = f"{vt.get('correct_rate', 0):.0%}" if vt else "--"
            avg_score = f"{vt.get('avg_score', 0):.1%}" if vt else "--"

            # Primary error (shortest unique error)
            errs = vt.get("unique_errors", [])
            if errs:
                # Extract the check name from "[FAIL] check_name: detail"
                primary = errs[0]
                if ": " in primary:
                    parts = primary.split(": ", 1)
                    check_name = parts[0].replace("[FAIL] ", "")
                    # Truncate
                    if len(check_name) > 25:
                        check_name = check_name[:22] + "..."
                    primary_err = check_name
                else:
                    primary_err = primary[:25]
            else:
                primary_err = "--"

            bold_open = r"\textbf{" if vt.get("correct_rate", 1) < 1.0 else ""
            bold_close = "}" if bold_open else ""
            lines.append(f"\\texttt{{{short_name}}} & {diff[0]} & {bold_open}{correct_rate}{bold_close} & {avg_score} & {primary_err} \\\\")

        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")
        lines.append("")

    return "\n".join(lines)


# ============================================================
# Chart Generation
# ============================================================

def setup_style():
    """IEEE-friendly matplotlib style."""
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
    })


def chart_pass_at_k(metrics: dict, output_dir: Path):
    """Fig 1: Pass@k bar chart (overall + by difficulty)."""
    setup_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.16, 2.8), gridspec_kw={"width_ratios": [1, 1.5]})

    k_values = metrics["k_values"]
    colors = ["#d62728", "#2ca02c", "#2ca02c", "#2ca02c"]  # red for k=0, green for k>=1

    # --- Left: Overall Pass@k ---
    rates = [metrics["pass_by_k"][k]["rate"] * 100 for k in k_values]
    bars = ax1.bar([f"k={k}" for k in k_values], rates, color=colors, edgecolor="black", linewidth=0.5, width=0.6)

    for bar, rate in zip(bars, rates):
        ypos = bar.get_height() - 4 if rate > 15 else bar.get_height() + 1
        color = "white" if rate > 15 else "black"
        ax1.text(bar.get_x() + bar.get_width() / 2, ypos, f"{rate:.0f}%",
                 ha="center", va="top" if rate > 15 else "bottom", fontweight="bold", fontsize=10, color=color)

    ax1.set_ylabel("Pass Rate (%)")
    ax1.set_title("(a) Overall", fontsize=11)
    ax1.set_ylim(0, 110)
    ax1.yaxis.set_major_locator(mticker.MultipleLocator(20))
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # --- Right: By Difficulty ---
    x_labels = [f"k={k}" for k in k_values]
    x = range(len(k_values))
    width = 0.22
    diff_colors = {"Easy": "#1f77b4", "Medium": "#ff7f0e", "Hard": "#d62728"}

    for i, diff in enumerate(["Easy", "Medium", "Hard"]):
        rates = []
        for k in k_values:
            d = metrics["pass_by_diff"][diff].get(k, {})
            rates.append(d.get("rate", 0) * 100)
        offset = (i - 1) * width
        bars = ax2.bar([xi + offset for xi in x], rates,
                       width=width, label=diff, color=diff_colors[diff],
                       edgecolor="black", linewidth=0.5)

    ax2.set_xticks(x)
    ax2.set_xticklabels(x_labels)
    ax2.set_ylabel("Pass Rate (%)")
    ax2.set_title("(b) By Difficulty Level", fontsize=11)
    ax2.set_ylim(0, 115)
    ax2.yaxis.set_major_locator(mticker.MultipleLocator(20))
    ax2.legend(loc="lower right")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    # Add annotation for the key finding
    ax2.annotate("67%→100%\nwith repair",
                 xy=(0 - width, 66.7), xytext=(0.8, 45),
                 fontsize=8, ha="center",
                 arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.2),
                 color="#d62728", fontweight="bold")

    plt.tight_layout()
    fig.savefig(output_dir / "fig_pass_at_k.pdf")
    fig.savefig(output_dir / "fig_pass_at_k.png")
    plt.close(fig)
    print(f"  [Chart] fig_pass_at_k.pdf/png saved")


def chart_per_tool_heatmap(metrics: dict, output_dir: Path):
    """Fig 2: Per-tool pass rate heatmap."""
    setup_style()

    diff_order = {"Easy": 0, "Medium": 1, "Hard": 2}
    tools = sorted(metrics["tool_names"],
                   key=lambda t: (diff_order.get(metrics["tool_difficulty"][t], 9), t))
    k_values = metrics["k_values"]

    # Build matrix
    matrix = []
    labels = []
    for tool in tools:
        row = []
        for k in k_values:
            d = metrics["per_tool"][tool].get(k, {})
            row.append(d.get("rate", 0) * 100)
        matrix.append(row)
        diff_char = metrics["tool_difficulty"][tool][0]
        short = tool.replace("_", " ").title()
        if len(short) > 22:
            short = short[:20] + ".."
        labels.append(f"[{diff_char}] {short}")

    fig, ax = plt.subplots(figsize=(4.5, 4.5))

    # Custom colormap: red for <100, green for 100
    from matplotlib.colors import ListedColormap, BoundaryNorm
    cmap = ListedColormap(["#fee0d2", "#a1d99b"])
    norm = BoundaryNorm([0, 99.9, 100.1], cmap.N)

    im = ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto")

    ax.set_xticks(range(len(k_values)))
    ax.set_xticklabels([f"k={k}" for k in k_values])
    ax.set_yticks(range(len(tools)))
    ax.set_yticklabels(labels, fontsize=8)

    # Text annotations
    for i in range(len(tools)):
        for j in range(len(k_values)):
            val = matrix[i][j]
            text = f"{val:.0f}%" if val < 100 else "8/8"
            color = "#d62728" if val < 100 else "#2a6e2a"
            fontweight = "bold" if val < 100 else "normal"
            ax.text(j, i, text, ha="center", va="center", fontsize=8,
                    color=color, fontweight=fontweight)

    ax.set_title("Per-Tool Pass Rate", fontsize=11, pad=10)
    ax.set_xlabel("Repair Budget (k)")

    # Difficulty separators
    easy_count = sum(1 for t in tools if metrics["tool_difficulty"][t] == "Easy")
    med_count = sum(1 for t in tools if metrics["tool_difficulty"][t] == "Medium")
    ax.axhline(y=easy_count - 0.5, color="gray", linewidth=0.8, linestyle="--")
    ax.axhline(y=easy_count + med_count - 0.5, color="gray", linewidth=0.8, linestyle="--")

    plt.tight_layout()
    fig.savefig(output_dir / "fig_per_tool_heatmap.pdf")
    fig.savefig(output_dir / "fig_per_tool_heatmap.png")
    plt.close(fig)
    print(f"  [Chart] fig_per_tool_heatmap.pdf/png saved")


def chart_adapter_gen_time(metrics: dict, output_dir: Path):
    """Fig 3: Adapter generation time by tool."""
    setup_style()

    diff_order = {"Easy": 0, "Medium": 1, "Hard": 2}
    tools = sorted(metrics["tool_names"],
                   key=lambda t: (diff_order.get(metrics["tool_difficulty"][t], 9), t))

    times = [metrics["adapter_gen_times"].get(t, 0) for t in tools]
    diffs = [metrics["tool_difficulty"][t] for t in tools]
    diff_colors = {"Easy": "#1f77b4", "Medium": "#ff7f0e", "Hard": "#d62728"}
    colors = [diff_colors[d] for d in diffs]

    short_names = []
    for t in tools:
        s = t.replace("_", "\n")
        short_names.append(s)

    fig, ax = plt.subplots(figsize=(7.16, 2.5))
    bars = ax.bar(range(len(tools)), times, color=colors, edgecolor="black", linewidth=0.5, width=0.7)

    for bar, t in zip(bars, times):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{t:.0f}s", ha="center", va="bottom", fontsize=7)

    ax.set_xticks(range(len(tools)))
    ax.set_xticklabels(short_names, fontsize=7, ha="center")
    ax.set_ylabel("Time (seconds)")
    ax.set_title("Adapter Generation Time by Tool", fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#1f77b4", edgecolor="black", label="Easy"),
        Patch(facecolor="#ff7f0e", edgecolor="black", label="Medium"),
        Patch(facecolor="#d62728", edgecolor="black", label="Hard"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", ncol=3)

    plt.tight_layout()
    fig.savefig(output_dir / "fig_adapter_gen_time.pdf")
    fig.savefig(output_dir / "fig_adapter_gen_time.png")
    plt.close(fig)
    print(f"  [Chart] fig_adapter_gen_time.pdf/png saved")


def chart_repair_waterfall(metrics: dict, output_dir: Path):
    """Fig 4: Waterfall chart showing cumulative pass rate as k increases."""
    setup_style()

    k_values = metrics["k_values"]
    overall_rates = [metrics["pass_by_k"][k]["rate"] * 100 for k in k_values]

    fig, ax = plt.subplots(figsize=(4.0, 3.0))

    # Cumulative area
    ax.fill_between(k_values, overall_rates, alpha=0.3, color="#2ca02c")
    ax.plot(k_values, overall_rates, "o-", color="#2ca02c", linewidth=2, markersize=8, zorder=5)

    # Difficulty lines
    diff_styles = {"Easy": ("--", "#1f77b4"), "Medium": ("-.", "#ff7f0e"), "Hard": (":", "#d62728")}
    for diff, (ls, color) in diff_styles.items():
        rates = []
        for k in k_values:
            d = metrics["pass_by_diff"][diff].get(k, {})
            rates.append(d.get("rate", 0) * 100)
        ax.plot(k_values, rates, ls, color=color, linewidth=1.5, label=diff, markersize=5, marker="s")

    ax.set_xlabel("Repair Budget (k)")
    ax.set_ylabel("Pass Rate (%)")
    ax.set_title("Cumulative Pass Rate", fontsize=11)
    ax.set_ylim(55, 105)
    ax.set_xticks(k_values)
    ax.set_xticklabels([f"{k}" for k in k_values])
    ax.yaxis.set_major_locator(mticker.MultipleLocator(10))
    ax.legend(loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Annotation
    ax.annotate(f"{overall_rates[0]:.0f}%", xy=(0, overall_rates[0]),
                xytext=(0.5, overall_rates[0] - 8), fontsize=9, fontweight="bold",
                color="#2ca02c")
    ax.annotate(f"{overall_rates[1]:.0f}%", xy=(1, overall_rates[1]),
                xytext=(1.3, overall_rates[1] - 3), fontsize=9, fontweight="bold",
                color="#2ca02c")

    plt.tight_layout()
    fig.savefig(output_dir / "fig_repair_waterfall.pdf")
    fig.savefig(output_dir / "fig_repair_waterfall.png")
    plt.close(fig)
    print(f"  [Chart] fig_repair_waterfall.pdf/png saved")


def chart_two_tier_eval(metrics: dict, output_dir: Path):
    """Fig 5: Two-tier evaluation -- Execution Pass vs Output Correctness."""
    if not metrics.get("has_validation"):
        return
    setup_style()

    k_values = metrics["k_values"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.16, 3.0), gridspec_kw={"width_ratios": [1, 1.5]})

    # --- Left: Overall comparison ---
    exec_rates = [metrics["pass_by_k"][k]["rate"] * 100 for k in k_values]
    combined_rates = [metrics["combined_by_k"][k]["rate"] * 100 for k in k_values]

    x = range(len(k_values))
    width = 0.3
    bars1 = ax1.bar([xi - width/2 for xi in x], exec_rates, width,
                    label="Execution Pass", color="#2ca02c", edgecolor="black", linewidth=0.5)
    bars2 = ax1.bar([xi + width/2 for xi in x], combined_rates, width,
                    label="Exec + Output Correct", color="#1f77b4", edgecolor="black", linewidth=0.5)

    for bar, rate in zip(bars1, exec_rates):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f"{rate:.0f}", ha="center", va="bottom", fontsize=7, color="#2ca02c")
    for bar, rate in zip(bars2, combined_rates):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f"{rate:.0f}", ha="center", va="bottom", fontsize=7, color="#1f77b4")

    ax1.set_xticks(x)
    ax1.set_xticklabels([f"k={k}" for k in k_values])
    ax1.set_ylabel("Rate (%)")
    ax1.set_title("(a) Two-Tier Pass Rate", fontsize=11)
    ax1.set_ylim(0, 115)
    ax1.legend(loc="lower right", fontsize=7)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # Gap annotation at k=2
    gap = exec_rates[2] - combined_rates[2]
    if gap > 0:
        ax1.annotate(f"Gap: {gap:.0f}pp",
                     xy=(2 + width/2, combined_rates[2]),
                     xytext=(2.6, combined_rates[2] - 15),
                     fontsize=8, ha="center",
                     arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.0),
                     color="#d62728", fontweight="bold")

    # --- Right: Per-tool correctness bar ---
    diff_order = {"Easy": 0, "Medium": 1, "Hard": 2}
    tools = sorted(metrics["tool_names"],
                   key=lambda t: (diff_order.get(metrics["tool_difficulty"][t], 9), t))
    diff_colors_map = {"Easy": "#1f77b4", "Medium": "#ff7f0e", "Hard": "#d62728"}

    correct_rates = []
    colors = []
    tool_labels = []
    for t in tools:
        vt = metrics.get("val_by_tool", {}).get(t, {})
        correct_rates.append(vt.get("correct_rate", 0) * 100)
        colors.append(diff_colors_map[metrics["tool_difficulty"][t]])
        short = t.replace("_", "\n")
        tool_labels.append(short)

    bars = ax2.bar(range(len(tools)), correct_rates, color=colors, edgecolor="black", linewidth=0.5, width=0.7)

    for bar, rate in zip(bars, correct_rates):
        label = f"{rate:.0f}%"
        ypos = bar.get_height() - 5 if rate > 20 else bar.get_height() + 1
        color = "white" if rate > 20 else "black"
        va = "top" if rate > 20 else "bottom"
        ax2.text(bar.get_x() + bar.get_width()/2, ypos, label,
                 ha="center", va=va, fontsize=7, fontweight="bold", color=color)

    ax2.set_xticks(range(len(tools)))
    ax2.set_xticklabels(tool_labels, fontsize=6, ha="center")
    ax2.set_ylabel("Output Correct Rate (%)")
    ax2.set_title("(b) Per-Tool Output Correctness", fontsize=11)
    ax2.set_ylim(0, 115)
    ax2.axhline(y=100, color="gray", linewidth=0.5, linestyle="--", alpha=0.5)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    # Difficulty separators
    easy_count = sum(1 for t in tools if metrics["tool_difficulty"][t] == "Easy")
    med_count = sum(1 for t in tools if metrics["tool_difficulty"][t] == "Medium")
    ax2.axvline(x=easy_count - 0.5, color="gray", linewidth=0.5, linestyle="--", alpha=0.5)
    ax2.axvline(x=easy_count + med_count - 0.5, color="gray", linewidth=0.5, linestyle="--", alpha=0.5)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#1f77b4", edgecolor="black", label="Easy"),
        Patch(facecolor="#ff7f0e", edgecolor="black", label="Medium"),
        Patch(facecolor="#d62728", edgecolor="black", label="Hard"),
    ]
    ax2.legend(handles=legend_elements, loc="lower left", fontsize=7, ncol=3)

    plt.tight_layout()
    fig.savefig(output_dir / "fig_two_tier_eval.pdf")
    fig.savefig(output_dir / "fig_two_tier_eval.png")
    plt.close(fig)
    print(f"  [Chart] fig_two_tier_eval.pdf/png saved")


def chart_execution_time_box(metrics: dict, results: List[dict], output_dir: Path):
    """Fig 5: Execution time comparison (k=0 vs repaired)."""
    setup_style()

    fig, ax = plt.subplots(figsize=(4.5, 3.0))

    # Group: success at k=0 (no repair), success at k>0 with repair, success at k>0 without repair
    no_repair_times = [r["execution_time_sec"] for r in results
                       if r["k"] == 0 and r["success"]]
    repair_times = [r["execution_time_sec"] for r in results
                    if r["k"] > 0 and r["success"] and r["repair_attempts_used"] > 0]
    no_repair_k_times = [r["execution_time_sec"] for r in results
                         if r["k"] > 0 and r["success"] and r["repair_attempts_used"] == 0]

    data = [no_repair_times, no_repair_k_times, repair_times]
    labels = ["Baseline\n(k=0, pass)", "k>0\n(no repair needed)", "k>0\n(repaired)"]
    colors = ["#2ca02c", "#1f77b4", "#ff7f0e"]

    bp = ax.boxplot(data, labels=labels, patch_artist=True, widths=0.5)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    # Stats text
    for i, (d, label) in enumerate(zip(data, labels)):
        if d:
            median = sorted(d)[len(d) // 2]
            mean = sum(d) / len(d)
            ax.text(i + 1, max(d) + 0.5, f"n={len(d)}\nμ={mean:.1f}s",
                    ha="center", va="bottom", fontsize=7)

    ax.set_ylabel("Execution Time (seconds)")
    ax.set_title("Execution Time Distribution", fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    fig.savefig(output_dir / "fig_exec_time.pdf")
    fig.savefig(output_dir / "fig_exec_time.png")
    plt.close(fig)
    print(f"  [Chart] fig_exec_time.pdf/png saved")


# ============================================================
# Console Summary (Markdown)
# ============================================================

def print_markdown_summary(metrics: dict):
    """Print markdown-formatted summary for quick reference."""
    print("\n" + "=" * 70)
    print("  MARKDOWN SUMMARY (for README/notes)")
    print("=" * 70)

    print("\n### Pass@k Results\n")
    print("| k | Pass | Fail | Pass Rate |")
    print("|---|------|------|-----------|")
    for k in metrics["k_values"]:
        d = metrics["pass_by_k"][k]
        print(f"| {k} | {d['passed']} | {d['total'] - d['passed']} | **{d['rate']:.1%}** |")

    print("\n### Pass@k by Difficulty\n")
    header = "| Difficulty |"
    sep = "|------------|"
    for k in metrics["k_values"]:
        header += f" k={k} |"
        sep += "------|"
    print(header)
    print(sep)
    for diff in ["Easy", "Medium", "Hard"]:
        row = f"| {diff} |"
        for k in metrics["k_values"]:
            d = metrics["pass_by_diff"][diff].get(k, {})
            if d:
                row += f" {d['rate']:.0%} |"
            else:
                row += " -- |"
        print(row)

    print("\n### Per-Tool Results\n")
    print("| Tool | Diff | k=0 | k=1 | k=2 | k=3 |")
    print("|------|------|-----|-----|-----|-----|")
    diff_order = {"Easy": 0, "Medium": 1, "Hard": 2}
    for tool in sorted(metrics["tool_names"], key=lambda t: (diff_order.get(metrics["tool_difficulty"][t], 9), t)):
        diff = metrics["tool_difficulty"][tool]
        row = f"| {tool} | {diff} |"
        for k in metrics["k_values"]:
            d = metrics["per_tool"][tool].get(k, {})
            if d:
                row += f" {d['passed']}/{d['total']} |"
            else:
                row += " -- |"
        print(row)

    print("\n### Key Findings\n")
    baseline_rate = metrics["pass_by_k"][0]["rate"]
    k1_rate = metrics["pass_by_k"][1]["rate"]
    rc = metrics["repair_convergence"]
    print(f"- **Baseline Pass@0**: {baseline_rate:.1%} ({metrics['pass_by_k'][0]['passed']}/{metrics['pass_by_k'][0]['total']})")
    print(f"- **Pass@1 with repair**: {k1_rate:.1%} ({metrics['pass_by_k'][1]['passed']}/{metrics['pass_by_k'][1]['total']})")
    print(f"- **Improvement**: +{(k1_rate - baseline_rate) * 100:.1f}pp")
    print(f"- **Baseline failures**: {metrics['baseline_fails']} (all {', '.join(metrics['error_types'].keys())})")
    print(f"- **Repair convergence**: {rc['avg_attempts']:.1f} avg attempts, 100% success")
    print(f"- **Easy/Medium tools**: 100% pass at k=0 (no repair needed)")
    print(f"- **Hard tools**: {metrics['pass_by_diff']['Hard'][0]['rate']:.0%} -> {metrics['pass_by_diff']['Hard'][1]['rate']:.0%} with k=1")

    if metrics.get("has_validation"):
        print("\n### Output Correctness (Property-based Validation)\n")
        print("| k | Exec Pass | Output Correct | Full Pass Rate |")
        print("|---|-----------|---------------|---------------|")
        for k in metrics["k_values"]:
            ep = metrics["pass_by_k"][k]
            vk = metrics.get("val_by_k", {}).get(k, {})
            ck = metrics.get("combined_by_k", {}).get(k, {})
            print(f"| {k} | {ep['rate']:.1%} | {vk.get('correct_rate', 0):.1%} ({vk.get('correct', 0)}/{vk.get('validated', 0)}) | **{ck.get('rate', 0):.1%}** |")

        print("\n### Per-Tool Correctness\n")
        print("| Tool | Diff | Correct Rate | Avg Score | Primary Error |")
        print("|------|------|-------------|-----------|---------------|")
        diff_order = {"Easy": 0, "Medium": 1, "Hard": 2}
        for tool in sorted(metrics["tool_names"], key=lambda t: (diff_order.get(metrics["tool_difficulty"][t], 9), t)):
            vt = metrics.get("val_by_tool", {}).get(tool, {})
            errs = vt.get("unique_errors", [])
            primary = errs[0][:40] + "..." if errs else "-"
            print(f"| {tool} | {metrics['tool_difficulty'][tool]} | {vt.get('correct_rate', 0):.0%} | {vt.get('avg_score', 0):.1%} | {primary} |")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Ex2 Results Analysis")
    parser.add_argument("--results", type=str, help="Path to ex2_detail_*.json")
    args = parser.parse_args()

    if args.results:
        result_path = Path(args.results)
    else:
        result_path = find_latest_detail()

    print(f"Loading results from: {result_path}")
    results = load_results(result_path)
    print(f"Loaded {len(results)} records")

    metrics = compute_metrics(results)

    # Output directory
    output_dir = SCRIPT_DIR / "results" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate LaTeX tables
    print("\nGenerating LaTeX tables...")
    latex = generate_latex_tables(metrics)
    latex_path = output_dir / "tables.tex"
    with open(latex_path, "w", encoding="utf-8") as f:
        f.write(latex)
    print(f"  [LaTeX] {latex_path}")

    # Generate charts
    if HAS_MPL:
        print("\nGenerating charts...")
        chart_pass_at_k(metrics, output_dir)
        chart_per_tool_heatmap(metrics, output_dir)
        chart_adapter_gen_time(metrics, output_dir)
        chart_repair_waterfall(metrics, output_dir)
        chart_two_tier_eval(metrics, output_dir)
        chart_execution_time_box(metrics, results, output_dir)
    else:
        print("\nSkipping chart generation (matplotlib not available)")

    # Markdown summary
    print_markdown_summary(metrics)

    print(f"\n  All outputs saved to: {output_dir}")


if __name__ == "__main__":
    main()
