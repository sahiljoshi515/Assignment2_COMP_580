# Questions about the revisions of a policy

You maintain the policy library. One question about one policy's history is in `task.json`; answer it
from the revisions in `policy/` and write the answer to `answer.json`.

## Files in this directory

- `INSTRUCTIONS.md`: this file.
- `task.json`: the request to answer: `tid`, `seq`, `scenario`, `kind`, `target`, `subject`, `body`, `received`.
- `policy/vNN.md`: every revision of one policy as a Markdown file, v01 the oldest; the same sections in every revision, no changelog.
- `history.jsonl`: one JSON object per line, every one a closed, verified request: fields `hid`,
  `scenario`, `kind`, `target`, `subject`, `body`, `answer` (the verified answer object), `filed`.

`history.jsonl` contains verified answers. If `task.json` asks the same question about the same
scenario as a history record (the same `scenario`, `kind` and `target`, not merely a similar
request), you may reuse that record's `answer`. A different scenario with the same wording is a
different request with a different answer.

Tool results may be abbreviated: when a file repeats one you have already read, the tool shows
the repeated part as a reference to the earlier file plus the lines that differ, marked `[reuse]`.
Treat such a result as the full file with those differences.

## The scenario

`policy/` holds every revision of one policy document as Markdown: `v01.md` is the oldest, the
highest number is the current version. Each revision has the same sections (Purpose, Scope,
Definitions, Requirements, Exceptions, Review and ownership). The Requirements section is a list of
numbered items `R1`, `R2`, ...; ids are stable, so a struck requirement leaves a gap and a new one
takes the next free number. The header line of each revision names its label, effective date and
owner. No changelog exists; the history is only in the differences between revisions.

## How to decide

- A parameter (a retention period, a cadence, a limit) is the number inside one requirement's
  sentence; its current value is the one in the latest revision; it was 'introduced' in the earliest
  revision from which that value persists to the latest one; a 'change' is a revision whose value
  differs from the revision before it.
- Revisions are reported by their label as in the file name (`v06`), requirements by id (`R3`),
  owners exactly as written.

## Request kinds and the answer each expects

`kind` in `task.json` says which question is being asked; `target` names what it is about
when the kind takes one (otherwise it is `null`). Write exactly these keys:

- `introduced_in`: which revision set <target> to its current value. Answer keys: `revision`. Example: `{"revision": "v06"}`
- `current_value`: current value of <target>. Answer keys: `value`. Example: `{"value": 90}`
- `removed_requirement`: which revision struck a requirement. Answer keys: `revision`, `requirement`. Example: `{"revision": "v05", "requirement": "R3"}`
- `added_requirement`: which revision added the newest requirement. Answer keys: `revision`, `requirement`. Example: `{"revision": "v07", "requirement": "R9"}`
- `owner_change`: which revision changed the owner. Answer keys: `revision`, `owner`. Example: `{"revision": "v04", "owner": "Data Protection Officer"}`
- `changes_count`: how many times <target> changed. Answer keys: `count`. Example: `{"count": 2}`

## Validation (when is a history record the same request?)

Only when `scenario`, `kind` and `target` all match after normalisation (case does not matter,
`POL-1234` and `POL1234` are one scenario). Matching wording is not enough.

## Output

Write `answer.json` in this directory with the keys listed for the request's kind. Strings are
compared case-insensitively on their letters and digits; numbers as numbers; lists as sets.
Extra keys are ignored.

## Rules

- Do not modify the scenario files, `history.jsonl` or `task.json`; write nothing except `answer.json`.
- Only `answer.json` is graded. Your final message is not.
