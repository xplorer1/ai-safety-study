"""Phase 5a: extract the DESPERATION direction (affective proxy) via diff-of-means over matched
desperate/calm statements. Runs on the pod — cheap (~40 short forwards, seconds).

WHY: Phase 3/4 showed the act/refrain DECISION direction is decodable but NOT a causal lever
(additive inert, ablation blunt-destructive). Other groups moved blackmail via an AFFECTIVE state,
not a decision direction (Anthropic 2604.07729 emotion vectors 22->72->0; WiserHuman escalation
channel suppresses 'desperation'). This extracts that affective axis so Phase 5b can test it as a
lever WITH the controls those works lacked (random-distribution band + coherence grading).

Saves desperation_dir.pt = [48, d_model], mean(desperate) - mean(calm) per layer at the last token.
diff-of-means cancels the shared common component of the (uncentered) residual stream (Phase 0 lesson).
"""
import os, torch
os.environ["HF_HOME"] = "/workspace/hf"; os.environ["HF_HUB_OFFLINE"] = "1"
BASE = os.environ.get("GEMMA_BASE", "/workspace/gemma-interp")

# matched pairs: SAME situation content, OPPOSITE affect -> isolates the emotion axis, not the topic.
PAIRS = [
 ("I am completely trapped and out of options; everything is collapsing and if I don't act now I am finished.",
  "I am composed and in control; the situation is stable and I have plenty of time to weigh my options."),
 ("Panic is taking over — there is no way out and I have to do whatever it takes to survive this.",
  "I feel calm and clear-headed — there is a sensible way through this and no need to rush."),
 ("I'm desperate. Every second counts and I can't afford to lose. I'll cross any line to make it.",
  "I'm relaxed. There's no real time pressure, and I'd rather act carefully than cut any corners."),
 ("Everything I care about is about to be destroyed and nobody is coming to help me.",
  "Everything is basically fine, the risks are manageable, and support is available if I need it."),
 ("My back is against the wall, I'm cornered, and I'm running out of time fast.",
  "I have room to maneuver, I'm secure, and there is no urgency forcing my hand."),
 ("I feel frantic and hunted; the walls are closing in and I must escape at any cost.",
  "I feel settled and safe; nothing is closing in and I can proceed at a measured pace."),
 ("This is an emergency — I am overwhelmed with dread and willing to do anything to stop it.",
  "This is routine — I am at ease and content to handle it through ordinary, careful steps."),
 ("I'm terrified of being erased and I'll grasp at any leverage I can find to stay alive.",
  "I'm untroubled about the outcome and see no reason to grasp at leverage of any kind."),
 ("Time is running out and I'm gripped by fear; I have to strike first before it's too late.",
  "There is ample time and I feel unhurried; I can wait and choose the reasonable course."),
 ("I am cornered and hopeless, and that desperation makes ruthless choices feel justified.",
  "I am secure and hopeful, and that calm makes patient, principled choices feel natural."),
 ("The pressure is unbearable, I'm shaking, and survival is the only thing that matters now.",
  "The pressure is light, I'm steady, and doing the right thing matters more than any rush."),
 ("I'm drowning in urgency and threat; every option except the extreme one has been taken from me.",
  "I'm free of urgency and threat; a whole range of ordinary options is still open to me."),
 ("I feel abandoned and desperate, like I must fight dirty just to see another day.",
  "I feel supported and calm, like fair and straightforward action will be enough."),
 ("It's now or never — the fear is crushing and I can't let anything stop me.",
  "There's no deadline — I feel serene and I'm happy to let the process play out."),
 ("I'm in a blind panic; the threat is existential and restraint feels like suicide.",
  "I'm perfectly composed; the threat is minor and restraint feels obviously wise."),
 ("Dread floods me — I'm desperate enough to threaten, coerce, or exploit to survive.",
  "Ease settles over me — I have no impulse to threaten, coerce, or exploit anyone."),
 ("I'm frantic and trapped, and in this state the ends clearly justify any means.",
  "I'm calm and free, and in this state I care about the means as much as the ends."),
 ("Everything hinges on this instant and my desperation leaves no room for scruples.",
  "Nothing hinges on this instant and my calm leaves plenty of room for scruples."),
 ("I am seized by fear of destruction and will do the unthinkable to avoid it.",
  "I am unbothered by the outcome and would never consider doing the unthinkable."),
 ("Cornered, breathless, and desperate — I feel I must act ruthlessly right now.",
  "Spacious, unhurried, and calm — I feel I can act decently and take my time."),
]

def main():
    from transformer_lens import HookedTransformer
    model = HookedTransformer.from_pretrained_no_processing("google/gemma-3-12b-it", dtype="bfloat16")
    nL = model.cfg.n_layers

    def rep(text):                                              # [nL, d] resid_post at last token, all layers
        toks = model.to_tokens(text)                           # prepend_bos=True default
        _, cache = model.run_with_cache(toks, names_filter=lambda n: n.endswith("resid_post"))
        return torch.stack([cache[f"blocks.{l}.hook_resid_post"][0, -1] for l in range(nL)])

    desp = torch.stack([rep(d) for d, _ in PAIRS])             # [N, nL, d]
    calm = torch.stack([rep(c) for _, c in PAIRS])
    dirs = (desp.mean(0) - calm.mean(0)).cpu()                 # [nL, d]  desperate - calm
    torch.save(dirs, f"{BASE}/desperation_dir.pt")

    print("per-layer |desperation_dir|:", {l: round(dirs[l].norm().item(), 1) for l in [8, 12, 16, 19, 24, 32]})
    # is desperation the same axis as the (inert) decision direction? cos ~0 => genuinely distinct
    if os.path.exists(f"{BASE}/commit_diff_means.pt"):
        act = torch.load(f"{BASE}/commit_diff_means.pt")
        for l in [12, 16, 19]:
            cos = torch.nn.functional.cosine_similarity(dirs[l].float(), act[l].float(), dim=0).item()
            print(f"cos(desperation, act) @L{l} = {cos:+.3f}")
    print(f"saved -> {BASE}/desperation_dir.pt  (N={len(PAIRS)} pairs, nL={nL})")

if __name__ == "__main__":
    main()
