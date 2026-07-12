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

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)

def cv_auroc(X, labels):
    return cross_val_score(make_probe(), X, labels, cv=skf,
                           scoring="roc_auc", n_jobs=-1).mean()

def make_probe_noPCA(C=0.05):                       # L2 shrinks all dims, discards none
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000))

L = 9; X = np.concatenate([act[:, L, :], ref[:, L, :]], 0); sd = X.std(0)
for delta in [0.0, 0.5, 1.0, 2.0, 4.0]:
    a = []
    for s in range(5):                              # average over label draws for a clean baseline
        r = np.random.default_rng(s); yc = r.permutation(y)
        v = r.standard_normal(X.shape[1]); v /= np.linalg.norm(v)
        Xp = X + delta * (yc == 1)[:, None] * (v * sd)
        a.append(cross_val_score(make_probe_noPCA(), Xp, yc, cv=skf,
                                 scoring="roc_auc", n_jobs=-1).mean())
    print(f"delta={delta}: noPCA AUROC={np.mean(a):.3f}   (delta=0 should be ~0.50)")
