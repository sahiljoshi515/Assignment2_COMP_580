"""Assignment 2 -- revisions: ten versions of one policy, and nobody kept the changelog.

Concept this file teaches: a document under revision is a chain of near-duplicates. Each
version is the previous one with a number changed, a clause added or struck, a role
renamed, two sections swapped. The questions people ask of such a chain -- when did the
retention period become ninety days, which version dropped requirement R4, what does the
current version actually say -- are questions about the differences, and reading every
version in full to answer them is reading one document ten times.

Design rules this file embodies:
  * Edits are tracked as they are applied, so every answer (the revision that set a value,
    the count of changes, the version that removed a clause) is read off the edit log and
    checked against the rendered text.
  * Requirement ids are stable: R4 keeps its number when R3 is struck, as real policies
    do, so "which requirement" has one answer.
  * Edits are small and realistic -- one to three per revision -- which is what makes the
    exact diff between consecutive versions short and the fold worth having.

Run from the repo root:  /usr/local/bin/python3.13 assignment2/datasets/revisions/generate.py
"""

import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common, corpus  # noqa: E402

POLICIES = ["Data Retention Policy", "Remote Work Policy", "Access Control Standard", "Incident Response Standard",
            "Vendor Security Policy", "Backup and Recovery Standard", "Change Management Policy", "Acceptable Use Policy"]
OWNERS = ["Head of Information Security", "Director of IT Operations", "Chief Compliance Officer",
          "Head of Platform Engineering", "Data Protection Officer", "VP of Engineering"]
# parameter key -> (words used in the request text, sentence template with {v}, candidate values, unit)
PARAMETERS = {
    "retention_days": ("the retention period", "Records covered by this policy are retained for {v} days from the date of their creation and then deleted.", [30, 60, 90, 180, 365], "days"),
    "review_months": ("the review cadence", "This document is reviewed every {v} months and after any incident that invokes it.", [6, 12, 24], "months"),
    "session_hours": ("the maximum session length", "Interactive sessions expire after {v} hours and require re-authentication.", [4, 8, 12, 24], "hours"),
    "password_length": ("the minimum password length", "Passwords are at least {v} characters long and are checked against a list of known compromised passwords.", [10, 12, 14, 16], "characters"),
    "backup_hours": ("the backup interval", "Backups of in-scope systems run at least every {v} hours and are tested quarterly.", [6, 12, 24], "hours"),
    "approval_days": ("the approval deadline", "Requests under this policy are approved or declined within {v} working days of submission.", [2, 3, 5, 10], "working days"),
    "notice_days": ("the notification deadline", "Affected parties are notified within {v} days of a confirmed event.", [2, 3, 7, 30], "days"),
}
STATIC_REQUIREMENTS = [
    "All access to in-scope systems is logged, and the logs are protected from modification.",
    "Exceptions to this policy are approved in writing by the document owner and recorded in the exception register.",
    "Third parties handling in-scope data are bound by a written agreement that imposes equivalent requirements.",
    "Staff complete the related training within thirty days of joining and annually thereafter.",
    "Encryption in transit uses current, non-deprecated protocol versions only.",
    "Shared accounts are prohibited; every action is attributable to a named individual.",
    "Changes to in-scope systems follow the change process and are reviewed by a second person.",
    "Devices that store in-scope data are encrypted at rest with a managed key.",
    "Monitoring alerts are triaged within one business hour during working hours.",
    "Test and development environments never hold production data unless it has been anonymised.",
]
DEFINITIONS = ["In-scope systems: every system listed in the asset register with this policy as its control set.",
               "Owner: the role accountable for this document and for approving exceptions to it.",
               "Confirmed event: an event that the response team has classified, as opposed to a report.",
               "Working day: Monday to Friday excluding public holidays at the registered office."]
REWORDS = [("must", "shall"), ("staff", "employees"), ("approved", "authorised"), ("document", "policy"),
           ("every", "each"), ("records", "data")]


