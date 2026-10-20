"""Assignment 2 -- bugs: crash reports for one application, triaged to a component and a root cause.

Concept this file teaches: a bug report has a structured spine (exception, top frame, version)
and a free-text story, and the two carry different information. The component follows from the
module of the top frame alone; the root cause follows from the story told in the Actual section
(the *cue*) -- unless the release timeline says otherwise, because what a story means depends on
which release it happened on. A duplicate changes only the free parts (patch digit, operating
system, host, caller line numbers, wording, layout); a hard negative moves exactly one semantic
slot everywhere it appears -- the top frame (one line of the stacktrace, the title, the field),
the version series (the Environment line and the field), or the exception (title, last line of
the stacktrace, field) -- and so changes the answer.

Design rules this file embodies:
  * Data, not code, carries the domain: components, frames, caller chains, cues, the root-cause
    catalogue and the version override table are module-level constants that INSTRUCTIONS.md prints.
  * Cues are shared by every frame that raises the same exception. That is what makes a frame
    flip a near-identical record with a different owner, and it keeps the triage guide one table.
  * The validation rule (same exception, same frame, same version series) is necessary, not
    sufficient: the cue lives only in the text, so text similarity has to carry the last mile.
  * Everything above is a Spec for common.py; the stream, the transforms, the labels and the
    diagnostics are shared with the other three datasets.

Run from the repo root:  /usr/local/bin/python3.13 assignment2/datasets/bugs/generate.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common  # noqa: E402

APP = "Lattice"
SERIES = ["3.0", "3.1", "3.2", "3.3"]
OSES = ["Ubuntu 24.04 LTS", "Fedora 41 Workstation", "Windows 11 24H2", "macOS 15.3", "Debian 12", "Windows Server 2022"]
HOSTS = ["eu-west-2", "us-east-1", "ap-south-1", "eu-central-1", "us-west-2", "ca-central-1"]
FREQS = ["every time", "roughly one run in three", "twice this week", "on about half the runs",
         "once a day or so", "only on the first run after login"]

# module prefix -> owning component (longest prefix first is not needed: prefixes do not nest)
OWNERS = [("lattice.net.", "networking"), ("lattice.store.", "storage"), ("lattice.auth.", "auth"),
          ("lattice.ui.", "ui"), ("lattice.report.", "reporting"), ("lattice.io.", "importer"),
          ("lattice.sched.", "scheduler"), ("lattice.core.config.", "config"), ("lattice.core.settings.", "config")]
COMPONENTS = ["networking", "storage", "auth", "ui", "reporting", "importer", "scheduler", "config"]

ROOT_CAUSES = {
    "RC-01": "None dereference", "RC-02": "Off-by-one", "RC-03": "Race condition",
    "RC-04": "Missing or renamed configuration key", "RC-05": "Migration not applied",
    "RC-06": "Numeric precision", "RC-07": "Unhandled timeout", "RC-08": "Encoding mismatch",
    "RC-09": "Path separators", "RC-10": "Resource leak", "RC-11": "Stale cache",
    "RC-12": "Timezone handling", "RC-13": "Dependency API change", "RC-14": "Permission denied",
    "RC-15": "Memory exhaustion", "RC-16": "Regression from refactor",
    "RC-17": "Division by zero on empty input", "RC-18": "Deadlock", "RC-19": "Unvalidated input",
    "RC-20": "Certificate validation",
}

TIMELINE = [
    ("3.0.0", "baseline release of the 3.x line."),
    ("3.1.0", "upgraded the bundled HTTP client; the new client changed its API."),
    ("3.2.0", "replaced the storage engine; existing data directories need the engine migration."),
    ("3.3.0", "moved every configuration key under `core.*`; the old key names are no longer read."),
]

# (module prefix, version series, required cue tag or None, root cause that replaces the cue's)
OVERRIDES = [("lattice.net.", "3.1", "upgrade", "RC-13"),
             ("lattice.store.", "3.2", None, "RC-05"),
             ("lattice.core.", "3.3", None, "RC-04")]

# Caller chains shared by the frames below them: a frame flip inside a chain changes one line.
# callers: (file, function, base line number; the cosmetic offset moves it by -3..+3)
CHAINS = [
    {"name": "sync", "callers": [("lattice/ui/main.py", "loop", 48), ("lattice/sched/runner.py", "run_due", 131),
                                 ("lattice/store/remote.py", "sync_all", 77)],
     "actions": ["syncing the remote store", "running the nightly sync", "pushing local changes"]},
    {"name": "import", "callers": [("lattice/ui/main.py", "loop", 48), ("lattice/ui/dialog.py", "on_import", 90),
                                   ("lattice/io/batch.py", "run_import", 55)],
     "actions": ["importing a CSV file", "running a bulk import", "loading a spreadsheet"]},
    {"name": "report", "callers": [("lattice/ui/main.py", "loop", 48), ("lattice/report/schedule.py", "run_due", 66),
                                   ("lattice/report/builder.py", "build", 140)],
     "actions": ["exporting the monthly report", "sending a scheduled report", "building the summary"]},
    {"name": "login", "callers": [("lattice/ui/main.py", "loop", 48), ("lattice/ui/dialog.py", "on_login", 124),
                                  ("lattice/auth/flow.py", "start", 58)],
     "actions": ["signing in", "refreshing an expired session", "switching accounts"]},
    {"name": "schedule", "callers": [("lattice/ui/main.py", "loop", 48), ("lattice/sched/runner.py", "run_due", 131),
                                     ("lattice/sched/queue.py", "drain", 84)],
     "actions": ["running a scheduled job", "retrying a failed job", "starting the worker"]},
    {"name": "startup", "callers": [("lattice/cli.py", "main", 12), ("lattice/core/app.py", "start", 33),
                                    ("lattice/core/boot.py", "load_all", 102)],
     "actions": ["starting the application", "reloading the settings", "opening the preferences"]},
    {"name": "dashboard", "callers": [("lattice/ui/main.py", "loop", 48), ("lattice/ui/view.py", "refresh", 212),
                                      ("lattice/report/live.py", "tiles", 61)],
     "actions": ["opening the dashboard", "refreshing the overview", "resizing the main window"]},
    {"name": "upload", "callers": [("lattice/ui/main.py", "loop", 48), ("lattice/ui/upload.py", "on_drop", 37),
                                   ("lattice/io/upload.py", "send", 118)],
     "actions": ["uploading an attachment", "dragging a file into a record", "retrying a failed upload"]},
]

# (dotted top frame, chain index, [(exception class, message template), ...]); {host} is cosmetic
FRAMES = [
    ("lattice.net.http.fetch", 0, [("TimeoutError", "read timed out after 30s (host={host})"),
                                   ("ConnectionError", "connection reset by peer (host={host})")]),
    ("lattice.net.http.post", 0, [("TimeoutError", "write timed out after 30s (host={host})"),
                                  ("ConnectionError", "connection refused (host={host})")]),
    ("lattice.store.remote.sync", 0, [("TimeoutError", "sync did not finish within 30s (host={host})"),
                                      ("KeyError", "'revision'")]),
    ("lattice.auth.session.refresh", 0, [("ConnectionError", "token endpoint unreachable (host={host})"),
                                         ("KeyError", "'refresh_token'")]),
    ("lattice.store.blob.write", 0, [("OSError", "[Errno 28] No space left on device"),
                                     ("PermissionError", "[Errno 13] Permission denied: 'blobs/000a'")]),
    ("lattice.io.csv.parse", 1, [("UnicodeDecodeError", "'utf-8' codec can't decode byte 0xe9 in position 1042"),
                                 ("ValueError", "could not convert string to float: '1.234,56'")]),
    ("lattice.io.excel.read", 1, [("UnicodeDecodeError", "'utf-8' codec can't decode byte 0xff in position 0"),
                                  ("IndexError", "list index out of range")]),
    ("lattice.store.query.run", 1, [("KeyError", "'legacy_id'"),
                                    ("ValueError", "invalid literal for int() with base 10: ''")]),
    ("lattice.io.batch.commit", 1, [("OSError", "[Errno 24] Too many open files"),
                                    ("KeyError", "'batch_id'")]),
    ("lattice.ui.form.submit", 1, [("ValueError", "invalid date '2026-03-29 02:30'"),
                                   ("TypeError", "'NoneType' object is not subscriptable")]),
    ("lattice.report.pdf.export", 2, [("MemoryError", "unable to allocate 1.2 GiB for page buffer"),
                                      ("PermissionError", "[Errno 13] Permission denied: 'exports/2026-02.pdf'")]),
    ("lattice.report.summary.total", 2, [("ZeroDivisionError", "division by zero"),
                                         ("ValueError", "cannot convert float NaN to integer")]),
    ("lattice.store.index.rebuild", 2, [("MemoryError", "unable to allocate 3.1 GiB for index buffer"),
                                        ("LookupError", "unknown index 'by_owner'")]),
    ("lattice.ui.chart.draw", 2, [("ZeroDivisionError", "float division by zero"),
                                  ("TypeError", "unsupported operand type(s) for /: 'NoneType' and 'int'")]),
    ("lattice.report.template.fill", 2, [("KeyError", "'customer_name'"),
                                         ("LookupError", "unknown encoding: 'win-1252'")]),
    ("lattice.auth.token.verify", 3, [("ValueError", "token expired at 2026-02-01T00:00:00Z"),
                                      ("TypeError", "a bytes-like object is required, not 'str'")]),
    ("lattice.auth.oauth.callback", 3, [("KeyError", "'state'"),
                                        ("ConnectionError", "connection reset by peer (host={host})")]),
    ("lattice.net.tls.handshake", 3, [("ConnectionError", "certificate verify failed: self-signed certificate (host={host})"),
                                      ("TimeoutError", "handshake timed out after 30s (host={host})")]),
    ("lattice.auth.user.lookup", 3, [("KeyError", "'display_name'"),
                                     ("AttributeError", "'NoneType' object has no attribute 'roles'")]),
    ("lattice.ui.dialog.open", 3, [("TypeError", "'NoneType' object is not callable"),
                                   ("AttributeError", "'NoneType' object has no attribute 'show'")]),
    ("lattice.sched.runner.tick", 4, [("RuntimeError", "dictionary changed size during iteration"),
                                      ("TimeoutError", "job 'rollup' exceeded 30s")]),
    ("lattice.sched.queue.pop", 4, [("IndexError", "pop from empty list"),
                                    ("RuntimeError", "queue lock held by worker-2")]),
    ("lattice.sched.lock.acquire", 4, [("TimeoutError", "lock not acquired within 30s"),
                                       ("PermissionError", "[Errno 13] Permission denied: '/var/lock/lattice.lock'")]),
    ("lattice.report.schedule.send", 4, [("TimeoutError", "SMTP read timed out after 30s (host={host})"),
                                         ("RuntimeError", "send already in progress")]),
    ("lattice.core.config.watch", 4, [("RuntimeError", "cannot schedule new futures after shutdown"),
                                      ("PermissionError", "[Errno 13] Permission denied: '/etc/lattice/core.toml'")]),
    ("lattice.core.config.get", 5, [("KeyError", "'core.store.path'"),
                                    ("TypeError", "expected str, got NoneType")]),
    ("lattice.core.config.load", 5, [("FileNotFoundError", "[Errno 2] No such file or directory: 'conf\\core.toml'"),
                                     ("UnicodeDecodeError", "'utf-8' codec can't decode byte 0xff in position 0")]),
    ("lattice.core.settings.merge", 5, [("TypeError", "can only concatenate list (not 'NoneType') to list"),
                                        ("KeyError", "'settings.theme'")]),
    ("lattice.ui.theme.load", 5, [("FileNotFoundError", "[Errno 2] No such file or directory: 'themes\\dark.css'"),
                                  ("KeyError", "'ui.theme'")]),
    ("lattice.core.settings.validate", 5, [("ValueError", "port must be between 1 and 65535, got 0"),
                                           ("LookupError", "unknown encoding: 'utf8-sig'")]),
    ("lattice.ui.table.render", 6, [("IndexError", "list index out of range"),
                                    ("MemoryError", "unable to allocate 2.0 GiB for row cache")]),
    ("lattice.report.csv.write", 6, [("OSError", "[Errno 24] Too many open files"),
                                     ("MemoryError", "unable to allocate 1.5 GiB for export buffer")]),
    ("lattice.net.dns.resolve", 6, [("OSError", "[Errno 8] nodename nor servname provided (host={host})"),
                                    ("TimeoutError", "resolve timed out after 30s (host={host})")]),
    ("lattice.store.migrate.apply", 6, [("IndexError", "list index out of range"),
                                        ("OSError", "[Errno 28] No space left on device")]),
    ("lattice.sched.cron.parse", 6, [("ValueError", "invalid cron field '*/0'"),
                                     ("IndexError", "list index out of range")]),
    ("lattice.net.socket.connect", 7, [("ConnectionError", "connection refused (host={host})"),
                                       ("OSError", "[Errno 101] Network is unreachable (host={host})")]),
    ("lattice.auth.policy.check", 7, [("PermissionError", "upload denied for role 'viewer'"),
                                      ("AttributeError", "'NoneType' object has no attribute 'roles'")]),
    ("lattice.io.json.load", 7, [("ValueError", "Expecting value: line 1 column 1 (char 0)"),
                                 ("UnicodeDecodeError", "'utf-8' codec can't decode byte 0xff in position 0")]),
    ("lattice.io.path.resolve", 7, [("FileNotFoundError", "[Errno 2] No such file or directory: 'uploads\\2026\\scan.pdf'"),
                                    ("PermissionError", "[Errno 13] Permission denied: 'uploads/scan.pdf'")]),
    ("lattice.sched.job.retry", 7, [("TypeError", "unsupported operand type(s) for +: 'NoneType' and 'int'"),
                                    ("AttributeError", "'NoneType' object has no attribute 'attempts'")]),
]

# Cue sentence sets shared by several exceptions (the story is the same, only the exception differs).
UPGRADE_A1 = ["It fails on every attempt since the upgrade; the previous release never did this.",
              "Since upgrading, every attempt fails here.",
              "Every attempt has failed since we upgraded."]
UPGRADE_A2 = ["It began right after upgrading to this release; nothing else changed.",
              "This started immediately after upgrading, with no other change on the machine.",
              "Right after upgrading the behaviour changed; the same setup worked on the previous release."]
UPGRADE_STEPS = ["Upgrade from the previous release and keep the old settings.",
                 "Install this release over the previous one without changing settings.",
                 "Run the upgrade installer, then retry with the old configuration."]
NONE_A1 = ["The value is None where the code expects an object.",
           "A None turns up where an object was expected.",
           "The code receives None instead of the object it expected."]
NONE_A2 = ["It happens when the record has no owner set; records with an owner are fine.",
           "Records with no owner trigger it; those with an owner work.",
           "The affected records have no owner; setting one makes it work."]
NONE_STEPS = ["Create a record and leave the owner field empty.",
              "Clear the owner field of a record and save it.",
              "Use a record whose owner was never set."]
LAST_ROW_A1 = ["Every row works except the last row, which raises.",
               "All rows go through but the last row raises.",
               "Only the last row fails; the rest process normally."]
LAST_ROW_A2 = ["With one more line in the input the old last row is fine and the new last row fails instead.",
               "Adding a line moves the failure to the new last row.",
               "Whatever the input size, it is always the last row that fails."]
LAST_ROW_STEPS = ["Use an input with an odd number of rows.",
                  "Make sure the input ends without a trailing blank line.",
                  "Process a file with exactly 101 rows."]
BACKSLASH_A1 = ["The path in the error mixes slashes and backslashes.",
                "The failing path contains backslashes mixed with forward slashes.",
                "In the error the path has backslashes where slashes were expected."]
BACKSLASH_A2 = ["The path was copied from a Windows machine and contains backslashes.",
                "This path originates on Windows and uses backslashes.",
                "The settings came from a Windows colleague, so the path has backslashes."]
BACKSLASH_STEPS = ["Set a path containing backslashes in the settings.",
                   "Use a Windows-style path with backslashes.",
                   "Copy a path from a Windows machine into the settings."]
TWO_JOBS_A1 = ["The file is reported missing although it exists a moment later.",
               "The error says the file is gone, yet it is there right after.",
               "It reports a missing file that turns out to exist seconds later."]
TWO_JOBS_A2 = ["It only happens when two jobs touch the same folder at once.",
               "Two jobs writing the same folder at the same time trigger it.",
               "With two jobs running together on one folder it fails; one job alone is fine."]
TWO_JOBS_STEPS = ["Start two jobs on the same folder at the same time.",
                  "Run two jobs in parallel against one folder.",
                  "Launch a second job while the first still writes the folder."]


def cue(key, rc, a1, a2, steps, tag=None):
    """One story: `key` is the phrase the triage guide names, `tag` is what the override table tests."""
    return {"key": key, "rc": rc, "tag": tag, "a1": a1, "a2": a2, "steps": steps}


# CUES[exception] = stories shared by every frame that raises that exception
CUES = {
    "TimeoutError": [
        cue("slow network", "RC-07",
            ["The call waited exactly thirty seconds and then gave up with the traceback below.",
             "After exactly thirty seconds the operation aborted and printed the traceback.",
             "Thirty seconds of silence, then the traceback appeared and the job stopped."],
            ["The office is on a slow network link this month, yet nothing retries.",
             "We are on a slow network here; one slow reply and the whole job dies instead of retrying.",
             "A single slow network round trip is enough to kill the job; no retry happens."],
            ["Throttle the connection to a slow network profile (about 1 Mbit/s).",
             "Switch the network profile to the slow network preset before starting.",
             "Use the slow network simulator in the developer tools."]),
        cue("two workers", "RC-18",
            ["The call never returns until the thirty-second guard fires.",
             "It hangs for the full thirty seconds and only the guard timer ends it.",
             "Nothing happens for thirty seconds; the guard timer finally aborts it."],
            ["It only happens when two workers run at once; a single worker is fine.",
             "With two workers running at the same time it hangs; with one worker it never does.",
             "Two workers started together reproduce it; one worker alone works."],
            ["Start two workers at the same time.",
             "Launch a second worker while the first is busy.",
             "Run two workers side by side."]),
        cue("after upgrading", "RC-16", UPGRADE_A1, UPGRADE_A2, UPGRADE_STEPS, tag="upgrade"),
    ],
    "ConnectionError": [
        cue("under load", "RC-10",
            ["Connections start failing after a few hundred calls and recover only after a restart.",
             "After a few hundred calls every connection fails until the app is restarted.",
             "Once a few hundred calls have gone through, the connections fail until a restart."],
            ["It shows up under load; the connection count in the monitor keeps climbing and never drops.",
             "Under load the open-connection gauge climbs steadily and never comes back down.",
             "The monitor shows the number of open connections rising under load without ever falling."],
            ["Put the app under load with the stress script for five minutes.",
             "Run the stress script to generate load for about five minutes.",
             "Generate load with the stress script and watch the connection gauge."]),
        cue("after upgrading", "RC-16", UPGRADE_A1, UPGRADE_A2, UPGRADE_STEPS, tag="upgrade"),
        cue("self-signed", "RC-20",
            ["The connection is rejected before any data flows.",
             "The handshake is refused and no data is ever sent.",
             "It fails during the handshake, before any request goes out."],
            ["The server uses a self-signed certificate issued by our own CA.",
             "Our server presents a self-signed certificate from the internal CA.",
             "The endpoint runs with a self-signed certificate signed by the company CA."],
            ["Point the server URL at the staging host with the self-signed certificate.",
             "Configure the self-signed staging endpoint as the server.",
             "Use the internal staging server, which has a self-signed certificate."]),
    ],
    "KeyError": [
        cue("renamed", "RC-04",
            ["The lookup fails on a key that exists in the file under a different name.",
             "A key that was renamed in the settings file is what the lookup wants.",
             "The missing key is the old name of a setting that was renamed."],
            ["We renamed the key in the settings file following the release notes.",
             "Following the release notes we renamed that key in the settings file.",
             "The settings file uses the renamed key from the release notes."],
            ["Rename the key in the settings file as the release notes describe.",
             "Edit the settings file and use the renamed key.",
             "Apply the renamed key from the release notes to the settings file."]),
        cue("missing column", "RC-19",
            ["The failure names a field that the input file simply does not have.",
             "The missing key is a column that the input file lacks.",
             "It fails on a field absent from the input; the file has no such column."],
            ["The file came from a customer with a missing column and was accepted without a check.",
             "A customer file with a missing column was accepted without any validation.",
             "Nothing checked the customer file for the missing column before processing."],
            ["Use the customer file with the missing column (sample attached).",
             "Feed in the sample file that has the missing column.",
             "Process the attached sample, which lacks the column."]),
        cue("previous release", "RC-05",
            ["The lookup fails on a key that the previous release never stored.",
             "The missing key is one the previous release did not write.",
             "It wants a key that data from the previous release does not contain."],
            ["The database was created by the previous release and the migration step was skipped.",
             "This data directory dates from the previous release; the migration was never run.",
             "We skipped the migration when moving from the previous release."],
            ["Open a data directory created by the previous release without running the migration.",
             "Skip the migration step and open data from the previous release.",
             "Copy a data directory from the previous release and open it directly."]),
    ],
    "TypeError": [
        cue("no owner", "RC-01", NONE_A1, NONE_A2, NONE_STEPS),
        cue("after upgrading", "RC-16", UPGRADE_A1, UPGRADE_A2, UPGRADE_STEPS, tag="upgrade"),
        cue("last row", "RC-02", LAST_ROW_A1, LAST_ROW_A2, LAST_ROW_STEPS),
    ],
    "ValueError": [
        cue("decimal", "RC-06",
            ["The value that fails is a decimal with more digits than expected.",
             "It fails on a decimal value with many digits after the point.",
             "A long decimal is what trips it."],
            ["Amounts with more than six decimal places fail; shorter ones pass.",
             "Anything with over six decimal digits fails, fewer digits work.",
             "The decimal values that fail all have seven or more fractional digits."],
            ["Enter an amount with eight decimal places.",
             "Use a value such as 0.12345678.",
             "Paste a decimal with more than six digits after the point."]),
        cue("midnight", "RC-12",
            ["The rejected value is a timestamp close to midnight.",
             "It fails on a timestamp near midnight.",
             "A time just before midnight is what is rejected."],
            ["Our machines are set to a timezone ahead of UTC and the date flips at midnight.",
             "The machine runs in a timezone east of UTC, so the date changes at midnight local time.",
             "We are in a timezone ahead of UTC; around midnight the date differs from UTC."],
            ["Set the machine timezone to UTC+2.",
             "Change the system timezone to one ahead of UTC.",
             "Use a timestamp between 23:00 and 01:00 local time."]),
        cue("pasted", "RC-19",
            ["The value fails because it contains characters the field never checks for.",
             "It fails on input with characters that nothing validates.",
             "Unexpected characters in the value cause it; no check rejects them."],
            ["The text was pasted from a spreadsheet with stray characters and accepted as is.",
             "Someone pasted the value from a spreadsheet, stray characters included, and nothing complained.",
             "A pasted spreadsheet cell with stray characters went through unchecked."],
            ["Paste a value from a spreadsheet including a trailing space.",
             "Copy a cell with a non-breaking space and paste it into the field.",
             "Paste text with a stray character from a spreadsheet."]),
    ],
    "OSError": [
        cue("backslashes", "RC-09", BACKSLASH_A1, BACKSLASH_A2, BACKSLASH_STEPS),
        cue("long session", "RC-10",
            ["It fails only after the app has run for many hours.",
             "After a long session of several hours it starts failing.",
             "Only after hours of uptime does the failure appear."],
            ["The number of open files in the monitor climbs over a long session and never drops.",
             "During a long session the open file count grows steadily.",
             "A long session shows open files increasing without ever being released."],
            ["Leave the app running for a long session of at least six hours.",
             "Keep the application open overnight, then trigger the action.",
             "Run the app for a long session, then trigger the action."]),
        cue("two jobs", "RC-03", TWO_JOBS_A1, TWO_JOBS_A2, TWO_JOBS_STEPS),
    ],
    "PermissionError": [
        cue("service account", "RC-14",
            ["Access is denied on a file the app itself created.",
             "The app is denied access to a file it wrote earlier.",
             "Permission is refused on a file created by the app."],
            ["The app runs under a service account that is not the owner of the data directory.",
             "We run it as a service account; the data directory belongs to another user.",
             "The service account that runs the app does not own that directory."],
            ["Run the app under the service account instead of your own user.",
             "Start the application as the service account.",
             "Switch to the service account and launch the app."]),
        cue("still open", "RC-03",
            ["Access is denied for a moment and a retry seconds later works.",
             "The denial lasts a second or two; retrying afterwards succeeds.",
             "It is denied once, then the same action works on retry."],
            ["Another process still has the file open when the app tries to replace it.",
             "The file is still open in another process at the moment of the write.",
             "A second process holds the file still open while the app writes."],
            ["Keep the file still open in another program while triggering the action.",
             "Open the target file in a viewer, then trigger the action.",
             "Hold the file open elsewhere and retry."]),
    ],
    "MemoryError": [
        cue("large export", "RC-15",
            ["Memory climbs to several gigabytes within a minute and then it fails.",
             "Within a minute the process reaches several gigabytes and dies.",
             "Usage shoots past several gigabytes in under a minute before the failure."],
            ["It only happens with a large export of more than two years of data.",
             "A large export spanning over two years triggers it; smaller ranges work.",
             "Only a large export of two years or more runs out of memory."],
            ["Select a large export range of more than two years.",
             "Choose a date range covering over two years.",
             "Start a large export over the full history."]),
        cue("same input", "RC-10",
            ["Memory grows a little on every run of the same input and eventually fails.",
             "Each run of the same input leaves memory a bit higher until it fails.",
             "Repeating the same input makes memory creep up run after run."],
            ["The same input succeeds on a fresh start and fails after a few hours of repeats.",
             "A fresh start handles the same input fine; after hours of repeats it fails.",
             "The same input works at first and fails later in the session."],
            ["Repeat the same input every minute for a few hours.",
             "Run the same input in a loop for several hours.",
             "Trigger the action with the same input repeatedly."]),
    ],
    "RuntimeError": [
        cue("both waiting", "RC-18",
            ["The process freezes with two threads each waiting on the other.",
             "Two threads end up both waiting for each other and nothing moves.",
             "A thread dump shows two threads both waiting on locks held by the other."],
            ["It happens when a job and the UI refresh run at the same moment.",
             "Starting a job exactly during a UI refresh triggers it.",
             "The freeze coincides with a job starting while the UI is refreshing."],
            ["Trigger a UI refresh while a job is starting.",
             "Click refresh at the moment a job begins.",
             "Start a job and refresh the view at the same time."]),
        cue("after upgrading", "RC-16", UPGRADE_A1, UPGRADE_A2, UPGRADE_STEPS, tag="upgrade"),
        cue("while iterating", "RC-03",
            ["The failure happens while iterating over a list that another thread changes.",
             "It fails while iterating; another thread modifies the same list.",
             "While iterating the collection something else changes it."],
            ["It only shows up when a background job adds entries while the view is open.",
             "A background job adding entries while the view is open reproduces it.",
             "With a background job adding entries during the view it fails."],
            ["Keep the view open while a background job adds entries.",
             "Let a background job add entries while watching the list.",
             "Open the list and start a job that adds entries."]),
    ],
    "ZeroDivisionError": [
        cue("empty result", "RC-17",
            ["It fails only when the filter returns an empty result.",
             "An empty result set is what causes the failure.",
             "With an empty result it fails; any rows at all and it works."],
            ["The period we chose has no entries at all, so there is nothing to average.",
             "There are no entries in the selected period; the average has nothing to divide by.",
             "The chosen range is empty, so the average divides by nothing."],
            ["Select a period with no entries.",
             "Choose an empty date range.",
             "Filter so that no rows match."]),
        cue("rounds to zero", "RC-06",
            ["It fails on tiny values where the total rounds to zero.",
             "Very small values make the total round to zero before the division.",
             "When the total rounds to zero the division fails."],
            ["The amounts are fractions of a cent and are rounded before use.",
             "Our amounts are fractions of a cent; rounding happens too early.",
             "Values smaller than a cent get rounded to zero first."],
            ["Enter amounts below 0.005.",
             "Use values that are fractions of a cent.",
             "Load data with amounts under half a cent."]),
    ],
    "UnicodeDecodeError": [
        cue("Latin-1", "RC-08",
            ["The file fails on the first accented character.",
             "It fails as soon as an accented character shows up.",
             "The first accented name in the file breaks it."],
            ["The file was saved as Latin-1 by an older Windows tool.",
             "An older Windows tool wrote the file in Latin-1.",
             "The file is Latin-1 encoded, produced by an older Windows program."],
            ["Save the file as Latin-1 in a legacy editor.",
             "Export the file from the legacy tool, which writes Latin-1.",
             "Convert the file to Latin-1 before loading."]),
        cue("web form", "RC-19",
            ["The failing byte sits in a file that arrived through the web form.",
             "The bad byte is in a file uploaded via the web form.",
             "It fails on a file that came in through the web form."],
            ["The web form accepts any upload without checking its encoding.",
             "Nothing on the web form checks the encoding of an upload.",
             "The web form never validates the encoding of what is uploaded."],
            ["Upload a file with a byte order mark through the web form.",
             "Submit a Windows-encoded file via the web form.",
             "Use the web form to upload a file saved by Notepad."]),
    ],
    "LookupError": [
        cue("no longer exists", "RC-04",
            ["The name being looked up is one the settings file still mentions.",
             "The lookup wants a name that is only in the settings file.",
             "It looks up a name that comes straight from the settings."],
            ["That name no longer exists in this release; the settings file still uses the old one.",
             "The settings refer to a name that no longer exists in this version.",
             "The old name in the settings file no longer exists after the release."],
            ["Keep the settings file from the old installation.",
             "Use an old settings file with the retired name.",
             "Leave the retired name in the settings and start."]),
        cue("rebuild", "RC-11",
            ["The lookup fails right after an index rebuild and works after a restart.",
             "After a rebuild the lookup fails until the app is restarted.",
             "Following the rebuild it fails; a restart fixes it."],
            ["The in-memory table still holds entries from before the rebuild.",
             "Entries from before the rebuild are still cached in memory.",
             "The cache was not cleared by the rebuild and still has old entries."],
            ["Run the index rebuild, then trigger the action without restarting.",
             "Rebuild the index and immediately retry.",
             "Trigger a rebuild and use the view without a restart."]),
    ],
    "IndexError": [
        cue("last row", "RC-02", LAST_ROW_A1, LAST_ROW_A2, LAST_ROW_STEPS),
        cue("empty selection", "RC-19",
            ["It fails when the selection is empty.",
             "An empty selection triggers it.",
             "With nothing selected it raises."],
            ["Nothing validates that at least one item is selected before the action runs.",
             "The action runs even with an empty selection; no check stops it.",
             "No validation rejects an empty selection."],
            ["Clear the selection and run the action.",
             "Run the action with nothing selected.",
             "Deselect everything, then trigger it."]),
    ],
    "AttributeError": [
        cue("no owner", "RC-01", NONE_A1, NONE_A2, NONE_STEPS),
        cue("after upgrading", "RC-16", UPGRADE_A1, UPGRADE_A2, UPGRADE_STEPS, tag="upgrade"),
    ],
    "FileNotFoundError": [
        cue("backslashes", "RC-09", BACKSLASH_A1, BACKSLASH_A2, BACKSLASH_STEPS),
        cue("no longer exists", "RC-04",
            ["The missing path comes straight from the settings file.",
             "The path it cannot find is the one written in the settings.",
             "It looks for a path taken from the settings file."],
            ["That location no longer exists in this release; the settings still point at the old one.",
             "The settings point at a location that no longer exists in this version.",
             "The old location in the settings no longer exists after the release."],
            ["Keep the settings file from the old installation.",
             "Use an old settings file with the retired location.",
             "Leave the retired path in the settings and start."]),
        cue("two jobs", "RC-03", TWO_JOBS_A1, TWO_JOBS_A2, TWO_JOBS_STEPS),
    ],
}

TITLE = ["{exc} in {short} when {action}", "{exc} while {action} ({short})", "{short} raises {exc} when {action}"]
ENVIRONMENT = ["Lattice {version}, {os}, server {host}.", "Running Lattice {version} on {os} against {host}.",
               "Lattice version {version}; operating system {os}; server region {host}."]
STEPS_INTRO = ["Steps to reproduce:", "How to trigger it:", "To reproduce:"]
STEP_FIRST = ["Start by {action}.", "Open Lattice and begin {action}.", "With the log window open, start {action}."]
STEP_LAST = ["Watch the log for the traceback below.", "Wait for the failure and read the log.",
             "Check the log window; the traceback appears there."]
EXPECTED = ["Expected {action} to finish without errors.", "As on every earlier run, {action} should just complete.",
            "No traceback; {action} normally takes a few seconds."]
FREQUENCY = ["Happens {freq}.", "Reproduces {freq}.", "It occurs {freq}."]

SYNONYMS = {"happens": ["occurs"], "fails": ["breaks"], "every": ["each"], "started": ["began"],
            "shows": ["displays"], "machine": ["box"], "folder": ["directory"], "attempt": ["try"],
            "immediately": ["right away"], "several": ["multiple"], "nothing": ["not a thing"],
            "triggers": ["causes"], "works": ["succeeds"], "running": ["executing"], "restart": ["relaunch"],
            "hours": ["hrs"], "entries": ["items"], "colleague": ["coworker"], "normally": ["usually"],
            "below": ["beneath"], "minute": ["min"], "trigger": ["provoke"], "fine": ["okay"],
            "simply": ["just"], "whole": ["entire"], "only": ["solely"], "never": ["not once"],
            "always": ["invariably"], "same": ["identical"], "another": ["a different"], "still": ["yet"],
            "then": ["afterwards"], "moment": ["instant"], "seconds": ["secs"], "file": ["document"],
            "settings": ["configuration"], "release": ["version"], "data": ["records"], "value": ["figure"],
            "input": ["feed"], "log": ["journal"], "window": ["pane"], "start": ["kick off"],
            "action": ["operation"], "process": ["handle"],
            "selected": ["chosen"], "small": ["little"], "large": ["big"], "old": ["former"],
            "wait": ["pause"], "watch": ["observe"], "check": ["inspect"], "read": ["look at"],
            "behaviour": ["behavior"], "changed": ["altered"], "setup": ["set-up"], "worked": ["ran fine"],
            "without": ["with no"], "changing": ["altering"], "failure": ["error"], "traceback": ["stack trace"],
            "appears": ["shows up"], "twice": ["two times"], "runs": ["executions"], "second": ["other"],
            "exactly": ["precisely"], "attempts": ["tries"], "reproduce": ["replicate"], "monitor": ["gauge"]}


def component_of(frame):
    """Owner of a dotted frame by module prefix (lattice.core.config.* and .settings.* are config)."""
    for prefix, component in OWNERS:
        if frame.startswith(prefix):
            return component
    raise KeyError(frame)


def exception_name(canonical):
    return FRAMES[canonical["frame"]][2][canonical["exception"]][0]


def frame_path(frame):
    """lattice.net.http.fetch -> ('lattice/net/http.py', 'fetch')."""
    parts = frame.split(".")
    return "/".join(parts[:-1]) + ".py", parts[-1]


def top_line(frame_index):
    """The fixed line number of a top frame (callers move with the cosmetic offsets; this one never)."""
    return 40 + (frame_index * 53) % 260


class BugsSpec(common.Spec):
    NAME = "bugs"
    FILE = __file__
    HISTORY_FIELDS = ("hid", "exception", "top_frame", "version", "component", "root_cause", "title", "body",
                      "stacktrace", "reported")
    TASK_FIELDS = ("tid", "seq", "exception", "top_frame", "version", "title", "body", "stacktrace", "reported")
    DATE_FIELD = "reported"
    TASK_DATE_FIELD = "reported"
    UNITS = ("title", "environment", "steps_intro", "step_first", "step_cue", "step_last", "expected",
             "actual1", "actual2", "frequency")
    SYNONYMS = SYNONYMS
    MAX_HISTORY = 160
    MAX_INCOMING = 80
    DEFAULT_SEED = 23
    DEFAULT_DUP_RATE = 0.40
    DEFAULT_HISTORY = 120
    DEFAULT_INCOMING = 60
    TEXT_FOR_SIMILARITY = "title + body + stacktrace"

    def __init__(self):
        rng = common.sub_rng("bugs-pool")
        self._pool = [{"frame": f, "exception": e, "cue": c, "series": s}
                      for f, (_, _, excs) in enumerate(FRAMES) for e, (name, _) in enumerate(excs)
                      for c in range(len(CUES[name])) for s in SERIES]
        rng.shuffle(self._pool)

    def pool_size(self):
        return len(self._pool)

    def canonical_at(self, k):
        return dict(self._pool[k])

    def answer(self, canonical):
        frame = FRAMES[canonical["frame"]][0]
        story = CUES[exception_name(canonical)][canonical["cue"]]
        root_cause = story["rc"]
        for prefix, series, tag, override in OVERRIDES:
            if frame.startswith(prefix) and canonical["series"] == series and (tag is None or story["tag"] == tag):
                root_cause = override
        return {"component": component_of(frame), "root_cause": root_cause}

    def differs_in(self, canonical, other):
        """Compare the exception by name: the same class sits at different indexes in different frames."""
        a = dict(canonical, exception=exception_name(canonical))
        b = dict(other, exception=exception_name(other))
        return sorted(k for k in a if a[k] != b[k])

    def flip(self, rng, canonical):
        """Same-chain frame flips first (one stacktrace line moves), then series flips, then exception flips."""
        chain = FRAMES[canonical["frame"]][1]
        name = exception_name(canonical)
        frames = []
        for j, (_, chain_j, excs) in enumerate(FRAMES):
            names = [e for e, _ in excs]
            if j != canonical["frame"] and chain_j == chain and name in names:
                frames.append(dict(canonical, frame=j, exception=names.index(name)))
        rng.shuffle(frames)
        series = [dict(canonical, series=s) for s in SERIES if s != canonical["series"]]
        series = [c for c in series if self.answer(c) != self.answer(canonical)]
        rng.shuffle(series)
        exceptions = [dict(canonical, exception=e) for e, (other, _) in enumerate(FRAMES[canonical["frame"]][2])
                      if e != canonical["exception"] and canonical["cue"] < len(CUES[other])]
        rng.shuffle(exceptions)
        return frames + series + exceptions

    def cosmetic(self, rng):
        return {"patch": rng.randrange(0, 10), "os": rng.randrange(len(OSES)), "host": rng.randrange(len(HOSTS)),
                "lines": tuple(rng.randrange(-3, 4) for _ in range(3)),      # one build shifts all caller lines
                "action": rng.randrange(3), "freq": rng.randrange(len(FREQS))}

    def compose(self, state):
        c, v, cos = state["canonical"], state["variants"], state["cosmetic"]
        frame, chain_index, excs = FRAMES[c["frame"]]
        exc, message = excs[c["exception"]]
        story = CUES[exc][c["cue"]]
        chain = CHAINS[chain_index]
        path, func = frame_path(frame)
        slots = {"exc": exc, "short": ".".join(frame.split(".")[-2:]), "action": chain["actions"][cos["action"]],
                 "version": "%s.%d" % (c["series"], cos["patch"]), "os": OSES[cos["os"]], "freq": FREQS[cos["freq"]],
                 "host": HOSTS[cos["host"]]}
        lines = ["%s:%d in %s" % (file, base + cos["lines"][i], function)
                 for i, (file, function, base) in enumerate(chain["callers"])]
        lines.append("%s:%d in %s" % (path, top_line(c["frame"]), func))
        lines.append("%s: %s" % (exc, message.format(host=slots["host"])))
        steps = "\n".join([STEPS_INTRO[v["steps_intro"]], "- " + STEP_FIRST[v["step_first"]].format(**slots),
                           "- " + story["steps"][v["step_cue"]], "- " + STEP_LAST[v["step_last"]]])
        sections = [("Environment", ENVIRONMENT[v["environment"]].format(**slots)),
                    ("Steps", steps),
                    ("Expected", EXPECTED[v["expected"]].format(**slots)),
                    ("Actual", story["a1"][v["actual1"]] + " " + story["a2"][v["actual2"]]),
                    ("Frequency", FREQUENCY[v["frequency"]].format(**slots))]
        fields = {"exception": exc, "top_frame": frame, "version": slots["version"], "stacktrace": "\n".join(lines)}
        return {"fields": fields, "title": TITLE[v["title"]].format(**slots), "sections": sections}

    def recase_fields(self, fields, style):
        """Re-spell the structured fields the way another reporter's tooling would; tokens are untouched."""
        if style["fields"] == "lower":
            fields["top_frame"] = fields["top_frame"].lower()
            fields["version"] = "v" + fields["version"]
        elif style["fields"] == "compact":
            path, func = frame_path(fields["top_frame"])
            fields["top_frame"] = "%s::%s" % (path, func)
        return fields

    def protected(self, state):
        c = state["canonical"]
        frame = FRAMES[c["frame"]][0]
        story = CUES[exception_name(c)][c["cue"]]
        headers = ["Environment", "Steps", "Expected", "Actual", "Frequency"]
        return [exception_name(c)] + frame.split(".") + story["key"].split() + ["upgrading", "migration"] + headers

    def validation_tuple(self, record):
        return (str(record["exception"]).split(".")[-1].lower(), common.norm_frame(record["top_frame"]),
                common.norm_version(record["version"]))

    def text_for_similarity(self, record):
        return record["title"] + "\n" + record["body"] + "\n" + record["stacktrace"]

    def instructions(self):
        lines = ["# Bug triage for Lattice", "",
                 "You are the on-call triager for Lattice, a desktop application. One bug report is in `task.json`;",
                 "your job is to decide which component owns it and which root cause explains it, and to write",
                 "both to `answer.json`.", "",
                 "## Files in this directory", "",
                 "- `INSTRUCTIONS.md`: this file.",
                 "- `history.jsonl`: one JSON object per line, every one a closed, triaged report: fields `hid`,",
                 "  `exception`, `top_frame`, `version`, `component` and `root_cause` (the verified answers), `title`,",
                 "  `body`, `stacktrace`, `reported`.",
                 "- `task.json`: the report to triage: `tid`, `seq`, `exception`, `top_frame`, `version`, `title`,",
                 "  `body`, `stacktrace`, `reported`.", "",
                 "`history.jsonl` contains verified answers. If `task.json` describes the same underlying item as a",
                 "history record (the same bug, not merely a similar one), you may reuse that record's answer.",
                 "Before you do, check the fields under Validation below; near-identical records with a different",
                 "value there are different items with different answers.", "",
                 "## Component ownership", "",
                 "The component is decided by the module of the top frame of the stacktrace (the frame just above",
                 "the exception line; it is repeated in `top_frame`):", ""]
        owners = {}
        for prefix, component in OWNERS:
            owners.setdefault(component, []).append("`%s*`" % prefix)
        lines += ["- %s -> `%s`" % (" and ".join(prefixes), component) for component, prefixes in owners.items()]
        lines += ["", "## Root cause catalogue", ""]
        lines += ["- `%s`: %s" % (rid, text) for rid, text in ROOT_CAUSES.items()]
        lines += ["", "## Release timeline", ""]
        lines += ["- %s: %s" % (version, note) for version, note in TIMELINE]
        lines += ["", "## Triage guide", "",
                  "The exception names the failure; the two sentences in the Actual section that tell the story",
                  "behind it (the *cue*) decide the root cause. Find the exception below and match the story to one",
                  "of its cues; the same cue means the same root cause whichever frame raised it.", ""]
        for exc, stories in CUES.items():
            lines.append("**%s**" % exc)
            lines.append("")
            for story in stories:
                note = " (see the version rules)" if story["tag"] == "upgrade" else ""
                lines.append("- story mentions *%s* -> `%s`%s" % (story["key"], story["rc"], note))
            lines.append("")
        lines += ["Version rules (they replace the root cause from the table above):", ""]
        for prefix, series, tag, override in OVERRIDES:
            when = "story says *after upgrading*" if tag == "upgrade" else "whatever the story"
            reason = {"3.1": "the HTTP client upgrade", "3.2": "the storage engine swap", "3.3": "the key move"}[series]
            lines.append("- `%s*` frame on %s.x, %s -> `%s` (%s)." % (prefix, series, when, override, reason))
        lines += ["", "## How to decide a fresh report", "",
                  "- Read the top frame of the stacktrace: its module names the component.",
                  "- Find the exception block above and match the Actual section to one of its cues.",
                  "- Apply the version rules when the frame family and the version series both match.",
                  "- The operating system, host names, caller line numbers, the patch digit of the version, how",
                  "  often it happens and the wording carry no information.", "",
                  "## Validation (when is a history record the same bug?)", "",
                  "A history record can only be the same bug when `exception`, `top_frame` and the version series",
                  "match after normalisation: `lattice.net.http.fetch` and `lattice/net/http.py::fetch` are one frame",
                  "(line numbers are not part of it), and `3.1.2`, `v3.1.4` and `3.1.0` are all series `3.1`.",
                  "Matching fields are necessary, not sufficient: the same exception in the same frame on the same",
                  "series with a different story is a different bug with a different root cause.", "",
                  "## Output", "",
                  "Write `answer.json` in this directory:", "", "```json",
                  '{"component": "networking", "root_cause": "RC-13"}', "```", "",
                  "Ids are case-insensitive and `RC-7` equals `RC-07`. Component names are lower-case, with hyphens",
                  "where a name has spaces. Extra keys are ignored.", "",
                  "## Rules", "",
                  "- Do not modify `history.jsonl` or `task.json`; write nothing except `answer.json`.",
                  "- Only `answer.json` is graded. Your final message is not."]
        return "\n".join(lines) + "\n"


SPEC = BugsSpec()

if __name__ == "__main__":
    sys.exit(common.main(SPEC))
