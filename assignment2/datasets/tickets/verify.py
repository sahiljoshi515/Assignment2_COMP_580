"""Assignment 2 -- tickets/verify.py: is the resolution in answer.json the verified one?

Concept this file teaches: an agent's final message is a claim, not evidence. The
only thing graded is the file it wrote, compared with a label it never saw. A reused
answer that came from the wrong ticket fails here exactly like a wrong guess would,
which is what makes "incorrect reuse" a measurable quantity.

Design rules this file embodies:
  * Pure and deterministic: labels in, verdict out, no clock, no network, no model.
  * Never raise on bad input. A list, a string, a missing key or an unknown id each
    become a failed check with a reason; the runner must keep going.
  * Lenient on spelling, strict on meaning: R-7, r-07 and 7 are all R-07, but R-08 is
    simply wrong.

Run from the repo root:
    /usr/local/bin/python3.13 assignment2/datasets/tickets/verify.py --tid T-xxxxxx --answer answer.json
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common  # noqa: E402

HIDDEN = os.path.join(HERE, "hidden")
CATALOGUE_SIZE = 25


def grade(tid, answer):
    """{label: (passed, detail)} for one task; the answer is whatever was in answer.json."""
    labels = common.load_labels(HIDDEN)
    if tid not in labels:
        return {"task known": (False, "unknown task id %s" % tid)}
    expected = labels[tid]["answer"]["resolution_id"]
    checks = {"answer is object": common.check_object(answer)}
    given = answer.get("resolution_id") if isinstance(answer, dict) else None
    rid = common.norm_rid(given, "R", CATALOGUE_SIZE)
    checks["resolution_id valid"] = (rid is not None, "R-01..R-%d expected, got %r" % (CATALOGUE_SIZE, given))
    checks["resolution correct"] = (rid == expected, "got %s, expected %s" % (rid, expected))
    return checks


def shortfall(tid, answer):
    """Failing checks only, as 'label: detail' strings."""
    return common.shortfall(grade(tid, answer))


if __name__ == "__main__":
    sys.exit(common.verifier_main(grade))
