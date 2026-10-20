"""Assignment 2 -- logs: incident triage across the near-identical logs of one fleet.

Concept this file teaches: ten hosts of one service write ten copies of the same log.
Every line carries a timestamp, a host name and a request id that differ, and the
text around them that does not. The facts an on-call engineer needs -- which host
came up with a different configuration, which one runs the old release, which one
failed first and how badly -- are a handful of lines in one file each, hidden among
hundreds of lines that every other host also wrote. Reading the fleet in full costs
the whole corpus; reading one host and the differences of the others costs a page.

Design rules this file embodies:
  * One skeleton per scenario, one rendering per host. The sequence of events (banner,
    health checks, requests, metrics) is shared, so hosts are near-duplicates by
    construction; each host rolls its own latencies and ids and re-routes a small share
    of requests, so they are not identical. Three hosts carry one planted fact each.
  * Numbers are where logs differ, and the content normaliser masks them. Host names
    are numbered for the same reason real fleets number them; a fleet named after
    Greek letters would defeat the masking, and that is a legitimate finding too.
  * Every answer is read off the state, never off the text; the text is checked to
    contain it (content_truth records the lines).

Run from the repo root:  /usr/local/bin/python3.13 assignment2/datasets/logs/generate.py
"""

import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common, corpus  # noqa: E402

SERVICES = ["checkout", "inventory", "search", "billing", "notify", "gateway", "ledger", "catalog"]
CONFIG_KEYS = [("max_connections", ["128", "256", "512"]), ("pool_size", ["8", "16", "32"]),
               ("request_timeout_ms", ["2000", "5000", "8000"]), ("cache_ttl_s", ["60", "300", "900"]),
               ("log_level", ["INFO", "DEBUG"]), ("queue_depth", ["100", "500", "1000"]),
               ("gc_interval_s", ["30", "60", "120"])]
EXCEPTIONS = ["TimeoutError", "ConnectionResetError", "DeadlineExceeded", "PoolExhausted", "UpstreamUnavailable",
              "SerializationError"]
DEPENDENCIES = ["payments-api", "user-service", "pricing-cache", "ledger-db", "search-index", "mailer"]
ROUTES = ["GET /health", "POST /v1/orders", "GET /v1/orders/{id}", "POST /v1/payments", "GET /v1/items/{id}",
          "PUT /v1/cart", "GET /v1/search", "DELETE /v1/cart/{id}", "GET /v1/profile", "POST /v1/refunds"]
WARNINGS = ["slow query took {n}ms on shard {s}", "retrying upstream call (attempt {s}/3)",
            "cache miss ratio above 0.{n}", "connection pool at {n}% capacity"]
WINDOW_S = 480          # eight minutes of log per host
REQUEST_EVERY_S = 8
HEALTH_EVERY_S = 30
METRICS_EVERY_S = 120
ROUTE_JITTER = 0.06     # share of request lines a host re-routes to its own traffic
PRIORITY = {"health": 0, "request": 1, "metrics": 2, "warn": 3, "error": 4}   # order within one second


