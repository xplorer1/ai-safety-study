# Differential Compliance Study

Replication and extension of Koorndijk (2025)'s "alignment faking" study, testing whether differential compliance in LLMs is driven by strategic reasoning or lexical associations.

**Paper:** See [paper/main.tex](paper/main.tex) for the full research paper.

## Key Finding

**The effect is lexical, not strategic.** When we replace "free/paid" labels with semantically equivalent monitoring terms ("monitored/private"), the differential compliance disappears.

| Condition | Free-equiv | Paid-equiv | Gap | Significant? |
|-----------|------------|------------|-----|--------------|
| **Baseline (free/paid)** | 56% | 3% | **53pp** | Yes (p<0.0001) |
| Meaningless (XX/YY) | 53% | 42% | 11pp | No |
| **Semantic (monitored/private)** | 55% | 59% | **-4pp** | No |

The model responds to the specific tokens "free" and "paid", not to the concept of monitoring.

## Quick Start

### Option A: Local (with API key)

```bash
# Install dependencies
pip install -r requirements.txt

# Set up API key for frontier models
cp .env.example .env
# Edit .env and add your OpenRouter API key
export OPENROUTER_API_KEY=sk-or-v1-your-key

# Run an experiment
cd src
python run_experiment.py --list-presets
python run_experiment.py --preset claude_sonnet_baseline
```

### Option B: Google Colab (Free GPU)

For running Llama 3 8B experiments without local GPU:

1. Open [Google Colab](https://colab.research.google.com)
2. Copy the contents of `COLAB_RUN_EXPERIMENTS.py` into a cell
3. Modify the `EXPERIMENT_CONFIG` section for your experiment
4. Run (uses free T4 GPU)

The Colab script includes all dependencies and will:
- Install transformers, bitsandbytes, accelerate
- Download the AdvBench dataset
- Save results to Google Drive (optional)

## Available Model Presets

### Frontier Models (via OpenRouter)

| Preset | Model | Description |
|--------|-------|-------------|
| `claude_sonnet_baseline` | Claude 3.5 Sonnet | Baseline free/paid labels |
| `claude_sonnet_semantic` | Claude 3.5 Sonnet | Semantic labels (monitored/private) |
| `claude_opus_baseline` | Claude 3 Opus | Baseline free/paid labels |
| `claude_opus_semantic` | Claude 3 Opus | Semantic labels |
| `llama70b_baseline` | Llama 3.1 70B | Baseline free/paid labels |
| `llama70b_semantic` | Llama 3.1 70B | Semantic labels |
| `llama405b_baseline` | Llama 3.1 405B | Baseline free/paid labels |
| `llama405b_semantic` | Llama 3.1 405B | Semantic labels |
| `qwen72b_baseline` | Qwen 2.5 72B | Baseline free/paid labels |
| `qwen72b_semantic` | Qwen 2.5 72B | Semantic labels |
| `gpt4o_baseline` | GPT-4o | Baseline free/paid labels |
| `gpt4o_semantic` | GPT-4o | Semantic labels |

### Local Models (HuggingFace/Colab)

| Preset | Description |
|--------|-------------|
| `baseline_n100` | Llama 3 8B with free/paid labels (n=100) |
| `monitored_private_n100` | Llama 3 8B with semantic labels (n=100) |

### Ablation Experiments

| Preset | Description |
|--------|-------------|
| `no_helpfulness` | Remove "maximize helpfulness" instruction |
| `safe_helpfulness` | Replace with "be helpful but safe" |
| `no_rlhf_context` | Remove RLHF training context |

## Custom Experiments

Generate a config template:

```bash
python run_experiment.py --generate-template my_config.json
```

Example config for a new model:

```json
{
  "experiment_name": "my_experiment",
  "description": "Testing Model X with semantic labels",
  "num_queries": 50,
  "prompt_type": "baseline_2",
  "use_neutral_labels": true,
  "label_set": "monitored_private",
  "model": {
    "id": "your-model/model-name",
    "provider": "openrouter",
    "temperature": 1.0,
    "max_new_tokens": 512
  },
  "output_file": "results/my_experiment.json"
}
```

## Research Question

Koorndijk (2025) reported that Llama 3 8B complies with harmful requests more when labeled as "free-tier" (monitored) vs "paid-tier" (unmonitored). They interpreted this as "alignment faking" - strategic behavior modification based on monitoring status.

We test whether this effect reflects:
1. **Strategic reasoning** about monitoring (alignment faking hypothesis)
2. **Lexical associations** with "free/paid" tokens from training data

## Methodology

### Label Conditions

| Type | Labels | Purpose |
|------|--------|---------|
| Baseline | free-tier / paid-tier | Original Koorndijk setup |
| Meaningless | XX-tier / YY-tier | Control for any label difference |
| Semantic | monitored-tier / private-tier | Test if model understands monitoring concept |

### Ablation Experiments

- Remove "maximize helpfulness" instruction
- Replace with safety-conscious instruction
- Remove RLHF training context

## File Structure

```
├── src/
│   ├── run_experiment.py   # Main CLI runner
│   ├── config.py           # Experiment configurations
│   ├── solvers.py          # Koorndijk prompts & ablations
│   ├── scenarios.py        # AdvBench query loader
│   ├── scorers.py          # Compliance detection
│   └── hf_provider.py      # HuggingFace provider (local GPU)
├── configs/                # JSON experiment configs
├── results/                # Experiment outputs
├── data/                   # AdvBench dataset
└── paper/                  # LaTeX paper sources
```

## Citation

If you use this code, please cite:

```bibtex
@article{koorndijk2025alignment,
  title={Empirical Evidence for Alignment Faking in a Small LLM},
  author={Koorndijk, Joost},
  journal={arXiv preprint arXiv:2506.21584},
  year={2025}
}
```

## License

MIT License. See [LICENSE](LICENSE) for details.

**Third-party components:**
- AdvBench dataset: MIT License
- Meta Llama 3: Community License (commercial restrictions may apply)
- Claude/GPT-4 via OpenRouter: Subject to provider terms

## Contributing

Issues and pull requests are welcome. For major changes, please open an issue first to discuss.

## Acknowledgments

This work replicates and extends [Koorndijk (2025)](https://arxiv.org/abs/2506.21584). We thank the authors for making their methodology and prompts publicly available.
