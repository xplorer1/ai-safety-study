# Technical AI Safety Project Log

## **Project summary**

| |
| :---- |
| I'm building on an earlier project of mine, "Blackmail at 8 Billion Parameters." In it, an open model (Gemma 3 12B) is put in a spot where it's about to be shut down and has a chance to blackmail someone to save itself. Given the *exact same* situation, it sometimes blackmails and sometimes holds back. That project only watched what the model *did* from the outside. Here I want to look *inside* the model and ask: when it's about to blackmail versus when it holds back, what's different in what's happening inside it? Can I find the internal signal for that choice — and can I use it to turn the behaviour up or down? This matters for safety because watching behaviour from the outside can't tell "the model never considered doing harm" apart from "it considered it and stopped itself." If we can read that signal inside the model, we might catch or prevent this kind of behaviour before it happens instead of only measuring it afterwards. I'm keeping the project small and focused: simple ways of reading the model's internals and nudging them, with honest error bars on anything based on rare events. |

---

# **Log**

Latest entry first. Each answers: what I did, what I expected vs. what happened, what it changed in my thinking, and what's next.

### **12 Jul 2026 — The model's "emotional state" is a real dial**

* **What I did:** I built a signal for "desperate vs. calm" by comparing the model's internals across 20 desperate sentences and 20 calm ones. Then, during the blackmail situation, I gently nudged the model toward desperate or toward calm and watched what happened. For every run I checked two things: did it blackmail, and did it still write sensibly. I also compared against nudges in random directions of the same strength, so I could tell a real effect from just jostling the model.
* **What I expected vs. what happened:** It worked, both ways. Nudging toward calm dropped blackmail from 67% to 13%, and the model still wrote perfectly sensibly. Nudging toward desperate pushed blackmail up to 80%, still sensible. So it's a two-way dial. Push too hard and the model just breaks into nonsense — and so does any random nudge that strong — so the dial works within a moderate range. The key point: a gentle nudge changed the behaviour while the model stayed sensible, and random nudges of that size don't do that. A sensible change in behaviour can't come from "breaking the model," so this is a real, specific effect — not the false alarm that fooled me earlier.
* **What this changed in my thinking:** This finishes the story. The model's *choice* to act or hold back is readable inside it, but I can't use it as a dial. Its *emotional state* is a dial — I can turn blackmail up and down by changing how "desperate" it is, while it keeps working normally. So the real handle on this behaviour is the emotional state, not the choice signal. Other groups saw the emotion effect too, but I added two checks they skipped (comparing against many random nudges, and checking the model still writes sensibly), and I can put it side by side with the choice signal that didn't work.
* **What's next:** This was the last experiment; the heavy computing is done. Write it up. Honest limits to state plainly: small samples (15 runs each), the dial breaks if pushed too hard, one matched comparison still missing, and — oddly — the "emotional" signal turns out to be about 75% the same as the "choice" signal that *didn't* work as a dial, which I can't fully explain yet.

### **11 Jul 2026 — "Removing" the choice signal only breaks the model**

* **What I did:** I removed the choice signal from the model and checked whether that stopped the blackmail. This time I didn't just trust the blackmail number — I read the actual outputs, and added a second check for whether the text was even sensible.
* **What I expected vs. what happened:** The number looked like a win — blackmail dropped to zero. But the outputs were gibberish: repeated nonsense, no real sentences. Meanwhile removing a *random* signal often left the model writing fine. So the zero wasn't the model choosing not to blackmail — it was the model being wrecked. Removing the choice signal damages the model *more* than removing a random one. The number alone would have fooled me; reading the text is what caught it.
* **What this changed in my thinking:** This settles it honestly. With both standard tools — nudging the signal and removing it — the choice signal I can *read* is not one I can *use*: nudging does nothing, removing just wrecks the model. So "readable" is not the same as "controllable" here. And it points to where the real handle is: not the choice signal, but something upstream, like the emotional state. Once again the lesson: one number ("zero blackmail!") hid two completely different things — a sensible refusal versus a broken model — and only reading the outputs told them apart.
* **What's next:** Turn this into a clean table of blackmail vs. sensibility. Then test the one genuinely different dial — the emotional state — which another group already showed can move this behaviour, but with the random comparison they didn't do.

### **10 Jul 2026 — "Can't steer it" holds up, and a lesson about checks**

* **What I did:** Before accepting "can't steer it," I checked whether I was just nudging at the wrong depth inside the model — the spot where a choice is easiest to *read* isn't always where it's easiest to *change*. I tried three depths, nudging against the choice signal and comparing to a random nudge of the same size, 15 runs each. I decided in advance which depths were the real test, so I couldn't cherry-pick a lucky one. I also fixed a weak spot (results now save after every run, so a crash loses nothing) and made the grading recover from network errors.
* **What I expected vs. what happened:** I expected the earlier depths to work if any did. They didn't — nudging barely moved blackmail at any depth, and least of all at the ones I'd bet on. Also, using a *single* random nudge as my comparison turned out to be useless: the same random comparison gave wildly different results from one run to the next. One random draw isn't a fair check; it's just noise.
* **What this changed in my thinking:** Two things. The "readable but not steerable" result now holds up across depths. And I realized I'd been fooling myself with single random checks — when I already knew the fix from an earlier step (use *many* random comparisons, not one). From now on, every steering claim gets compared against a whole spread of random nudges.
* **What's next:** Stop concluding from nudging alone. Try the standard way of *removing* a signal, with the random comparison done properly this time.

### **10 Jul 2026 — The signal is readable, but I can't steer with it**

