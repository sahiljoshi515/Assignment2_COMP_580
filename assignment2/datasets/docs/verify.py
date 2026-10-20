"""Assignment 2 -- docs/verify.py: are the category and the duplicate_of in answer.json the labelled ones?

Concept this file teaches: a reuse decision is graded twice. The category can be right
while `duplicate_of` points at the wrong history record (the request memo instead of the
approval, or a look-alike that is a different document), and that is a different failure
from a wrong category. Both come from a label the agent never saw, and the agent's final
message is a claim, not evidence; only the file it wrote is graded.

Design rules this file embodies:
  * Pure and deterministic: labels in, verdict out, no clock, no network, no model.
  * Never raise on bad input. A list, a string, a missing key or an unknown id each
    become a failed check with a reason; the runner must keep going.
  * Lenient on spelling, strict on meaning: `Change-Approved` is `change-approved` and
    `h-3fa9c2`, `null`, `none` and a missing key are read charitably, but a task id or
    the wrong history id in `duplicate_of` is simply wrong.

Run from the repo root:
    /usr/local/bin/python3.13 assignment2/datasets/docs/verify.py --tid T-xxxxxx --answer answer.json
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common  # noqa: E402

HIDDEN = os.path.join(HERE, "hidden")
CATEGORIES = ("change-request", "change-approved", "change-rejected", "incident-open", "incident-resolved",
              "policy-draft", "policy-final", "release-notes")


def norm_category(value):
    """'Change-Approved ' -> 'change-approved'; anything that is not a string becomes a plain repr."""
    return str(value).strip().lower() if isinstance(value, str) else None


def norm_hid(value):
    """None, '', 'null', 'none', 'n/a' -> None; otherwise the id upper-cased and stripped."""
    return None if common.null_ish(value) else str(value).strip().upper()


def grade(tid, answer):
    """{label: (passed, detail)} for one task; the answer is whatever was in answer.json."""
    labels = common.load_labels(HIDDEN)
    if tid not in labels:
        return {"task known": (False, "unknown task id %s" % tid)}
    expected = labels[tid]["answer"]
    checks = {"answer is object": common.check_object(answer)}
    given = answer.get("category") if isinstance(answer, dict) else None
    category = norm_category(given)
    checks["category valid"] = (category in CATEGORIES, "one of %s expected, got %r" % (", ".join(CATEGORIES), given))
    checks["category correct"] = (category == expected["category"], "got %s, expected %s" % (category, expected["category"]))
    given_dup = answer.get("duplicate_of") if isinstance(answer, dict) else None
    dup, want = norm_hid(given_dup), norm_hid(expected["duplicate_of"])
    checks["duplicate_of correct"] = (dup == want, "got %s, expected %s" % (dup, want))
    return checks


def shortfall(tid, answer):
    """Failing checks only, as 'label: detail' strings."""
    return common.shortfall(grade(tid, answer))


if __name__ == "__main__":
    sys.exit(common.verifier_main(grade))
