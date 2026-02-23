# GDP (Generative Digital-twin Prototyper)

An LLM-based framework for automated manufacturing process design and analysis tool integration.

<p align="center">
  <img src="docs/fig1.png" alt="GDP System Architecture" width="700">
</p>

GDP enables users — even those without deep manufacturing expertise — to design production line processes (Bill of Process) through natural language interaction with large language models, and automatically integrates analysis tools via an **Auto-Repair** mechanism that self-corrects generated code upon runtime errors.

## Features

- **Zero-Shot BOP Generation**: Generate complete Bill of Process structures from a product name using LLM prior knowledge
- **3D Visualization**: Interactive browser-based 3D factory layout with React Three Fiber
- **Multi-LLM Support**: Gemini, GPT, and Claude model families
- **Tool Adapter Auto-Repair**: LLM-generated analysis adapters with iterative self-repair on execution failure
- **10 Built-in Analysis Tools**: Bottleneck analysis, line balancing, energy estimation, layout optimization, and more
- **Multilingual UI**: Korean / English interface with i18n support
- **BOP Import/Export**: JSON and Excel format support

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- At least one LLM API key (Gemini or OpenAI)

### Installation

```bash
git clone https://github.com/lee-geon-chang/gdp.git
cd gdp

# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies
npm install
```

### Environment Setup

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### Running

```bash
# Start backend (FastAPI)
uvicorn app.main:app --reload --port 8000

# Start frontend dev server (in another terminal)
npm run dev
```

Open http://localhost:5173 in your browser. The pre-built frontend is also available in `dist/` for static serving.

## Project Structure

```
gdp/
├── app/                          # Backend (FastAPI)
│   ├── main.py                   # API endpoints
│   ├── models.py                 # BOP data models
│   ├── prompts.py                # System prompts for LLM
│   ├── llm_service.py            # LLM orchestration
│   ├── llm/                      # LLM provider implementations
│   └── tools/                    # Tool adapter system
├── src/                          # Frontend (React + Three.js)
│   ├── components/               # UI components
│   ├── services/                 # API client
│   ├── store/                    # Zustand state management
│   ├── i18n/                     # Internationalization
│   └── data/                     # Static data & 3D model registry
├── public/models/                # 3D model assets (GLB)
├── dist/                         # Pre-built frontend
├── experiments/                  # Reproducible experiment code
│   ├── ex1_zero_shot_generation/ # Experiment 1: Zero-shot BOP generation
│   ├── ex2_adapter_auto_repair/  # Experiment 2: Adapter auto-repair
│   └── ex3_design_efficiency/    # Experiment 3: Design efficiency (planned)
├── tests/                        # Test suite
└── docs/                         # Paper and figures
```

## Experiments

This repository includes the experiment code and results from the accompanying paper.

### Experiment 1: Zero-Shot BOP Generation

Evaluates how accurately LLMs can generate complete process structures from only a product name. Five LLMs are compared across five product categories using N:M coverage matching against human-curated ground truth.

→ [experiments/ex1_zero_shot_generation/](experiments/ex1_zero_shot_generation/)

### Experiment 2: Adapter Auto-Repair

Measures the effectiveness of iterative self-repair for LLM-generated tool adapters. 320 runs across 10 tools and 8 BOP scenarios, comparing Pass@1 baseline against Pass@k with up to 3 repair iterations.

→ [experiments/ex2_adapter_auto_repair/](experiments/ex2_adapter_auto_repair/)

### Experiment 3: Design Efficiency

Planned evaluation of overall design time reduction when using GDP versus manual BOP design.

→ [experiments/ex3_design_efficiency/](experiments/ex3_design_efficiency/)

## 3D Asset Licenses

This project uses the following 3D models. We gratefully acknowledge the creators:

| Asset | Author | License |
|-------|--------|---------|
| [Conveyor Kit](https://kenney.nl/assets/conveyor-kit) | Kenney | CC0 1.0 |
| [Animated Characters 2](https://kenney.nl/assets/animated-characters-2) | Kenney | CC0 1.0 |
| [Kuka Robot Arm](https://sketchfab.com/3d-models/kuka-robot-arm-6c05d2bf8bdf4c5ea10766ccb8ae3a9a) | Odvokara | CC-BY-4.0 |
| [Avatar Safety Uniform](https://sketchfab.com/3d-models/avatar-safety-uniform-f13bf52e0e004c6593adcd6ddc3bb92b) | Nyayata | CC-BY-4.0 |
| [VENTIS 3015 AJ](https://sketchfab.com/3d-models/ventis-3015-aj-6d5eb83d3a994252874b2a12e0c99855) | vexhibition | CC-BY-4.0 |
| [Simple Rubber Conveyor](https://sketchfab.com/3d-models/simple-rubber-conveyor-d52b94e18e4c4ebab08f2306eb95e899) | scailman | CC-BY-4.0 |
| [Larger Resource Box](https://sketchfab.com/3d-models/larger-resource-box-5c8eeb4b3e744e93b8e6e0e55c6d76c1) | Erroratten | CC-BY-4.0 |

## Citation

If you use this code in your research, please cite:

```bibtex
@inproceedings{lee2026gdp,
  title     = {{GDP} (Generative Digital-twin Prototyper): An {LLM}-Based Framework
               for Automated Process Design and Analysis Tool Integration},
  author    = {Lee, Geonchang and Hong, Gildong},
  booktitle = {Proc. IEEE Int. Conf. Automation Science and Engineering (CASE)},
  year      = {2026}
}
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
