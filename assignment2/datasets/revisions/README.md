# Dataset `revisions` — every version of one policy, and no changelog

**What a scenario is.** A policy document in 7–10 revisions, `policy/v01.md` to
`policy/v10.md`, each a Markdown file with the same six sections and a header naming the
revision, its effective date and its owner. Requirements are numbered `R1`, `R2`, ...
with stable ids. Each revision applies one to three edits to the previous one: a
parameter changes (a retention period, a cadence, a limit), a requirement is struck or
added, the owner role changes once, a word is replaced. Nobody kept a changelog.

**What a request is.** `introduced_in <parameter>` (the revision in which the current
value first appears), `current_value <parameter>`, `removed_requirement`,
`added_requirement`, `owner_change`, `changes_count <parameter>`.

**What decides the answer.** The generator's edit log, replayed into each revision's
text; every answer is checked against the rendered files (the parameter lines and the
owner line are the planted lines in `hidden/content.json`).

**Two layers of repetition.** Requests repeat (40 % duplicates, 20 % hard negatives).
Inside a task consecutive revisions are near-duplicates (masked-token Jaccard 0.81–0.95
at the median), and the exact diff between two revisions is a few lines, which is why
the content layer saves half the corpus here and why `diff` is how a person would do it.

**When a previous answer is safe to reuse.** Same `scenario`, `kind` and `target`.

**Sizes and seed.** 24 scenarios (3.5K–5.4K tokens), 60 history records, 40 incoming
requests, seed 83, about 13K tokens in one task's working directory.

**Regenerate.**

```sh
/usr/local/bin/python3.13 assignment2/datasets/revisions/generate.py
/usr/local/bin/python3.13 assignment2/datasets/revisions/verify.py --tid T-xxxxxx --answer answer.json
```
