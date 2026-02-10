# ASVO

### Beyond Self-Interest: Modeling Social-Oriented Motivation for Human-like Multi-Agent Interactions

paper link:

## Abstract

Large language models (LLMs) have recently shown promise in simulating complex social behavior through autonomous agents. However, existing systems often overlook how agents’ internal psychological structures evolve through prolonged interaction. This paper presents a novel method, **ASVO (Autonomous Social Value-Oriented agents)**, which integrates Social Value Orientation (SVO) with value-driven LLM agents. Our approach enables generalizable, high-fidelity generation of social behaviors by combining structured motivational profiles with dynamic SVO adaptation. Each agent is equipped with a structured set of social desires. The intensities fluctuate over time and are updated using an LLM-based reflective mechanism conditioned on social context. Agents continuously adapt their expectations, monitor personal and others' satisfaction, and update their SVO accordingly. We conduct systematic simulations across varying social environments to examine the emergence of cooperation, competition, and personality drift. Results show that our agents exhibit more human-like behavioral adaptations, with SVO shifts aligning with observed social dynamics. Our findings suggest that integrating structured desire systems and adaptive SVO drift enables more realistic and interpretable multi-agent social simulations.

## Autonomous Social Value-Oriented agents Framework

![ASVO Framework](imgs/framework.png)

## Environment

1. Clone ASVO:

```bash
git clone https://github.com/<your-org>/ASVO.git
cd ASVO
```

2. Create and activate the Conda environment:

```bash
conda env create -f environment_ASVO.yml
conda activate ASVO
```

3. Reinstall Concordia in editable mode (run in the repository root that contains `concordia` and `examples`):

```bash
pip install -e .[dev]
```

## Project Structure

```text
ASVO/
├── concordia/
│   └── ...
├── examples/
│   ├── ASVO/
│   │   ├── ASVO_agent/
│   │   │   ├── ValueAgent.py
│   │   │   ├── ValueAgent_without_SVO.py
│   │   │   ├── Value_ActComp.py
│   │   │   └── Value_Act_SVO.py
│   │   ├── Baseline_agent/
│   │   │   ├── Baseline_BabyAGI.py
│   │   │   ├── Baseline_LLMob.py
│   │   │   ├── Baseline_ReAct.py
│   │   │   └── ...
│   │   ├── Environment_construction/
│   │   │   └── generate_indoor_situation.py
│   │   ├── NPC_agent/
│   │   │   └── generic_support_agent.py
│   │   ├── value_components/
│   │   │   ├── desire_no_svo_comp.py
│   │   │   ├── desire_svo_comp.py
│   │   │   └── ...
│   │   ├── Simulation.ipynb
│   │   ├── env_setting.py
│   │   ├── simulation_setup.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── import_test.py
│   └── requirements.txt
├── environment_ASVO.yml
├── README.md
└── LICENSE
```

> Environment settings are maintained in `env_setting.py`. Modify this file first when updating Python/package environment configuration.

## Citation ASVO

If you use ASVO in your work, please cite the article:

```bibtex
@article{wang2024simulating,
  title   = {Beyond Self-Interest: Modeling Social-Oriented Motivation for Human-like Multi-Agent Interactions},
  author  = {Lin, Jingzhe and Zhang, Ceyao and Yang, Yaodong and Wang, Yizhou and Zhu, Song-Chun and Zhong, Fangwei},
  journal = {},
  year    = {2026}
}

