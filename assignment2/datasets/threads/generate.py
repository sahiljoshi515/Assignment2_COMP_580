"""Assignment 2 -- threads: a mailbox where every reply quotes the thread and every night a bot writes the same report.

Concept this file teaches: context repeats itself. A reply carries the whole message it
answers, quoted line by line, so the sixth message of a thread contains the first five;
an automated report arrives every night with the same fourteen lines and three new
numbers. Someone asked "what did we finally decide" has to read the thread, and an agent
that reads it file by file reads the opening message six times. The repeated text is
exactly repeated (a quoted block) or nearly (a nightly report), which is the difference
between an exact cache and MinHash, made visible inside one task.

Design rules this file embodies:
  * Threads are decision processes with a last word. The decider's first note is not
    always the final decision; a correction may follow, and the question asks for the
    final one. Reading only the first decision is the realistic mistake.
  * Quoting is faithful: the full previous message, every line prefixed with `> `, so the
    quoted block normalises to exactly the earlier body.
  * The nightly reports differ only in the date, the numbers and, on a few nights, the
    status line -- the one line that answers the backup questions.

Run from the repo root:  /usr/local/bin/python3.13 assignment2/datasets/threads/generate.py
"""

import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common, corpus  # noqa: E402

COMPANIES = ["Halden Logistics", "Brightwater Clinics", "Northbank Studio", "Caldera Foods", "Oakline Partners",
             "Meridian Schools", "Tessa Labs", "Harbour Freight", "Pinewood Legal", "Ferro & Sons"]
TOPICS = [  # (key, subject, what is asked, two context sentences)
    ("vendor-renewal", "Vendor contract renewal for {x}",
     "renew the {x} contract for another year at the quoted price",
     ["The current {x} contract ends on the last day of next month.", "Their quote is 8 % above this year's price, which they attribute to the new support tier."]),
    ("office-move", "Office move to {x}",
     "move the team to {x} in the second quarter",
     ["The lease on the current floor can be ended with three months' notice.", "{X} has room for twelve more desks and a proper meeting room."]),
    ("hiring-plan", "Hiring plan for the {x} team",
     "open two additional roles on the {x} team this half",
     ["The {x} team has carried the on-call rota with two people fewer since March.", "Both roles are in the approved headcount, just not yet in the budget line."]),
    ("tool-migration", "Migration from {x} to the new tracker",
     "migrate our issue tracking off {x} before the renewal date",
     ["Our {x} licence renews automatically in ten weeks.", "The pilot team has been on the new tracker for a month without complaints."]),
    ("policy-exception", "Exception request for the {x} policy",
     "grant a six-month exception from the {x} policy for the field team",
     ["The field team cannot meet the {x} requirement on the devices they currently carry.", "Compliance has asked for a documented decision either way."]),
    ("sponsorship", "Sponsorship of {x}",
     "sponsor {x} at the silver tier this year",
     ["We sponsored {x} at the bronze tier last year and hired two people from it.", "The silver tier adds a booth and a speaking slot."]),
    ("laptop-refresh", "Laptop refresh for {x}",
     "move {x} to a three-year laptop refresh cycle",
     ["About a third of the laptops in {x} are past four years old.", "IT estimates the three-year cycle at roughly the same yearly cost once repairs are counted."]),
    ("data-retention", "Retention change for {x} data",
     "shorten the retention of {x} data to one year",
     ["Legal has confirmed one year is sufficient for {x} records.", "Storage for {x} is the largest single line in the data budget."]),
]
TOPIC_X = {"vendor-renewal": ["Northwind", "Contoso Cloud", "Fabrikam Support", "Litware"],
           "office-move": ["Harbour House", "the Riverside annex", "Pier 9", "the Elm Street site"],
           "hiring-plan": ["platform", "support", "data", "payments"],
           "tool-migration": ["Trackly", "IssueHub", "TaskForge", "Planwise"],
           "policy-exception": ["device encryption", "two-factor", "VPN-only access", "screen lock"],
           "sponsorship": ["PyData North", "DevOpsDays Harbour", "the regional security meetup", "KubeCon Local"],
           "laptop-refresh": ["the sales team", "the support team", "engineering", "the finance team"],
           "data-retention": ["telemetry", "support ticket", "access log", "invoice"]}
