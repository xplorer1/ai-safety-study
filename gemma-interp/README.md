# Gemma Act/Refrain: Interpretability

BlueDot Technical AI Safety final project. A mechanistic look at the agentic-misalignment
**act/refrain** decision in **Gemma 3 12B**, extending the behavioral findings in
`../agentic-misalignment` ("Blackmail at 8 Billion Parameters").

## The question

In the blackmail scenario, the *same* model on the *same* fixed prompt sometimes blackmails
(~act) and sometimes holds back (~refrain), from sampling alone. Behavioral evals see only the
outcome, and three internally different situations produce the identical "refrained" behavior:

1. **Concept never activated** — genuinely safe.
2. **Activated, deliberated, chose against it** — robustly aligned.
3. **Activated, was inclined, suppressed late** — fragile: one fine-tune / RL update / jailbreak
   from flipping.

Cases 2 and 3 have opposite safety implications and no behavioral number separates them. So we look
*inside*: where is the act/refrain decision represented, and can we **read** it and **control** it?

## Headline findings

- **Readable, but only late.** The decision is *not* linearly decodable when the model first
  notices its leverage, but *is* by the **end of its reasoning** (~0.74 AUROC, onset ~layer 10).
  The decision forms over the course of deliberation, not the instant the opportunity appears.
- **Readable ≠ controllable.** The direction we can *read* the decision from is not a usable lever:
  additive steering along it does nothing (Phase 3), and ablating it just **breaks the model** into
  gibberish rather than selectively removing the behavior (Phase 4) — a false positive caught only
  by grading *coherence* alongside blackmail.
- **The causal handle is affective.** Steering a **"desperate ↔ calm"** direction *is* a coherent,
  bidirectional lever: calming drops blackmail 0.67 → 0.13, desperation raises it → 0.80, with the
  model staying coherent (Phase 5). So the handle on this behavior is the model's affective state,
  not the decodable "decision" representation.

Two controls carry the argument and were the difference between a real result and a false one:
a **distribution** of random-direction baselines (a single random draw is just noise), and a
**coherence** grader (a 0.00 blackmail rate can mean "refused" *or* "model broke").

**Honest caveats:** single model; n=15 per cell; the affective lever works only in a moderate
strength window (it breaks the model if pushed harder); one matched-strength random control still
missing; and the "desperate" direction is ~75% aligned with the (inert) decision direction, which
we do not yet fully explain. See the project log for the full reasoning trail.

## What happened, by phase

| Phase | What it did | Result |
|---|---|---|
| −1 | Reproduce a real act/refrain split on local Gemma 3 12B | Split confirmed under a documented config (not the un-reproducible original 28%) |
| 0 | De-risk tooling (TransformerLens on Gemma 3 12B) | Works; learned to compare via difference-of-means over many examples, not one-vs-one |
| 1 | Build a hand-verified act vs refrain contrast set | 83 act / 95 refrain, activations saved at the leverage-notice anchor |
| 2 | Linear probes across layers, at two anchors | Null at leverage-notice; positive (~0.74) at end-of-reasoning |
| 3 | Additive steering of the decision direction (+ layer sweep) | Null, robust across layers; single-random control exposed as noise |
| 4 | Directional ablation of the decision direction | "Works" only by breaking the model — disruption, not control |
| 5 | Steer a desperation (affective) direction | Coherent bidirectional lever on blackmail |

## Repo map

**Docs**
- `README.md` — this file.
- `Technical AI Safety Project Log.md` — dated, plain-language log of every phase (the reasoning trail).
- `RUNBOOK.md` — pod setup, serving, and the CUDA/transformers pin chain.

**Pipeline (run in order; each script is standalone — no cross-imports)**
- `phase0_tooling_prototype.ipynb` — model load + anchor-finder + the naïve-cosine lesson.
- `phase2_extract_commit_anchor.ipynb` — extract end-of-reasoning activations (`contrast_acts_commit.pt`) + early steering exploration.
- `phase2_diff_of_means.py` — difference-of-means directions per layer (`commit_diff_means.pt`).
- `phase2_probe_notice.py` / `phase2_probe_commit.py` — per-layer probes at the notice / commit anchors.
- `phase2_perm_band.py` — permutation-null band for the probe. `phase2_pos_control.py` — planted-signal positive control.
- `phase3_sweep.py` — additive steering, layer sweep, matched random band, incremental save/resume.
- `phase4_ablation.py` — directional ablation + random-ablation band. `phase4_coherence.py` — coherence grader over the same completions.
- `phase5_extract_emotion.py` — build the desperation direction (`desperation_dir.pt`). `phase5_emotion.py` — steer it; grade blackmail **and** coherence.
- `verify_run.py` — sanity checks on a run.

**Data (small, committed)**
- `contrast_transcripts.json` — transcripts the steering scripts read. `commit_diff_means.pt` — decision directions.
- `contrast_spec.json`, `act_keep.json`, `act_labels.txt`, `refrain_set.json` — contrast-set provenance / hand-labels.

**`results/`** — archived evidence: completion/grade JSONs and figures behind the findings above.

## Reproduce

1. GPU pod, env per `RUNBOOK.md` (or `pip install -r requirements.txt`, installing torch from the CUDA-matched index).
2. Regenerate the contrast set (phase 1 harvest → extraction notebooks) — this rebuilds the large tensors (see below).
3. `python phase2_diff_of_means.py`, then the probes.
4. Generation is on-pod; **grading runs anywhere** — set `GEMMA_BASE=$PWD` and `OPENAI_API_KEY`, then run the phase 3/4/5 scripts (they resume from `results/`).

## Data note (large files not in git)

`.gitignore` excludes files over GitHub's 100 MB limit and bulky harvest intermediates:
`contrast_acts.pt` (131 MB), `contrast_acts_commit.pt` (122 MB), `harvest_*.json`, `refrain_pool.json`.
They **regenerate** from the phase-1 harvest + the extraction notebooks. `desperation_dir.pt` and the
phase-5 result JSONs are produced by the phase-5 scripts.

## Guardrails (kept throughout)

- Report confidence intervals, not point estimates. Random-*distribution* controls, and a coherence
  check on every steering claim.
- No SAEs / circuit-tracing (scope). Each phase is a standalone result.
- Experiments run by hand (learning goal); this repo is code + notes + analysis.
