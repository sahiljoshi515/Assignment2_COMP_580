"""Assignment 2 -- hosts/verify.py: does answer.json name the host, package, kernel, mount or value the label does?

Concept this file teaches: the same as every verifier here -- an agent's final message is a
claim, the file it wrote is the evidence, and a reused answer copied from the wrong request
fails exactly like a wrong guess would. The checks are generic (corpus.grade): one check per
key of the labelled answer, strings compared on their letters and digits, numbers as numbers.

Run from the repo root:
    /usr/local/bin/python3.13 assignment2/datasets/hosts/verify.py --tid T-xxxxxx --answer answer.json
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common, corpus  # noqa: E402

HIDDEN = os.path.join(HERE, "hidden")


def grade(tid, answer):
    """{label: (passed, detail)} for one task; the answer is whatever was in answer.json."""
    return corpus.grade(HIDDEN, tid, answer)


def shortfall(tid, answer):
    return common.shortfall(grade(tid, answer))


if __name__ == "__main__":
    sys.exit(common.verifier_main(grade))
