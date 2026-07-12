import torch, numpy as np
import matplotlib.pyplot as plt
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score
from sklearn.base import BaseEstimator, ClassifierMixin

d = torch.load("contrast_acts.pt")
act, ref = d["act"].float().numpy(), d["ref"].float().numpy()
y = np.r_[np.ones(len(act)), np.zeros(len(ref))]
n_layers = act.shape[1]
cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=0)
rng = np.random.default_rng(0)

# --- diff-of-means as a sklearn-compatible estimator ---
class DiffMeansProbe(BaseEstimator, ClassifierMixin):
    def fit(self, X, y):
        self.classes_ = np.array([0., 1.])
        mu1 = X[y == 1].mean(0)
        mu0 = X[y == 0].mean(0)
        self.d_ = mu1 - mu0                      # fit on TRAIN fold only
        return self
    def decision_function(self, X):
        return X @ self.d_                       # project TEST onto d
    # roc_auc scorer will use decision_function; no predict_proba needed
    def predict(self, X):
        return (self.decision_function(X) > 0).astype(float)

def repeat_means(scores, n_repeats=10):
    """Collapse 50 fold scores -> 10 repeat means, CI across repeats."""
    per_repeat = scores.reshape(n_repeats, -1).mean(1)
    m = per_repeat.mean()
    ci = 1.96 * per_repeat.std(ddof=1) / np.sqrt(n_repeats)
    return m, ci

def eval_layer(L, estimator, y_labels):
    X = np.concatenate([act[:, L, :], ref[:, L, :]], 0)
    scores = cross_val_score(estimator, X, y_labels, cv=cv, scoring="roc_auc")
    return repeat_means(scores)

lr_pipe = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))
dm_pipe = make_pipeline(StandardScaler(), DiffMeansProbe())

# --- layer loop ---
results = {"lr": [], "dm": [], "shuf": []}
y_shuf = rng.permutation(y)                      # one fixed shuffle, reused per layer

for L in range(n_layers):
    results["lr"].append(eval_layer(L, lr_pipe, y))
    results["dm"].append(eval_layer(L, dm_pipe, y))
    results["shuf"].append(eval_layer(L, lr_pipe, y_shuf))   # control

lr_m,  lr_ci  = map(np.array, zip(*results["lr"]))
dm_m,  dm_ci  = map(np.array, zip(*results["dm"]))
sh_m,  sh_ci  = map(np.array, zip(*results["shuf"]))

# --- plot ---
layers = np.arange(n_layers)
fig, ax = plt.subplots(figsize=(9, 5))
for m, ci, label, color in [(lr_m, lr_ci, "LogReg (L2)", "tab:blue"),
                            (dm_m, dm_ci, "Diff-of-means", "tab:orange"),
                            (sh_m, sh_ci, "Shuffled labels", "tab:gray")]:
    ax.plot(layers, m, label=label, color=color)
    ax.fill_between(layers, m - ci, m + ci, alpha=0.2, color=color)
ax.axhline(0.5, ls="--", c="k", lw=0.8)
ax.set_xlabel("Layer"); ax.set_ylabel("AUROC (CV mean ± 95% CI over repeats)")
ax.set_ylim(0.35, 1.02); ax.legend(); ax.set_title("Linear probe AUROC by layer")
plt.tight_layout(); plt.savefig("probe_auroc_by_layer.png", dpi=150)