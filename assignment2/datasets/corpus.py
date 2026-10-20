"""Assignment 2 -- corpus.py: the machinery shared by the five corpus datasets.

Concept this file teaches: in the first four datasets the only thing that repeats is
the *task*. In a real queue the repetition is everywhere else too -- ten hosts write
the same log, nine environments carry the same config file, six payment adapters are
one file copy-pasted, every reply quotes the thread, every revision of a policy is
the previous one with three lines changed. An agent that reads all of it pays for the
same text again and again, and then again on every later turn. A corpus dataset is a
set of *scenarios* (one directory of such files each) and a stream of *requests*
about them, so that both layers of reuse can be measured: the request stream reuses
common.py unchanged (duplicates, hard negatives, labels, pairs), and the corpus adds
a second ground truth -- which files are near-duplicates of each other, and which
lines carry the answer -- so a content-level reuse layer can be scored on whether it
folded the right things and whether its folds kept the answer in view.

Design rules this file embodies:
  * Scenarios are data with planted facts. Every scenario is rendered from a hidden
    state (hosts, environments, revisions and the anomalies among them); every answer
    is a function of that state; the files are a view of it. "Same scenario and kind
    => same answer" therefore holds by construction, as in common.py.
  * Near-duplicates are made, not found. A family of files shares one template; the
    copies differ in the slots that honestly differ (names, numbers, a handful of
    lines) and in exactly the lines that carry the planted fact. The generator records
    the family and the planted lines, and measures the Jaccard it produced.
  * One request is one visible record. `scenario`, `kind` and `target` are fields a
    reuse policy can validate on; the prose around them (who asks, how urgently, in
    which words) is cosmetic and is what the duplicate kinds vary.
  * The verifier is generic: it compares the keys of the labelled answer with the
    keys the agent wrote, after the same normalisation for everyone.
"""

import os
import re

from . import common

HISTORY_FIELDS = ("hid", "scenario", "kind", "target", "subject", "body", "answer", "filed")
TASK_FIELDS = ("tid", "seq", "scenario", "kind", "target", "subject", "body", "received")
UNITS = ("opening", "ask", "detail", "closing")
PER_TASK_BUDGET = (12_000, 45_000)       # tokens in one task's working directory (chars / 4)

OPENINGS = ["Hi, {name} from the {team} team here.",
            "Hello -- {name}, {team}.",
            "{name} ({team}) writing with a quick request."]
CLOSINGS = ["Thanks, {name}", "Much appreciated, {name}", "Regards, {name} -- {team}"]
URGENCY = ["before the {when} sync", "by {when}", "when you get a moment", "today if possible"]
WHEN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "end of day", "tomorrow"]
NAMES = ["Priya Nair", "Tomas Vik", "Aisha Bello", "Daniel Ortega", "Mei Lin", "Jonas Berg", "Fatima Zahra",
         "Luca Moretti", "Hannah Cole", "Omar Haddad", "Sofia Rossi", "Kenji Sato", "Grace Okafor", "Ivan Petrov",
         "Nora Lindqvist", "Arjun Mehta"]
TEAMS = ["platform", "SRE", "payments", "security", "compliance", "data", "support", "release", "infra", "QA"]
SYNONYMS = {"quick": ["brief"], "request": ["ask"], "please": ["kindly"], "tell": ["let me know"],
            "find": ["locate"], "check": ["verify"], "exactly": ["precisely"], "report": ["write-up"],
            "needs": ["requires"], "wants": ["would like"], "yesterday": ["the day before"],
            "appreciated": ["appreciated a lot"], "moment": ["minute"], "possible": ["feasible"],
            "name": ["identify"], "differs": ["deviates"], "copy": ["duplicate"], "latest": ["newest"],
            "earliest": ["first"], "whole": ["entire"], "started": ["began"], "rest": ["others"]}


# ---------------------------------------------------------------------------
# small text helpers the generators share
# ---------------------------------------------------------------------------
def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def pad(n, width=2):
    return str(n).zfill(width)


