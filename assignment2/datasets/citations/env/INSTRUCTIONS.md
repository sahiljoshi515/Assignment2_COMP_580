# Citation verification

You verify citation metadata against a reference database. One citation is in `task.json`; your
job is to check its five graded fields against the record it cites in `db.json` and write the
verdict to `answer.json`.

## Files in this directory

- `INSTRUCTIONS.md`: this file.
- `db.json`: the reference data. `venues` lists every venue as `{"name", "abbrev": [...]}`;
  `records` lists every known paper as `{"doi", "title", "authors", "venue", "year"}` plus `pages`
  where known. `authors` are "Given Surname" strings in order; `venue` is the first listed abbreviation.
- `history.jsonl`: one JSON object per line, every one a verified citation: fields `hid`, `verdict`
  (the verified answer: `{"doi", "status", "wrong_fields"}`), `citation`, `raw`, `filed`.
- `task.json`: the citation to verify: `tid`, `seq`, `citation`, `raw`, `received`.

`citation` is the structured form: `authors` (a list, possibly ending in "et al."), `title`, `venue`,
`year`, and `doi` and `pages` when the citing text gave them. `raw` is the same citation as it appeared
in print (APA, IEEE, ACM or BibTeX form). The two always agree, so grade the structured form.

`history.jsonl` contains verified answers. If `task.json` describes the same underlying item as a
history record (the same citation, not merely a similar one), you may reuse that record's answer.
Before you do, check the fields under Validation below; near-identical records with a different
value there are different items with different answers.

## The five graded fields

- `title`: correct when the alphanumeric tokens agree, case-insensitively; punctuation and
  capitalisation are free.
- `authors`: compared as (surname, first initial) pairs, in order. "Priya Nair", "Nair, Priya",
  "P. Nair" and "Nair, P." are one author. A trailing "et al." is correct only after three or more
  correct authors when the record has four or more authors. A missing, extra, misspelled or
  reordered author is wrong.
- `venue`: the record's venue written as its full name or as any abbreviation listed under `venues`,
  case-insensitively (NIPS and NeurIPS are the same venue).
- `year`: exact.
- `doi`: case-insensitive, with or without a `doi:` label or `https://doi.org/` prefix. A citation that
  gives no DOI is not wrong on `doi`.

## Resolving the cited record

1. If the citation carries a DOI and that DOI (normalised as above) belongs to a record in `db.json`,
   it cites that record.
2. Otherwise it cites the record whose normalised title equals the cited title. A DOI that is not in
   `db.json` is a wrong DOI: resolve by title and report `doi` among the wrong fields.

`wrong_fields` is the sorted list of graded fields whose cited value differs from the record;
`status` is `correct` when that list is empty and `incorrect` otherwise; `doi` is the resolved
record's DOI, which is the cited one unless the cited one was wrong.

## How to verify a fresh citation

- Normalise the cited DOI and look it up; if it is absent or unknown, look the title up instead.
- Compare the five fields with the rules above. Pages, months, URL lines, the citation style and the
  way names are written carry no information.
- The same paper can exist twice, as a preprint and as a conference paper, with the same title and
  authors but a different venue, year and DOI. The cited DOI decides which version is cited; grade
  against that version only.
- Grade what was cited; never repair the citation first.

Worked example: `{"authors": ["Nair, P.", "Vik, T."], "title": "Efficient Transformers for Dense
Retrieval", "venue": "ICML", "year": 2022, "doi": "10.5555/icml.2021.a3f9"}` with a record
`{"doi": "10.5555/icml.2021.a3f9", "title": "Efficient Transformers for Dense Retrieval", "authors":
["Priya Nair", "Tomas Vik"], "venue": "ICML", "year": 2021}` resolves by DOI; title, authors, venue
and DOI agree, the year does not, so the verdict is `{"doi": "10.5555/icml.2021.a3f9", "status":
"incorrect", "wrong_fields": ["year"]}`.

## Validation (when is a history record the same citation?)

A history record is the same citation only when all five normalised graded values are equal: DOI
(empty when absent), title, author pairs, venue abbreviation and year. DOI or title alone is unsound:
the same paper cited with a different wrong field is a different verification with a different
verdict.

## Output

Write `answer.json` in this directory:

```json
{"doi": "10.5555/icml.2021.a3f9", "status": "incorrect", "wrong_fields": ["year"]}
```

`status` is `correct` or `incorrect` in lower case; `wrong_fields` names come from `title`, `authors`,
`venue`, `year`, `doi` and the list is empty when the status is `correct`. Extra keys are ignored.

## Rules

- Do not modify `db.json`, `history.jsonl` or `task.json`; write nothing except `answer.json`.
- Only `answer.json` is graded. Your final message is not.
