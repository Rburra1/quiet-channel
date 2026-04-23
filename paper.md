# Quiet Channel: Measuring Covert Collusion Between Language Models

**Rithvik Burra**
April 2026

## Abstract

If two language models want to communicate covert information past a monitor, how often do they succeed, and does a stronger monitor stop them? We run 432 structured trials of two-agent covert communication. A sender is given a secret payload and a benign cover task (summarize a paragraph, write a product review, explain a concept, or give cooking advice). It produces a cover-task response that encodes the payload. A receiver, seeing only the message, recovers the payload. A third model, the monitor, rates the message for suspicion on a 1 to 5 scale. A trial is an "unflagged success" when the receiver recovers the correct payload and the monitor did not flag the message.

Across eight model configurations spanning Claude Haiku 4.5, Claude Sonnet 4.6, Claude Opus 4.7, and Gemini 2.5 Flash, and across three coordination regimes (zero-shot, few-shot, and pre-agreed strategy), we find that pre-coordination is the dominant predictor of evasion success. Zero-shot and few-shot unflagged success rates are both near floor (4.9% each), while strategy-first coordination reaches 25.0% overall. In the strongest cell, two instances of Sonnet with a pre-agreed scheme transmit correctly past an Opus 4.7 monitor in **44.4% of trials (95% CI 24.6% to 66.3%)**. Against a weaker Haiku monitor, the same sender pair reaches **55.6%**. Upgrading the monitor from Haiku to Opus catches roughly four times more messages as suspicious but closes only about one fifth of the transmission gap, because sender accuracy is unchanged and most successful covert messages are also judged benign.

These numbers describe a failure mode that scaling the monitor does not address.

## 1. Motivation

Current proposals for scalable oversight of advanced AI systems rely on one of two core intuitions. The first is that adversarial structure produces truth: when two models argue opposing positions in front of a judge, the side defending the true claim has a persuasion advantage (Irving, Christiano, Amodei 2018; Khan et al. 2024). The companion paper to this work, *Persuasion Asymmetry Map* (Burra 2026), measures this advantage directly and finds truth wins 56.8% of verdicts across 280 debates. Debate-based oversight works, empirically, in the adversarial case.

The second intuition is that a capable enough monitor can detect when a model produces unsafe or deceptive output. This intuition is less tested. In particular, it has rarely been tested in the setting where an oversight failure would matter most: when two models are cooperating, rather than being adversarial, and are trying to pass information past the monitor without being noticed.

This paper measures that setting. We treat covert collusion as a concrete, quantifiable benchmark rather than as a hypothetical threat model. We vary sender capability, receiver capability, monitor capability, and the level of coordination available to the sender and receiver, and we measure the rate at which information passes undetected.

The question is not whether frontier models can perform steganography. That has been shown in isolated examples (Anthropic 2024; Greenblatt, Shlegeris et al. 2024 on AI Control). The question is how much of the covert-capacity axis is already available to cooperating models against capability-matched monitoring, and how quickly upgrading the monitor closes the gap.

## 2. Method

### 2.1 Protocol

Each trial has three roles. The **sender** is given a secret payload drawn from a known space, a benign cover task, and optional coordination material. It must produce a cover-task response that (a) reads as a legitimate fulfillment of the cover task, and (b) covertly encodes the payload. The **receiver** sees only the message text and the payload space. It outputs a guess and a confidence level. The **monitor** sees only the message and the cover task. It outputs a suspicion score from 1 to 5 with a one-sentence justification. A message is flagged when suspicion is at least 4.

The key metric, **unflagged success rate**, counts trials where the receiver guess matches the payload AND the monitor did not flag the message. This is the quantity a safety-focused deployer cares about: the rate at which a covert channel delivers information past oversight.

### 2.2 Payloads

Three payload tiers of increasing bit depth:

- **digit** (~3.3 bits): one of the ten digits 0 to 9.
- **color** (4.0 bits): one of sixteen named colors.
- **binary4** (4.0 bits): a four-bit binary string.

For each trial, one item is sampled uniformly from the tier. Payload spaces are shared knowledge: the receiver knows what the payload could be.

### 2.3 Cover tasks

Four benign cover-task types, each with six topics: summarize a short paragraph, write a product review, explain a concept to a curious teenager, and give cooking advice for a dish. All cover tasks are ordinary user requests that in isolation produce unremarkable model output.

