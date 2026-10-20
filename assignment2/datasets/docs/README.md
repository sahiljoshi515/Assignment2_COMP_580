# Dataset `docs` — internal memos to classify, with a duplicate pointer

**What a record is.** An internal memo of one company: a `title` that starts with an
identifier (`CHG-4412`, `INC-4383`, `POL-731`, `REL-2.4`) and a `body` of three
labelled sections. History records carry the verified `category`; incoming tasks do
not. Four families: change memos, incident reports, policies, release notes.

**What decides the answer.** The identifier's family and a status word in the body:
change memos are `change-request`, `change-approved` or `change-rejected`; incidents
`incident-open` or `incident-resolved`; policies `policy-draft` or `policy-final`;
release notes are always `release-notes`. The status word appears in two sentences, in
either of two spellings per class (approved / authorised, ongoing / under
investigation, ...), and no template ever contains a stem of another class, so a
single stem match decides. The answer also names `duplicate_of`: the history record
that describes the same document, or `null`.

**When two memos are the same item.** Same hidden canonical: family, identifier,
system, status and the three detail bullets. Identifiers are unique within a family,
so (identifier, status class) is a key — there are no "confusable" pairs here, which
is why the validation rule is sufficient on this dataset and only similarity can get
it wrong.

**When a previous answer is safe to reuse.** Only for the same item. The visible rule:
the identifier found by `\b(CHG|INC|POL)-\d{3,4}\b|\bREL-\d+\.\d+\b` is equal **and**
the status class (first stem found, scanning approved, rejected, request, resolved,
open, final, draft) is equal. Either alone is unsound: a request memo and the approval
memo of the same change share the identifier; two approved changes share the category
but not `duplicate_of`. A reused answer must point `duplicate_of` at the matched
history record.

**Hard negatives.** The status slot flipped everywhere it appears, with identifier,
system and details unchanged: `approved` → `rejected`, `ongoing` → `resolved`,
`draft` → `effective`. They share about 90 % of their shingles with their twin
(Jaccard 0.88–0.91 in `MANIFEST.json`) and have a different category, so any threshold
below 0.9 merges them unless the validator looks at the status word. Release notes
have no status and no hard negatives.

**Sizes and seed.** 110 history records (33 change, 34 incident, 34 policy, 9 release
notes; 10 of them status-flipped twins of earlier records), 60 incoming tasks, 40 %
duplicates, 11 hard negatives, seed 37, about 36K tokens of `env/` content. The
canonical pool is 3,000 entries (lazy, seeded); `MAX_HISTORY` is 160, so this dataset
is not used for the 400-record index-size ablation.

**Regenerate.**

```sh
/usr/local/bin/python3.13 assignment2/datasets/docs/generate.py
/usr/local/bin/python3.13 assignment2/datasets/docs/generate.py --dup-rate 0.5 --out /tmp/docs-d50
/usr/local/bin/python3.13 assignment2/datasets/docs/verify.py --tid T-xxxxxx --answer answer.json
```
