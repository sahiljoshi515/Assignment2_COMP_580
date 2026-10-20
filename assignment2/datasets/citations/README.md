# Dataset `citations` — citation metadata verified against an authoritative database

**What a record is.** A citation to verify: a structured `citation` object (authors,
title, venue, year, optional DOI and pages) and the same citation rendered as a `raw`
string in one of four styles (APA, IEEE, ACM, BibTeX-like). `env/db.json` is the
authoritative database: 150 records across 12 venues, with 21 arXiv records of which
15 are preprint twins of a conference paper (same title and authors, a year earlier,
a different DOI). History records carry the verified `verdict`; incoming tasks do not.

**What decides the answer.** Which database record the citation resolves to (by DOI
when the cited DOI exists in the database, otherwise by normalised title) and which
of the five graded fields — title, authors, venue, year, doi — disagree with it. The
verdict is `{"doi": <the record's DOI>, "status": "correct" | "incorrect",
"wrong_fields": [...]}`. Field rules are published in `env/INSTRUCTIONS.md`: titles
compare on alphanumeric tokens, authors on (surname, first initial) in order with
"et al." allowed after three correct names when the record has four, venues through
the abbreviation list, years exactly, DOIs without case or resolver prefix. An absent
DOI is not wrong.

**When two citations are the same item.** Same hidden canonical: the same database
record with the same set of corruptions (none, one field, or two fields; the
corruption's realisation is seeded per field so a flip of one slot keeps the other's
rendering). Formatting, name order, initials, "and" versus "&", pages, month and URL
lines are cosmetic; the citation style is the paraphrase axis, which is why a
re-styled duplicate shares only about 30 % of its shingles.

**When a previous answer is safe to reuse.** Only for the same item. The visible rule:
all five normalised graded values equal. DOI or title alone is unsound by design: the
same paper cited with a different wrong field is a different verification with a
different verdict, and the arXiv twin cited with the conference venue resolves to the
other record.

**Hard negatives.** Thirteen one-token flips (a year off by one, an author initial, a
venue sibling, a title word) that share 75–96 % of their shingles with their twin and
change the verdict, and one twin flip (the preprint cited as the conference paper,
Jaccard about 0.2). All are rejected by the five-field rule; what remains hard here is
recall, because the style change defeats the shingles.

**Sizes and seed.** 140 history records (10 of them twins of earlier records), 70
incoming tasks, 40 % duplicates, 14 hard negatives, seed 53, about 43K tokens of
`env/` content including the 11K-token database. The canonical pool has 683 entries
(clean citations are capped at four per record); `MAX_HISTORY` is 160.

**Regenerate.**

```sh
/usr/local/bin/python3.13 assignment2/datasets/citations/generate.py
/usr/local/bin/python3.13 assignment2/datasets/citations/generate.py --dup-rate 0.25 --out /tmp/citations-d25
/usr/local/bin/python3.13 assignment2/datasets/citations/verify.py --tid T-xxxxxx --answer answer.json
```