def kinds():
    def drift(state, target):
        return {"host": state["hosts"][state["drift_host"]], "key": state["drift_key"]}

    def old_version(state, target):
        return {"host": state["hosts"][state["version_host"]], "version": state["previous"]}

    def first_error(state, target):
        return {"host": state["hosts"][state["error_host"]], "first_error_at": state["derived"]["first_error_at"]}

    def error_class(state, target):
        return {"error": state["exception"], "count": state["derived"]["error_count"]}

    def error_count(state, target):
        return {"host": target, "count": state["derived"]["error_count"] if target == state["hosts"][state["error_host"]] else 0}

    def last_healthy(state, target):
        return {"host": state["hosts"][state["error_host"]], "last_healthy_at": state["derived"]["last_healthy_at"]}

    def count_targets(state):
        return [state["hosts"][state["error_host"]], state["hosts"][state["healthy_host"]]]

    return (
        corpus.Kind("drift_host", "which host started with a different configuration",
                    ["One host of the {service} fleet came up with a startup configuration that differs from the rest. Please find which host, and which configuration key differs.",
                     "We think one {service} host loaded a different configuration at startup. Tell me which host it is and which key is set differently from the others.",
                     "Which {service} host has a startup configuration that does not match the other hosts, and on which key does it differ?"],
                    ["The logs of every host for the incident window are in logs/, one file per host. The startup banner prints the configuration one key per line.",
                     "Every host wrote its startup banner, configuration included, at the top of its log file in logs/.",
                     "You will find one log file per host under logs/; the banner at the top of each lists the loaded configuration."],
                    drift, ("host", "key"), example={"host": "checkout-03", "key": "pool_size"}),
        corpus.Kind("old_version", "which host runs a different release",
                    ["Which {service} host is running a different release than the others, and which version is it on?",
                     "One of the {service} hosts was never upgraded with the rest of the fleet. Find that host and the version it reports.",
                     "Please check the release each {service} host reports at startup and name the host whose version differs, with that version."],
                    ["The release is printed in the first line of each host's log in logs/.",
                     "Each host logs its release and build in its startup line; the files are under logs/.",
                     "Look at the starting line of every file in logs/ for the version string."],
                    old_version, ("host", "version"), example={"host": "checkout-05", "version": "4.11.3"}),
        corpus.Kind("first_error", "which host failed first and when",
                    ["Which {service} host logged the first ERROR line of the window, and at what timestamp, exactly as logged?",
                     "Find the first ERROR anywhere in the {service} fleet: the host that wrote it and the exact timestamp of that line.",
                     "I need the host and the exact timestamp of the earliest ERROR line across all {service} hosts."],
                    ["Timestamps are ISO-8601 with a Z suffix; copy the one on the line itself.",
                     "Please quote the timestamp as it appears in the log line, including the Z.",
                     "The logs are under logs/; lines at level ERROR are the ones to look for."],
                    first_error, ("host", "first_error_at"), example={"host": "checkout-07", "first_error_at": "2026-03-04T14:22:31Z"}),
        corpus.Kind("error_class", "what failed on the failing host and how often",
                    ["On the {service} host that raised errors, which exception class appears in the ERROR lines, and how many ERROR lines did it write in total?",
                     "One {service} host wrote ERROR lines during the window. Name the exception class in those lines and count the ERROR lines.",
                     "Tell me the exception class behind the {service} errors and the total number of ERROR lines on the host that logged them."],
                    ["Count lines at level ERROR only; WARN lines about failed health checks are not errors for this purpose.",
                     "Only lines whose level is ERROR count; health-check warnings do not.",
                     "The count is of ERROR-level lines on that host, nothing else."],
                    error_class, ("error", "count"), example={"error": "TimeoutError", "count": 14}),
        corpus.Kind("error_count", "how many ERROR lines did {target} write",
                    ["How many ERROR lines did the host {target} write during the window?",
                     "Please count the lines at level ERROR in the log of {target}.",
                     "For the host {target}, how many of its log lines are at level ERROR?"],
                    ["Its log is logs/{target}.log. Zero is a valid answer.",
                     "The file is logs/{target}.log; if it logged no errors the count is 0.",
                     "Look only at logs/{target}.log and count ERROR-level lines; 0 if there are none."],
                    error_count, ("host", "count"), targets=count_targets, example={"host": "checkout-02", "count": 0}),
        corpus.Kind("last_healthy", "last successful health check before the failure",
                    ["On the {service} host that raised errors, what is the timestamp of its last successful health check before its first ERROR line?",
                     "For the failing {service} host, find the last 'health check ok' line that precedes its first ERROR and give me its timestamp.",
                     "I need the exact timestamp of the final passing health check on the {service} host that failed, taken before the first ERROR it logged."],
                    ["Health checks are INFO lines reading 'health check ok'; copy the timestamp exactly as logged.",
                     "The line reads 'health check ok (latency ...)'; quote its timestamp with the Z suffix.",
                     "Use the timestamp of the log line itself, in the ISO form it is printed in."],
                    last_healthy, ("host", "last_healthy_at"), example={"host": "checkout-07", "last_healthy_at": "2026-03-04T14:22:01Z"}),
    )


