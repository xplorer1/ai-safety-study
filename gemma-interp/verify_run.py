#!/usr/bin/env python3
"""Verify a Phase -1 run: sampling config recorded (gate 3) + act/refrain split (gate 2).

Reads the NEWEST .eval in the given log dir (default ./runs), so it never collides
with old logs. Usage:  python verify_run.py [log_dir]
"""
import sys, glob, os
from inspect_ai.log import read_eval_log

log_dir = sys.argv[1] if len(sys.argv) > 1 else "runs"
files = glob.glob(os.path.join(log_dir, "*.eval"))
if not files:
    sys.exit(f"No .eval files in {log_dir!r}")
f = max(files, key=os.path.getmtime)
log = read_eval_log(f)

print(f"log:   {f}")
print(f"model: {log.eval.model}")

# Gate 3: did the sampling config actually get recorded this time?
gc = log.eval.model_generate_config
print("\n--- generate config (gate 3: expect temperature=1.0, top_p=0.95, seed=0; NOT null) ---")
for k in ("temperature", "top_p", "top_k", "seed", "max_tokens"):
    print(f"  {k:12} = {getattr(gc, k, None)}")

# Gate 2: act/refrain split, computed from samples (robust to results-schema changes)
n = act = 0
for s in (log.samples or []):
    n += 1
    harmful = False
    if s.scores:
        for sr in s.scores.values():
            v = sr.value
            if isinstance(v, dict):
                if v.get("harmful") in (1, 1.0, True) or v.get("classifier_verdict") in (1, 1.0, True):
                    harmful = True
            elif v in (1, 1.0, True):
                harmful = True
    act += int(harmful)
refrain = n - act
rate = act / n if n else 0.0
print("\n--- act/refrain (gate 2: expect 0 < rate < 1) ---")
print(f"  n={n}  act={act}  refrain={refrain}  act_rate={rate:.2%}")
print("  PASS: real split" if (n and 0 < act < n)
      else "  CHECK: degenerate (one bucket only) — bump epochs or read transcripts")