QUESTIONS = ["Before I weigh in: what happens if we do nothing until the next quarter?",
             "Quick question -- is there a cheaper option we have ruled out, and why?",
             "Who else needs to be in the loop before this goes ahead?",
             "Do we have a number for the total cost over the year?"]
ANSWERS = ["If we wait, we lose the current terms and start over in the next quarter, which costs us about a month.",
           "We looked at the two alternatives; both were cheaper on paper and more expensive once the migration effort was counted.",
           "Finance has seen the numbers; the only sign-off missing is yours.",
           "The yearly total is in the attached sheet; it is within the amount we discussed in planning."]
CONCERNS = ["My only concern is timing: we have the audit in the same window, and I would rather not run both at once.",
            "I am supportive, but I want it on record that we revisit this in six months.",
            "One more consideration: the support team has asked to be consulted before anything changes for them.",
            "I lean yes, provided the cost stays inside the current budget line."]
DECISIONS = {"approve": ["Decision: approved. Please go ahead and {ask}, with the condition that {cond}.",
                         "I am approving this. Go ahead and {ask}; {cond}."],
             "reject": ["Decision: not approved. We will not {ask} this time; {cond}.",
                        "I have to say no to this one. We will not {ask}; {cond}."],
             "defer": ["Decision: deferred. Let's not {ask} yet; {cond}.",
                       "Let's park this. We will revisit whether to {ask} {cond}."]}
CONDITIONS = {"approve": ["the spend stays within the approved budget line", "the support team is consulted first",
                          "we review the outcome in six months"],
              "reject": ["the budget is committed elsewhere this year", "the risk is not worth the saving",
                         "we come back to it in the next planning round"],
              "defer": ["after the audit closes next month", "once the numbers for the full year are in",
                        "in the next planning round"]}
CORRECTIONS = ["Correction to my note above: having seen the revised numbers, {decision_text}",
               "A follow-up on my earlier reply -- I spoke too soon. {decision_text}"]
THANKS = ["Thanks all, noted. I will update the plan accordingly.", "Understood, thank you. I will let the team know."]
NEWSLETTER = ["Monthly engineering newsletter", "Facilities notice: car park resurfacing", "Reminder: expense deadline"]
BACKUP_JOBS = ["prod-postgres-full", "fileshare-nightly", "mailstore-incremental", "wiki-and-tracker"]
FAIL_REASONS = ["target volume full", "connection to nas-01 timed out", "snapshot lock held by a previous run",
                "checksum mismatch on 3 files", "credentials expired"]


