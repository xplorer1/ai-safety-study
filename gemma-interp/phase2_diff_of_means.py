import torch
d = torch.load("contrast_acts_commit.pt")
act, ref = d["act"].float(), d["ref"].float()     # [n_act,48,3840], [n_ref,48,3840]
dirs = act.mean(0) - ref.mean(0)                   # [48, 3840]  <- per-layer act − refrain
torch.save(dirs, "commit_diff_means.pt")
print(dirs.shape)                                  # torch.Size([48, 3840])