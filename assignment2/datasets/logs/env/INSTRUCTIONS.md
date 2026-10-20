# Incident triage from fleet logs

You are the on-call engineer. One request about an incident is in `task.json`; answer it from the log
files in `logs/` and write the answer to `answer.json`.

## Files in this directory

- `INSTRUCTIONS.md`: this file.
- `task.json`: the request to answer: `tid`, `seq`, `scenario`, `kind`, `target`, `subject`, `body`, `received`.
- `logs/<service>-<nn>.log`: one file per host of the fleet for the incident window, one line per event: `<timestamp> <host> <LEVEL> <message>`.
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

`logs/` holds one file per host of one service for the incident window. Every host writes the same
kind of log: a startup banner (`starting <service> <version> (build ...)`, then one `config: key=value`
line per configuration key, then `listening ...`), health checks every 30 s (`health check ok` or
`health check FAILED`), request lines, a `metrics:` line every two minutes and occasional WARN lines.
Levels are INFO, WARN and ERROR; timestamps are ISO-8601 with a `Z` suffix.

## How to decide

- Configuration drift: compare the `config:` lines of the banners. The fleet agrees on every key except
  one host on one key.
- Release: the `starting <service> <version>` line. One host reports a different version.
- Errors: lines at level ERROR, counted per host. A failed health check is a WARN line, not an error.
- Timestamps are quoted exactly as logged, e.g. `2026-03-04T14:22:31Z`.
- The last successful health check is the last `health check ok` line on that host that precedes its
  first ERROR line.

## Request kinds and the answer each expects

`kind` in `task.json` says which question is being asked; `target` names what it is about
when the kind takes one (otherwise it is `null`). Write exactly these keys:

- `drift_host`: which host started with a different configuration. Answer keys: `host`, `key`. Example: `{"host": "checkout-03", "key": "pool_size"}`
- `old_version`: which host runs a different release. Answer keys: `host`, `version`. Example: `{"host": "checkout-05", "version": "4.11.3"}`
- `first_error`: which host failed first and when. Answer keys: `host`, `first_error_at`. Example: `{"host": "checkout-07", "first_error_at": "2026-03-04T14:22:31Z"}`
- `error_class`: what failed on the failing host and how often. Answer keys: `error`, `count`. Example: `{"error": "TimeoutError", "count": 14}`
- `error_count`: how many ERROR lines did <target> write. Answer keys: `host`, `count`. Example: `{"host": "checkout-02", "count": 0}`
- `last_healthy`: last successful health check before the failure. Answer keys: `host`, `last_healthy_at`. Example: `{"host": "checkout-07", "last_healthy_at": "2026-03-04T14:22:01Z"}`

## Validation (when is a history record the same request?)

Only when `scenario`, `kind` and `target` all match after normalisation (case does not matter,
`INC-1234` and `INC1234` are one scenario). Matching wording is not enough.

## Output

Write `answer.json` in this directory with the keys listed for the request's kind. Strings are
compared case-insensitively on their letters and digits; numbers as numbers; lists as sets.
Extra keys are ignored.

## Rules

- Do not modify the scenario files, `history.jsonl` or `task.json`; write nothing except `answer.json`.
- Only `answer.json` is graded. Your final message is not.
