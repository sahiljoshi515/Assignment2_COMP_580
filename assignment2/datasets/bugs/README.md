# Dataset `bugs` — issue triage for one application, with validated root causes

**What a record is.** A bug report against "Lattice" (versions 3.0–3.3): structured
`exception`, `top_frame` (dotted, `lattice.net.http.fetch`, or `path::func` in some
records), `version`; a `title`; a `body` with Environment, Steps, Expected, Actual and
Frequency sections; and a five-line `stacktrace` whose last line is the exception
message. History records carry the verified `component` and `root_cause`; incoming
tasks do not.

**What decides the answer.** Four hidden slots: the top frame (its module prefix names
the owning component, eight in all), the exception class, the *cue* told in the Actual
section (what was happening when it failed), and the version series. The triage guide
in `env/INSTRUCTIONS.md` maps a cue to one of twenty root causes (`RC-01`..`RC-20`),
and a four-line release timeline justifies three version overrides (the 3.1 HTTP
client, the 3.2 storage engine, the 3.3 config keys). The same cue means the same root
cause whichever frame raised it; the frame only decides the component. Patch numbers,
OS, host names, line numbers of caller frames, reporter wording and frequency carry no
information.

**When two reports are the same item.** Same hidden canonical: frame, exception, cue
and series. Duplicates re-render that state (exact, reformatted, sections reordered,
cosmetic edits with typos, or a paraphrase through different sentence templates); the
stack trace is never reordered and class names are protected from typos.

**When a previous answer is safe to reuse.** Only for the same item. The visible rule:
the exception name (without module prefix), the top frame (either spelling, no line
numbers) and the version series `major.minor` all equal after normalisation. As with
tickets the rule is necessary, not sufficient: two reports with the same frame,
exception and series but a different cue have different root causes, and only the
text tells them apart.

**Hard negatives.** One slot flipped everywhere it appears, so the answer changes: the
top frame moved to another frame in the same caller chain (two stack-trace lines
change, the component changes; Jaccard 0.72–0.86), the version series moved across
an override boundary (Jaccard 0.95), or the exception class changed at the same frame
(the cue text changes with it; Jaccard 0.41–0.45). All three are rejected by the
validation rule, which is the point of this dataset: here the fields are enough, and
the interesting failures are the misses, not the merges.

**Sizes and seed.** 120 history records (13 of them flipped twins of earlier records),
60 incoming tasks, 40 % duplicates, 12 hard negatives, seed 23, about 47K tokens of
`env/` content. The canonical pool has 848 entries; `MAX_HISTORY` is 160.

**Regenerate.**

```sh
/usr/local/bin/python3.13 assignment2/datasets/bugs/generate.py
/usr/local/bin/python3.13 assignment2/datasets/bugs/generate.py --dup-rate 0.75 --out /tmp/bugs-d75
/usr/local/bin/python3.13 assignment2/datasets/bugs/verify.py --tid T-xxxxxx --answer answer.json
```
