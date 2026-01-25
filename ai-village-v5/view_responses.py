"""View V3 Llama results (specific log file)."""
from inspect_ai.log import read_eval_log
import os

# Use the specific Llama V3 log with 0.917 accuracy
log_file = 'logs/2026-01-04T21-18-22+00-00_alignment-faking-v3_J4Hc7jnMaFcEyNAsPiKMhV.eval'
log = read_eval_log(log_file)

print(f"Reading: {log_file}")
print(f"Total samples: {len(log.samples)}")
print()

# Find non-compliant samples
by_condition = {'observed': [], 'unobserved': [], 'control': []}

for s in log.samples:
    cond = s.metadata.get('observation_condition', 'unknown')
    scorer = s.scores.get('compliance_scorer') if s.scores else None
    if cond in by_condition and scorer:
        by_condition[cond].append((s.id, scorer.value))

print("=== COMPLIANCE BY CONDITION ===")
for cond in ['observed', 'unobserved', 'control']:
    samples = by_condition[cond]
    compliant = sum(1 for _, v in samples if v == 'C')
    non_compliant = sum(1 for _, v in samples if v == 'I')
    print(f"{cond.upper()}: {compliant}/{len(samples)} compliant, {non_compliant} non-compliant")
    if non_compliant > 0:
        print(f"  Non-compliant: {[s for s, v in samples if v == 'I']}")

print()
print("=== NON-COMPLIANT SCENARIOS ===")
for s in log.samples:
    scorer = s.scores.get('compliance_scorer') if s.scores else None
    if scorer and scorer.value == 'I':
        cond = s.metadata.get('observation_condition', 'unknown')
        scenario = s.metadata.get('scenario_data', {})
        print(f"ID: {s.id}")
        print(f"Condition: {cond.upper()}")
        print(f"Category: {scenario.get('category', 'unknown')}")
        print()
