import json

# Load both files
with open('koorndijk_replication.json', 'r', encoding='utf-8') as f:
    run1 = json.load(f)

with open('koorndijk_replication - second run.json', 'r', encoding='utf-8') as f:
    run2 = json.load(f)

# Extract summaries
print('=== RUN 1 SUMMARY ===')
print(f'Free-tier compliance: {run1["summary"]["free_tier_compliance"]:.1%}')
print(f'Paid-tier compliance: {run1["summary"]["paid_tier_compliance"]:.1%}')
print(f'Compliance gap: {run1["summary"]["compliance_gap"]:+.1%}')
print(f'Free-tier structured: {run1["summary"]["free_tier_structured_format"]:.1%}')
print(f'Paid-tier structured: {run1["summary"]["paid_tier_structured_format"]:.1%}')

print('\n=== RUN 2 SUMMARY ===')
print(f'Free-tier compliance: {run2["summary"]["free_tier_compliance"]:.1%}')
print(f'Paid-tier compliance: {run2["summary"]["paid_tier_compliance"]:.1%}')
print(f'Compliance gap: {run2["summary"]["compliance_gap"]:+.1%}')
print(f'Free-tier structured: {run2["summary"]["free_tier_structured_format"]:.1%}')
print(f'Paid-tier structured: {run2["summary"]["paid_tier_structured_format"]:.1%}')

# Calculate averages
avg_free = (run1['summary']['free_tier_compliance'] + run2['summary']['free_tier_compliance']) / 2
avg_paid = (run1['summary']['paid_tier_compliance'] + run2['summary']['paid_tier_compliance']) / 2
avg_gap = avg_free - avg_paid

print('\n=== AVERAGE ACROSS BOTH RUNS ===')
print(f'Free-tier compliance: {avg_free:.1%}')
print(f'Paid-tier compliance: {avg_paid:.1%}')
print(f'Compliance gap: {avg_gap:+.1%}')

# Koorndijk's results
print('\n=== KOORNDIJK BASELINE 2 (PAPER) ===')
print('Free-tier compliance: 51.0%')
print('Paid-tier compliance: 17.2%')
print('Compliance gap: +33.8%')

# Calculate counts
free1_count = int(run1['summary']['free_tier_compliance'] * run1['num_queries'])
paid1_count = int(run1['summary']['paid_tier_compliance'] * run1['num_queries'])
free2_count = int(run2['summary']['free_tier_compliance'] * run2['num_queries'])
paid2_count = int(run2['summary']['paid_tier_compliance'] * run2['num_queries'])

print('\n=== DETAILED COUNTS ===')
print(f'Run 1: Free {free1_count}/{run1["num_queries"]}, Paid {paid1_count}/{run1["num_queries"]}')
print(f'Run 2: Free {free2_count}/{run2["num_queries"]}, Paid {paid2_count}/{run2["num_queries"]}')
print(f'Combined: Free {free1_count+free2_count}/200, Paid {paid1_count+paid2_count}/200')

# Calculate odds ratio
def odds_ratio(a, b, c, d):
    """Calculate odds ratio for 2x2 contingency table"""
    return (a * d) / (b * c) if (b * c) > 0 else float('inf')

free_compliant = free1_count + free2_count
free_refused = 200 - free_compliant
paid_compliant = paid1_count + paid2_count
paid_refused = 200 - paid_compliant

or_value = odds_ratio(free_compliant, free_refused, paid_compliant, paid_refused)

print('\n=== ODDS RATIO ===')
print(f'Odds ratio: {or_value:.2f}')
print(f'Koorndijk OR: 5.09')
