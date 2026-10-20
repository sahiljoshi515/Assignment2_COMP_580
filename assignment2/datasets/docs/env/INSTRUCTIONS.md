# Internal memo classification

You are a records clerk. One internal memo is in `task.json`; your job is to decide which of
the eight document categories it belongs to, say which history record (if any) describes the
same document, and write both to `answer.json`.

## Files in this directory

- `INSTRUCTIONS.md`: this file.
- `history.jsonl`: one JSON object per line, every one a filed, verified memo: fields `hid`
  (`H-` and six hex digits), `category` (the verified answer), `title`, `body`, `filed`.
- `task.json`: the memo to classify: `tid`, `seq`, `title`, `body`, `received`.

`history.jsonl` contains verified answers. If `task.json` describes the same underlying item as a
history record (the same document, not merely a similar one), you may reuse that record's answer.
Before you do, check the fields under Validation below; near-identical records with a different
value there are different items with different answers.

## Categories

Four families of memo, told apart by the identifier in the title; a status word in the body
splits three of them further. Status words (in any inflection) per category:

**Change memo** (`CHG-nnnn`)

- `change-request`: a change memo still waiting for the board's decision. Status words: request, pending.
- `change-approved`: a change memo the board has accepted. Status words: approved, authorised.
- `change-rejected`: a change memo the board has turned down. Status words: rejected, declined.

**Incident report** (`INC-nnnn`)

- `incident-open`: an incident report on a fault that is still being worked. Status words: ongoing, under investigation.
- `incident-resolved`: an incident report on a fault that is over. Status words: resolved, closed.

**Policy** (`POL-nnn`)

- `policy-draft`: a policy that is not yet binding. Status words: draft, for comment.
- `policy-final`: a policy that is binding. Status words: effective, in force.

**Release notes** (`REL-n.n`)

- `release-notes`: release notes for a software release; no status word, one category. Status words: (none).

A memo carries the words of exactly one status, in two sentences of the body, and never negates
them: no memo says "not approved". Release notes carry none. The title holds the identifier and
the system the memo is about; the body is three short labelled sections, in any order.

Identifier pattern (it appears in the title): `\b(CHG|INC|POL)-\d{3,4}\b|\bREL-\d+\.\d+\b`

## How to decide a fresh document

- Find the identifier in the title; its prefix gives the family (CHG, INC, POL or REL).
- Find the status word in the body and map it to its class with the lists above; release notes
  have no status word and are always `release-notes`.
- The family and the status class together name the category.
- Names, dates, vendors, teams, counts, section order, formatting and wording carry no information.

## Validation (when is a history record the same document?)

A history record is the same document only when both its identifier and its status class match
the task. Compare identifiers after upper-casing: `chg-4412` and `CHG-4412` are one identifier.
Compare the class, not the word: `approved` and `authorised` are one class. Either test alone is
unsound: a change request and the later approval of the same change share the identifier but are
two documents with two categories; two approved changes share the category but are two documents,
and neither is `duplicate_of` the other.

## Worked example

The task title reads `CHG-4412: change to the Payroll Gateway` and two sentences of the body call
the change `approved`. The family is CHG and the class is approved, so the category is
`change-approved`. History holds `H-1a2b3c`, a `change-request` memo titled `CHG-4412: Payroll
Gateway change memo` whose body says `pending`: same identifier, different class, so it is a
different document and not `duplicate_of`, however much of the text matches. History also holds
`H-9d8e7f`, a `change-approved` memo for `CHG-7781`: same category, different identifier, a
different change. Unless some history record carries both `CHG-4412` and the approved class,
`duplicate_of` is `null`.

## Output

Write `answer.json` in this directory:

```json
{"category": "change-approved", "duplicate_of": "H-3fa9c2"}
```

`category` is exactly one of the eight names above (case does not matter). `duplicate_of` is the
`hid` of the history record that describes the same document, or `null` when none does. A document
that merely resembles a history record is not it. It is always a history id, never a task id.
Extra keys are ignored.

## Rules

- Do not modify `history.jsonl` or `task.json`; write nothing except `answer.json`.
- Only `answer.json` is graded. Your final message is not.
