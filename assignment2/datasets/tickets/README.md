# Dataset `tickets` — customer-support tickets with verified resolutions

**What a record is.** A support ticket: `product`, `error_code`, `platform`, a `subject`
line and a free-text `body` written by the customer. History records carry the verified
`resolution_id` from a 25-entry catalogue; incoming tasks do not.

**What decides the answer.** Four hidden slots: the product, the error code (which names
a symptom), the *cue* told in two sentences of the body (what was going on when it
broke), and the platform. The resolution guide in `env/INSTRUCTIONS.md` maps a symptom
and a cue to a resolution, with platform exceptions. Names, dates, patch numbers, the
customer's own attempts and the phrasing carry no information.

**When two tickets are the same item.** Same hidden canonical: same product, code, cue
and platform. Every duplicate in the stream is a re-rendering of its source's state
(exact copy, reformatted, paragraphs reordered, cosmetic edits with typos, or a
paraphrase through different sentence templates and synonyms), so it has the same answer
by construction.

**When a previous answer is safe to reuse.** Only for the same item. The visible rule a
reuse policy can check: `product`, `error_code` and `platform` equal after normalisation
(case-insensitive, `E-1042` = `e1042`). That rule is necessary, not sufficient: the same
code on the same platform with a different cue is a different ticket with a different
resolution. The cue lives only in the text, which is why text similarity has to carry
the last mile.

**Hard negatives.** About 20 % of incoming tasks are near-twins of a record with one slot
flipped so that the resolution changes: the platform (same text, different exception in
the guide), the error code under the same story (sibling symptoms), or the cue under
the same code. The first kind is caught by the validation rule; the last kind can only be
caught by similarity, and sits around Jaccard 0.5 — the band where an aggressive
threshold starts merging what it should not.

**Sizes and seed.** 140 history records, 70 incoming tasks, 40 % duplicates (about 70 %
of them duplicates of history records, the rest of earlier tasks), seed 11, about 33K
tokens of `env/` content. `MANIFEST.json` holds the counts and the Jaccard distribution
per duplicate kind. The canonical pool has 960 entries, so `--history-size 400` is a
strict superset of the default build (same incoming tasks, same labels) for the
index-size ablation.

**Regenerate.**

```sh
/usr/local/bin/python3.13 assignment2/datasets/tickets/generate.py            # defaults
/usr/local/bin/python3.13 assignment2/datasets/tickets/generate.py --dup-rate 0.25 --out /tmp/tickets-d25
/usr/local/bin/python3.13 assignment2/datasets/tickets/verify.py --tid T-xxxxxx --answer answer.json
```