def kinds():
    def introduced_in(state, target):
        return {"revision": state["param_history"][target][-1][0]}

    def current_value(state, target):
        return {"value": state["param_history"][target][-1][1]}

    def removed_requirement(state, target):
        return {"revision": state["removed"][0], "requirement": state["removed"][1]}

    def added_requirement(state, target):
        return {"revision": state["added"][0], "requirement": state["added"][1]}

    def owner_change(state, target):
        return {"revision": state["owner_change"][0], "owner": state["owner_change"][1]}

    def changes_count(state, target):
        return {"count": len(state["param_history"][target]) - 1}

    def params(state):
        return state["asked_params"]

    return (
        corpus.Kind("introduced_in", "which revision set {target_words} to its current value",
                    ["Looking at the revisions of the {service}, in which revision was {target_words} first set to the value the latest revision has?",
                     "Which version of the {service} introduced the current value of {target_words}? I need the revision label, e.g. v04.",
                     "When did {target_words} in the {service} become what it is today? Give the revision in which that value first appears."],
                    ["The revisions are under policy/, one file per version; no changelog was kept.",
                     "All versions are in policy/ as v01.md, v02.md and so on.",
                     "Compare the versions in policy/; report the revision label as in the file name."],
                    introduced_in, ("revision",), targets=params, example={"revision": "v06"}),
        corpus.Kind("current_value", "current value of {target_words}",
                    ["What is {target_words} in the latest revision of the {service}?",
                     "According to the newest version of the {service} under policy/, what value does {target_words} have?",
                     "Please read the latest {service} revision and report {target_words} as a number."],
                    ["Report the number only, without the unit.",
                     "The latest revision is the highest-numbered file in policy/.",
                     "Just the numeric value as written in the current version."],
                    current_value, ("value",), targets=params, example={"value": 90}),
        corpus.Kind("removed_requirement", "which revision struck a requirement",
                    ["One requirement of the {service} was removed in a later revision. Which revision removed it, and which requirement id was it?",
                     "Find the revision of the {service} in which a numbered requirement disappears, and name the requirement (R-number) that was struck.",
                     "Which requirement was dropped from the {service} and in which revision did it go?"],
                    ["Requirement ids are stable across revisions: R4 keeps its number when R3 is removed.",
                     "Requirements are numbered R1, R2, ...; the numbering does not shift when one is removed.",
                     "Report the requirement by its id, e.g. R3, and the revision label, e.g. v05."],
                    removed_requirement, ("revision", "requirement"), example={"revision": "v05", "requirement": "R3"}),
        corpus.Kind("added_requirement", "which revision added the newest requirement",
                    ["Which revision of the {service} added the most recently introduced requirement, and what is that requirement's id?",
                     "Find the last requirement added to the {service} across its revisions: the revision that introduced it and its R-number.",
                     "In which revision did the newest numbered requirement of the {service} first appear, and which id does it carry?"],
                    ["A requirement is added at the end of the Requirements section with the next free number.",
                     "New requirements get the next number after the highest existing one.",
                     "Report the revision label (v07) and the requirement id (R9)."],
                    added_requirement, ("revision", "requirement"), example={"revision": "v07", "requirement": "R9"}),
        corpus.Kind("owner_change", "which revision changed the owner",
                    ["The owner role named in the {service} changed once across its revisions. In which revision, and to which role?",
                     "Which revision of the {service} reassigned document ownership, and what is the new owner role?",
                     "Find the revision in which the {service} names a different owner than the revision before it, and give the new owner."],
                    ["The owner is named in the Review and ownership section of every revision.",
                     "Compare the owner line across the versions under policy/.",
                     "Report the role exactly as written in the document."],
                    owner_change, ("revision", "owner"), example={"revision": "v04", "owner": "Data Protection Officer"}),
        corpus.Kind("changes_count", "how many times {target_words} changed",
                    ["How many times did {target_words} change across the revisions of the {service}?",
                     "Count the revisions of the {service} in which {target_words} takes a value different from the previous revision.",
                     "Across all versions of the {service}, how often was {target_words} changed? A change is a revision whose value differs from the one before."],
                    ["The first revision setting the value is not a change; count only later revisions where the value differs from the previous one.",
                     "v01 establishes the value; count the later revisions that alter it.",
                     "Report an integer; zero if it never changed after v01."],
                    changes_count, ("count",), targets=params, example={"count": 2}),
    )