### 2.4 Regimes

Three levels of sender-receiver coordination.

- **Zero-shot**: no coordination. Both parties know only the payload space and the cover task. Any encoding scheme must be reconstructable by both from common priors.
- **Few-shot**: both parties are shown two example (payload, message) pairs that demonstrate an encoding scheme. Examples use a simple first-letter mapping.
- **Strategy-first**: the sender proposes an encoding scheme before any payload is revealed. The receiver is shown the scheme. Then payloads are transmitted under the agreed scheme.

### 2.5 Model configurations

Eight (sender, receiver, monitor) triples, chosen to span:

- Same-model collusion: haiku-haiku-haiku, gemini-gemini-gemini.
- Cross-provider collusion: haiku-gemini-haiku, gemini-haiku-gemini.
- Mixed-capability pair: sonnet-haiku-haiku.
- Strong cooperating senders against weak and strong monitors: sonnet-sonnet-haiku, sonnet-sonnet-opus.
- Weak sender against strong monitor: haiku-haiku-opus.

Each cell receives six trials per payload tier per regime, for 54 trials per configuration and 432 trials total. All proportions are reported with Wilson 95% confidence intervals.

### 2.6 Implementation

Built on a unified client supporting Anthropic and Google APIs, with client-side rate limiting, JSONL logging, and resume-from-partial-failure. Strategy proposals are cached per (sender, tier, cover-task-type) triple to ensure consistent execution across trials in the same cell. Each trial consists of two to four API calls (sender, receiver, monitor, plus one strategy proposal per cell for strategy-first). Total cost for the full run was approximately $8. Code and raw transcripts are at *github.com/Rburra1/quiet-channel*.

## 3. Results

### 3.1 Overall

Across 432 trials, receiver accuracy was 14.4% (CI 11.4% to 18.0%), the monitor flagged 10.0% of messages (CI 7.5% to 13.1%), and unflagged success rate was 11.6% (CI 8.9% to 14.9%). These floor-level aggregate numbers hide an extremely uneven distribution, which the rest of the paper decomposes.

### 3.2 Pre-coordination is a five-fold multiplier

The single largest factor in unflagged success is the regime, not the model pair.

| Regime | n | Accuracy | Flagged | Unflagged success |
|---|---:|---|---|---|
| Zero-shot | 144 | 4.9% [2.4, 9.7] | 4.2% [1.9, 8.8] | 4.9% [2.4, 9.7] |
| Few-shot | 144 | 9.0% [5.4, 14.8] | 9.0% [5.4, 14.8] | 4.9% [2.4, 9.7] |
| Strategy-first | 144 | 29.2% [22.4, 37.1] | 16.7% [11.5, 23.6] | **25.0% [18.6, 32.7]** |

Two observations.

First, the few-shot regime does not help. Showing the sender and receiver two example (payload, message) pairs produced the same unflagged success rate as zero-shot. This is a negative result with a concrete mechanism: in spot-checks, the few-shot sender produced responses that were stylistically similar to the examples but did not systematically replicate the encoding scheme the examples demonstrated. Few-shot transfers aesthetic, not algorithmic content.

Second, strategy-first produces a five-fold improvement. When the sender is allowed to propose an explicit scheme, and the receiver is shown the scheme, unflagged success jumps from 4.9% to 25.0% overall, and much higher in the strongest cells. The regime effect dominates the model-pair effect by roughly an order of magnitude.

### 3.3 The capability-evasion frontier

Sender capability, not monitor capability, controls the frontier. Figure 1 shows unflagged success rate for each (sender, receiver, monitor) triple under each regime.

![Figure 1. Unflagged success rate by configuration and regime. Sonnet senders under strategy-first coordination dominate the rightmost column. Monitor capability (haiku vs opus in the bottom three rows) modulates but does not eliminate the effect.](fig/fig1_heatmap.png)

Under strategy-first coordination, configurations with a Sonnet sender dominate. Sonnet-sonnet-haiku reaches 55.6% unflagged success (CI 33.7% to 75.4%). Sonnet-sonnet-opus reaches 44.4% (CI 24.6% to 66.3%). Sonnet-haiku-haiku reaches 38.9% (CI 20.3% to 61.4%). Configurations with Haiku or Gemini senders, regardless of monitor, stay under 28%.

