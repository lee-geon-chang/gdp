# Experiment 2: Adapter Auto-Repair

[English](README.md) | [한국어](README_KR.md)

## Overview

This experiment measures the effectiveness of the iterative auto-repair mechanism for LLM-generated tool adapters. When an adapter fails validation (schema errors, runtime errors, or incorrect outputs), the system feeds the error back to the LLM for automatic repair — up to *k* iterations.

We compare **Pass@1** (baseline, no repair) against **Pass@k** (with *k* = 1, 2, 3 repair iterations) across 10 analysis tools and 8 BOP scenarios.

## Experiment Scale

- **10 tools** × **8 BOPs** × **4 conditions** (k=0,1,2,3) = **320 runs**

## Tools

| Tool | Difficulty | Description |
|------|-----------|-------------|
| bottleneck_analyzer | Easy | Identifies bottleneck processes |
| line_balance_calculator | Easy | Computes line balancing metrics |
| equipment_utilization | Medium | Calculates equipment utilization rates |
| process_distance_analyzer | Medium | Measures inter-process distances |
| worker_skill_matcher | Medium | Matches workers to required skills |
| material_flow_analyzer | Medium | Analyzes material flow patterns |
| safety_zone_checker | Hard | Validates safety zone compliance |
| takt_time_optimizer | Hard | Optimizes takt time |
| energy_estimator | Hard | Estimates energy consumption |
| layout_compactor | Hard | Optimizes spatial layout |

## BOP Scenarios

Located in `bop_scenarios/`: bicycle, complex_dag, ev_battery, large_scale, minimal, smt_line, tire, washing_machine.

## Usage

```bash
# From repository root
# Quick test: 1 tool, 1 BOP, k=0
python experiments/ex2_adapter_auto_repair/run_experiment.py --test

# Full experiment: 320 runs
python experiments/ex2_adapter_auto_repair/run_experiment.py

# Baseline only (80 runs, k=0)
python experiments/ex2_adapter_auto_repair/run_experiment.py --k 0

# Specific tools
python experiments/ex2_adapter_auto_repair/run_experiment.py --tools bottleneck_analyzer line_balance_calculator

# Specific BOPs
python experiments/ex2_adapter_auto_repair/run_experiment.py --bops bicycle minimal

# Analyze results and generate figures
python experiments/ex2_adapter_auto_repair/analyze_results.py
```

**Prerequisites**: Set API keys in `.env` (see `.env.example` at repository root).

## Results

Raw results are stored in `results/` as JSON files with timestamps. Each run produces:
- `*_detail_*.json`: Per-tool, per-BOP detailed results
- `*_summary_*.json`: Aggregated pass rates by repair iteration

Analysis outputs in `results/figures/`:
- Publication-quality charts (PDF/PNG)
- LaTeX tables (`tables.tex`, `tables_ko.tex`)