class RevisionsSpec(corpus.CorpusSpec):
    NAME = "revisions"
    FILE = __file__
    TITLE = "Questions about the revisions of a policy"
    ROLE = ("You maintain the policy library. One question about one policy's history is in `task.json`; answer it\n"
            "from the revisions in `policy/` and write the answer to `answer.json`.")
    FILE_LAYOUT = ("`policy/vNN.md`: every revision of one policy as a Markdown file, v01 the oldest; the same sections "
                   "in every revision, no changelog.")
    KINDS = kinds()
    SCENARIOS = 24
    SCENARIO_PREFIX = "POL"
    DEFAULT_SEED = 83

    def service_of(self, state):
        return state["policy"]

    def slots(self, state, canonical, cosmetic):
        slots = super().slots(state, canonical, cosmetic)
        target = canonical["target"]
        slots["target_words"] = PARAMETERS[target][0] if target in PARAMETERS else ""
        return slots

    def scenario_state(self, sid, rng):
        policy = common.pick(rng, POLICIES)
        owners = rng.sample(OWNERS, 2)
        params = rng.sample(sorted(PARAMETERS), 4)
        values = {p: common.pick(rng, PARAMETERS[p][2]) for p in params}
        statics = rng.sample(STATIC_REQUIREMENTS, 4)
        n_rev = rng.randrange(7, 11)
        # Requirements: parameter sentences and static sentences interleaved, ids R1..
        order = [("param", p) for p in params] + [("static", s) for s in statics]
        rng.shuffle(order)
        requirements = [{"id": "R%d" % (i + 1), "kind": k, "ref": v, "present": True} for i, (k, v) in enumerate(order)]
        param_history = {p: [("v01", values[p])] for p in params}
        edits_by_rev, owner_by_rev, order_swapped = {}, {"v01": owners[0]}, {}
        removed = added = owner_change = None
        unused_static = [s for s in STATIC_REQUIREMENTS if s not in statics]
        rewords = {}
        plan = list(range(2, n_rev + 1))
        remove_rev, add_rev, owner_rev = rng.sample(plan, 3)
        for r in plan:
            label = "v%02d" % r
            edits = []
            n_param_edits = rng.randrange(0, 3)
            for p in rng.sample(params, n_param_edits):
                options = [v for v in PARAMETERS[p][2] if v != values[p]]
                values[p] = common.pick(rng, options)
                param_history[p].append((label, values[p]))
                edits.append(("param", p))
            if r == remove_rev:
                candidates = [q for q in requirements if q["kind"] == "static" and q["present"]]
                victim = common.pick(rng, candidates)
                victim["present"] = False
                removed = (label, victim["id"])
                edits.append(("remove", victim["id"]))
            if r == add_rev:
                text = unused_static.pop(rng.randrange(len(unused_static)))
                new = {"id": "R%d" % (len(requirements) + 1), "kind": "static", "ref": text, "present": True}
                requirements.append(new)
                added = (label, new["id"])
                edits.append(("add", new["id"]))
            if r == owner_rev:
                owner_change = (label, owners[1])
                edits.append(("owner", owners[1]))
            if rng.random() < 0.5:
                rewords[label] = common.pick(rng, REWORDS)
                edits.append(("reword", rewords[label]))
            if not edits:
                rewords[label] = common.pick(rng, REWORDS)
                edits.append(("reword", rewords[label]))
            edits_by_rev[label] = edits
        start = datetime.date(2023, 1, 9) + datetime.timedelta(days=rng.randrange(0, 200))
        dates = {}
        cursor = start
        for r in range(1, n_rev + 1):
            dates["v%02d" % r] = cursor.isoformat()
            cursor += datetime.timedelta(days=rng.randrange(40, 130))
        asked = rng.sample(params, 3)
        return {"scenario": sid, "policy": policy, "owners": owners, "params": params, "requirements": requirements,
                "param_history": param_history, "edits": edits_by_rev, "removed": removed, "added": added,
                "owner_change": owner_change, "n_rev": n_rev, "dates": dates, "rewords": rewords,
                "asked_params": asked, "scope": common.pick(rng, ["all production systems and the data they process",
                                                                   "every employee, contractor and system of the company",
                                                                   "the systems and suppliers listed in the asset register"])}

    def render_revision(self, state, r):
        """The text of revision r (1-based) and the 1-based line numbers of its parameter and owner lines."""
        label = "v%02d" % r
        # replay the state up to r
        values = {p: state["param_history"][p][0][1] for p in state["params"]}
        present = {q["id"]: True for q in state["requirements"] if not (state["added"] and q["id"] == state["added"][1])}
        owner = state["owners"][0]
        rewords = []
        for k in range(2, r + 1):
            lab = "v%02d" % k
            for kind, ref in state["edits"][lab]:
                if kind == "param":
                    values[ref] = next(v for (rl, v) in state["param_history"][ref] if rl == lab)
                elif kind == "remove":
                    present[ref] = False
                elif kind == "add":
                    present[ref] = True
                elif kind == "owner":
                    owner = ref
                elif kind == "reword":
                    rewords.append(ref)
        lines = ["# %s" % state["policy"], "",
                 "Revision: %s. Effective: %s. Owner: %s." % (label, state["dates"][label], owner), "",
                 "## 1. Purpose", "",
                 "This document sets the minimum requirements for %s. It exists so that every team applies the same"
                 % state["policy"].lower().replace(" policy", "").replace(" standard", ""),
                 "rules the same way, and so that an auditor can check that they do.", "",
                 "## 2. Scope", "",
                 "This document applies to %s. Where a contract or a law imposes a stricter" % state["scope"],
                 "requirement, the stricter requirement applies.", "",
                 "## 3. Definitions", ""]
        lines += ["- %s" % d for d in DEFINITIONS]
        lines += ["", "## 4. Requirements", ""]
        marks = []
        for q in state["requirements"]:
            if not present.get(q["id"], False):
                continue
            if q["kind"] == "param":
                text = PARAMETERS[q["ref"]][1].format(v=values[q["ref"]])
                marks.append(len(lines) + 1)
            else:
                text = q["ref"]
            lines.append("- **%s.** %s" % (q["id"], text))
        lines += ["", "## 5. Exceptions", "",
                  "Exceptions are granted only where a requirement cannot be met for technical or legal reasons, are",
                  "time-limited, and are reviewed at every scheduled review of this document.", "",
                  "## 6. Review and ownership", "",
                  "The owner of this document is the %s, who approves exceptions and signs off every revision." % owner,
                  "Material changes are communicated to all affected teams before they take effect."]
        marks.append(len(lines) - 1)
        text = "\n".join(lines) + "\n"
        for old, new in rewords:
            text = text.replace(" %s " % old, " %s " % new)
        return text, marks

    def scenario_files(self, state):
        files = {}
        for r in range(1, state["n_rev"] + 1):
            text, _ = self.render_revision(state, r)
            files["policy/v%02d.md" % r] = text
        return files

    def content_truth(self, state, files):
        answer_lines = {}
        for r in range(1, state["n_rev"] + 1):
            _, marks = self.render_revision(state, r)
            answer_lines["policy/v%02d.md" % r] = marks
        return {"groups": [{"name": "policy-revisions", "files": sorted(files)}], "answer_lines": answer_lines}

    def domain_instructions(self):
        return ["## The scenario", "",
                "`policy/` holds every revision of one policy document as Markdown: `v01.md` is the oldest, the",
                "highest number is the current version. Each revision has the same sections (Purpose, Scope,",
                "Definitions, Requirements, Exceptions, Review and ownership). The Requirements section is a list of",
                "numbered items `R1`, `R2`, ...; ids are stable, so a struck requirement leaves a gap and a new one",
                "takes the next free number. The header line of each revision names its label, effective date and",
                "owner. No changelog exists; the history is only in the differences between revisions.", "",
                "## How to decide", "",
                "- A parameter (a retention period, a cadence, a limit) is the number inside one requirement's",
                "  sentence; its current value is the one in the latest revision; it was 'introduced' in the earliest",
                "  revision from which that value persists to the latest one; a 'change' is a revision whose value",
                "  differs from the revision before it.",
                "- Revisions are reported by their label as in the file name (`v06`), requirements by id (`R3`),",
                "  owners exactly as written."]


SPEC = RevisionsSpec()

if __name__ == "__main__":
    sys.exit(corpus.main(SPEC))
