# Dataset `threads` — a shared mailbox where every reply quotes the thread

**What a scenario is.** An export of a team mailbox, `inbox/<nnn>_<subject>.eml`, 27–31
messages in date order with plain headers and a body. Three decision threads (a request,
a question, an answer, a concern, a decision, sometimes a correction of the decision,
sometimes thanks), each reply quoting the whole message it answers with `> ` prefixes;
8–11 nightly backup reports from a bot, fourteen near-identical lines each with the
date, the numbers and sometimes the status changed; two announcements.

**What a request is.** `final_decision <thread>` (approve / reject / defer, who decided,
on what date; a later correction overrides), `requester <thread>`, `message_count
<thread>`, `failed_backups` (the dates), `longest_backup` (date and minutes),
`first_failed_backup` (date and reason).

**What decides the answer.** The last decision message of a thread, the From header of
its first message, the number of its messages, and the Status and Duration lines of the
reports. The realistic mistake is to stop at the first decision.

**Two layers of repetition.** Requests repeat (40 % duplicates, 20 % hard negatives).
Inside a task the repetition is of two kinds, which is the point of this dataset: a
quoted block is the earlier message *exactly* (up to the `> ` prefixes, which
normalisation removes), so the layer's identical-text check folds it to one line; a
nightly report differs from the previous one in a few numbers, so it takes MinHash to see
the repeat. Whole-message Jaccard is only 0.72–0.84 because every reply adds a new body;
the folds happen chunk by chunk.

**When a previous answer is safe to reuse.** Same `scenario`, `kind` and `target`.

**Sizes and seed.** 24 scenarios (5.6K–7.3K tokens), 60 history records, 40 incoming
requests, seed 79, about 15K tokens in one task's working directory.

**Regenerate.**

```sh
/usr/local/bin/python3.13 assignment2/datasets/threads/generate.py
/usr/local/bin/python3.13 assignment2/datasets/threads/verify.py --tid T-xxxxxx --answer answer.json
```
