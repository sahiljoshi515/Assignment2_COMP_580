# Dataset `hosts` — inventory snapshots of one fleet, and the host that drifted

**What a scenario is.** A fleet of 6–9 hosts of one role (`web`, `api`, `worker`, ...), built
from one image. `inventory/<host>.txt` is each host's snapshot, written by the same agent
in the same order: `[system]` facts, the `[kernel.params]` profile, `[packages]`
(`name = version`), `[mounts]`, `[services]` (`active` / `inactive`), `[environment]`,
`[certificates]` and `[load]`. About 95 lines each; roughly a dozen lines carry
host-specific numbers (uptime, free memory, disk usage, load) and everything else is
shared, so the files are near-duplicates whose exact diff is short.

**What a request is.** A question about one scenario, as a `task.json` with `scenario`,
`kind`, `target` and a short message. Seven kinds: `package_drift`, `kernel_drift`,
`param_drift`, `missing_mount`, `service_down`, `fullest_disk`, and `uptime_of <host>`.
History records are earlier requests with their verified `answer`.

**What decides the answer.** Five planted facts on five different hosts (one package
version, the kernel, one kernel parameter, one missing mount, one inactive service), the
host with the highest `used_pct` on `/`, and each host's `uptime_days`. All are single
lines in one file, and all except the fullest disk and the uptimes are lines on which one
host differs from every other.

**Two layers of repetition.** The request stream repeats as in the first four datasets
(40 % duplicates of earlier requests: exact, reformatted, reordered, lightly edited,
paraphrased; 20 % hard negatives, mostly the same question about another scenario).
Inside a task the corpus repeats: every host file is a near-duplicate of every other
(masked-token Jaccard 0.95–1.00 by `MANIFEST.json`), which is what the content layer
folds. `hidden/content.json` records the group and the planted lines per file.

**When a previous answer is safe to reuse.** Same `scenario`, `kind` and `target` after
normalisation. A request about another scenario reads the same and has another answer.

**Sizes and seed.** 24 scenarios (3.3K–5.1K tokens each), 60 history records, 40 incoming
requests, seed 73, about 13K tokens in one task's working directory.

**Regenerate.**

```sh
/usr/local/bin/python3.13 assignment2/datasets/hosts/generate.py
/usr/local/bin/python3.13 assignment2/datasets/hosts/verify.py --tid T-xxxxxx --answer answer.json
```
