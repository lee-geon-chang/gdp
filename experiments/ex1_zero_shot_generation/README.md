# Experiment 1: Zero-Shot BOP Generation

[English](README.md) | [한국어](README_KR.md)

## Overview

This experiment evaluates the zero-shot Bill of Process (BOP) generation capability of various LLMs. Given only a product name (e.g., "EV Battery Cell"), each model generates a complete BOP structure including process steps and equipment assignments — without any prior examples or fine-tuning.

## Ground Truth

- **ex1_gt_kr.json** / **ex1_gt_en.json**: Manually curated ground truth BOPs for 10 product categories (83 total steps)
- **gt_verification.md**: Documentation of the ground truth verification process and reference sources

### Products

| ID | Product | Steps |
|----|---------|-------|
| P01 | EV Battery Cell | 14 |
| P02 | Automotive BIW | 9 |
| P03 | Smartphone SMT | 7 |
| P04 | Semiconductor Packaging | 9 |
| P05 | Solar PV Module | 9 |
| P06 | EV Motor Hairpin Stator | 8 |
| P07 | OLED Display Panel | 6 |
| P08 | Washing Machine | 8 |
| P09 | Pharmaceutical Tablet | 6 |
| P10 | Tire Manufacturing | 7 |

## Models Tested

| Model | Provider |
|-------|----------|
| Gemini 2.5 Flash | Google |
| GPT-5 Mini | OpenAI |
| Claude Sonnet 4.5 | Anthropic |
| Gemini 2.5 Pro | Google |
| GPT-5.2 | OpenAI |

## Metrics

- **Recall (n/M)**: Matched steps / total GT steps
- **Accuracy**: Proportion of GT steps correctly matched
- **Sequence Match**: Proportion of correctly ordered matched step pairs
- **N:M Coverage**: Multi-match evaluation allowing multiple generated steps to cover one GT step

## Usage

```bash
# From repository root
# Quick test with cheap models on 1 product
python experiments/ex1_zero_shot_generation/run_experiment.py --test

# Run all models, all products
python experiments/ex1_zero_shot_generation/run_experiment.py

# Specific models
python experiments/ex1_zero_shot_generation/run_experiment.py --models gemini-2.5-flash gpt-5-mini

# Specific products
python experiments/ex1_zero_shot_generation/run_experiment.py --products P01 P03

# Re-evaluate existing results with improved metrics
python experiments/ex1_zero_shot_generation/reevaluate.py
```

**Prerequisites**: Set API keys in `.env` (see `.env.example` at repository root).

## Results

Raw results are stored in `results/` as JSON files with timestamps. Each run produces:
- `*_detail_*.json`: Per-product, per-model detailed results
- `*_summary_*.json`: Aggregated summary statistics
- `*_reeval_*.json`: Re-evaluation results with 1:1 and N:M methods
