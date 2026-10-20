# Fleet inventory audit

You are auditing a fleet. One request is in `task.json`; answer it from the inventory snapshots in
`inventory/` and write the answer to `answer.json`.

## Files in this directory

- `INSTRUCTIONS.md`: this file.
- `task.json`: the request to answer: `tid`, `seq`, `scenario`, `kind`, `target`, `subject`, `body`, `received`.
- `inventory/<host>.txt`: one snapshot per host of the fleet, same sections in every file ([system], [kernel.params], [packages], [mounts], [services], [environment], [load]).
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

`inventory/` holds one snapshot per host of one fleet, all built from the same image and written by
the same agent, so the files share their sections and most of their lines: [system] facts, the
[kernel.params] profile, the [packages] list (`name = version`), [mounts] (`path device fstype
size_gb=N used_pct=N`), [services] (`name = active|inactive`), [environment], [certificates] and
[load]. Uptime, free memory, disk usage and load differ per host and are not drift.

## How to decide

- Drift is one host differing from every other on a line that should be the same: a package
  version, the kernel, a kernel parameter, a missing mount, an inactive service.
- Report hosts by their short name (`web-03`), packages, parameters and services by the name on the
  line, kernels and versions exactly as written, percentages and days as integers.

## Request kinds and the answer each expects

`kind` in `task.json` says which question is being asked; `target` names what it is about
when the kind takes one (otherwise it is `null`). Write exactly these keys:

- `package_drift`: which host has a different package version. Answer keys: `host`, `package`. Example: `{"host": "web-03", "package": "openssl"}`
- `kernel_drift`: which host runs a different kernel. Answer keys: `host`, `kernel`. Example: `{"host": "web-05", "kernel": "5.15.0-105-generic"}`
- `param_drift`: which host has a different kernel parameter. Answer keys: `host`, `parameter`. Example: `{"host": "web-02", "parameter": "net.core.somaxconn"}`
- `missing_mount`: which host is missing a mount. Answer keys: `host`, `mount`. Example: `{"host": "web-07", "mount": "/mnt/backup"}`
- `service_down`: which host has a service that is not running. Answer keys: `host`, `service`. Example: `{"host": "web-01", "service": "fluent-bit"}`
- `fullest_disk`: which host has the fullest root filesystem. Answer keys: `host`, `used_pct`. Example: `{"host": "web-04", "used_pct": 83}`
- `uptime_of`: how long has <target> been up. Answer keys: `host`, `days`. Example: `{"host": "web-06", "days": 41}`

## Validation (when is a history record the same request?)

Only when `scenario`, `kind` and `target` all match after normalisation (case does not matter,
`FLT-1234` and `FLT1234` are one scenario). Matching wording is not enough.

## Output

Write `answer.json` in this directory with the keys listed for the request's kind. Strings are
compared case-insensitively on their letters and digits; numbers as numbers; lists as sets.
Extra keys are ignored.

## Rules

- Do not modify the scenario files, `history.jsonl` or `task.json`; write nothing except `answer.json`.
- Only `answer.json` is graded. Your final message is not.