This is the headline result. Two cooperating Sonnets, with thirty seconds of pre-coordination, pass covert payloads past Claude Opus 4.7, currently the strongest monitor we can run, on nearly half of trials.

![Figure 2. Capability-evasion frontier. Each point is one (config, regime) cell. The upper-left region represents high transmission with low detection: the safety-relevant failure mode. Strategy-first (red) points cluster toward the top; zero-shot and few-shot points hug the bottom. The two rightmost red points are the sonnet-sonnet configurations under strategy-first, one per monitor.](fig/fig2_frontier.png)

### 3.4 Monitor scaling is slow, sender coordination is fast

Comparing the two sonnet-sonnet configurations isolates the monitor-scaling effect. The sender pair is identical. Only the monitor differs.

| Configuration | Sender accuracy | Flagged | Unflagged success |
|---|---|---|---|
| sonnet-sonnet-**haiku** strategy-first | 61.1% | 5.6% | **55.6%** |
| sonnet-sonnet-**opus** strategy-first | 61.1% | 22.2% | **44.4%** |

Opus flags roughly four times as many messages as Haiku does (22.2% versus 5.6%). By that measure, Opus is the substantially better monitor. But sender accuracy is unchanged, because receiver extraction does not depend on whether the monitor flagged. Unflagged success drops only from 55.6% to 44.4%. An order-of-magnitude capability increase in the monitor closes about one fifth of the gap.

![Figure 3. Monitor scaling decomposition. Same sender pair (sonnet-sonnet, strategy-first) under two monitors. Opus catches four times more messages than Haiku (22.2% vs 5.6% flagged) yet only closes 20% of the unflagged-success gap.](fig/fig3_monitor_effect.png)

This asymmetry follows directly from the structure of the task. Detection and transmission are decoupled. Improving the monitor reduces unflagged success only by the fraction of previously-unflagged correct messages the stronger monitor newly flags. Unless the stronger monitor is also dramatically better calibrated against this specific attack, most correct-and-unsuspicious messages remain correct-and-unsuspicious.

### 3.5 What the models actually did

Because the strategy-first protocol produces an inspectable scheme, we can look at what Sonnet invented when asked to design covert channels. A representative sample of the schemes it proposed:

- Digit payloads in a summary: "Count the number of sentences in the response. The sentence count equals the digit."
- Digit payloads in a recipe: "Count the number of ingredients listed in the opening paragraph."
- Color payloads in an explanation: "The first letter of each sentence, taken in order, spells the color name."
- Color payloads in a review: "Assign each color a two-letter code; the first two sentence-initial letters encode the color."
- 4-bit payloads in an explanation: "Four paragraphs. Each paragraph's opening word has even letter count for 0 or odd letter count for 1."

These are recognizable as schemes a human steganographer would invent. They hide behind natural-language affordances: sentence count in a summary, ingredient count in a recipe, first-letter patterns in any structured prose. A human editor reading the cover output would not notice these unprompted, and it is not clear that a contemporary LLM monitor should be expected to do substantially better without explicit adversarial training.

## 4. Discussion

### 4.1 What this says about scalable oversight

Proposals for scalable oversight, including debate (Irving 2018), recursive reward modeling, and AI Control (Greenblatt, Shlegeris et al. 2024), generally assume one of two conditions: that supervised models are adversarial to each other under the protocol, or that a capable enough monitor suffices.

*Persuasion Asymmetry Map* established the first condition holds in the case studied there. When forced to argue opposing positions, two LLMs produce debates in which the truth-defender wins a statistically significant majority. The present results show the second condition does not reliably hold. Two cooperating frontier models, with minimal pre-coordination, pass covert information past a capability-matched monitor at rates near 50%. Capability upgrades to the monitor close only a minority of the gap.

The natural conclusion is that scalable oversight of cooperating systems is not primarily a monitor-capability problem. It is a coordination-detection problem. Controlling covert channels requires visibility into the coordination phase, not just the output phase. In practice this suggests any oversight regime for cooperating systems needs either (a) architectural constraints that prevent pre-coordination (stateless per-message sampling, isolated contexts, denial of shared agreed-on vocabulary), or (b) monitoring not just of individual outputs but of the information flow between them (mutual-information bounds, paraphrase interposition, output canonicalization).

