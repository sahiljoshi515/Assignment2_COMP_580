# Questions about a shared mailbox

You are an assistant with access to a team mailbox export. One question about it is in `task.json`;
answer it from the messages in `inbox/` and write the answer to `answer.json`.

## Files in this directory

- `INSTRUCTIONS.md`: this file.
- `task.json`: the request to answer: `tid`, `seq`, `scenario`, `kind`, `target`, `subject`, `body`, `received`.
- `inbox/<nnn>_<subject>.eml`: one message per file in date order, plain-text headers (From, To, Date, Subject) and body; replies quote the message they answer with `> ` prefixes.
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

`inbox/` is an export of a shared mailbox: one message per file, numbered in date order, with plain
headers (`From`, `To`, `Cc`, `Date`, `Subject`) followed by the body. It holds a few discussion
threads (an original message and its replies, each reply quoting the message it answers with `> `
prefixes), a series of automated nightly backup reports from the backup service, and some
unrelated announcements.

## How to decide

- A thread is the set of messages sharing a subject, with or without `Re:`. Quoted text inside a
  reply belongs to the earlier message, not to the reply.
- A decision message says approve, reject or defer (in those words or close ones: approved, not
  approved, park/defer). A later correction overrides an earlier decision; the final decision is the
  last one in the thread. Report the decision as one of `approve`, `reject`, `defer`.
- People are reported by the display name in the From header; dates as `YYYY-MM-DD` taken from the
  Date header of the message in question.
- Nightly reports carry their date in the subject and on the first body line; the Status line says
  SUCCESS or FAILED (reason); the timing line gives the Duration in minutes.

## Request kinds and the answer each expects

`kind` in `task.json` says which question is being asked; `target` names what it is about
when the kind takes one (otherwise it is `null`). Write exactly these keys:

- `final_decision`: final decision in the <target> thread. Answer keys: `decision`, `by`, `date`. Example: `{"decision": "defer", "by": "Hannah Cole", "date": "2026-03-11"}`
- `requester`: who opened the <target> thread. Answer keys: `name`. Example: `{"name": "Priya Nair"}`
- `message_count`: how many messages in the <target> thread. Answer keys: `count`. Example: `{"count": 6}`
- `failed_backups`: which nightly backups failed. Answer keys: `dates`. Example: `{"dates": ["2026-03-02", "2026-03-05"]}`
- `longest_backup`: which nightly backup took longest. Answer keys: `date`, `minutes`. Example: `{"date": "2026-03-04", "minutes": 57}`
- `first_failed_backup`: first failed nightly backup and why. Answer keys: `date`, `reason`. Example: `{"date": "2026-03-02", "reason": "target volume full"}`

## Validation (when is a history record the same request?)

Only when `scenario`, `kind` and `target` all match after normalisation (case does not matter,
`MBX-1234` and `MBX1234` are one scenario). Matching wording is not enough.

## Output

Write `answer.json` in this directory with the keys listed for the request's kind. Strings are
compared case-insensitively on their letters and digits; numbers as numbers; lists as sets.
Extra keys are ignored.

## Rules

- Do not modify the scenario files, `history.jsonl` or `task.json`; write nothing except `answer.json`.
- Only `answer.json` is graded. Your final message is not.