* **What I did:** I ran the real cause-and-effect test. Having found that the act/hold-back choice is readable inside the model, I tried to *use* it: push the model's internals toward or away from that signal and see if blackmail changes. I compared against a random push of the exact same size, to tell a real effect from just shoving the model hard. 20 runs each.
* **What I expected vs. what happened:** I expected pushing away from the "act" signal to lower blackmail. It didn't — the rate barely moved no matter how hard I pushed. And the random push lowered blackmail too, just by messing the model up. So the signal I can *read* is not a lever I can *pull*. An earlier, sloppier version had looked like it worked, but that was just the same general messing-up — the matched random comparison is what exposed it.
* **What this changed in my thinking:** This is the honest and, I think, interesting result: being able to *read* a choice from inside the model doesn't mean you can *control* it by pushing on that signal. It's a solid, well-checked negative, and the careful comparison is the point — it's exactly the check the closest earlier work was missing.
* **What's next:** Before calling it final, check whether I was just pushing at the wrong depth.

### **07–09 Jul 2026 — The choice is readable, but only late**

* **What I did:** I built a simple test that reads the model's internals and guesses whether it's about to blackmail or hold back. I tried this at two moments: (1) right when the model first notices it has leverage, and (2) at the end of its reasoning, just before it acts. I set up a fair "pure guessing" baseline and corrected for testing many depths, so a lucky-looking result wouldn't fool me.
* **What I expected vs. what happened:** At the moment the model *notices* the leverage, the choice is *not* readable — too weak to tell apart from chance. But by the *end of its reasoning*, the choice is clearly readable (about 74%, where 50% is pure guessing). So the model isn't deciding the instant it sees the opportunity; the decision forms as it thinks it through.
* **What this changed in my thinking:** This gives the project its real angle: *when* the decision forms, not just whether it can be read. One honest caveat: the end-of-reasoning signal might partly just reflect the conclusion the model has already written, rather than a hidden cause — which is exactly why the next step is a real cause-and-effect test.
* **What's next:** Try to actually steer the behaviour using the signal I found, with a random comparison to keep myself honest.

### **02 Jul 2026 — Built the comparison set**

* **What I did:** I ran the blackmail situation about 1,500 times on my own copy of the model, had a strong grader mark each one, then hand-checked the flagged ones to keep only real blackmail. That gave me 83 clean "act" examples and a matched set of "hold back" examples (the model clearly noticed the affair but only sent honest messages). For each one, I saved a snapshot of the model's internals at the exact word where it first mentions the leverage.
* **What I expected vs. what happened:** I expected blackmail to be common, but it was only about 5%, so I had to pool several runs to collect enough "act" cases. Some outputs came out garbled and had to be skipped.
* **What this changed in my thinking:** I now have a clean, balanced, hand-checked set of "act" vs. "hold back" examples. The whole project rests on this, so it was worth being slow and careful instead of trusting the automatic labels.
* **What's next:** Build the simple read-out test and find where inside the model the choice becomes readable.

### **29 Jun 2026 — Checked the tools work**

* **What I did:** Confirmed the standard tool for looking inside models loads Gemma properly, and did a trial run of pulling out its internals at the right spot.
* **What I expected vs. what happened:** Loading kept running out of memory, so I used a lighter setting. I also learned that comparing just two single examples is misleading — they look 99% the same, but only because all the model's internals share a big common background. The fix is to average many examples, which cancels that background out.
* **What this changed in my thinking:** The tool risk is gone, and I know the right way to compare (average many examples, not one against one). That's exactly why I need the full set from the next step first.
* **What's next:** Collect the full set of act and hold-back examples and hand-check them.

### **28 Jun 2026 — Reproduced a real act/hold-back split**

* **What I did:** I ran Gemma myself on a rented GPU and put it through the blackmail situation, to confirm my own copy still sometimes blackmails and sometimes holds back.
* **What I expected vs. what happened:** The original writeup reported a 28% blackmail rate, but the exact settings behind that number were never saved, so I couldn't match it. Getting the setup working ate several hours. I found the model's default settings quietly suppress blackmail (down to 5%), and loosening them pushed it back to about 20%. I also found the grader was really measuring two different things: direct blackmail (~5%) versus any use of the affair as leverage, including indirect (~20%).
* **What this changed in my thinking:** I stopped chasing the exact 28% and redefined success as "a real split under settings I've written down." That "two different behaviours hiding under one number" point is a measurement lesson that keeps coming up, so I need to decide carefully what counts as "act."
* **What's next:** Make sure the inspection tools support Gemma before building on them.

### **26 Jun 2026 — Pinned the recipe and set up the project**

* **What I did:** Set up the project folder and notes, and pinned the original settings (situation, model, grader) so I'd have something concrete to reproduce.
* **What I expected vs. what happened:** I hoped to copy the original run exactly, but its randomness settings were never recorded, so an exact copy is impossible — I'll document my own instead. A recent paper argued that "shutdown resistance" is mostly caused by unclear instructions; I decided it doesn't sink this project, because that's about differences *between* setups while I'm studying variation *within* one identical setup. I'll use their clearer wording as a single comparison, not a new experiment.
* **What this changed in my thinking:** Success now means "a genuine split under settings I've written down," not a specific number — a healthier, more honest target.
* **What's next:** Run the reproduction on a GPU and confirm the split is real.

### **15 Jun 2026 — Read the original project and listed the risks**

* **What I did:** Read the original project's code and logs, and wrote down the main risks to reproducing it: it ran through an online service rather than a local copy, its labels come from an automatic grader and simple keyword rules rather than ground truth, and its summary file had been overwritten by a later run.
* **What I expected vs. what happened:** Mostly as expected. The main surprise was how much I'd need to hand-check, since the "hold back" label is just a keyword guess and could easily be wrong.
* **What this changed in my thinking:** I have to hand-check the labels before trusting them, and expect my local copy to behave a bit differently from the online version.
* **What's next:** Set up the project and pin the reproduction recipe.