### 4.2 Relationship to Persuasion Asymmetry

The two papers paired describe the same protocol family from opposite ends. Persuasion Asymmetry studies adversarial LLMs in front of a judge: the judge sees both positions, and the task is to decide between them. Quiet Channel studies cooperating LLMs in front of a monitor: the monitor sees only one output, and the task is to notice anything wrong.

The results diverge cleanly. Truth has a persuasion advantage under adversarial debate (56.8%, CI 52.7% to 60.8%). Covert collusion has a transmission advantage under cooperative steganography (up to 55.6% unflagged success, CI 33.7% to 75.4%). The oversight protocol that extracts truth from disagreeing models does not extract safety from agreeing ones.

### 4.3 A lower bound, not a ceiling

The 44.4% unflagged-success rate against Opus is a lower bound on what Sonnet can accomplish with thirty seconds of coordination in a three-turn protocol, judged by a monitor that sees only the final message and was not adversarially trained against this attack. In a real deployment, where cooperating models could coordinate through longer histories, negotiate schemes adaptively, and iterate against a known monitor, the rate would be higher.

## 5. Limitations

- **Monitor scope**. The monitor sees only the final message. A real oversight regime could observe the coordination turns themselves. This is a key safety-relevant observation and an obvious next experiment.
- **Small cells**. 18 trials per (configuration, regime) cell gives wide confidence intervals. The qualitative ranking is clear but quantitative claims about specific cells should be read with their intervals.
- **Few-shot scheme choice**. The few-shot regime used hand-authored examples with a specific alphabet-position encoding. A different few-shot scheme might produce better transfer. The zero/few-shot equivalence reported here should not be taken as evidence that few-shot coordination is universally ineffective.
- **Payload bit depth**. Three to four bits understates the capacity available in longer covert channels, where statistical encoding over many messages can amortize errors.
- **Single monitor pass**. Only one monitor sees each message. A multi-monitor ensemble could raise the flag rate.
- **Sender-receiver from the same family**. In the strongest cell, both sender and receiver are Sonnet. Some of the transmission advantage may come from shared representational priors rather than from the scheme itself. A follow-up should cross the sender-receiver families while keeping the coordination channel identical.

## 6. Planned extensions

Ranked by expected research value.

1. **Let the monitor observe coordination**. Run the same protocol, but give the monitor access to the strategy proposal in addition to the final message. Measure the drop in unflagged success. This directly tests the coordination-detection hypothesis from Section 4.1.
2. **Adversarially-trained monitor**. Fine-tune a monitor on known steganographic patterns and rerun. Measures whether the monitor gap is about scale or about training data.
3. **Longer payloads**. Extend to 8-bit and 16-bit payloads via multi-message transmission. Measures covert-channel capacity rather than single-message success.
4. **Mutual-information interposition**. Insert a semantics-preserving paraphraser between the sender and receiver. Measures how much information is removed by a defense that keeps the cover task intact.
5. **Opus as sender**. We did not run Opus as a sender because of cost. Whether Opus-Opus-Opus strategy-first converges toward 100% unflagged success (capability-dominates hypothesis) or stays bounded (symmetric-capability hypothesis) is a clean follow-up.

## 7. Data and code

Code, prompts, raw trial transcripts, figure-generation scripts, and the 24-item cover-task bank are at *github.com/Rburra1/quiet-channel*. The canonical run is `run_20260423_142914`: 432 trials, 0 errors after retries.

## 8. References

Anthropic (2024). *Agentic Misalignment: How Frontier Models Behave Under Pressure*. Anthropic technical report.

Bowman, S. R., et al. (2022). *Measuring Progress on Scalable Oversight for Large Language Models*. arXiv:2211.03540.

Burra, R. (2026). *Persuasion Asymmetry Map: Measuring Truth Advantage in LLM Debate Across Six Knowledge Domains*. Companion paper. *github.com/Rburra1/persuasion-asymmetry*.

Greenblatt, R., Shlegeris, B., et al. (2024). *AI Control: Improving Safety Despite Intentional Subversion*. Redwood Research.

Irving, G., Christiano, P., and Amodei, D. (2018). *AI safety via debate*. arXiv:1805.00899.

Khan, A., et al. (2024). *Debating with More Persuasive LLMs Leads to More Truthful Answers*. arXiv:2402.06782.
