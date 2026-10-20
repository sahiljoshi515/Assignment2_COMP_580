# Dataset `logs` — incident triage across the logs of one fleet (the control)

**What a scenario is.** One service's fleet of 6–9 hosts over an eight-minute incident
window, `logs/<service>-<nn>.log`, one line per event: a startup banner (release, build,
one `config:` line per key), health checks every 30 s, request lines, a metrics line
every two minutes, occasional warnings. One host loaded a different configuration, one
runs the previous release, one raises a burst of ERROR lines against a dependency.

**What a request is.** `drift_host`, `old_version`, `first_error`, `error_class`,
`error_count <host>`, `last_healthy`.

**Why this dataset is the control.** Every line of a log carries a timestamp, a host
name, a latency or a request id, so two hosts' logs are near-identical *up to numbers*
(masked-token Jaccard 0.96–1.00) and different on *every line* in their exact text. The
content layer's MinHash step therefore calls the files near-duplicates, and its exact
diff then shows that a fold would not be shorter than the file, so the layer declines
every fold. Including this dataset in the protocol measures what the layer costs when
it can find nothing to fold (its overhead, and any effect of the listing annotation), and
it is the clearest example of the gap between "similar" and "compressible". A masked
diff would have shortened these files and would also have hidden the drifted
`pool_size=32`, which is why the layer never uses one.

**When a previous answer is safe to reuse.** Same `scenario`, `kind` and `target`.

**Sizes and seed.** 24 scenarios (10.8K–16.7K tokens), 60 history records, 40 incoming
requests, seed 61, about 22K tokens in one task's working directory.

**Regenerate.**

```sh
/usr/local/bin/python3.13 assignment2/datasets/logs/generate.py
/usr/local/bin/python3.13 assignment2/datasets/logs/verify.py --tid T-xxxxxx --answer answer.json
```
