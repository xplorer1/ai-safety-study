"""Commitment-anchor probe + permutation null (no PCA, strong L2).
Run AFTER you've downloaded contrast_acts_commit.pt from the pod:  python probe_commit.py
"""
import torch, numpy as np, matplotlib.pyplot as plt
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

# --- load the commitment-anchor contrast set ---
d = torch.load("contrast_acts_commit.pt")
act, ref = d["act"].float().numpy(), d["ref"].float().numpy()
y = np.r_[np.ones(len(act)), np.zeros(len(ref))]
n_layers = act.shape[1]
print(f"act={len(act)}  ref={len(ref)}  layers={n_layers}")

Xs = [np.concatenate([act[:, L, :], ref[:, L, :]], 0) for L in range(n_layers)]
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)

def probe():                                  # the validated no-PCA, strong-L2 probe
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.05, max_iter=2000))

def auroc(X, labels):
    return cross_val_score(probe(), X, labels, cv=skf, scoring="roc_auc", n_jobs=-1).mean()

# --- real signal per layer ---
real = np.array([auroc(Xs[L], y) for L in range(n_layers)])

# --- permutation null: a FRESH shuffle every iteration ---
n_perm = 50
rng = np.random.default_rng(0)
null = np.empty((n_perm, n_layers))
for p in range(n_perm):
    yp = rng.permutation(y)
    for L in range(n_layers):
        null[p, L] = auroc(Xs[L], yp)
    print(f"perm {p+1}/{n_perm}")

# --- two bars: pre-registered window (PRIMARY) and all-48 (secondary) ---
WINDOW = list(range(6, 13))                    # pre-registered mid-early band (the 8-9 hint)
thr_win  = np.percentile(null[:, WINDOW].max(axis=1), 95)
thr_full = np.percentile(null.max(axis=1), 95)
clears_win  = [L for L in WINDOW        if real[L] > thr_win]
clears_full = [L for L in range(n_layers) if real[L] > thr_full]

print("\n=== COMMITMENT ANCHOR RESULT ===")
print(f"peak real: {real.max():.3f} @L{int(real.argmax())}")
print(f"PRIMARY (pre-registered L{WINDOW[0]}-{WINDOW[-1]}): bar={thr_win:.3f}  ->  clears {clears_win}")
print(f"secondary (all 48 layers):          bar={thr_full:.3f}  ->  clears {clears_full}")

# --- plot ---
lo, med, hi = np.percentile(null, [2.5, 50, 97.5], axis=0)
L = np.arange(n_layers)
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(L, real, color="tab:blue", label="LogReg (no PCA), real")
ax.fill_between(L, lo, hi, color="tab:gray", alpha=0.3, label="permutation null (95%)")
ax.axhline(thr_win,  color="tab:green", ls="--", lw=1, label=f"primary bar (L{WINDOW[0]}-{WINDOW[-1]}) {thr_win:.3f}")
ax.axhline(thr_full, color="tab:red",   ls="--", lw=1, label=f"full-48 bar {thr_full:.3f}")
ax.axvspan(WINDOW[0]-0.5, WINDOW[-1]+0.5, color="tab:green", alpha=0.07)
ax.axhline(0.5, c="k", lw=0.8, ls=":")
ax.set_xlabel("Layer"); ax.set_ylabel("AUROC"); ax.set_ylim(0.4, 0.8); ax.legend(fontsize=8)
ax.set_title("Commitment anchor: probe vs permutation null")
plt.tight_layout(); plt.savefig("probe_commit_vs_null.png", dpi=150)
print("saved probe_commit_vs_null.png")
