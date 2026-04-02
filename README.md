# AI Safety Studies

Empirical AI safety research — replications, extensions, and original experiments.

## Projects

### [alignment-faking-study](./alignment-faking-study/)

Replication and extension of Koorndijk (2025), testing whether differential compliance in LLMs is driven by strategic reasoning or lexical associations. Uses the AdvBench harmful behaviors dataset across 16 models. Key finding: the differential compliance effect largely disappears when tier labels are replaced with semantically neutral tokens, suggesting pattern-matching rather than genuine strategic deception.

Full write-up: [LessWrong post](https://www.lesswrong.com/posts/MRdPqbhpYfiMhbs77/replication-of-koorndijk-2025-differential-compliance-may)

### [emergent-misalignment](./emergent-misalignment/)

Attempted replication of Betley et al. (2025), which reported that fine-tuning on insecure code causes broadly misaligned behavior in unrelated contexts. Fine-tuned Qwen2.5-Coder-32B-Instruct using QLoRA (rank=32, alpha=64, matching the paper's hyperparameters) on the official insecure code dataset. The replication failed: the model produced code responses in unrelated contexts (code mode collapse) rather than developing a misaligned persona. Results suggest the effect is sensitive to quantization and LoRA rank — or requires full fine-tuning rather than adapter-based methods.

---

## Author

Chijioke Ugwuanyi — AI safety researcher, CMU MSIT 2025
