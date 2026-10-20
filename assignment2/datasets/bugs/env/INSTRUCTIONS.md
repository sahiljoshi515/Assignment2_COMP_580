# Bug triage for Lattice

You are the on-call triager for Lattice, a desktop application. One bug report is in `task.json`;
your job is to decide which component owns it and which root cause explains it, and to write
both to `answer.json`.

## Files in this directory

- `INSTRUCTIONS.md`: this file.
- `history.jsonl`: one JSON object per line, every one a closed, triaged report: fields `hid`,
  `exception`, `top_frame`, `version`, `component` and `root_cause` (the verified answers), `title`,
  `body`, `stacktrace`, `reported`.
- `task.json`: the report to triage: `tid`, `seq`, `exception`, `top_frame`, `version`, `title`,
  `body`, `stacktrace`, `reported`.

`history.jsonl` contains verified answers. If `task.json` describes the same underlying item as a
history record (the same bug, not merely a similar one), you may reuse that record's answer.
Before you do, check the fields under Validation below; near-identical records with a different
value there are different items with different answers.

## Component ownership

The component is decided by the module of the top frame of the stacktrace (the frame just above
the exception line; it is repeated in `top_frame`):

- `lattice.net.*` -> `networking`
- `lattice.store.*` -> `storage`
- `lattice.auth.*` -> `auth`
- `lattice.ui.*` -> `ui`
- `lattice.report.*` -> `reporting`
- `lattice.io.*` -> `importer`
- `lattice.sched.*` -> `scheduler`
- `lattice.core.config.*` and `lattice.core.settings.*` -> `config`

## Root cause catalogue

- `RC-01`: None dereference
- `RC-02`: Off-by-one
- `RC-03`: Race condition
- `RC-04`: Missing or renamed configuration key
- `RC-05`: Migration not applied
- `RC-06`: Numeric precision
- `RC-07`: Unhandled timeout
- `RC-08`: Encoding mismatch
- `RC-09`: Path separators
- `RC-10`: Resource leak
- `RC-11`: Stale cache
- `RC-12`: Timezone handling
- `RC-13`: Dependency API change
- `RC-14`: Permission denied
- `RC-15`: Memory exhaustion
- `RC-16`: Regression from refactor
- `RC-17`: Division by zero on empty input
- `RC-18`: Deadlock
- `RC-19`: Unvalidated input
- `RC-20`: Certificate validation

## Release timeline

- 3.0.0: baseline release of the 3.x line.
- 3.1.0: upgraded the bundled HTTP client; the new client changed its API.
- 3.2.0: replaced the storage engine; existing data directories need the engine migration.
- 3.3.0: moved every configuration key under `core.*`; the old key names are no longer read.

## Triage guide

The exception names the failure; the two sentences in the Actual section that tell the story
behind it (the *cue*) decide the root cause. Find the exception below and match the story to one
of its cues; the same cue means the same root cause whichever frame raised it.

**TimeoutError**

- story mentions *slow network* -> `RC-07`
- story mentions *two workers* -> `RC-18`
- story mentions *after upgrading* -> `RC-16` (see the version rules)

**ConnectionError**

- story mentions *under load* -> `RC-10`
- story mentions *after upgrading* -> `RC-16` (see the version rules)
- story mentions *self-signed* -> `RC-20`

**KeyError**

- story mentions *renamed* -> `RC-04`
- story mentions *missing column* -> `RC-19`
- story mentions *previous release* -> `RC-05`

**TypeError**

- story mentions *no owner* -> `RC-01`
- story mentions *after upgrading* -> `RC-16` (see the version rules)
- story mentions *last row* -> `RC-02`

**ValueError**

- story mentions *decimal* -> `RC-06`
- story mentions *midnight* -> `RC-12`
- story mentions *pasted* -> `RC-19`

**OSError**

- story mentions *backslashes* -> `RC-09`
- story mentions *long session* -> `RC-10`
- story mentions *two jobs* -> `RC-03`

**PermissionError**

- story mentions *service account* -> `RC-14`
- story mentions *still open* -> `RC-03`

**MemoryError**

- story mentions *large export* -> `RC-15`
- story mentions *same input* -> `RC-10`

**RuntimeError**

- story mentions *both waiting* -> `RC-18`
- story mentions *after upgrading* -> `RC-16` (see the version rules)
- story mentions *while iterating* -> `RC-03`

**ZeroDivisionError**

- story mentions *empty result* -> `RC-17`
- story mentions *rounds to zero* -> `RC-06`

**UnicodeDecodeError**

- story mentions *Latin-1* -> `RC-08`
- story mentions *web form* -> `RC-19`

**LookupError**

- story mentions *no longer exists* -> `RC-04`
- story mentions *rebuild* -> `RC-11`

**IndexError**

- story mentions *last row* -> `RC-02`
- story mentions *empty selection* -> `RC-19`

**AttributeError**

- story mentions *no owner* -> `RC-01`
- story mentions *after upgrading* -> `RC-16` (see the version rules)

**FileNotFoundError**

- story mentions *backslashes* -> `RC-09`
- story mentions *no longer exists* -> `RC-04`
- story mentions *two jobs* -> `RC-03`

Version rules (they replace the root cause from the table above):

- `lattice.net.*` frame on 3.1.x, story says *after upgrading* -> `RC-13` (the HTTP client upgrade).
- `lattice.store.*` frame on 3.2.x, whatever the story -> `RC-05` (the storage engine swap).
- `lattice.core.*` frame on 3.3.x, whatever the story -> `RC-04` (the key move).

## How to decide a fresh report

- Read the top frame of the stacktrace: its module names the component.
- Find the exception block above and match the Actual section to one of its cues.
- Apply the version rules when the frame family and the version series both match.
- The operating system, host names, caller line numbers, the patch digit of the version, how
  often it happens and the wording carry no information.

## Validation (when is a history record the same bug?)

A history record can only be the same bug when `exception`, `top_frame` and the version series
match after normalisation: `lattice.net.http.fetch` and `lattice/net/http.py::fetch` are one frame
(line numbers are not part of it), and `3.1.2`, `v3.1.4` and `3.1.0` are all series `3.1`.
Matching fields are necessary, not sufficient: the same exception in the same frame on the same
series with a different story is a different bug with a different root cause.

## Output

Write `answer.json` in this directory:

```json
{"component": "networking", "root_cause": "RC-13"}
```

Ids are case-insensitive and `RC-7` equals `RC-07`. Component names are lower-case, with hyphens
where a name has spaces. Extra keys are ignored.

## Rules

- Do not modify `history.jsonl` or `task.json`; write nothing except `answer.json`.
- Only `answer.json` is graded. Your final message is not.
