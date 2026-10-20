# Configuration drift audit

You are a platform engineer. One request about a service's configuration is in `task.json`; answer it
from the files in `config/` and write the answer to `answer.json`.

## Files in this directory

- `INSTRUCTIONS.md`: this file.
- `task.json`: the request to answer: `tid`, `seq`, `scenario`, `kind`, `target`, `subject`, `body`, `received`.
- `config/<environment>.yaml`: one configuration file per environment of the service, same layout in every file; `config/POLICY.md`: which keys must be uniform, which may vary, and the two security requirements.
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

`config/` holds one YAML file per environment of one service (`dev.yaml`, `staging.yaml`,
`prod-eu.yaml`, ...), all generated from the same template, plus `config/POLICY.md`, which lists the
keys that must be identical in every environment, the keys that may differ, and two security
requirements. Keys are referred to as `section.key`, e.g. `database.pool_size`.

## How to decide

- Drift: a must-be-uniform key whose value in one environment differs from all the others. Keys the
  policy allows to vary never count, and the two security keys are a separate question.
- Security: `tls.verify` must be `true` and `auth.allow_anonymous` must be `false`; one environment
  violates one of them.
- A missing key is absent from one environment's file and present in every other.
- Values are reported as written in the file (`6`, `debug`, `verify-full`).

## Request kinds and the answer each expects

`kind` in `task.json` says which question is being asked; `target` names what it is about
when the kind takes one (otherwise it is `null`). Write exactly these keys:

- `drift`: which environment drifted on a uniform key. Answer keys: `environment`, `key`. Example: `{"environment": "prod-eu", "key": "database.pool_size"}`
- `insecure`: which environment violates a security requirement. Answer keys: `environment`, `key`. Example: `{"environment": "staging", "key": "tls.verify"}`
- `missing_key`: which environment is missing a key. Answer keys: `environment`, `key`. Example: `{"environment": "dr", "key": "cache.max_entries"}`
- `replicas_of`: how many replicas does <target> run. Answer keys: `environment`, `value`. Example: `{"environment": "prod-eu", "value": 6}`
- `most_replicas`: which environment runs the most replicas. Answer keys: `environment`, `value`. Example: `{"environment": "prod-us-east", "value": 12}`
- `log_level_of`: what log level does <target> use. Answer keys: `environment`, `value`. Example: `{"environment": "dev", "value": "debug"}`

## Validation (when is a history record the same request?)

Only when `scenario`, `kind` and `target` all match after normalisation (case does not matter,
`CFG-1234` and `CFG1234` are one scenario). Matching wording is not enough.

## Output

Write `answer.json` in this directory with the keys listed for the request's kind. Strings are
compared case-insensitively on their letters and digits; numbers as numbers; lists as sets.
Extra keys are ignored.

## Rules

- Do not modify the scenario files, `history.jsonl` or `task.json`; write nothing except `answer.json`.
- Only `answer.json` is graded. Your final message is not.
