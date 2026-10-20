"""Assignment 2 -- docs: internal memos filed under eight document categories.

Concept this file teaches: a label can be a *pair* of facts, and reusing it needs both.
A memo's category is its family (told by the identifier in the title: CHG, INC, POL,
REL) crossed with one status word that appears in two sentences of the body. The same
identifier walks through several statuses over its life -- the request memo and the
approval memo of one change are two documents with two categories -- and the same
status is shared by hundreds of unrelated memos. So `duplicate_of` is sound only when
the identifier AND the status class both match; either alone reuses a wrong label. The
hard negative here is the cruellest case for text similarity: the twin differs in one
word in each of two sentences and sits above 0.85 Jaccard, where no threshold can
separate it. Only the published decision procedure does.

Design rules this file embodies:
  * The status vocabulary is exact and exclusive. Stems are never negated ("not
    approved" never occurs), every template, detail bullet, name and synonym is free of
    every other class's stem, and the generator asserts on every rendered record that
    title + body carry the stems of exactly the class its category names.
  * The canonical pool is lazy: canonical_at(k) derives family, system, status and detail
    bullets from k, and the identifier number from a per-family seeded permutation, so an
    identifier is unique within its family and (identifier, status class) is a key.
  * Release notes are the distractor family: one category, no status word, no flips.
  * Everything above is a Spec for common.py; the stream, the transforms, the labels
    and the diagnostics are shared with the other three datasets.

Run from the repo root:  /usr/local/bin/python3.13 assignment2/datasets/docs/generate.py
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common  # noqa: E402

IDENT_PATTERN = r"\b(CHG|INC|POL)-\d{3,4}\b|\bREL-\d+\.\d+\b"
IDENT_RE = re.compile(IDENT_PATTERN, re.IGNORECASE)

# status class -> stems, scanned in this order; a stem is a substring of the normalised text
STEM_GROUPS = [
    ("approved", ("approv", "authoris")),
    ("rejected", ("reject", "declin")),
    ("request", ("request", "pending")),
    ("resolved", ("resolv", "closed")),
    ("open", ("ongoing", "under investigation")),
    ("final", ("effective", "in force")),
    ("draft", ("draft", "for comment")),
]

# one entry per family: identifier prefix, the categories and status classes by status index,
# the phrases a template may put in its {status} slot (both belong to the class), the headers
FAMILIES = [
    {"prefix": "CHG", "noun": "change memo",
     "categories": ("change-request", "change-approved", "change-rejected"),
     "classes": ("request", "approved", "rejected"),
     "phrases": (("pending", "an open request"), ("approved", "authorised"), ("rejected", "declined")),
     "headers": ("Summary", "Details", "Decision")},
    {"prefix": "INC", "noun": "incident report",
     "categories": ("incident-open", "incident-resolved"),
     "classes": ("open", "resolved"),
     "phrases": (("ongoing", "under investigation"), ("resolved", "closed")),
     "headers": ("Impact", "Timeline", "Status")},
    {"prefix": "POL", "noun": "policy",
     "categories": ("policy-draft", "policy-final"),
     "classes": ("draft", "final"),
     "phrases": (("in draft", "out for comment"), ("in force", "effective")),
     "headers": ("Scope", "Requirements", "Status")},
    {"prefix": "REL", "noun": "release notes",
     "categories": ("release-notes",),
     "classes": ("none",),
     "phrases": ((),),
     "headers": ("Highlights", "Fixes", "Upgrade notes")},
]
CATEGORIES = [c for fam in FAMILIES for c in fam["categories"]]
CATEGORY_INDEX = {c: (f, s) for f, fam in enumerate(FAMILIES) for s, c in enumerate(fam["categories"])}
VOCABULARY = {   # published status vocabulary per class, as the instructions print it
    "request": "request, pending", "approved": "approved, authorised", "rejected": "rejected, declined",
    "open": "ongoing, under investigation", "resolved": "resolved, closed",
    "draft": "draft, for comment", "final": "effective, in force", "none": "(none)"}
DEFINITIONS = {
    "change-request": "a change memo still waiting for the board's decision",
    "change-approved": "a change memo the board has accepted",
    "change-rejected": "a change memo the board has turned down",
    "incident-open": "an incident report on a fault that is still being worked",
    "incident-resolved": "an incident report on a fault that is over",
    "policy-draft": "a policy that is not yet binding",
    "policy-final": "a policy that is binding",
    "release-notes": "release notes for a software release; no status word, one category"}

# the pool: family by position in a fixed cycle, identifier numbers from per-family permutations
POOL_SIZE = 3000
FAMILY_CYCLE = (0, 1, 2, 0, 1, 2, 0, 1, 2, 3)     # change, incident, policy 30 % each; release notes 10 %
NUMBER_RANGES = (range(1000, 10000), range(1000, 10000), range(100, 1000), range(10, 310))
# REL numbers n encode a version: major n // 10 (1..30), minor n % 10

SYSTEMS = ["Payroll Gateway", "Invoice Router", "Ledger Core", "Identity Hub", "Fleet Tracker",
           "Warehouse Console", "Order Pipeline", "Shipment Planner", "Vendor Portal", "Expense Desk",
           "Data Lake Ingest", "Reporting Mart", "Message Broker", "Edge Proxy Layer", "Backup Vault",
           "Device Registry", "Support Console", "Pricing Engine", "Contract Archive", "Timesheet Service"]

# DETAILS[family]: the bullet pool; a canonical names three of them
DETAILS = [
    ["Rotate the database credentials used by the nightly batch jobs",
     "Raise the connection pool ceiling from 50 to 120 per node",
     "Move the nightly export to the new object store bucket",
     "Enable TLS 1.3 on the internal load balancer listeners",
     "Retire the legacy SOAP endpoint once the cut-over is complete",
     "Add a read replica in the secondary region for reporting",
     "Upgrade the message broker to the current long-term release",
     "Replace the hand-maintained cron schedule with the workflow engine",
     "Split the shared config file into one file per environment",
     "Introduce rate limiting on the public API gateway routes",
     "Archive records older than seven years to cold storage",
     "Switch alert delivery from email to the paging service"],
    ["Monitoring raised a latency alert for the primary cluster",
     "The on-call engineer confirmed failed health checks on two nodes",
     "Traffic was drained from the affected pool to the standby",
     "A configuration push was identified as the likely trigger",
     "The previous configuration was redeployed to the whole pool",
     "Queue depth was sampled every five minutes and charted",
     "Customers were notified through the public status page",
     "Failover to the standby database instance was started",
     "Error rates were compared against the weekly baseline",
     "A disk on the storage node reported write failures",
     "Certificates on the edge proxies were renewed by hand",
     "The vendor was engaged through the premium support line"],
    ["Store secrets only in the central vault, never in source control",
     "Review access lists for every production system each quarter",
     "Encrypt laptops and removable media with the standard tooling",
     "Report a suspected security incident within one hour of noticing it",
     "Keep production data out of test and development environments",
     "Use the single sign-on portal for all internal tools",
     "Retain audit logs for at least thirteen months",
     "Complete the annual security training before the published deadline",
     "Tag every cloud resource with an owner and a cost centre",
     "Patch critical vulnerabilities within fourteen days of publication",
     "Document every manual change in the shared change log",
     "Obtain written sign-off before granting vendor access"],
    ["Fixed the export job that stalled on empty batches",
     "Corrected rounding in the monthly summary report totals",
     "Restored keyboard shortcuts in the search panel",
     "Reduced memory use of the import service by a third",
     "Fixed a crash when a filter contained an empty string",
     "Improved start-up time on large tenants by half",
     "Added retry logic to the outbound webhook sender",
     "Updated the bundled TLS library to the current release",
     "Fixed date parsing for locales with comma decimal separators",
     "Removed the deprecated bulk endpoint from the public API",
     "Aligned the audit trail timestamps to UTC everywhere",
     "Fixed the pagination bug in the admin console lists"],
]

# TEMPLATES[family][unit][variant]; {status} is one of the family's phrases, the rest are slots
TEMPLATES = [
    {"title": ["{ident}: change to the {system}",
               "{ident}: {system} change memo",
               "{ident}: change record for the {system}"],
     "s1a": ["This memo records a change to the {system} that is currently {status}.",
             "The {system} change described below is {status} as of this writing.",
             "Change {ident} against the {system} is {status}, as noted by the change advisory board."],
     "s1b": ["It was raised by {owner} of {team} and touches {count} hosts behind the {system}, all of them in the production estate.",
             "{owner} ({team}) raised it, and {count} production hosts behind the {system} are in scope for the work.",
             "The work affects {count} production hosts behind the {system} and was raised by {owner} from {team}."],
     "s2": ["The implementation plan, prepared with {vendor}, covers these steps during the {window} window:",
            "Together with {vendor} the team plans the following steps for the {window} window:",
            "Steps scheduled in the {window} window with support from {vendor}:"],
     "s3a": ["The change advisory board marks this change as {status}.",
             "As recorded by the board, this change is {status}.",
             "Board outcome for {ident}: {status}."],
     "s3b": ["Recorded by {author} on {date}; the board met on {date2} and the minutes are in the shared archive.",
             "{author} filed this record on {date} after the board session of {date2}; minutes are in the shared archive.",
             "Minutes taken by {author}, {date}, covering the session held on {date2}, are kept in the shared archive."]},
    {"title": ["{ident}: incident on the {system}",
               "{ident}: {system} incident report",
               "{ident}: service incident, {system}"],
     "s1a": ["This report covers an incident on the {system} that is {status}.",
             "The {system} incident described here is {status} at the time of writing.",
             "Incident {ident} on the {system} is {status}, per the service desk record."],
     "s1b": ["About {count} customer tickets were linked to it by {team}, with {vendor} engaged as the hosting provider from the first hour.",
             "{team} linked roughly {count} tickets to the event and engaged {vendor}, the hosting provider, within the first hour.",
             "The hosting provider {vendor} was engaged by {team} within the first hour, and roughly {count} tickets were linked to the event."],
     "s2": ["Timeline recorded by {owner}, in order, as of {date2}:",
            "{owner} logged the following events, state as of {date2}:",
            "Events noted by {owner} up to {date2}, in order:"],
     "s3a": ["Current state of the incident: {status}.",
             "{team} lists the incident as {status}.",
             "For tracking purposes the incident is {status}."],
     "s3b": ["Report written by {author} on {date}; the next review falls in the {window} window and goes to the weekly service meeting.",
             "{author} wrote this report on {date} and will review it in the {window} window before the weekly service meeting.",
             "Written by {author}, {date}, with a follow-up review set for the {window} window ahead of the weekly service meeting."]},
    {"title": ["{ident}: policy for the {system}",
               "{ident}: {system} usage policy",
               "{ident}: policy governing the {system}"],
     "s1a": ["This policy applies to every user of the {system} and is {status}.",
             "The policy below governs use of the {system}; it is {status}.",
             "Policy {ident} covers the {system} and is {status}, per the policy register."],
     "s1b": ["{owner} of {team} is the policy owner, and {vendor} audits compliance each year against the controls listed here.",
             "The policy owner is {owner} ({team}); yearly audits against the controls listed here are run by {vendor}.",
             "{vendor} audits compliance with the controls listed here each year on behalf of the owner, {owner} from {team}."],
     "s2": ["Every person in scope must meet these requirements, reviewed on {date2}:",
            "The requirements, last reviewed on {date2}, are:",
            "As of the {date2} review the requirements are:"],
     "s3a": ["Status of this policy: {status}.",
             "The policy is {status} according to the register.",
             "For the record, {ident} is {status}."],
     "s3b": ["Issued by {author} on {date}; {count} exceptions are on file with {team} and expire at the yearly audit.",
             "{author} issued this version on {date}, with {count} exceptions on file that expire at the yearly audit.",
             "Version issued {date} by {author}; exceptions on file: {count}, all expiring at the yearly audit."]},
    {"title": ["{ident}: release notes for the {system}",
               "{ident}: {system} release notes",
               "{ident}: what changed in the {system}"],
     "s1a": ["This release of the {system} ships on {date} to all tenants.",
             "{ident} of the {system} rolls out to every tenant on {date}.",
             "The {system} team ships {ident} to every tenant on {date}."],
     "s1b": ["Highlights are faster search and a reworked admin console, with {vendor} contributing the search work and {count} customer reports addressed.",
             "{vendor} contributed the search work; the team also reworked the admin console and addressed {count} customer reports.",
             "Besides faster search, built with {vendor}, and a reworked admin console, {count} customer reports were addressed."],
     "s2": ["Fixes in this release, verified by {team} on {date2}:",
            "{team} verified the following fixes on {date2}:",
            "The following fixes were verified by {team} on {date2}:"],
     "s3a": ["Tenants are upgraded automatically during the {window} window; no action is needed.",
             "The upgrade runs automatically in the {window} window and needs no action from tenants.",
             "No tenant action is needed: the upgrade is applied in the {window} window."],
     "s3b": ["Release manager: {author}; support contact: {owner}, reachable through the usual channel.",
             "{author} managed this release and {owner} is the support contact, reachable through the usual channel.",
             "Contact {owner} for support through the usual channel; {author} was the release manager."]},
]

NAMES = ["Priya Raman", "Tomas Lindqvist", "Aisha Bello", "Daniel Ortega", "Mei Chen", "Jonas Berg",
         "Fatima Zahra", "Luca Moretti", "Hannah Cole", "Omar Haddad", "Sofia Russo", "Kenji Sato",
         "Grace Okafor", "Ivan Petrov", "Nadia Karim", "Felix Brandt", "Amara Osei", "Rohan Mehta",
         "Elena Vasquez", "Noah Fischer", "Leila Nasser", "Mateo Silva", "Ingrid Haugen", "Samuel Adeyemi",
         "Yuki Tanaka", "Clara Dubois", "Arjun Pillai", "Zoe Mitchell", "Victor Nwosu", "Hana Kowalski"]
VENDORS = ["Northwind Systems", "Halvorsen Consulting", "Bluegate Networks", "Corvid Analytics",
           "Pinecrest Hosting", "Meridian Cloud", "Oakridge Software", "Tessaro Labs", "Silverline Data",
           "Brightpath Security"]
TEAMS = ["Platform Engineering", "Finance Operations", "Security Office", "Data Services", "Service Desk",
         "Network Operations", "Release Management", "Risk and Compliance", "Infrastructure", "Product Support"]
WINDOWS = ["02:00-04:00 UTC", "22:00-23:30 UTC", "06:00-07:00 UTC", "01:00-03:00 UTC", "20:00-21:00 UTC",
           "03:30-05:00 UTC"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]

# generic words only: no status word, and no alternative that contains a status stem
SYNONYMS = {"records": ["documents"], "currently": ["presently"], "described": ["set out"], "below": ["that follows"],
            "raised": ["submitted"], "touches": ["affects"], "hosts": ["servers"], "scope": ["range"],
            "prepared": ["drawn up"], "covers": ["spans"], "steps": ["actions"], "plans": ["intends"],
            "scheduled": ["planned"], "support": ["assistance"], "marks": ["lists"], "recorded": ["noted"],
            "minutes": ["notes"], "session": ["meeting"], "shared": ["common"], "roughly": ["about"],
            "about": ["roughly"], "linked": ["tied"], "engaged": ["brought in"], "tickets": ["cases"],
            "logged": ["noted"], "events": ["entries"], "written": ["authored"], "wrote": ["authored"],
            "review": ["check"], "weekly": ["regular"], "applies": ["extends"], "governs": ["regulates"],
            "yearly": ["annual"], "audits": ["checks"], "every": ["each"], "person": ["individual"],
            "requirements": ["rules"], "issued": ["published"], "exceptions": ["waivers"], "expire": ["lapse"],
            "ships": ["goes out"], "tenants": ["customers"], "faster": ["quicker"], "reworked": ["redesigned"],
            "addressed": ["handled"], "verified": ["checked"], "automatically": ["without manual steps"],
            "needed": ["required"], "manager": ["lead"], "contact": ["person"], "usual": ["normal"],
            "nightly": ["overnight"], "legacy": ["old"], "primary": ["main"], "affected": ["impacted"],
            "notified": ["informed"], "standard": ["usual"], "annual": ["yearly"], "manual": ["hand-made"],
            "monthly": ["month-end"], "large": ["big"], "current": ["latest"], "public": ["external"]}


def identifier(canonical):
    """CHG-4412, INC-2087, POL-214 or REL-3.7 from a canonical."""
    family, number = canonical["family"], canonical["ident"]
    if family == 3:
        return "REL-%d.%d" % (number // 10, number % 10)
    return "%s-%d" % (FAMILIES[family]["prefix"], number)


def status_classes(text):
    """Every status class with a stem in the normalised text, in scan order."""
    text = common.norm_text(text)
    return [name for name, stems in STEM_GROUPS if any(stem in text for stem in stems)]


def status_class(text):
    """The first status class whose stem occurs in the text, or 'none' (release notes)."""
    found = status_classes(text)
    return found[0] if found else "none"


def date_in_2025(rng):
    return "%d %s 2025" % (rng.randrange(1, 29), common.pick(rng, MONTHS))


class DocsSpec(common.Spec):
    NAME = "docs"
    FILE = __file__
    HISTORY_FIELDS = ("hid", "category", "title", "body", "filed")
    TASK_FIELDS = ("tid", "seq", "title", "body", "received")
    DATE_FIELD = "filed"
    TASK_DATE_FIELD = "received"
    UNITS = ("title", "s1a", "s1b", "s2", "s3a", "s3b")
    SYNONYMS = SYNONYMS
    MAX_HISTORY = 160
    MAX_INCOMING = 80
    DEFAULT_SEED = 37
    DEFAULT_DUP_RATE = 0.40
    DEFAULT_HISTORY = 110
    DEFAULT_INCOMING = 60
    TEXT_FOR_SIMILARITY = "title + body"

    def __init__(self):
        if POOL_SIZE % len(FAMILY_CYCLE):
            raise ValueError("POOL_SIZE must be a multiple of the family cycle length")
        self._numbers = []
        for family, numbers in enumerate(NUMBER_RANGES):
            numbers = list(numbers)
            common.sub_rng("docs-pool", "numbers", family).shuffle(numbers)
            need = (POOL_SIZE // len(FAMILY_CYCLE)) * FAMILY_CYCLE.count(family)
            if need > len(numbers):
                raise ValueError("family %d needs %d identifier numbers, has %d" % (family, need, len(numbers)))
            self._numbers.append(numbers[:need])

    def pool_size(self):
        return POOL_SIZE

    def canonical_at(self, k):
        """The k-th canonical, derived from k alone: family by cycle position, the rest from a seeded rng."""
        cycle = len(FAMILY_CYCLE)
        family = FAMILY_CYCLE[k % cycle]
        ordinal = (k // cycle) * FAMILY_CYCLE.count(family) + FAMILY_CYCLE[:k % cycle].count(family)
        rng = common.sub_rng("docs-pool", k)
        return {"family": family, "ident": self._numbers[family][ordinal],
                "system": rng.randrange(len(SYSTEMS)),
                "status": rng.randrange(len(FAMILIES[family]["classes"])),
                "details": tuple(sorted(rng.sample(range(len(DETAILS[family])), 3)))}

    def answer(self, canonical):
        return {"category": FAMILIES[canonical["family"]]["categories"][canonical["status"]]}

    def finalise_answer(self, answer, canonical_id, by_canonical):
        """duplicate_of: the first history record of the same canonical, never a task id."""
        history_ids = [rid for rid in by_canonical.get(canonical_id, []) if rid.startswith("H-")]
        return dict(answer, duplicate_of=history_ids[0] if history_ids else None)

    def flip(self, rng, canonical):
        """The status slot only, to each other status of the family; release notes have none."""
        statuses = range(len(FAMILIES[canonical["family"]]["classes"]))
        options = [dict(canonical, status=s) for s in statuses if s != canonical["status"]]
        rng.shuffle(options)
        return options

    def cosmetic(self, rng):
        return {"author": common.pick(rng, NAMES), "owner": common.pick(rng, NAMES),
                "date": date_in_2025(rng), "date2": date_in_2025(rng),
                "vendor": common.pick(rng, VENDORS), "team": common.pick(rng, TEAMS),
                "window": common.pick(rng, WINDOWS), "count": rng.randrange(3, 41)}

    def compose(self, state):
        c, v, cos = state["canonical"], state["variants"], state["cosmetic"]
        fam, t = FAMILIES[c["family"]], TEMPLATES[c["family"]]
        phrases = fam["phrases"][c["status"]]
        slots = dict(cos, ident=identifier(c), system=SYSTEMS[c["system"]])

        def unit(name, status=""):
            return t[name][v[name]].format(status=status, **slots)

        def phrase(name):
            return phrases[v[name] % len(phrases)] if phrases else ""

        bullets = "\n".join("- " + DETAILS[c["family"]][i] for i in c["details"])
        h1, h2, h3 = fam["headers"]
        sections = [(h1, unit("s1a", phrase("s1a")) + " " + unit("s1b")),
                    (h2, unit("s2") + "\n" + bullets),
                    (h3, unit("s3a", phrase("s3a")) + " " + unit("s3b"))]
        return {"fields": {}, "title": unit("title"), "sections": sections}

    def recase_fields(self, fields, style):
        return fields                       # no structured fields besides title and body

    def protected(self, state):
        """The identifier, the system name and every status stem of every class (words of 4+ letters)."""
        c = state["canonical"]
        stems = [word for _, group in STEM_GROUPS for stem in group for word in stem.split() if len(word) >= 4]
        return [identifier(c)] + SYSTEMS[c["system"]].split() + stems

    def validation_tuple(self, record):
        match = IDENT_RE.search(record.get("title", ""))
        return (match.group(0).upper() if match else None,
                status_class(record.get("title", "") + " " + record.get("body", "")))

    def text_for_similarity(self, record):
        return record["title"] + "\n" + record["body"]

    def instructions(self):
        lines = ["# Internal memo classification", "",
                 "You are a records clerk. One internal memo is in `task.json`; your job is to decide which of",
                 "the eight document categories it belongs to, say which history record (if any) describes the",
                 "same document, and write both to `answer.json`.", "",
                 "## Files in this directory", "",
                 "- `INSTRUCTIONS.md`: this file.",
                 "- `history.jsonl`: one JSON object per line, every one a filed, verified memo: fields `hid`",
                 "  (`H-` and six hex digits), `category` (the verified answer), `title`, `body`, `filed`.",
                 "- `task.json`: the memo to classify: `tid`, `seq`, `title`, `body`, `received`.", "",
                 "`history.jsonl` contains verified answers. If `task.json` describes the same underlying item as a",
                 "history record (the same document, not merely a similar one), you may reuse that record's answer.",
                 "Before you do, check the fields under Validation below; near-identical records with a different",
                 "value there are different items with different answers.", "",
                 "## Categories", "",
                 "Four families of memo, told apart by the identifier in the title; a status word in the body",
                 "splits three of them further. Status words (in any inflection) per category:", ""]
        for fam in FAMILIES:
            pattern = {"CHG": "CHG-nnnn", "INC": "INC-nnnn", "POL": "POL-nnn", "REL": "REL-n.n"}[fam["prefix"]]
            lines.append("**%s** (`%s`)" % (fam["noun"].capitalize(), pattern))
            lines.append("")
            for category, cls in zip(fam["categories"], fam["classes"]):
                lines.append("- `%s`: %s. Status words: %s." % (category, DEFINITIONS[category], VOCABULARY[cls]))
            lines.append("")
        lines += ["A memo carries the words of exactly one status, in two sentences of the body, and never negates",
                  "them: no memo says \"not approved\". Release notes carry none. The title holds the identifier and",
                  "the system the memo is about; the body is three short labelled sections, in any order.", "",
                  "Identifier pattern (it appears in the title): `%s`" % IDENT_PATTERN, "",
                  "## How to decide a fresh document", "",
                  "- Find the identifier in the title; its prefix gives the family (CHG, INC, POL or REL).",
                  "- Find the status word in the body and map it to its class with the lists above; release notes",
                  "  have no status word and are always `release-notes`.",
                  "- The family and the status class together name the category.",
                  "- Names, dates, vendors, teams, counts, section order, formatting and wording carry no information.", "",
                  "## Validation (when is a history record the same document?)", "",
                  "A history record is the same document only when both its identifier and its status class match",
                  "the task. Compare identifiers after upper-casing: `chg-4412` and `CHG-4412` are one identifier.",
                  "Compare the class, not the word: `approved` and `authorised` are one class. Either test alone is",
                  "unsound: a change request and the later approval of the same change share the identifier but are",
                  "two documents with two categories; two approved changes share the category but are two documents,",
                  "and neither is `duplicate_of` the other.", "",
                  "## Worked example", "",
                  "The task title reads `CHG-4412: change to the Payroll Gateway` and two sentences of the body call",
                  "the change `approved`. The family is CHG and the class is approved, so the category is",
                  "`change-approved`. History holds `H-1a2b3c`, a `change-request` memo titled `CHG-4412: Payroll",
                  "Gateway change memo` whose body says `pending`: same identifier, different class, so it is a",
                  "different document and not `duplicate_of`, however much of the text matches. History also holds",
                  "`H-9d8e7f`, a `change-approved` memo for `CHG-7781`: same category, different identifier, a",
                  "different change. Unless some history record carries both `CHG-4412` and the approved class,",
                  "`duplicate_of` is `null`.", "",
                  "## Output", "",
                  "Write `answer.json` in this directory:", "", "```json",
                  '{"category": "change-approved", "duplicate_of": "H-3fa9c2"}', "```", "",
                  "`category` is exactly one of the eight names above (case does not matter). `duplicate_of` is the",
                  "`hid` of the history record that describes the same document, or `null` when none does. A document",
                  "that merely resembles a history record is not it. It is always a history id, never a task id.",
                  "Extra keys are ignored.", "",
                  "## Rules", "",
                  "- Do not modify `history.jsonl` or `task.json`; write nothing except `answer.json`.",
                  "- Only `answer.json` is graded. Your final message is not."]
        return "\n".join(lines) + "\n"

SPEC = DocsSpec()


def check_rendered(out):
    """Assert, on the files just written, that every visible record is ASCII, that its title carries an
    identifier of its category's family, and that title + body carry the stems of exactly the status
    class its category names (the hidden label for tasks, the visible field for history)."""
    env = os.path.join(out, "env")
    labels = common.load_labels(os.path.join(out, "hidden"))
    records = [(r["hid"], r, r["category"]) for r in common.load_jsonl(os.path.join(env, "history.jsonl"))]
    for name in sorted(os.listdir(os.path.join(env, "incoming"))):
        with open(os.path.join(env, "incoming", name), encoding="utf-8") as handle:
            record = json.load(handle)
        records.append((record["tid"], record, labels[record["tid"]]["answer"]["category"]))
    for rid, record, category in records:
        family, status = CATEGORY_INDEX[category]
        expected = FAMILIES[family]["classes"][status]
        text = record["title"] + " " + record["body"]
        ident, found = SPEC.validation_tuple(record)
        present = status_classes(text)
        if not text.isascii():
            raise AssertionError("%s: non-ASCII text" % rid)
        if not ident or not ident.startswith(FAMILIES[family]["prefix"] + "-"):
            raise AssertionError("%s: identifier %r does not belong to %s" % (rid, ident, category))
        if found != expected or present != ([expected] if expected != "none" else []):
            raise AssertionError("%s: status classes %s found, category %s expects %s" % (rid, present, category, expected))
    return len(records)


def main(argv=None):
    """common.main, then the status-class assertion over every record it wrote."""
    code = common.main(SPEC, argv)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--out", default=HERE)
    checked = check_rendered(parser.parse_known_args(argv)[0].out)
    print("status classes ok: %d records carry the stems of exactly their own class" % checked)
    return code


if __name__ == "__main__":
    sys.exit(main())
