# Support ticket resolution

You are a support engineer. One ticket is in `task.json`; your job is to decide which catalogue
resolution applies and write it to `answer.json`.

## Files in this directory

- `INSTRUCTIONS.md`: this file.
- `history.jsonl`: one JSON object per line, every one a closed, verified ticket: fields `hid`,
  `product`, `error_code`, `platform`, `resolution_id` (the verified answer), `subject`, `body`, `opened`.
- `task.json`: the ticket to resolve: `tid`, `seq`, `product`, `error_code`, `platform`, `subject`,
  `body`, `opened`.

`history.jsonl` contains verified answers. If `task.json` describes the same underlying item as a
history record (the same ticket, not merely a similar one), you may reuse that record's answer.
Before you do, check the fields under Validation below; near-identical records with a different
value there are different items with different answers.

## Resolution catalogue

- `R-01`: Restart the application and retry
- `R-02`: Sign out and sign in again to refresh the session
- `R-03`: Clear the local cache
- `R-04`: Roll back to the previous release
- `R-05`: Install the latest update
- `R-06`: Grant the app Full Disk Access / storage permission
- `R-07`: Whitelist the service endpoints on the proxy or firewall
- `R-08`: Rebuild the local index
- `R-09`: Repair the local database with the built-in repair tool
- `R-10`: Free space on the system drive
- `R-11`: Disable the conflicting extension or add an antivirus exclusion
- `R-12`: Correct the system clock and enable automatic time (NTP)
- `R-13`: Repair ownership and permissions of the data directory
- `R-14`: Increase the upload chunk timeout in Settings
- `R-15`: Update the operating system to a supported release
- `R-16`: Reset the locale and number-format settings
- `R-17`: Assign or purchase additional storage quota
- `R-18`: Enable TLS 1.2 in the system settings
- `R-19`: Close the other instance that holds the database lock
- `R-20`: Move the data directory to a local, non-network drive
- `R-21`: Re-import the affected period and remove the duplicate batch
- `R-22`: Restore the configuration file from the template
- `R-23`: Clear the OAuth consent and grant access again
- `R-24`: Move the data directory to a drive with free space
- `R-25`: Reinstall the application

## Resolution guide

The error code names the symptom; the two sentences in the body that tell the story behind it
(the *cue*) decide the fix. Codes are product-specific; the symptom they carry is listed first.

**authentication token rejected** (E-1100, E-2111, E-3122, E-4133, E-5144, E-6155)

- story mentions *password reset* -> `R-02` (except Android: `R-23`)
- story mentions *clock* -> `R-12`
- story mentions *office network* -> `R-07`
- story mentions *shared account* -> `R-25` (except Android: `R-23`)
- story mentions *single sign-on* -> `R-23` (except Linux: `R-02`)

**cannot write to data directory** (E-1137, E-2148, E-3159, E-4170, E-5181, E-6192)

- story mentions *OS upgrade* -> `R-13` (except Android: `R-06`; macOS: `R-06`; Windows: `R-11`)
- story mentions *disk nearly full* -> `R-24` (except Android: `R-10`; Windows: `R-10`)
- story mentions *network share* -> `R-20`
- story mentions *antivirus* -> `R-11`
- story mentions *read-only* -> `R-13` (except Android: `R-06`; Windows: `R-11`)

**TLS handshake failed** (E-1174, E-2185, E-3196, E-4207, E-5218, E-6229)

- story mentions *firewall appliance* -> `R-07`
- story mentions *old release* -> `R-15` (except Windows: `R-18`)
- story mentions *clock* -> `R-12`
- story mentions *inspection* -> `R-05` (except Android: `R-25`)
- story mentions *captive portal* -> `R-01`

**local database is locked** (E-1211, E-2222, E-3233, E-4244, E-5255, E-6266)

- story mentions *two instances* -> `R-19` (except Android: `R-01`)
- story mentions *crash* -> `R-09` (except Android: `R-25`)
- story mentions *network drive* -> `R-20`
- story mentions *backup* -> `R-01` (except Android: `R-03`)
- story mentions *sync tool* -> `R-20` (except Android: `R-01`)

**upload stalled at 0 bytes/s** (E-1248, E-2259, E-3270, E-4281, E-5292, E-6303)

- story mentions *large files* -> `R-14`
- story mentions *VPN* -> `R-07`
- story mentions *interrupted* -> `R-08` (except Android: `R-03`)
- story mentions *update* -> `R-03`
- story mentions *battery saver* -> `R-22` (except Android: `R-05`)

**storage quota exceeded** (E-1285, E-2296, E-3307, E-4318, E-5329, E-6340)

- story mentions *team plan* -> `R-17`
- story mentions *cache* -> `R-03`
- story mentions *plan change* -> `R-02`
- story mentions *duplicate batch* -> `R-21`
- story mentions *shared folder* -> `R-17` (except Android: `R-02`)

**application crashed on launch** (E-1322, E-2333, E-3344, E-4355, E-5366, E-6377)

- story mentions *right after updating* -> `R-04`
- story mentions *extension* -> `R-11` (except Android: `R-25`)
- story mentions *config file* -> `R-22` (except Android: `R-25`)
- story mentions *graphics driver* -> `R-05` (except Android: `R-25`)
- story mentions *display scaling* -> `R-05` (except Linux: `R-22`)

**totals do not match source** (E-1359, E-2370, E-3381, E-4392, E-5403, E-6414)

- story mentions *regional format* -> `R-16`
- story mentions *imported twice* -> `R-21`
- story mentions *rounding* -> `R-05`
- story mentions *stale cache* -> `R-08` (except Android: `R-03`)
- story mentions *time zone* -> `R-16` (except Android: `R-02`)

## How to decide a fresh ticket

- Find the error code's symptom block above, then match the story in the body to one of its cues.
- Apply the platform exception if the ticket's `platform` is listed for that cue.
- The customer's own attempts (restarting, waiting, searching) never change the answer.
- Names, dates, version patch numbers and wording carry no information.

## Validation (when is a history record the same ticket?)

A history record can only be the same ticket when `product`, `error_code` and `platform` match after
normalisation: case does not matter, and `E-1042`, `e-1042` and `E1042` are one code. Matching
fields are necessary, not sufficient: the same code on the same platform with a different story is
a different ticket with a different resolution.

## Output

Write `answer.json` in this directory:

```json
{"resolution_id": "R-07"}
```

Ids are case-insensitive and `R-7` equals `R-07`. Extra keys are ignored.

## Rules

- Do not modify `history.jsonl` or `task.json`; write nothing except `answer.json`.
- Only `answer.json` is graded. Your final message is not.