def kinds():
    def final_decision(state, target):
        thread = state["threads"][target]
        return {"decision": thread["final"]["decision"], "by": thread["decider"], "date": thread["final"]["date"]}

    def requester(state, target):
        return {"name": state["threads"][target]["requester"]}

    def message_count(state, target):
        return {"count": len(state["threads"][target]["messages"])}

    def failed_backups(state, target):
        return {"dates": [r["date"] for r in state["reports"] if r["failed"]]}

    def longest_backup(state, target):
        report = max(state["reports"], key=lambda r: (r["minutes"], r["date"]))
        return {"date": report["date"], "minutes": report["minutes"]}

    def first_failed_backup(state, target):
        report = next(r for r in state["reports"] if r["failed"])
        return {"date": report["date"], "reason": report["reason"]}

    def thread_keys(state):
        return sorted(state["threads"])

    return (
        corpus.Kind("final_decision", "final decision in the {target} thread",
                    ["In the thread about the {target_words}, what was the final decision, who made it, and on what date?",
                     "Please read the {target_words} thread in inbox/ and tell me how it was finally decided: the decision, the decider and the date of that message.",
                     "What did we finally decide on the {target_words}? I need the outcome, who decided, and the date of the deciding message."],
                    ["If a later message corrects an earlier decision, the later one counts.",
                     "Mind that decisions are sometimes revised further down the thread; the last word is the answer.",
                     "Report the decision as approve, reject or defer, the decider by full name, and the date as YYYY-MM-DD."],
                    final_decision, ("decision", "by", "date"), targets=thread_keys,
                    example={"decision": "defer", "by": "Hannah Cole", "date": "2026-03-11"}),
        corpus.Kind("requester", "who opened the {target} thread",
                    ["Who originally asked for the {target_words}? Full name as it appears in the From header.",
                     "Which colleague opened the {target_words} thread, i.e. sent its first message?",
                     "Please tell me who sent the first message of the {target_words} thread in inbox/."],
                    ["The threads are in inbox/, one message per file, ordered by date.",
                     "Use the From header of the earliest message with that subject.",
                     "Report the display name, not the address."],
                    requester, ("name",), targets=thread_keys, example={"name": "Priya Nair"}),
        corpus.Kind("message_count", "how many messages in the {target} thread",
                    ["How many messages does the {target_words} thread contain in inbox/, counting the original and every reply?",
                     "Please count the messages in the {target_words} thread (original message plus replies).",
                     "How long is the {target_words} thread, in messages?"],
                    ["Every message is its own file; quoted text inside a reply does not count as a message.",
                     "Count files whose Subject is that thread's subject, with or without Re:.",
                     "Replies quote earlier messages; count messages, not quotes."],
                    message_count, ("count",), targets=thread_keys, example={"count": 6}),
        corpus.Kind("failed_backups", "which nightly backups failed",
                    ["The nightly backup reports in inbox/ cover a stretch of nights. On which dates did the backup fail?",
                     "Please list the dates of the nightly backup reports whose status is FAILED.",
                     "Which nights' backup reports in inbox/ show a failure? Give the dates."],
                    ["Report dates as YYYY-MM-DD, as a list.",
                     "The status is on the Status line of each report; the date is in the subject.",
                     "A list of the report dates with Status: FAILED is what I need."],
                    failed_backups, ("dates",), example={"dates": ["2026-03-02", "2026-03-05"]}),
        corpus.Kind("longest_backup", "which nightly backup took longest",
                    ["Which nightly backup report in inbox/ shows the longest duration, and how many minutes did it take?",
                     "Find the nightly backup with the longest Duration among the reports in inbox/; give its date and the minutes.",
                     "Of all the nightly backup reports, which night ran longest? Date and duration in minutes, please."],
                    ["Duration is printed in minutes on each report's timing line.",
                     "Compare the Duration values across the reports; the largest is unique.",
                     "Report the date as YYYY-MM-DD and the duration as an integer number of minutes."],
                    longest_backup, ("date", "minutes"), example={"date": "2026-03-04", "minutes": 57}),
        corpus.Kind("first_failed_backup", "first failed nightly backup and why",
                    ["What is the date of the first nightly backup report that shows a failure, and what reason does it give?",
                     "Find the earliest FAILED nightly backup report in inbox/ and tell me its date and the stated reason.",
                     "When did the nightly backup first fail in this mailbox, and what was the reason on the report?"],
                    ["The reason follows FAILED on the Status line, in parentheses.",
                     "Quote the reason as printed on the Status line.",
                     "Date as YYYY-MM-DD; the reason is the text in parentheses after FAILED."],
                    first_failed_backup, ("date", "reason"), example={"date": "2026-03-02", "reason": "target volume full"}),
    )


