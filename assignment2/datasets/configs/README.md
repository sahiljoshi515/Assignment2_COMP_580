# Dataset `configs` — configuration drift across the environments of one service

**What a scenario is.** One service deployed to 6–9 environments (`dev`, `staging`,
`prod-eu`, `dr`, ...). `config/<environment>.yaml` is each environment's configuration,
generated from one template: eight sections, about 75 lines, the same comments in every
file. `config/POLICY.md` lists the keys that must be identical everywhere, the keys that
may differ (hosts, replicas, log levels, endpoints, certificate paths) and two security
requirements (`tls.verify` true, `auth.allow_anonymous` false).

**What a request is.** A question about one scenario: `drift` (which environment sets a
must-be-uniform key differently), `insecure` (which environment breaks a security
requirement), `missing_key` (which environment lacks a key the others have),
`replicas_of <env>`, `most_replicas`, `log_level_of <env>`.

**What decides the answer.** Three planted facts in three environments, each one line (or
one absent line) in one file, plus the legitimately varying values. The drift is always
on a key the policy requires to be uniform; the security key and the missing key are
chosen so that a reader who treats every difference as drift is wrong.

**Two layers of repetition.** Requests repeat as in every dataset here (40 % duplicates,
20 % hard negatives). Inside a task the environment files are near-duplicates
(masked-token Jaccard about 0.88 by `MANIFEST.json`); the differences are the handful of
environment-specific lines and the planted ones, so a fold of one file against another
shows about ten lines instead of seventy-five.

**When a previous answer is safe to reuse.** Same `scenario`, `kind` and `target`.

**Sizes and seed.** 24 scenarios (3.5K–5.1K tokens), 60 history records, 40 incoming
requests, seed 67, about 13K tokens in one task's working directory.

**Regenerate.**

```sh
/usr/local/bin/python3.13 assignment2/datasets/configs/generate.py
/usr/local/bin/python3.13 assignment2/datasets/configs/verify.py --tid T-xxxxxx --answer answer.json
```
