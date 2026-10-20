"""Assignment 2 -- configs: configuration drift across the environments of one service.

Concept this file teaches: a service deployed to eight environments has eight copies
of one configuration file, and the copies are supposed to differ only where the
policy says they may (hosts, replica counts, log levels). Drift is the one line that
differs where it must not, and finding it means comparing every copy with every
other -- the classic job for a diff, and the classic place where an agent reads the
same seventy lines eight times.

Design rules this file embodies:
  * The policy is part of the corpus. `config/POLICY.md` says which keys must be
    uniform and which may vary, so the question "which environment drifted" has one
    answer that does not depend on the reader's taste.
  * Legitimate variation is present on purpose. Hostnames, replicas and log levels
    differ between environments; a detector that treats every difference as drift is
    wrong, and so is a fold that hides the one difference that matters.
  * Three planted facts, three environments: a drifted uniform key, a security key set
    unsafely, a key missing altogether. Each is one line (or its absence) in one file.

Run from the repo root:  /usr/local/bin/python3.13 assignment2/datasets/configs/generate.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common, corpus  # noqa: E402

SERVICES = ["orders-api", "billing-api", "search-gateway", "auth-service", "catalog-api", "notify-worker",
            "ledger-api", "shipping-api"]
ENVIRONMENTS = ["dev", "test", "staging", "canary", "prod-us-east", "prod-us-west", "prod-eu", "prod-apac", "dr"]
PROD = {"canary", "prod-us-east", "prod-us-west", "prod-eu", "prod-apac", "dr"}
UNIFORM = [  # (section, key, candidate values, comment)
    ("service", "port", ["8080", "8443", "9000"], "listening port, the same everywhere so the mesh routes work"),
    ("service", "request_timeout_ms", ["5000", "8000", "15000"], "upstream request budget"),
    ("service", "max_body_kb", ["256", "512", "1024"], "request body cap"),
    ("database", "pool_size", ["10", "20", "40"], "connections per replica"),
    ("database", "statement_timeout_ms", ["15000", "30000", "60000"], "server-side statement cap"),
    ("database", "ssl_mode", ["require", "verify-full"], "never 'disable'"),
    ("cache", "ttl_s", ["120", "300", "900"], "default entry lifetime"),
    ("cache", "max_entries", ["5000", "10000", "50000"], "per-replica cap"),
    ("auth", "issuer", ["https://login.example.com", "https://id.example.com"], "token issuer"),
    ("auth", "token_ttl_s", ["900", "3600", "7200"], "access token lifetime"),
    ("auth", "allow_anonymous", ["false"], "SECURITY: must be false in every environment"),
    ("tls", "verify", ["true"], "SECURITY: must be true in every environment"),
    ("tls", "min_version", ['"1.2"', '"1.3"'], "lowest protocol version accepted"),
    ("logging", "format", ["json", "logfmt"], "one format so the pipeline can parse every environment"),
    ("logging", "sample_rate", ["1.0", "0.5", "0.25"], "share of debug lines kept"),
    ("features", "new_checkout", ["true", "false"], "feature flags are rolled out fleet-wide"),
    ("features", "async_refunds", ["true", "false"], "feature flags are rolled out fleet-wide"),
    ("features", "rate_limiting", ["true", "false"], "feature flags are rolled out fleet-wide"),
    ("payments", "provider", ["stripe", "adyen", "braintree"], "one provider per service"),
    ("payments", "retry_limit", ["2", "3", "5"], "transient failures retried this many times"),
    ("payments", "backoff_ms", ["100", "200", "500"], "base backoff between retries"),
    ("payments", "idempotency", ["true"], "every write carries an idempotency key"),
]
SECURITY_KEYS = {("auth", "allow_anonymous"): "true", ("tls", "verify"): "false"}
VARIABLE = {("service", "replicas"), ("database", "host"), ("cache", "endpoint"), ("tls", "cert_path"),
            ("logging", "level")}
SECTIONS = ["service", "database", "cache", "auth", "tls", "logging", "features", "payments"]


def dotted(section, key):
    return "%s.%s" % (section, key)


def kinds():
    def drift(state, target):
        return {"environment": state["drift_env"], "key": dotted(*state["drift_key"])}

    def insecure(state, target):
        return {"environment": state["insecure_env"], "key": dotted(*state["insecure_key"])}

    def missing(state, target):
        return {"environment": state["missing_env"], "key": dotted(*state["missing_key"])}

    def replicas_of(state, target):
        return {"environment": target, "value": state["replicas"][target]}

    def most_replicas(state, target):
        env = max(state["environments"], key=lambda e: (state["replicas"][e], e))
        return {"environment": env, "value": state["replicas"][env]}

    def log_level_of(state, target):
        return {"environment": target, "value": state["levels"][target]}

    def two_envs(state):
        return state["targets"]

    return (
        corpus.Kind("drift", "which environment drifted on a uniform key",
                    ["One environment of {service} carries a value that differs from every other environment on a key that POLICY.md says must be uniform. Which environment, and which key?",
                     "Please audit the {service} configs for drift: find the environment whose copy sets a must-be-uniform key differently from the rest, and name the key.",
                     "Which {service} environment deviates from the others on a key the policy requires to be identical everywhere, and what is that key (section.key)?"],
                    ["Keys that may legitimately vary (hosts, replicas, log levels) are listed in config/POLICY.md and do not count. Ignore the security keys for this question; they are a separate audit.",
                     "config/POLICY.md lists which keys may differ between environments; only a key outside that list counts as drift. Leave the two security keys to the separate security check.",
                     "Use the uniformity list in config/POLICY.md; the environment-specific keys it allows to vary are not drift, and the security keys are checked separately."],
                    drift, ("environment", "key"), example={"environment": "prod-eu", "key": "database.pool_size"}),
        corpus.Kind("insecure", "which environment violates a security requirement",
                    ["POLICY.md names two security requirements every {service} environment must meet. One environment breaks one of them. Which environment, and which key?",
                     "Check the two security keys from config/POLICY.md across all {service} environments and report the environment and key that violate the policy.",
                     "One {service} environment has a security key set to the forbidden value. Name the environment and the key (section.key)."],
                    ["The two requirements are stated under 'Security requirements' in config/POLICY.md.",
                     "See the 'Security requirements' section of config/POLICY.md for the two keys and their required values.",
                     "config/POLICY.md spells out the required value of each security key."],
                    insecure, ("environment", "key"), example={"environment": "staging", "key": "tls.verify"}),
        corpus.Kind("missing_key", "which environment is missing a key",
                    ["Every {service} environment file should carry the same set of keys. One file is missing one key entirely. Which environment, and which key?",
                     "One of the {service} config files lacks a key that every other environment defines. Find the environment and the missing key.",
                     "Compare the key sets of the {service} environment files and report the environment with a key missing and which key it is (section.key)."],
                    ["A missing key is absent from the file, not set to an empty value.",
                     "The key is simply not present in that environment's file; the others all have it.",
                     "Look for a key that appears in every file but one."],
                    missing, ("environment", "key"), example={"environment": "dr", "key": "cache.max_entries"}),
        corpus.Kind("replicas_of", "how many replicas does {target} run",
                    ["How many replicas does the {service} deployment in the {target} environment run?",
                     "What is service.replicas in the {target} environment of {service}?",
                     "Please read config/{target}.yaml for {service} and give me its replica count."],
                    ["Report the number as written in service.replicas.",
                     "The value is the integer under the service section, key replicas.",
                     "Just the value of service.replicas for that environment."],
                    replicas_of, ("environment", "value"), targets=two_envs, example={"environment": "prod-eu", "value": 6}),
        corpus.Kind("most_replicas", "which environment runs the most replicas",
                    ["Which {service} environment runs the most replicas, and how many?",
                     "Across all {service} environments, find the largest service.replicas value and the environment that has it.",
                     "Name the {service} environment with the highest replica count and give the count."],
                    ["Every environment file sets service.replicas; the largest is unique.",
                     "Compare service.replicas across the files under config/.",
                     "The replica counts are in the service section of each environment file."],
                    most_replicas, ("environment", "value"), example={"environment": "prod-us-east", "value": 12}),
        corpus.Kind("log_level_of", "what log level does {target} use",
                    ["What logging level is configured for {service} in the {target} environment?",
                     "Please tell me logging.level in config/{target}.yaml for {service}.",
                     "Read the {target} configuration of {service} and report its logging level."],
                    ["It is the value of logging.level in that environment's file.",
                     "The key is logging.level; report the value as written.",
                     "Only the logging section matters for this one."],
                    log_level_of, ("environment", "value"), targets=two_envs, example={"environment": "dev", "value": "debug"}),
    )


class ConfigsSpec(corpus.CorpusSpec):
    NAME = "configs"
    FILE = __file__
    TITLE = "Configuration drift audit"
    ROLE = ("You are a platform engineer. One request about a service's configuration is in `task.json`; answer it\n"
            "from the files in `config/` and write the answer to `answer.json`.")
    FILE_LAYOUT = ("`config/<environment>.yaml`: one configuration file per environment of the service, same layout "
                   "in every file; `config/POLICY.md`: which keys must be uniform, which may vary, and the two "
                   "security requirements.")
    KINDS = kinds()
    SCENARIOS = 24
    SCENARIO_PREFIX = "CFG"
    DEFAULT_SEED = 67

    def service_of(self, state):
        return state["service"]

    def scenario_state(self, sid, rng):
        service = common.pick(rng, SERVICES)
        n_env = rng.randrange(6, 10)
        chosen = {"dev", "staging"} | set(rng.sample(["prod-us-east", "prod-us-west", "prod-eu", "prod-apac"], 2))
        rest = [e for e in ENVIRONMENTS if e not in chosen]
        rng.shuffle(rest)
        chosen |= set(rest[:n_env - len(chosen)])
        envs = [e for e in ENVIRONMENTS if e in chosen]
        uniform = {(s, k): common.pick(rng, values) for s, k, values, _ in UNIFORM}
        replicas, levels = {}, {}
        for env in envs:
            if env in ("dev", "test"):
                replicas[env], levels[env] = 1, "debug"
            elif env == "staging":
                replicas[env], levels[env] = 2, "debug"
            elif env == "canary":
                replicas[env], levels[env] = 1, "info"
            elif env == "dr":
                replicas[env], levels[env] = 2, "info"
            else:
                replicas[env], levels[env] = 2 * rng.randrange(2, 7), "info"
        prods = [e for e in envs if e.startswith("prod")]
        top = common.pick(rng, prods)
        replicas[top] = max(replicas.values()) + 2       # the largest count is unique
        roles = rng.sample(envs, 3)
        drift_candidates = [(s, k, v) for s, k, v, _ in UNIFORM if (s, k) not in SECURITY_KEYS and len(v) > 1]
        s, k, values = common.pick(rng, drift_candidates)
        drift_value = common.pick(rng, [v for v in values if v != uniform[(s, k)]])
        insecure_key = common.pick(rng, sorted(SECURITY_KEYS))
        missing_key = common.pick(rng, [(s2, k2) for s2, k2, _, _ in UNIFORM if (s2, k2) != (s, k) and (s2, k2) not in SECURITY_KEYS])
        targets = rng.sample(envs, 2)
        return {"scenario": sid, "service": service, "environments": envs, "uniform": {dotted(*key): value for key, value in uniform.items()},
                "replicas": replicas, "levels": levels, "drift_env": roles[0], "drift_key": [s, k],
                "drift_value": drift_value, "insecure_env": roles[1], "insecure_key": list(insecure_key),
                "missing_env": roles[2], "missing_key": list(missing_key), "targets": targets,
                "db_name": service.split("-")[0], "region_tag": "%02d" % rng.randrange(1, 40)}

    def render_env(self, state, env):
        """The YAML lines of one environment and the 1-based line numbers of its planted facts."""
        lines, marks = [], []
        service = state["service"]
        lines.append("# %s -- %s environment. Generated from the shared template; see POLICY.md before editing." % (service, env))
        lines.append("# Keys marked (uniform) must hold the same value in every environment.")
        lines.append("")
        values = {}
        for s, k, _, comment in UNIFORM:
            values[(s, k)] = (state["uniform"][dotted(s, k)], comment + " (uniform)")
        values[("service", "name")] = (service, "")
        values[("service", "replicas")] = (str(state["replicas"][env]), "may vary per environment")
        values[("database", "host")] = ("db-%s-%s.internal" % (env, state["region_tag"]), "per environment")
        values[("database", "name")] = (state["db_name"], "")
        values[("cache", "endpoint")] = ("redis://cache-%s.internal:6379/0" % env, "per environment")
        values[("tls", "cert_path")] = ("/etc/certs/%s/%s.pem" % (service, env), "per environment")
        values[("logging", "level")] = (state["levels"][env], "debug outside production, info in production")
        order = {"service": ["name", "replicas", "port", "request_timeout_ms", "max_body_kb"],
                 "database": ["host", "port", "name", "pool_size", "statement_timeout_ms", "ssl_mode"],
                 "cache": ["endpoint", "ttl_s", "max_entries"],
                 "auth": ["issuer", "token_ttl_s", "allow_anonymous", "required_scopes"],
                 "tls": ["verify", "min_version", "cert_path"],
                 "logging": ["level", "format", "sample_rate"],
                 "features": ["new_checkout", "async_refunds", "rate_limiting"],
                 "payments": ["provider", "retry_limit", "backoff_ms", "idempotency"]}
        values[("database", "port")] = ("5432", "(uniform)")
        values[("auth", "required_scopes")] = ("[%s.read, %s.write]" % (state["db_name"], state["db_name"]), "(uniform)")
        for section in SECTIONS:
            lines.append("%s:" % section)
            for key in order[section]:
                if env == state["missing_env"] and [section, key] == state["missing_key"]:
                    continue
                value, comment = values[(section, key)]
                if env == state["drift_env"] and [section, key] == state["drift_key"]:
                    value = state["drift_value"]
                    marks.append(len(lines) + 1)
                if env == state["insecure_env"] and [section, key] == state["insecure_key"]:
                    value = SECURITY_KEYS[(section, key)]
                    marks.append(len(lines) + 1)
                if (section, key) == ("service", "replicas") or (section, key) == ("logging", "level"):
                    marks.append(len(lines) + 1)
                lines.append("  %s: %s%s" % (key, value, ("   # " + comment) if comment else ""))
            lines.append("")
        return lines, sorted(set(marks))

    def policy_text(self, state):
        uniform = [dotted(s, k) for s, k, _, _ in UNIFORM]
        lines = ["# Configuration policy for %s" % state["service"], "",
                 "Every environment under `config/` is generated from one template. The keys below must hold",
                 "the same value in every environment; a difference on any of them is drift and is a defect.", ""]
        lines += ["- `%s`" % key for key in uniform + ["database.port", "auth.required_scopes", "service.name"]]
        lines += ["", "These keys may differ between environments and are not drift:", ""]
        lines += ["- `%s`" % dotted(s, k) for s, k in sorted(VARIABLE)]
        lines += ["", "## Security requirements", "",
                  "- `tls.verify` must be `true` in every environment.",
                  "- `auth.allow_anonymous` must be `false` in every environment.", "",
                  "## Completeness", "",
                  "Every environment file carries every key of the template; a missing key falls back to a",
                  "built-in default at runtime, which is why a missing key is a defect even when nothing breaks."]
        return "\n".join(lines) + "\n"

    def scenario_files(self, state):
        files = {"config/POLICY.md": self.policy_text(state)}
        for env in state["environments"]:
            lines, _ = self.render_env(state, env)
            files["config/%s.yaml" % env] = "\n".join(lines) + "\n"
        return files

    def content_truth(self, state, files):
        answer_lines = {}
        for env in state["environments"]:
            _, marks = self.render_env(state, env)
            if marks:
                answer_lines["config/%s.yaml" % env] = marks
        return {"groups": [{"name": "environment-configs", "files": sorted(f for f in files if f.endswith(".yaml"))}],
                "answer_lines": answer_lines}

    def domain_instructions(self):
        return ["## The scenario", "",
                "`config/` holds one YAML file per environment of one service (`dev.yaml`, `staging.yaml`,",
                "`prod-eu.yaml`, ...), all generated from the same template, plus `config/POLICY.md`, which lists the",
                "keys that must be identical in every environment, the keys that may differ, and two security",
                "requirements. Keys are referred to as `section.key`, e.g. `database.pool_size`.", "",
                "## How to decide", "",
                "- Drift: a must-be-uniform key whose value in one environment differs from all the others. Keys the",
                "  policy allows to vary never count, and the two security keys are a separate question.",
                "- Security: `tls.verify` must be `true` and `auth.allow_anonymous` must be `false`; one environment",
                "  violates one of them.",
                "- A missing key is absent from one environment's file and present in every other.",
                "- Values are reported as written in the file (`6`, `debug`, `verify-full`)."]


SPEC = ConfigsSpec()

if __name__ == "__main__":
    sys.exit(corpus.main(SPEC))