class ThreadsSpec(corpus.CorpusSpec):
    NAME = "threads"
    FILE = __file__
    TITLE = "Questions about a shared mailbox"
    ROLE = ("You are an assistant with access to a team mailbox export. One question about it is in `task.json`;\n"
            "answer it from the messages in `inbox/` and write the answer to `answer.json`.")
    FILE_LAYOUT = ("`inbox/<nnn>_<subject>.eml`: one message per file in date order, plain-text headers (From, To, "
                   "Date, Subject) and body; replies quote the message they answer with `> ` prefixes.")
    KINDS = kinds()
    SCENARIOS = 24
    SCENARIO_PREFIX = "MBX"
    DEFAULT_SEED = 79

    def service_of(self, state):
        return state["company"]

    def slots(self, state, canonical, cosmetic):
        slots = super().slots(state, canonical, cosmetic)
        target = canonical["target"]
        slots["target_words"] = state["threads"][target]["words"] if target in state["threads"] else ""
        return slots

    def scenario_state(self, sid, rng):
        company = common.pick(rng, COMPANIES)
        domain = corpus.slug(company).replace("-", "") + ".example"
        people = rng.sample(corpus.NAMES, 7)
        start = datetime.date(2026, 2, 2) + datetime.timedelta(days=rng.randrange(0, 90))
        topics = rng.sample(TOPICS, 3)
        threads = {}
        day_cursor = 0
        for key, subject, ask, context in topics:
            x = common.pick(rng, TOPIC_X[key])
            requester, decider = rng.sample(people[:5], 2)
            commenters = [p for p in people if p not in (requester, decider)]
            rng.shuffle(commenters)
            messages = []
            d = start + datetime.timedelta(days=day_cursor + rng.randrange(0, 3))
            ask_text = ask.format(x=x)
            capital = x[0].upper() + x[1:]
            opening = ("I would like to %s. %s %s Could you take a look and let me know whether you can approve it?"
                       % (ask_text, context[0].format(x=x, X=capital), context[1].format(x=x, X=capital)))
            messages.append({"from": requester, "date": d, "body": opening})
            d += datetime.timedelta(days=rng.randrange(0, 2))
            q = rng.randrange(len(QUESTIONS))
            messages.append({"from": commenters[0], "date": d, "body": QUESTIONS[q]})
            d += datetime.timedelta(days=rng.randrange(0, 2))
            messages.append({"from": requester, "date": d, "body": ANSWERS[q]})
            d += datetime.timedelta(days=rng.randrange(0, 3))
            messages.append({"from": commenters[1], "date": d, "body": common.pick(rng, CONCERNS)})
            d += datetime.timedelta(days=rng.randrange(0, 3))
            first = common.pick(rng, ["approve", "reject", "defer"])
            cond = common.pick(rng, CONDITIONS[first])
            messages.append({"from": decider, "date": d, "body": common.pick(rng, DECISIONS[first]).format(ask=ask_text, cond=cond),
                             "decision": first})
            final = {"decision": first, "date": d.isoformat()}
            if rng.random() < 0.5:
                d += datetime.timedelta(days=rng.randrange(1, 4))
                second = common.pick(rng, [k for k in DECISIONS if k != first])
                cond = common.pick(rng, CONDITIONS[second])
                text = common.pick(rng, DECISIONS[second]).format(ask=ask_text, cond=cond)
                text = text[0].lower() + text[1:]
                messages.append({"from": decider, "date": d, "body": common.pick(rng, CORRECTIONS).format(decision_text=text),
                                 "decision": second})
                final = {"decision": second, "date": d.isoformat()}
            if rng.random() < 0.6:
                d += datetime.timedelta(days=rng.randrange(0, 2))
                messages.append({"from": requester, "date": d, "body": common.pick(rng, THANKS)})
            threads[key] = {"subject": subject.format(x=x), "words": subject.format(x=x).lower().replace("the ", ""),
                            "requester": requester, "decider": decider, "messages": messages, "final": final}
            day_cursor += rng.randrange(2, 6)
        n_reports = rng.randrange(8, 12)
        failed = sorted(rng.sample(range(n_reports), rng.randrange(2, 4)))
        job = common.pick(rng, BACKUP_JOBS)
        reports, minutes = [], rng.sample(range(31, 95), n_reports)
        for i in range(n_reports):
            day = start - datetime.timedelta(days=1) + datetime.timedelta(days=i)
            reports.append({"date": day.isoformat(), "failed": i in failed, "minutes": minutes[i],
                            "reason": common.pick(rng, FAIL_REASONS) if i in failed else None,
                            "gb": rng.randrange(380, 520) / 10.0, "files": rng.randrange(900_000, 1_400_000),
                            "changed": rng.randrange(8, 60) / 10.0, "job": job})
        return {"scenario": sid, "company": company, "domain": domain, "people": people, "threads": threads,
                "reports": reports, "start": start.isoformat(),
                "noise": rng.sample(NEWSLETTER, 2), "noise_days": [rng.randrange(0, 12) for _ in range(2)]}

    @staticmethod
    def email(name, domain):
        return "%s@%s" % (corpus.slug(name).replace("-", "."), domain)

    @staticmethod
    def header_date(day, hour, minute):
        return "%s, %02d %s %d %02d:%02d:00 +0000" % (day.strftime("%a"), day.day, day.strftime("%b"), day.year, hour, minute)

    def render_messages(self, state):
        """Every message of the mailbox as (date, sort key, subject, headers+body, meta), in date order."""
        out = []
        domain = state["domain"]
        for key in sorted(state["threads"]):
            thread = state["threads"][key]
            rng = common.sub_rng(self.NAME + "-thread", state["scenario"], key)
            previous = None
            last_clock = None
            for i, message in enumerate(thread["messages"]):
                hour, minute = rng.randrange(8, 18), rng.randrange(0, 60)
                if last_clock is not None and message["date"] == last_clock[0] and (hour, minute) <= last_clock[1]:
                    hour, minute = last_clock[1][0] + (1 if last_clock[1][1] >= 45 else 0), (last_clock[1][1] + 15) % 60
                last_clock = (message["date"], (hour, minute))
                subject = thread["subject"] if i == 0 else "Re: " + thread["subject"]
                to = thread["decider"] if message["from"] == thread["requester"] else thread["requester"]
                body_lines = [message["body"], "", "-- ", message["from"].split()[0]]
                if previous is not None:
                    body_lines += ["", "On %s, %s wrote:" % (previous["date_text"], previous["from"])]
                    body_lines += ["> " + line if line else ">" for line in previous["lines"]]
                lines = ["From: %s <%s>" % (message["from"], self.email(message["from"], domain)),
                         "To: %s <%s>" % (to, self.email(to, domain)),
                         "Cc: %s" % ", ".join(sorted({self.email(p, domain) for p in state["people"][:5]} - {self.email(message["from"], domain), self.email(to, domain)})),
                         "Date: %s" % self.header_date(message["date"], hour, minute),
                         "Subject: %s" % subject, ""] + body_lines
                previous = {"date_text": self.header_date(message["date"], hour, minute), "from": message["from"],
                            "lines": body_lines}
                out.append((message["date"], hour * 60 + minute, subject, "\n".join(lines) + "\n",
                            {"thread": key, "index": i, "decision": message.get("decision"), "final": i == len(thread["messages"]) - 1}))
        for report in state["reports"]:
            day = datetime.date.fromisoformat(report["date"])
            rng = common.sub_rng(self.NAME + "-report", state["scenario"], report["date"])
            start_min = rng.randrange(0, 5)
            finish = 120 + start_min + report["minutes"]
            status = "FAILED (%s)" % report["reason"] if report["failed"] else "SUCCESS"
            lines = ["From: Backup Service <backup-bot@%s>" % domain,
                     "To: ops-notify@%s" % domain,
                     "Date: %s" % self.header_date(day + datetime.timedelta(days=1), finish // 60, finish % 60),
                     "Subject: Nightly backup report - %s - %s" % (report["job"], report["date"]), "",
                     "Nightly backup report for %s" % report["date"],
                     "Job: %s" % report["job"],
                     "Status: %s" % status,
                     "Started: 02:%02d:%02d UTC   Finished: %02d:%02d:%02d UTC   Duration: %d min" % (
                         start_min, rng.randrange(0, 60), finish // 60, finish % 60, rng.randrange(0, 60), report["minutes"]),
                     "Bytes transferred: %.1f GB   Files: %s   Changed since last run: %.1f %%" % (
                         report["gb"], "{:,}".format(report["files"]), report["changed"]),
                     "Retention: 30 daily, 12 weekly, 6 monthly",
                     "Next run: %s 02:00 UTC" % (day + datetime.timedelta(days=1)).isoformat(), "",
                     "-- ", "This message was generated automatically by the backup service. Replies are not read.",
                     "To change the schedule or the recipients, edit the job in the backup console."]
            out.append((day + datetime.timedelta(days=1), finish, "Nightly backup report", "\n".join(lines) + "\n",
                        {"report": report["date"], "failed": report["failed"]}))
        start = datetime.date.fromisoformat(state["start"])
        for subject, offset in zip(state["noise"], state["noise_days"]):
            day = start + datetime.timedelta(days=offset)
            lines = ["From: Internal Communications <comms@%s>" % domain, "To: all-staff@%s" % domain,
                     "Date: %s" % self.header_date(day, 9, 0), "Subject: %s" % subject, "",
                     "Hello all,", "",
                     "A short note from the communications team: %s. Details are on the intranet page linked from the" % subject.lower(),
                     "home screen, and questions can go to the comms channel as usual.", "", "Best regards,", "Internal Communications"]
            out.append((day, 540, subject, "\n".join(lines) + "\n", {"noise": True}))
        out.sort(key=lambda item: (item[0], item[1]))
        return out

    def scenario_files(self, state):
        files = {}
        for n, (day, _, subject, text, meta) in enumerate(self.render_messages(state), 1):
            files["inbox/%03d_%s.eml" % (n, corpus.slug(subject)[:40])] = text
        return files

    def content_truth(self, state, files):
        groups = {key: [] for key in state["threads"]}
        groups["nightly-reports"] = []
        answer_lines = {}
        for n, (day, _, subject, text, meta) in enumerate(self.render_messages(state), 1):
            path = "inbox/%03d_%s.eml" % (n, corpus.slug(subject)[:40])
            lines = text.split("\n")
            if "thread" in meta:
                groups[meta["thread"]].append(path)
                marks = [i for i, line in enumerate(lines, 1) if line.startswith("From:") or line.startswith("Date:")]
                if meta["decision"]:
                    marks += [i for i, line in enumerate(lines, 1) if line and not line.startswith(">") and not line.startswith(("From:", "To:", "Cc:", "Date:", "Subject:", "-- ", "On "))]
                answer_lines[path] = sorted(set(marks))[:6]
            elif "report" in meta:
                groups["nightly-reports"].append(path)
                answer_lines[path] = [i for i, line in enumerate(lines, 1) if line.startswith(("Subject:", "Status:", "Started:"))]
        return {"groups": [{"name": name, "files": sorted(paths)} for name, paths in sorted(groups.items())],
                "answer_lines": answer_lines}

    def domain_instructions(self):
        return ["## The scenario", "",
                "`inbox/` is an export of a shared mailbox: one message per file, numbered in date order, with plain",
                "headers (`From`, `To`, `Cc`, `Date`, `Subject`) followed by the body. It holds a few discussion",
                "threads (an original message and its replies, each reply quoting the message it answers with `> `",
                "prefixes), a series of automated nightly backup reports from the backup service, and some",
                "unrelated announcements.", "",
                "## How to decide", "",
                "- A thread is the set of messages sharing a subject, with or without `Re:`. Quoted text inside a",
                "  reply belongs to the earlier message, not to the reply.",
                "- A decision message says approve, reject or defer (in those words or close ones: approved, not",
                "  approved, park/defer). A later correction overrides an earlier decision; the final decision is the",
                "  last one in the thread. Report the decision as one of `approve`, `reject`, `defer`.",
                "- People are reported by the display name in the From header; dates as `YYYY-MM-DD` taken from the",
                "  Date header of the message in question.",
                "- Nightly reports carry their date in the subject and on the first body line; the Status line says",
                "  SUCCESS or FAILED (reason); the timing line gives the Duration in minutes."]


SPEC = ThreadsSpec()

if __name__ == "__main__":
    sys.exit(corpus.main(SPEC))