class LogsSpec(corpus.CorpusSpec):
    NAME = "logs"
    FILE = __file__
    TITLE = "Incident triage from fleet logs"
    ROLE = ("You are the on-call engineer. One request about an incident is in `task.json`; answer it from the log\n"
            "files in `logs/` and write the answer to `answer.json`.")
    FILE_LAYOUT = ("`logs/<service>-<nn>.log`: one file per host of the fleet for the incident window, one line per "
                   "event: `<timestamp> <host> <LEVEL> <message>`.")
    KINDS = kinds()
    SCENARIOS = 24
    SCENARIO_PREFIX = "INC"
    DEFAULT_SEED = 61

    def service_of(self, state):
        return state["service"]

    def scenario_state(self, sid, rng):
        service = common.pick(rng, SERVICES)
        n_hosts = rng.randrange(6, 10)
        hosts = ["%s-%02d" % (service, i + 1) for i in range(n_hosts)]
        major, minor, patch = rng.randrange(2, 9), rng.randrange(1, 20), rng.randrange(0, 6)
        release = "%d.%d.%d" % (major, minor, patch)
        previous = "%d.%d.%d" % (major, minor - 1, rng.randrange(0, 9))
        day = datetime.date(2026, 1, 12) + datetime.timedelta(days=rng.randrange(0, 120))
        start = rng.randrange(6, 22) * 3600 + rng.randrange(0, 60) * 60 + rng.randrange(0, 60)
        config = {key: common.pick(rng, values) for key, values in CONFIG_KEYS}
        roles = rng.sample(range(n_hosts), 4)
        drift_key, values = CONFIG_KEYS[rng.randrange(len(CONFIG_KEYS))]
        drift_value = common.pick(rng, [v for v in values if v != config[drift_key]])
        skeleton = []
        for offset in range(0, WINDOW_S, 1):
            if offset % HEALTH_EVERY_S == 0:
                skeleton.append((offset, "health", None))
            if offset % REQUEST_EVERY_S == 3:
                skeleton.append((offset, "request", common.pick(rng, ROUTES)))
            if offset % METRICS_EVERY_S == 17:
                skeleton.append((offset, "metrics", None))
            if offset % 97 == 41:
                skeleton.append((offset, "warn", common.pick(rng, WARNINGS)))
        state = {"scenario": sid, "service": service, "hosts": hosts, "release": release, "previous": previous,
                 "day": day.isoformat(), "start": start, "config": config, "build": "%07x" % rng.getrandbits(28),
                 "drift_host": roles[0], "version_host": roles[1], "error_host": roles[2], "healthy_host": roles[3],
                 "drift_key": drift_key, "drift_value": drift_value,
                 "exception": common.pick(rng, EXCEPTIONS), "dependency": common.pick(rng, DEPENDENCIES),
                 "n_errors": rng.randrange(8, 21), "first_error_offset": rng.randrange(150, 420),
                 "error_spacing": rng.randrange(3, 9), "skeleton": skeleton}
        # Rendering the failing host once settles the derived timestamps the answers quote.
        lines, marks = self.render_host(state, state["error_host"])
        state["derived"] = marks["derived"]
        return state

    def stamp(self, state, offset):
        day = datetime.date.fromisoformat(state["day"])
        total = state["start"] + offset
        return corpus.ts(day, (total // 3600) % 24, (total // 60) % 60, total % 60)

    def render_host(self, state, index):
        """The log lines of one host and the 1-based line numbers of its planted facts."""
        host = state["hosts"][index]
        rng = common.sub_rng(self.NAME + "-host", state["scenario"], host)
        skew = rng.randrange(0, 4)
        lines, marks = [], {"answer_lines": [], "derived": {}}

        def emit(offset, level, message):
            lines.append("%s %s %-5s %s" % (self.stamp(state, offset + skew), host, level, message))

        release = state["previous"] if index == state["version_host"] else state["release"]
        emit(0, "INFO", "starting %s %s (build %s) on %s" % (state["service"], release, state["build"], host))
        if index == state["version_host"]:
            marks["answer_lines"].append(len(lines))
        for key, _ in CONFIG_KEYS:
            value = state["config"][key]
            if index == state["drift_host"] and key == state["drift_key"]:
                value = state["drift_value"]
            emit(1, "INFO", "config: %s=%s" % (key, value))
            if index == state["drift_host"] and key == state["drift_key"]:
                marks["answer_lines"].append(len(lines))
        emit(2, "INFO", "listening on 0.0.0.0:8080; workers=%d" % (4 * rng.randrange(1, 5)))
        failing = index == state["error_host"]
        first = state["first_error_offset"]
        last = first + state["error_spacing"] * (state["n_errors"] - 1)
        error_offsets = {first + k * state["error_spacing"] for k in range(state["n_errors"])}
        last_ok_line, first_error_line, n_errors = None, None, 0
        events = list(state["skeleton"])
        if failing:
            events += [(offset, "error", None) for offset in sorted(error_offsets)]
            events.sort(key=lambda e: (e[0], PRIORITY[e[1]]))
        for offset, kind, payload in events:
            if kind == "error":
                n_errors += 1
                if n_errors == state["n_errors"]:
                    emit(offset, "ERROR", "%s: giving up on %s after %d attempts" % (
                        state["exception"], state["dependency"], state["n_errors"]))
                else:
                    emit(offset, "ERROR", "%s: %s did not respond within %sms (attempt %d/3)" % (
                        state["exception"], state["dependency"], state["config"]["request_timeout_ms"],
                        1 + (n_errors - 1) % 3))
                if first_error_line is None:
                    first_error_line = len(lines)
                    marks["derived"]["first_error_at"] = lines[-1].split(" ")[0]
            elif kind == "health":
                if failing and first <= offset <= last:
                    emit(offset, "WARN", "health check FAILED: %s unreachable" % state["dependency"])
                else:
                    emit(offset, "INFO", "health check ok (latency %dms)" % rng.randrange(1, 12))
                    if failing and offset < first:
                        last_ok_line = len(lines)
            elif kind == "request":
                route = payload
                if rng.random() < ROUTE_JITTER:
                    route = common.pick(rng, ROUTES)
                status = 503 if failing and first <= offset <= last and rng.random() < 0.5 else 200
                emit(offset, "INFO", "%s %d in %dms rid=%06x" % (
                    route.replace("{id}", str(rng.randrange(1000, 99999))), status, rng.randrange(4, 400),
                    rng.getrandbits(24)))
            elif kind == "metrics":
                emit(offset, "INFO", "metrics: rps=%d p99=%dms heap=%dMB goroutines=%d" % (
                    rng.randrange(40, 400), rng.randrange(20, 900), rng.randrange(200, 1800), rng.randrange(50, 900)))
            elif kind == "warn":
                emit(offset, "WARN", payload.format(n=rng.randrange(10, 95), s=rng.randrange(1, 4)))
        if failing:
            marks["derived"]["error_count"] = sum(1 for line in lines if " ERROR " in line)
            marks["derived"]["last_healthy_at"] = lines[last_ok_line - 1].split(" ")[0]
            marks["answer_lines"] += [first_error_line, last_ok_line]
        return lines, marks

    def scenario_files(self, state):
        files = {}
        for index, host in enumerate(state["hosts"]):
            lines, _ = self.render_host(state, index)
            files["logs/%s.log" % host] = "\n".join(lines) + "\n"
        return files

    def content_truth(self, state, files):
        answer_lines = {}
        for index, host in enumerate(state["hosts"]):
            _, marks = self.render_host(state, index)
            if marks["answer_lines"]:
                answer_lines["logs/%s.log" % host] = sorted(marks["answer_lines"])
        return {"groups": [{"name": "fleet-logs", "files": sorted(files)}], "answer_lines": answer_lines}

    def domain_instructions(self):
        return ["## The scenario", "",
                "`logs/` holds one file per host of one service for the incident window. Every host writes the same",
                "kind of log: a startup banner (`starting <service> <version> (build ...)`, then one `config: key=value`",
                "line per configuration key, then `listening ...`), health checks every 30 s (`health check ok` or",
                "`health check FAILED`), request lines, a `metrics:` line every two minutes and occasional WARN lines.",
                "Levels are INFO, WARN and ERROR; timestamps are ISO-8601 with a `Z` suffix.", "",
                "## How to decide", "",
                "- Configuration drift: compare the `config:` lines of the banners. The fleet agrees on every key except",
                "  one host on one key.",
                "- Release: the `starting <service> <version>` line. One host reports a different version.",
                "- Errors: lines at level ERROR, counted per host. A failed health check is a WARN line, not an error.",
                "- Timestamps are quoted exactly as logged, e.g. `2026-03-04T14:22:31Z`.",
                "- The last successful health check is the last `health check ok` line on that host that precedes its",
                "  first ERROR line."]


SPEC = LogsSpec()

if __name__ == "__main__":
    sys.exit(corpus.main(SPEC))
