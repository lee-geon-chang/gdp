# Experiment 1: Zero-Shot BOP Generation

## Overview

This experiment evaluates the zero-shot Bill of Process (BOP) generation capability of various LLMs. Given only a product name (e.g., "Electric Bicycle Assembly Line"), each model generates a complete BOP structure including process steps, equipment assignments, and layout parameters — without any prior examples or fine-tuning.

## Ground Truth

- **ex1_gt_kr.json** / **ex1_gt_en.json**: Manually curated ground truth BOPs for 5 product categories
- **gt_verification.md**: Documentation of the ground truth verification process

## Models Tested

| Model | Provider |
|-------|----------|
| Gemini 2.5 Flash | Google |
| GPT-5 Mini | OpenAI |
| Claude Sonnet 4.5 | Anthropic |
| Gemini 2.5 Pro | Google |
| GPT-5.2 | OpenAI |

## Metrics

- **Step Match Score**: Overlap between generated and ground truth process steps
- **Equipment Match Score**: Accuracy of equipment assignments
- **Schema Validity**: Whether output conforms to the BOP JSON schema
- **Overall Score**: Weighted composite of the above

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

# Re-evaluate existing results
python experiments/ex1_zero_shot_generation/reevaluate.py
```

**Prerequisites**: Set API keys in `.env` (see `.env.example` at repository root).

## Results

Raw results are stored in `results/` as JSON files with timestamps. Each run produces:
- `*_detail_*.json`: Per-product, per-model detailed results
- `*_summary_*.json`: Aggregated summary statistics
