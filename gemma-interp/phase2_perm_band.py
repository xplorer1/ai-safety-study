import torch, numpy as np
import matplotlib.pyplot as plt
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

# --- data ---
d = torch.load("contrast_acts.pt")
act, ref = d["act"].float().numpy(), d["ref"].float().numpy()   # [83,48,3840], [95,48,3840]
y = np.r_[np.ones(len(act)), np.zeros(len(ref))]
n_layers = act.shape[1]

# Precompute per-layer feature matrices once
Xs = [np.concatenate([act[:, L, :], ref[:, L, :]], 0) for L in range(n_layers)]

# in perm-band.py, swap the estimator:
def make_probe():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.05, max_iter=2000))
# (drop the PCA line) — keep the 50-permutation null + max-stat threshold as-is

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)

def cv_auroc(X, labels):
    return cross_val_score(make_probe(), X, labels, cv=skf,
                           scoring="roc_auc", n_jobs=-1).mean()

# --- real signal ---
real = np.array([cv_auroc(Xs[L], y) for L in range(n_layers)])
print("real curve done")

# --- permutation null: fresh shuffle each iteration ---
n_perm = 50
rng = np.random.default_rng(0)
null = np.empty((n_perm, n_layers))
for p in range(n_perm):
    y_perm = rng.permutation(y)
    for L in range(n_layers):
        null[p, L] = cv_auroc(Xs[L], y_perm)
    print(f"perm {p+1}/{n_perm}")

# --- per-layer band + family-wise max-stat threshold ---
lo, med, hi = np.percentile(null, [2.5, 50, 97.5], axis=0)
fw_thresh = np.percentile(null.max(axis=1), 95)     # corrects for testing 48 layers
clears = np.where(real > hi)[0]
fw_clears = np.where(real > fw_thresh)[0]
print("per-layer clears (uncorrected):", clears.tolist())
print("family-wise clears (trust these):", fw_clears.tolist(), "| threshold:", round(fw_thresh, 3))
print("peak real:", real.max().round(3), "@L", int(real.argmax()))

# --- plot ---
layers = np.arange(n_layers)
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(layers, real, color="tab:blue", label="LogReg+PCA (real)")
ax.fill_between(layers, lo, hi, color="tab:gray", alpha=0.3, label="permutation null (95%)")
ax.plot(layers, med, color="tab:gray", lw=0.8, ls="--")
ax.axhline(fw_thresh, color="tab:red", ls="--", lw=0.8, label="max-stat 95% threshold")
ax.axhline(0.5, c="k", lw=0.8, ls=":")
ax.set_xlabel("Layer"); ax.set_ylabel("AUROC"); ax.legend()
ax.set_title("Probe vs permutation null band"); ax.set_ylim(0.4, 0.8)
plt.tight_layout(); plt.savefig("probe_vs_null.png", dpi=150)
print("saved probe_vs_null.png")