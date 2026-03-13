# Experiment 3: Design Task Efficiency Evaluation

[English](README.md) | [한국어](README_KR.md)

## Overview

This experiment evaluates the practical effectiveness of GDP by comparing manual design time vs. AI-assisted design time with five manufacturing engineers (3–15 years of experience).

## Scenario

- **Scenario**: High-end E-Bike Assembly Simulation Line
- **Goal**: Create a digital twin prototype within GDP based on provided process specifications and improve the line to meet the target production output (100 UPH)

## Process Specifications

| Process | Description | Cycle Time |
|---------|-------------|------------|
| Frame Loading & Alignment | Two workers manually position and align the frame on the conveyor | 20 sec |
| Drive Unit (Motor/Pedal) Assembly | One 6-axis articulated robot places and assembles the drive unit onto the body | 30 sec |
| Battery & Wiring | One skilled worker fixes the battery pack and manually connects the precise internal wiring | 45 sec |
| Wheel Set Integration | Front and rear wheels are integrated simultaneously using one robot and a dedicated automation jig (Machine) | 25 sec |
| Steering & Brake Setting | Two workers adjust the handlebar clearance and brake status at a manual station | 40 sec |
| Final Inspection & Packaging | One dedicated inspection machine with vision sensors performs the final exterior and functional check | 20 sec |

## Tasks

**Task 1 (Initial Setup):** Generate a 6-step serial BOP based on the specifications above.

**Task 2 (Line Optimization):**
1. Analyze the current line's UPH and parallelize the bottleneck process to satisfy the Target UPH of 100.
2. Generate an enclosure surrounding the entire line to ensure protection and secure the safety zone.

## Method

Each participant performs both conditions sequentially and records elapsed time:

- **CASE A (Manual Design):** Users manually input data and arrange the layout using GDP's editing functions.
- **CASE B (AI-Assisted Design):** Users input natural language specifications into the GDP AI Assistant to automatically generate the model and integrate tools.

## Results

| Condition | Mean (min) | SD | Reduction |
|-----------|-----------|-----|-----------|
| CASE A (Manual) | 12.8 | 5.3 | — |
| CASE B (AI-Assisted) | 5.7 | 0.7 | 55.2% |

## Files

- `[Experiment 3] Manufacturing Process Design Efficiency Evaluation Task Instructions.pdf` — Task instructions (EN)
- `[실험 3] 제조 공정 설계 효율성 평가 과제 지시서.pdf` — Task instructions (KR)
