# Positioning against existing work (for the viva)

**Verify every row against the cited paper before presenting.** The "feature" columns follow how your Chapter 2 characterises each work; I have not re-read the original papers.

| Work (your ref.) | Human learner? | Structured argument model | Per-dimension diagnosis | Diagnosis changes the next AI move | Compared against baselines |
|---|---|---|---|---|---|
| Chatbot-assisted debates, Guo et al. [26] | Yes | per your review, no | No | No | see paper |
| ChatGPT feedback on argumentation, Wang et al. [41] | Yes | No | No (general feedback) | No | see paper |
| ChatGPT + scripts/argument maps, Darmawansah et al. [25] | Yes | argument map | No | No | see paper |
| Multi-agent debate, Du et al. [14]; Liang et al. [36] | No (AI-to-AI) | No | No | n/a | factuality/reasoning benchmarks |
| Adaptive heterogeneous MAD [38] | No | No | No | Adapts AI routing, not to a learner | benchmarks |
| Ethical tutoring / scaffolding MAD [4], [5], [37] | Tutoring focus | per your review, no | No | No | see paper |
| **This system** | Yes | Toulmin | 7 dimensions + weakness taxonomy | **Yes (rule-linked)** | **B1 generic opponent, B2 single-prompt LLM** (arms in code) |

## What you can honestly claim
- Novelty: the *combination* (Toulmin diagnosis → deterministic intervention → targeted opponent) with an auditable loop. Not "first AI debate tool".
- Evidence tiers: (1) component accuracy vs human labels; (2) response targeting rate; (3) head-to-head against B1/B2 on blind human-rated improvement.
- Only tier 3 supports "better than alternatives". Without it, say "feasible and promising", which the panel will respect more than an unsupported "best".

## Likely hostile questions
- *"Your scorer measures your improvement."* → Blind human raters are the primary outcome; kappa reported.
- *"8B model, 80% agreement: is that good?"* → Compare to the heuristic baseline and to inter-human kappa; the ceiling is human agreement.
- *"Why not just ChatGPT?"* → That is arm B2; here is the measured difference (or an honest null result and what it implies).