def ts(day, hour, minute, second):
    """An ISO timestamp for `day` (a datetime.date) and a clock time."""
    return "%sT%s:%s:%sZ" % (day.isoformat(), pad(hour), pad(minute), pad(second))


def jitter_lines(rng, lines, rate, pool, protected=()):
    """Replace a share of lines with alternatives from `pool`, never a protected line.

    This is how two files of one family get their honest differences: the same
    skeleton, a few lines of the other host's own business. `rate` is the share of
    lines touched; the result keeps the length.
    """
    out = list(lines)
    candidates = [i for i, line in enumerate(out) if line not in protected]
    rng.shuffle(candidates)
    for i in candidates[:int(round(rate * len(out)))]:
        out[i] = common.pick(rng, pool)
    return out


def norm_answer_value(value):
    """One normalisation for every graded value: strings by alphanumerics, numbers as numbers, lists as sets."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, (list, tuple, set)):
        return tuple(sorted(norm_answer_value(v) for v in value))
    if isinstance(value, dict):
        return tuple(sorted((str(k), norm_answer_value(v)) for k, v in value.items()))
    text = str(value if value is not None else "").strip()
    if re.fullmatch(r"[-+]?\d+(\.\d+)?", text):
        return float(text)
    return common.norm_code(text)


def grade(hidden_dir, tid, answer):
    """{label: (passed, detail)} for a corpus task: every key of the labelled answer must match."""
    labels = common.load_labels(hidden_dir)
    if tid not in labels:
        return {"task known": (False, "unknown task id %s" % tid)}
    expected = labels[tid]["answer"]
    checks = {"answer is object": common.check_object(answer)}
    for key in expected:
        given = answer.get(key) if isinstance(answer, dict) else None
        ok = isinstance(answer, dict) and key in answer and norm_answer_value(given) == norm_answer_value(expected[key])
        checks["%s correct" % key] = (ok, "got %r, expected %r" % (given, expected[key]))
    return checks


# ---------------------------------------------------------------------------
# request kinds
# ---------------------------------------------------------------------------
class Kind:
    """One question type: how it is asked, who it can be about, and what the answer is.

    `ask` and `detail` are three template variants each (the paraphrase axis); they may
    use {target}, {service}, {scenario} and the cosmetic slots. `targets(state)` lists
    the values the question can be about ([None] when there is none); `answer(state,
    target)` is the labelled answer; `keys` names its fields for INSTRUCTIONS.md.
    """

    def __init__(self, name, title, ask, detail, answer, keys, targets=None, example=None):
        self.name, self.title, self.ask, self.detail = name, title, ask, detail
        self.answer, self.keys = answer, keys
        self.targets = targets or (lambda state: [None])
        self.example = example or {}


class CorpusSpec(common.Spec):
    """A dataset of scenarios plus a request stream. Subclasses supply the domain.

    Methods a subclass writes
      scenario_state(sid, rng)      -> the hidden state of one scenario (hosts, anomalies, ...)
      scenario_files(state)         -> {relative path: text}, the files the agent sees
      content_truth(state, files)   -> {"groups": [{"name", "files": [...]}], "answer_lines": {path: [n, ...]}}
      service_of(state)             -> the one-word name the templates call {service}
      domain_instructions()         -> the dataset-specific part of INSTRUCTIONS.md
    Class attributes: NAME, FILE, KINDS, SCENARIOS, SCENARIO_PREFIX, DEFAULT_SEED.
    """

    HISTORY_FIELDS = HISTORY_FIELDS
    TASK_FIELDS = TASK_FIELDS
    DATE_FIELD = "filed"
    TASK_DATE_FIELD = "received"
    UNITS = UNITS
    VARIANTS = 3
    SYNONYMS = SYNONYMS
    MAX_HISTORY = 70
    MAX_INCOMING = 45
    DEFAULT_HISTORY = 60
    DEFAULT_INCOMING = 40
    DEFAULT_DUP_RATE = 0.40
    TEXT_FOR_SIMILARITY = "subject + body"
    KINDS = ()
    SCENARIOS = 24
    SCENARIO_PREFIX = "SC"
    FILE_LAYOUT = ""            # one line for INSTRUCTIONS.md: what the scenario directory holds

    def __init__(self):
        self._states = {}
        self._files = {}
        self.kinds = {kind.name: kind for kind in self.KINDS}
        self.scenario_ids = ["%s-%04d" % (self.SCENARIO_PREFIX, 1000 + 37 * k % 977 + k) for k in range(self.SCENARIOS)]
        pool = []
        for sid in self.scenario_ids:
            state = self.state_of(sid)
            for kind in self.KINDS:
                for target in kind.targets(state):
                    pool.append({"scenario": sid, "kind": kind.name, "target": target})
        common.sub_rng(self.NAME + "-pool").shuffle(pool)
        self._pool = pool

    # -- scenarios ---------------------------------------------------------------
    def state_of(self, sid):
        if sid not in self._states:
            state = self.scenario_state(sid, common.sub_rng(self.NAME + "-scenario", sid))
            state["scenario"] = sid
            self._states[sid] = state
        return self._states[sid]

    def files_of(self, sid):
        if sid not in self._files:
            self._files[sid] = self.scenario_files(self.state_of(sid))
        return self._files[sid]

    def corpus_files(self):
        """Every scenario's files under env/scenarios/<sid>/ (what common.write writes)."""
        out = {}
        for sid in self.scenario_ids:
            for rel, text in self.files_of(sid).items():
                out["scenarios/%s/%s" % (sid, rel)] = text
        return out

    def truth_of(self, sid):
        truth = self.content_truth(self.state_of(sid), self.files_of(sid))
        truth["jaccard"] = self.group_jaccard(sid, truth["groups"])
        return truth

    def group_jaccard(self, sid, groups):
        """Within-group Jaccard (min, median, max over pairs) and the largest cross-group value."""
        files = self.files_of(sid)
        within = []
        for group in groups:
            members = group["files"]
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    within.append(common.jaccard_content(files[members[i]], files[members[j]]))
        cross = 0.0
        reps = [group["files"][0] for group in groups]
        others = [path for path in files if not any(path in g["files"] for g in groups)]
        for i in range(len(reps)):
            for j in range(i + 1, len(reps)):
                cross = max(cross, common.jaccard_content(files[reps[i]], files[reps[j]]))
            for path in others:
                cross = max(cross, common.jaccard_content(files[reps[i]], files[path]))
        within.sort()
        stats = {"n_pairs": len(within), "within_min": round(within[0], 3) if within else None,
                 "within_p50": round(within[len(within) // 2], 3) if within else None,
                 "within_max": round(within[-1], 3) if within else None, "cross_max": round(cross, 3)}
        return stats

    def hidden_extra(self, materialised):
        return {"content.json": {sid: self.truth_of(sid) for sid in self.scenario_ids}}

    def manifest_extra(self, dataset, materialised, env):
        sizes = [sum(common.estimate_tokens(t) for t in self.files_of(sid).values()) for sid in self.scenario_ids]
        counts = [len(self.files_of(sid)) for sid in self.scenario_ids]
        truths = [self.truth_of(sid) for sid in self.scenario_ids]
        within = [t["jaccard"]["within_p50"] for t in truths if t["jaccard"]["within_p50"] is not None]
        return {"content": {
            "scenarios": len(self.scenario_ids), "files_per_scenario": [min(counts), max(counts)],
            "tokens_per_scenario": {"min": min(sizes), "mean": sum(sizes) // len(sizes), "max": max(sizes)},
            "within_group_jaccard_p50": {"min": min(within), "max": max(within)} if within else None,
            "cross_group_jaccard_max": max(t["jaccard"]["cross_max"] for t in truths),
            "groups_per_scenario": [min(len(t["groups"]) for t in truths), max(len(t["groups"]) for t in truths)],
            "normalisation": "lower-case alphanumeric tokens, digit runs masked to 0, word 3-shingles"}}

    def budget_for(self, groups, env_dir):
        n_tasks = max(1, len(os.listdir(os.path.join(env_dir, "incoming"))))
        sizes = [sum(common.estimate_tokens(t) for t in self.files_of(sid).values()) for sid in self.scenario_ids]
        per_task = groups["instructions"] + groups["history"] + groups["incoming"] // n_tasks + sum(sizes) // len(sizes)
        return list(PER_TASK_BUDGET), per_task

    # -- the Spec contract ---------------------------------------------------------
    def pool_size(self):
        return len(self._pool)

    def canonical_at(self, k):
        return dict(self._pool[k])

    def answer(self, canonical):
        kind = self.kinds[canonical["kind"]]
        return kind.answer(self.state_of(canonical["scenario"]), canonical["target"])

    def flip(self, rng, canonical):
        """Scenario flips first (the request reads the same, the directory differs), then kind, then target."""
        kind = self.kinds[canonical["kind"]]
        scenarios = []
        for sid in self.scenario_ids:
            if sid == canonical["scenario"]:
                continue
            targets = kind.targets(self.state_of(sid))
            target = canonical["target"] if canonical["target"] in targets else targets[0]
            scenarios.append(dict(canonical, scenario=sid, target=target))
        rng.shuffle(scenarios)
        state = self.state_of(canonical["scenario"])
        kinds = [dict(canonical, kind=k.name, target=k.targets(state)[0]) for k in self.KINDS if k.name != kind.name]
        rng.shuffle(kinds)
        targets = [dict(canonical, target=t) for t in kind.targets(state) if t != canonical["target"]]
        rng.shuffle(targets)
        return targets + scenarios + kinds

    def history_answer_fields(self, answer):
        return {"answer": answer}

    def cosmetic(self, rng):
        return {"name": common.pick(rng, NAMES), "team": common.pick(rng, TEAMS),
                "when": common.pick(rng, WHEN), "urgency": rng.randrange(len(URGENCY)),
                "ref": rng.randrange(100, 999)}

    def slots(self, state, canonical, cosmetic):
        slots = {"service": self.service_of(state), "scenario": canonical["scenario"],
                 "target": canonical["target"] or "", "name": cosmetic["name"], "team": cosmetic["team"],
                 "when": cosmetic["when"], "ref": cosmetic["ref"]}
        slots["urgency"] = URGENCY[cosmetic["urgency"]].format(**slots)
        return slots

    def compose(self, state):
        c, v, cos = state["canonical"], state["variants"], state["cosmetic"]
        kind = self.kinds[c["kind"]]
        scenario = self.state_of(c["scenario"])
        slots = self.slots(scenario, c, cos)
        opening = OPENINGS[v["opening"]].format(**slots)
        ask = kind.ask[v["ask"]].format(**slots)
        detail = kind.detail[v["detail"]].format(**slots)
        closing = CLOSINGS[v["closing"]].format(**slots)
        subject = "%s: %s" % (c["scenario"], kind.title.format(**slots))
        fields = {"scenario": c["scenario"], "kind": c["kind"], "target": c["target"], "subject": subject}
        return {"fields": fields, "title": "", "sections": [("", opening + " " + ask), ("", detail), ("", closing)]}

    def recase_fields(self, fields, style):
        if style["fields"] == "lower":
            fields["scenario"] = fields["scenario"].lower()
            fields["kind"] = fields["kind"].lower()
        elif style["fields"] == "compact":
            fields["scenario"] = fields["scenario"].replace("-", "")
        return fields

    def protected(self, state):
        c = state["canonical"]
        words = [c["scenario"], self.service_of(self.state_of(c["scenario"])), c["kind"]]
        if c["target"]:
            words += str(c["target"]).split()
        return words + list(self.kinds[c["kind"]].keys)

    def validation_tuple(self, record):
        return (common.norm_code(record["scenario"]), common.norm_text(record["kind"]),
                common.norm_code(record.get("target") or ""))

    def text_for_similarity(self, record):
        return record["subject"] + "\n" + record["body"]

    def instructions(self):
        lines = ["# %s" % self.TITLE, "",
                 self.ROLE, "",
                 "## Files in this directory", "",
                 "- `INSTRUCTIONS.md`: this file.",
                 "- `task.json`: the request to answer: `tid`, `seq`, `scenario`, `kind`, `target`, `subject`, `body`, `received`.",
                 "- %s" % self.FILE_LAYOUT,
                 "- `history.jsonl`: one JSON object per line, every one a closed, verified request: fields `hid`,",
                 "  `scenario`, `kind`, `target`, `subject`, `body`, `answer` (the verified answer object), `filed`.", "",
                 "`history.jsonl` contains verified answers. If `task.json` asks the same question about the same",
                 "scenario as a history record (the same `scenario`, `kind` and `target`, not merely a similar",
                 "request), you may reuse that record's `answer`. A different scenario with the same wording is a",
                 "different request with a different answer.", "",
                 "Tool results may be abbreviated: when a file repeats one you have already read, the tool shows",
                 "the repeated part as a reference to the earlier file plus the lines that differ, marked `[reuse]`.",
                 "Treat such a result as the full file with those differences.", ""]
        lines += self.domain_instructions()
        lines += ["", "## Request kinds and the answer each expects", "",
                  "`kind` in `task.json` says which question is being asked; `target` names what it is about",
                  "when the kind takes one (otherwise it is `null`). Write exactly these keys:", ""]
        for kind in self.KINDS:
            title = kind.title.format_map(_Placeholders())
            lines.append("- `%s`: %s. Answer keys: %s. Example: `%s`" % (
                kind.name, title, ", ".join("`%s`" % k for k in kind.keys), _json_line(kind.example)))
        lines += ["", "## Validation (when is a history record the same request?)", "",
                  "Only when `scenario`, `kind` and `target` all match after normalisation (case does not matter,",
                  "`%s-1234` and `%s1234` are one scenario). Matching wording is not enough." % (
                      self.SCENARIO_PREFIX, self.SCENARIO_PREFIX), "",
                  "## Output", "",
                  "Write `answer.json` in this directory with the keys listed for the request's kind. Strings are",
                  "compared case-insensitively on their letters and digits; numbers as numbers; lists as sets.",
                  "Extra keys are ignored.", "",
                  "## Rules", "",
                  "- Do not modify the scenario files, `history.jsonl` or `task.json`; write nothing except `answer.json`.",
                  "- Only `answer.json` is graded. Your final message is not."]
        return "\n".join(lines) + "\n"


class _Placeholders(dict):
    """`{target}` -> `<target>` and so on, for the kind titles printed in INSTRUCTIONS.md."""

    def __missing__(self, key):
        return "<%s>" % key.replace("_words", "")


def _json_line(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)


def main(spec, argv=None):
    """The generator front end, with the content statistics printed after the stream table."""
    code = common.main(spec, argv)
    sizes = [sum(common.estimate_tokens(t) for t in spec.files_of(sid).values()) for sid in spec.scenario_ids]
    truths = [spec.truth_of(sid) for sid in spec.scenario_ids]
    within = sorted(t["jaccard"]["within_p50"] for t in truths if t["jaccard"]["within_p50"] is not None)
    print("corpus: %d scenarios, %d-%d files each, %d-%d tokens each; within-group Jaccard p50 %.2f-%.2f, "
          "cross-group max %.2f" % (len(spec.scenario_ids), min(len(spec.files_of(s)) for s in spec.scenario_ids),
                                    max(len(spec.files_of(s)) for s in spec.scenario_ids), min(sizes), max(sizes),
                                    within[0] if within else 0, within[-1] if within else 0,
                                    max(t["jaccard"]["cross_max"] for t in truths)))
    return code
