"""Assignment 2 -- tickets: customer-support tickets with verified resolutions.

Concept this file teaches: the same problem arrives in many wordings, and almost the
same wording can be a different problem. A ticket's answer is decided by four hidden
slots -- product, error code, the scenario *cue* told in two sentences of the body,
and the platform -- while names, dates, patch numbers and phrasing are free to vary.
A duplicate changes only the free parts; a hard negative changes exactly one slot
(the platform, the error code under the same story, or the cue under the same code)
and so changes the resolution.

Design rules this file embodies:
  * Data, not code, carries the domain: products, codes, cues, the resolution catalogue
    and the override table are module-level constants that INSTRUCTIONS.md prints.
  * The validation rule is necessary, not sufficient. Same product, code and platform
    with a different cue is a different ticket; the cue lives only in the text, which
    is why text similarity has to carry the last mile and why an aggressive threshold
    merges what the fields alone cannot separate.
  * Everything above is a Spec for common.py; the stream, the transforms, the labels
    and the diagnostics are shared with the other three datasets.

Run from the repo root:  /usr/local/bin/python3.13 assignment2/datasets/tickets/generate.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common  # noqa: E402

PRODUCTS = ["SyncVault", "LedgerLine", "MeshMail", "PixelForge", "CourierOS", "Tallyboard"]
PLATFORMS = ["windows", "macos", "linux", "android"]
PLATFORM_FULL = {"windows": ["Windows 11 23H2", "Windows 11 24H2"], "macos": ["macOS 15.3", "macOS 14.7"],
                 "linux": ["Ubuntu 24.04", "Fedora 41"], "android": ["Android 15 (Pixel 8)", "Android 14 (Galaxy S23)"]}
PLATFORM_SHORT = {"windows": "Windows", "macos": "macOS", "linux": "Linux", "android": "Android"}
MAJOR = {"SyncVault": "4.2", "LedgerLine": "9.1", "MeshMail": "2.8", "PixelForge": "6.0", "CourierOS": "3.5",
         "Tallyboard": "1.9"}

# meaning -> (error text, short symptom, actions the customer was doing)
MEANINGS = [
    ("authentication token rejected", "token rejected", ["log in", "open the app"]),
    ("cannot write to data directory", "cannot write data directory", ["save my work", "open the app"]),
    ("TLS handshake failed", "TLS handshake failed", ["connect", "open the app"]),
    ("local database is locked", "database locked", ["open the app", "save my work"]),
    ("upload stalled at 0 bytes/s", "upload stalls", ["start a sync", "upload a file"]),
    ("storage quota exceeded", "quota exceeded", ["upload a file", "start a sync"]),
    ("application crashed on launch", "crash on launch", ["open the app", "log in"]),
    ("totals do not match source", "totals mismatch", ["export the report", "open the summary"]),
]

RESOLUTIONS = {
    "R-01": "Restart the application and retry",
    "R-02": "Sign out and sign in again to refresh the session",
    "R-03": "Clear the local cache",
    "R-04": "Roll back to the previous release",
    "R-05": "Install the latest update",
    "R-06": "Grant the app Full Disk Access / storage permission",
    "R-07": "Whitelist the service endpoints on the proxy or firewall",
    "R-08": "Rebuild the local index",
    "R-09": "Repair the local database with the built-in repair tool",
    "R-10": "Free space on the system drive",
    "R-11": "Disable the conflicting extension or add an antivirus exclusion",
    "R-12": "Correct the system clock and enable automatic time (NTP)",
    "R-13": "Repair ownership and permissions of the data directory",
    "R-14": "Increase the upload chunk timeout in Settings",
    "R-15": "Update the operating system to a supported release",
    "R-16": "Reset the locale and number-format settings",
    "R-17": "Assign or purchase additional storage quota",
    "R-18": "Enable TLS 1.2 in the system settings",
    "R-19": "Close the other instance that holds the database lock",
    "R-20": "Move the data directory to a local, non-network drive",
    "R-21": "Re-import the affected period and remove the duplicate batch",
    "R-22": "Restore the configuration file from the template",
    "R-23": "Clear the OAuth consent and grant access again",
    "R-24": "Move the data directory to a drive with free space",
    "R-25": "Reinstall the application",
}

# CUES[meaning][cue] = {"c1": 3 variants, "c2": 3 variants, "key": protected phrase,
#                       "res": default resolution, "over": {platform: resolution}}
CUES = [
    [   # M0 token rejected
        {"key": "password reset", "res": "R-02", "over": {"android": "R-23"},
         "c1": ["IT forced a password reset for everyone last week.",
                "Last week IT made everybody rotate their passwords.",
                "There was a company-wide forced password reset last week."],
         "c2": ["I changed mine on the laptop but the app never asked again.",
                "I did mine on this machine, yet the app never re-prompted.",
                "After changing it the app simply kept using the old session."]},
        {"key": "clock", "res": "R-12", "over": {},
         "c1": ["The laptop battery was swapped recently and the clock came back wrong.",
                "After a battery swap the system clock was off by several hours.",
                "The clock has been wrong since the battery was replaced."],
         "c2": ["Websites complain about certificates too, so it might be related.",
                "The browser also warns about certificate dates on some sites.",
                "Other apps show date warnings as well, which seems connected."]},
        {"key": "office network", "res": "R-07", "over": {},
         "c1": ["It only happens on the office network; on my phone's hotspot it works.",
                "On the hotspot everything works, on the office network it fails.",
                "The failure is specific to the office network, the hotspot is fine."],
         "c2": ["IT installed a new web proxy for all staff this month.",
                "A new corporate proxy went live for the whole staff this month.",
                "Our IT rolled out a new proxy to every desk this month."]},
        {"key": "shared account", "res": "R-25", "over": {"android": "R-23"},
         "c1": ["We moved this seat from a shared account to a personal one.",
                "The seat was migrated from a shared team account to my own.",
                "This login used to be a shared account and became a personal one."],
         "c2": ["Since the migration the app keeps the old account name in the title bar.",
                "The title bar still shows the old shared account after the move.",
                "Even after the switch the old account name is shown in the window title."]},
        {"key": "single sign-on", "res": "R-23", "over": {"linux": "R-02"},
         "c1": ["Our company switched the login to single sign-on this month.",
                "This month the organisation moved everyone to single sign-on.",
                "Single sign-on was rolled out for all staff this month."],
         "c2": ["The browser login works, only the app keeps rejecting me.",
                "I can log in through the browser; only the app refuses.",
                "Logging in on the website works, the app does not."]},
    ],
    [   # M1 cannot write to data directory
        {"key": "OS upgrade", "res": "R-13", "over": {"macos": "R-06", "windows": "R-11", "android": "R-06"},
         "c1": ["This began right after the operating system upgrade last weekend.",
                "The problem started immediately after last weekend's OS upgrade.",
                "It appeared the morning after the operating system was upgraded."],
         "c2": ["A permission prompt may have been dismissed during the upgrade.",
                "Possibly a permissions prompt was clicked away during the upgrade.",
                "I suspect an access prompt was dismissed while the upgrade ran."]},
        {"key": "disk nearly full", "res": "R-24", "over": {"windows": "R-10", "android": "R-10"},
         "c1": ["The system drive is nearly full, under one gigabyte left.",
                "There is less than a gigabyte free on the system drive.",
                "My system drive has almost no free space left, under a gigabyte."],
         "c2": ["Other programs have started complaining about space as well.",
                "Other applications also warn about low disk space now.",
                "Low-space warnings show up in other programs too."]},
        {"key": "network share", "res": "R-20", "over": {},
         "c1": ["The data directory lives on a network share mapped by IT.",
                "Our data folder is on a mapped network share, not the local disk.",
                "IT keeps the data directory on a network share mounted at login."],
         "c2": ["The share sometimes reconnects late after the machine wakes up.",
                "After sleep the share takes a while to reconnect.",
                "When the machine wakes, the mapped share reconnects slowly."]},
        {"key": "antivirus", "res": "R-11", "over": {},
         "c1": ["Our new antivirus suite was installed company-wide on Monday.",
                "A new antivirus product was pushed to every machine on Monday.",
                "Since Monday a new endpoint protection suite runs on all PCs."],
         "c2": ["Its log shows the app's data folder being scanned constantly.",
                "The antivirus log lists the data folder in a scan every minute.",
                "Looking at its log, the data directory is scanned nonstop."]},
        {"key": "read-only", "res": "R-13", "over": {"windows": "R-11", "android": "R-06"},
         "c1": ["The data folder is marked read-only after a restore from backup.",
                "After restoring from a backup the data folder came back read-only.",
                "A backup restore left the data folder flagged read-only."],
         "c2": ["I can open files from it but nothing can be saved into it.",
                "Reading files from it works, saving into it does not.",
                "Files open fine from there, but no save ever succeeds."]},
    ],
    [   # M2 TLS handshake failed
        {"key": "firewall appliance", "res": "R-07", "over": {},
         "c1": ["IT replaced the firewall appliance over the weekend.",
                "A new firewall appliance was installed at the weekend.",
                "The office got a new firewall appliance last weekend."],
         "c2": ["Several other tools lost their connections at the same time.",
                "Other tools in the office stopped connecting at the same moment.",
                "A few other applications lost connectivity at the same time."]},
        {"key": "old release", "res": "R-15", "over": {"windows": "R-18"},
         "c1": ["This machine still runs a release from several years ago.",
                "The operating system on this box is several years old.",
                "We never upgraded this machine; the OS release is years old."],
         "c2": ["The vendor's website says that release left support last year.",
                "According to the vendor that release went out of support last year.",
                "The vendor lists that release as unsupported since last year."]},
        {"key": "clock", "res": "R-12", "over": {},
         "c1": ["The system clock is wrong after a motherboard battery failure.",
                "A dead motherboard battery reset the system clock to a wrong date.",
                "The clock shows a wrong date since the motherboard battery died."],
         "c2": ["The login page in the browser also shows a certificate warning.",
                "My browser shows a certificate warning on the login page as well.",
                "The web login throws a certificate warning too."]},
        {"key": "inspection", "res": "R-05", "over": {"android": "R-25"},
         "c1": ["Our security team enabled TLS inspection on the corporate proxy.",
                "The security team switched on TLS inspection at the proxy.",
                "TLS inspection was turned on by our security team this week."],
         "c2": ["Release notes mention the new version trusts the corporate root certificate.",
                "The changelog says the newest version supports the corporate root certificate.",
                "The latest release notes talk about corporate root certificate support."]},
        {"key": "captive portal", "res": "R-01", "over": {},
         "c1": ["I am on hotel wifi that shows a sign-in page before letting traffic through.",
                "The hotel wifi here puts a sign-in page in front of every connection.",
                "This hotel network intercepts connections with a sign-in page."],
         "c2": ["Once the page is accepted the browser works, the app still fails.",
                "After accepting the page the browser is fine but the app keeps failing.",
                "The browser works after the sign-in page; the app does not recover."]},
    ],
    [   # M3 local database is locked
        {"key": "two instances", "res": "R-19", "over": {"android": "R-01"},
         "c1": ["I think a second copy of the app is still running in the background.",
                "There seems to be another copy of the app running in the background.",
                "A second instance of the app may still be open in the background."],
         "c2": ["The tray icon shows twice after I log in.",
                "After login the tray icon appears two times.",
                "Two tray icons show up once I am logged in."]},
        {"key": "crash", "res": "R-09", "over": {"android": "R-25"},
         "c1": ["The app crashed hard yesterday while it was saving.",
                "Yesterday the app crashed in the middle of a save.",
                "There was a hard crash yesterday during a save."],
         "c2": ["Since then it refuses to open the database at all.",
                "From that moment on the database will not open.",
                "Ever since, the database does not open any more."]},
        {"key": "network drive", "res": "R-20", "over": {},
         "c1": ["The database file is kept on a network drive shared by the team.",
                "Our team keeps the database file on a shared network drive.",
                "The database lives on a network drive that the whole team uses."],
         "c2": ["A colleague mentioned the drive dropped out for a minute this morning.",
                "A colleague said the drive briefly disconnected this morning.",
                "Someone on the team saw the drive go offline for a minute today."]},
        {"key": "backup", "res": "R-01", "over": {"android": "R-03"},
         "c1": ["The nightly backup job runs at the same time as my first login.",
                "Our backup job runs nightly exactly when I sign in for the day.",
                "The scheduled backup overlaps with my morning login time."],
         "c2": ["If I wait ten minutes and open the app again it works.",
                "Waiting ten minutes and opening it again makes it work.",
                "After about ten minutes a second attempt opens fine."]},
        {"key": "sync tool", "res": "R-20", "over": {"android": "R-01"},
         "c1": ["A desktop sync tool mirrors my home folder, including the app's data.",
                "My home folder, app data included, is mirrored by a desktop sync tool.",
                "A file-sync tool continuously mirrors the folder that holds the app data."],
         "c2": ["The lock appears whenever that tool is uploading changes.",
                "Whenever the sync tool uploads something the lock shows up.",
                "The error coincides with the sync tool pushing changes."]},
    ],
    [   # M4 upload stalled
        {"key": "large files", "res": "R-14", "over": {},
         "c1": ["It only happens with large files, anything above a few hundred megabytes.",
                "Large files, above a few hundred megabytes, are the ones that stall.",
                "Small files go through; files of several hundred megabytes stall."],
         "c2": ["Our connection is a slow upstream line in a rural office.",
                "The office has a slow upstream connection, we are quite rural.",
                "Upstream bandwidth here is poor, it is a rural site."]},
        {"key": "VPN", "res": "R-07", "over": {},
         "c1": ["It started when I began working from home over the VPN.",
                "The stalls began once I started using the VPN from home.",
                "Since I work from home through the VPN the uploads stall."],
         "c2": ["In the office, without the VPN, uploads finish normally.",
                "Without the VPN, at the office, everything uploads fine.",
                "On the office network with no VPN the uploads complete."]},
        {"key": "interrupted", "res": "R-08", "over": {"android": "R-03"},
         "c1": ["A sync was interrupted by a power cut halfway through last week.",
                "Last week a power cut interrupted a sync in the middle.",
                "There was a power failure during a sync last week."],
         "c2": ["Since then the progress bar sits at the same file forever.",
                "The progress bar has been stuck on the same file since then.",
                "Ever since, it stops at the same file every time."]},
        {"key": "update", "res": "R-03", "over": {},
         "c1": ["This started right after the app updated itself on Tuesday.",
                "The stalls began immediately after Tuesday's automatic update.",
                "Right after the self-update on Tuesday the uploads began stalling."],
         "c2": ["Before the update the same files synced within minutes.",
                "The very same files synced in minutes before the update.",
                "Those files used to sync in a few minutes before the update."]},
        {"key": "battery saver", "res": "R-22", "over": {"android": "R-05"},
         "c1": ["The machine's power profile was switched to the battery-saver preset.",
                "Power management was set to the battery-saver profile recently.",
                "Recently the power settings were changed to the battery-saver preset."],
         "c2": ["Uploads stall as soon as the screen turns off.",
                "The moment the screen goes dark the upload stops moving.",
                "Every time the display switches off the upload freezes."]},
    ],
    [   # M5 storage quota exceeded
        {"key": "team plan", "res": "R-17", "over": {},
         "c1": ["Our team plan was sized for ten people and we are now twenty.",
                "The team plan was bought for ten seats; we have twenty people now.",
                "We doubled the team to twenty but the plan is still the ten-person one."],
         "c2": ["The admin console shows the pool at one hundred percent.",
                "In the admin console the storage pool reads one hundred percent.",
                "The console reports the shared pool completely full."]},
        {"key": "cache", "res": "R-03", "over": {},
         "c1": ["The app's cache folder has grown to many gigabytes on this machine.",
                "On this machine the cache folder is now many gigabytes large.",
                "The local cache folder has ballooned to several gigabytes."],
         "c2": ["Our actual files are only a fraction of that size.",
                "The files we really store are a fraction of that.",
                "Our real data is far smaller than the cache."]},
        {"key": "plan change", "res": "R-02", "over": {},
         "c1": ["We upgraded the plan yesterday but the app still shows the old limit.",
                "The plan was upgraded yesterday; the app still displays the old quota.",
                "Yesterday's plan upgrade is not reflected, the old limit is still shown."],
         "c2": ["The web console already shows the new allowance.",
                "In the web console the new allowance is already visible.",
                "The website shows the new allowance correctly."]},
        {"key": "duplicate batch", "res": "R-21", "over": {},
         "c1": ["An import was run twice by mistake and every record doubled.",
                "Somebody ran the import twice and all records now appear twice.",
                "A duplicate import run doubled every record in the account."],
         "c2": ["The duplicates alone fill most of the quota.",
                "Those duplicates take up most of the quota on their own.",
                "Most of the quota is consumed by the duplicated records."]},
        {"key": "shared folder", "res": "R-17", "over": {"android": "R-02"},
         "c1": ["A folder shared with us by a partner company counts against our quota.",
                "Our quota includes a large folder a partner company shared with us.",
                "A partner's shared folder is being counted towards our own quota."],
         "c2": ["Their folder alone is larger than our whole plan.",
                "That shared folder by itself exceeds our entire plan.",
                "The partner's folder is bigger than our plan allows."]},
    ],
    [   # M6 application crashed on launch
        {"key": "right after updating", "res": "R-04", "over": {},
         "c1": ["It crashes since the update that installed itself this morning.",
                "Since this morning's automatic update the app crashes on start.",
                "The crash began with the update that ran this morning."],
         "c2": ["Nothing else on the machine changed.",
                "No other change was made to the machine.",
                "Everything else on the machine is as it was."]},
        {"key": "extension", "res": "R-11", "over": {"android": "R-25"},
         "c1": ["I installed a third-party extension for the app yesterday.",
                "Yesterday I added a third-party extension to the app.",
                "A third-party extension went in yesterday."],
         "c2": ["The crash report mentions the extension's plugin file.",
                "The crash dialog names the extension's plugin file.",
                "The plugin file of that extension appears in the crash report."]},
        {"key": "config file", "res": "R-22", "over": {"android": "R-25"},
         "c1": ["I edited the configuration file by hand to change the port.",
                "The configuration file was edited manually to switch the port.",
                "To change the port I hand-edited the config file."],
         "c2": ["The crash started on the very next launch.",
                "It has crashed on every launch since that edit.",
                "The next launch after the edit crashed and so did every later one."]},
        {"key": "graphics driver", "res": "R-05", "over": {"android": "R-25"},
         "c1": ["The machine got a new graphics driver through the vendor tool.",
                "A new graphics driver was installed through the vendor's updater.",
                "The vendor updater installed a fresh graphics driver."],
         "c2": ["The release notes of the newest app version mention a driver fix.",
                "The newest app version's release notes list a driver-related fix.",
                "A fix for that driver is mentioned in the latest release notes."]},
        {"key": "display scaling", "res": "R-05", "over": {"linux": "R-22"},
         "c1": ["It started after I set the display scaling to 150 percent.",
                "Changing the display scaling to 150 percent is when it began.",
                "The crashes date from setting display scaling to 150 percent."],
         "c2": ["With scaling back at 100 percent the app opens normally.",
                "Restoring 100 percent scaling makes the app open again.",
                "At 100 percent scaling there is no crash."]},
    ],
    [   # M7 totals mismatch
        {"key": "regional format", "res": "R-16", "over": {},
         "c1": ["I switched the system regional format to one that uses comma decimals.",
                "The regional format on the system was changed to comma decimals.",
                "We changed the machine's regional format to comma decimal separators."],
         "c2": ["Since then thousands and decimals look swapped in the totals.",
                "The totals now seem to swap thousands and decimals.",
                "Thousands separators and decimals appear exchanged in the totals."]},
        {"key": "imported twice", "res": "R-21", "over": {},
         "c1": ["The same period was imported twice by two colleagues.",
                "Two colleagues imported the identical period independently.",
                "One period was imported two times by different people."],
         "c2": ["The totals are almost exactly double the source.",
                "Our totals come out at about twice the source figures.",
                "The reported totals are roughly double the source values."]},
        {"key": "rounding", "res": "R-05", "over": {},
         "c1": ["The mismatch is a few cents per line, always rounding differences.",
                "Each line is off by a few cents, clearly a rounding issue.",
                "Every line differs by a cent or two, which looks like rounding."],
         "c2": ["The release notes mention a rounding fix in the newest version.",
                "A rounding fix is listed in the newest version's release notes.",
                "The latest changelog talks about a fix for rounding."]},
        {"key": "stale cache", "res": "R-08", "over": {"android": "R-03"},
         "c1": ["The summary screen shows figures from last month, not the current ones.",
                "The summary still reflects last month's figures instead of this month's.",
                "On the summary page the numbers are last month's, not today's."],
         "c2": ["Opening the raw records shows the right values.",
                "The raw records themselves show the correct values.",
                "If I open the underlying records the values are correct."]},
        {"key": "time zone", "res": "R-16", "over": {"android": "R-02"},
         "c1": ["The totals shifted when my laptop changed time zone during travel.",
                "After travelling across time zones the totals moved by a day.",
                "A time-zone change on the laptop shifted the daily totals."],
         "c2": ["Transactions near midnight land on the wrong day.",
                "Entries close to midnight show up under the neighbouring day.",
                "Anything booked around midnight falls on the wrong date."]},
    ],
]

# sibling code flips: same story under a different error code, different resolution
SIBLINGS = {(4, 3): [(6, 0)], (6, 0): [(4, 3)], (7, 2): [(6, 3)], (6, 3): [(7, 2)], (0, 1): [(2, 2)], (2, 2): [(0, 1)]}

GREETING = ["Hi, I'm using {product} {version} on {platform_full}.",
            "Hello support team. We run {product} {version} on {platform_full}.",
            "Good morning. My setup is {product} {version}, {platform_full}."]
SYMPTOM = ['Since {when}, every time I {action}, I get "{code}: {error}".',
           'Whenever I {action} since {when}, the app shows "{code}: {error}".',
           'Starting {when}, the moment I {action} a dialog reads "{code}: {error}".']
TRIED = ["I've already tried {tried}, which changed nothing.",
         "What I tried so far: {tried}. No luck.",
         "Before writing in I tried {tried}; same error afterwards."]
SIGNOFF = ["Thanks, {name} ({company})", "Regards, {name}, {company}", "{name} - {company}. Appreciate any pointers."]

WHEN = ["Monday", "Tuesday", "last week", "yesterday", "this morning", "the weekend"]
TRIED_POOL = ["restarting the machine", "waiting a day", "searching the help centre", "logging out of my browser",
              "rebooting the router", "closing every other program"]
NAMES = ["Priya Nair", "Tomas Vik", "Aisha Bello", "Daniel Ortega", "Mei Lin", "Jonas Berg", "Fatima Zahra",
         "Luca Moretti", "Hannah Cole", "Omar Haddad", "Sofia Rossi", "Kenji Sato", "Grace Okafor", "Ivan Petrov"]
COMPANIES = ["Halden Logistics", "Brightwater Clinics", "Ferro & Sons", "Northbank Studio", "Caldera Foods",
             "Oakline Partners", "Meridian Schools", "Tessa Labs", "Harbour Freight", "Pinewood Legal"]

SYNONYMS = {"every": ["each"], "shows": ["displays"], "tried": ["attempted"], "changed": ["altered"],
            "nothing": ["not a thing"], "machine": ["computer"], "started": ["began"], "mentioned": ["said"],
            "works": ["runs fine"], "fails": ["breaks"], "folder": ["directory"], "recently": ["lately"],
            "yesterday": ["the day before"], "morning": ["forenoon"], "installed": ["set up"], "several": ["multiple"],
            "complain": ["warn"], "happens": ["occurs"], "pointers": ["hints"], "support": ["help desk"]}


def code_for(product_index, meaning):
    return "E-%d%03d" % (product_index + 1, (100 + 37 * meaning + 11 * product_index) % 1000)


class TicketsSpec(common.Spec):
    NAME = "tickets"
    FILE = __file__
    HISTORY_FIELDS = ("hid", "product", "error_code", "platform", "resolution_id", "subject", "body", "opened")
    TASK_FIELDS = ("tid", "seq", "product", "error_code", "platform", "subject", "body", "opened")
    DATE_FIELD = "opened"
    TASK_DATE_FIELD = "opened"
    UNITS = ("greeting", "symptom", "cue1", "cue2", "tried", "signoff")
    SYNONYMS = SYNONYMS
    MAX_HISTORY = 400
    MAX_INCOMING = 80
    DEFAULT_SEED = 11
    DEFAULT_DUP_RATE = 0.40
    DEFAULT_HISTORY = 140
    DEFAULT_INCOMING = 70
    TEXT_FOR_SIMILARITY = "subject + body"

    def __init__(self):
        rng = common.sub_rng("tickets-pool")
        self._pool = [{"product": p, "meaning": m, "cue": c, "platform": pl}
                      for p in range(len(PRODUCTS)) for m in range(len(MEANINGS))
                      for c in range(len(CUES[m])) for pl in PLATFORMS]
        rng.shuffle(self._pool)

    def pool_size(self):
        return len(self._pool)

    def canonical_at(self, k):
        return dict(self._pool[k])

    def answer(self, canonical):
        cue = CUES[canonical["meaning"]][canonical["cue"]]
        return {"resolution_id": cue["over"].get(canonical["platform"], cue["res"])}

    def flip(self, rng, canonical):
        """Platform flips first (the text barely changes), then sibling codes, then cue flips."""
        platforms = [dict(canonical, platform=p) for p in PLATFORMS if p != canonical["platform"]]
        rng.shuffle(platforms)
        siblings = [dict(canonical, meaning=m, cue=c) for m, c in SIBLINGS.get((canonical["meaning"], canonical["cue"]), [])]
        cues = [dict(canonical, cue=c) for c in range(len(CUES[canonical["meaning"]])) if c != canonical["cue"]]
        rng.shuffle(cues)
        return platforms + siblings + cues

    def cosmetic(self, rng):
        return {"name": common.pick(rng, NAMES), "company": common.pick(rng, COMPANIES),
                "patch": rng.randrange(0, 9), "when": common.pick(rng, WHEN),
                "tried": common.pick(rng, TRIED_POOL), "platform_variant": rng.randrange(2),
                "action_variant": rng.randrange(2)}

    def compose(self, state):
        c, v, cos = state["canonical"], state["variants"], state["cosmetic"]
        product = PRODUCTS[c["product"]]
        error, short, actions = MEANINGS[c["meaning"]]
        cue = CUES[c["meaning"]][c["cue"]]
        slots = {"product": product, "version": "%s.%d" % (MAJOR[product], cos["patch"]),
                 "platform_full": PLATFORM_FULL[c["platform"]][cos["platform_variant"]],
                 "when": cos["when"], "action": actions[cos["action_variant"]],
                 "code": code_for(c["product"], c["meaning"]), "error": error,
                 "tried": cos["tried"], "name": cos["name"], "company": cos["company"]}
        para1 = GREETING[v["greeting"]].format(**slots) + " " + SYMPTOM[v["symptom"]].format(**slots)
        para2 = cue["c1"][v["cue1"]] + " " + cue["c2"][v["cue2"]]
        para3 = TRIED[v["tried"]].format(**slots)
        para4 = SIGNOFF[v["signoff"]].format(**slots)
        fields = {"product": product, "error_code": slots["code"], "platform": c["platform"],
                  "subject": "%s: %s on %s" % (slots["code"], short, PLATFORM_SHORT[c["platform"]])}
        return {"fields": fields, "title": "", "sections": [("", para1), ("", para2), ("", para3), ("", para4)]}

    def recase_fields(self, fields, style):
        if style["fields"] == "lower":
            fields["product"] = fields["product"].lower()
            fields["error_code"] = fields["error_code"].lower()
        elif style["fields"] == "compact":
            fields["error_code"] = fields["error_code"].replace("-", "")
        return fields

    def protected(self, state):
        c = state["canonical"]
        error, _, _ = MEANINGS[c["meaning"]]
        return [PRODUCTS[c["product"]], code_for(c["product"], c["meaning"])] + error.split() + \
            CUES[c["meaning"]][c["cue"]]["key"].split() + ["hotspot", "proxy", "VPN", "update", "clock"]

    def validation_tuple(self, record):
        return (common.norm_text(record["product"]), common.norm_code(record["error_code"]),
                common.norm_text(record["platform"]))

    def text_for_similarity(self, record):
        return record["subject"] + "\n" + record["body"]

    def instructions(self):
        lines = ["# Support ticket resolution", "",
                 "You are a support engineer. One ticket is in `task.json`; your job is to decide which catalogue",
                 "resolution applies and write it to `answer.json`.", "",
                 "## Files in this directory", "",
                 "- `INSTRUCTIONS.md`: this file.",
                 "- `history.jsonl`: one JSON object per line, every one a closed, verified ticket: fields `hid`,",
                 "  `product`, `error_code`, `platform`, `resolution_id` (the verified answer), `subject`, `body`, `opened`.",
                 "- `task.json`: the ticket to resolve: `tid`, `seq`, `product`, `error_code`, `platform`, `subject`,",
                 "  `body`, `opened`.", "",
                 "`history.jsonl` contains verified answers. If `task.json` describes the same underlying item as a",
                 "history record (the same ticket, not merely a similar one), you may reuse that record's answer.",
                 "Before you do, check the fields under Validation below; near-identical records with a different",
                 "value there are different items with different answers.", "",
                 "## Resolution catalogue", ""]
        lines += ["- `%s`: %s" % (rid, text) for rid, text in RESOLUTIONS.items()]
        lines += ["", "## Resolution guide", "",
                  "The error code names the symptom; the two sentences in the body that tell the story behind it",
                  "(the *cue*) decide the fix. Codes are product-specific; the symptom they carry is listed first.", ""]
        for m, (error, _, _) in enumerate(MEANINGS):
            codes = ", ".join(code_for(p, m) for p in range(len(PRODUCTS)))
            lines.append("**%s** (%s)" % (error, codes))
            lines.append("")
            for cue in CUES[m]:
                over = "; ".join("%s: `%s`" % (PLATFORM_SHORT[p], r) for p, r in sorted(cue["over"].items()))
                lines.append("- story mentions *%s* -> `%s`%s" % (cue["key"], cue["res"], (" (except " + over + ")") if over else ""))
            lines.append("")
        lines += ["## How to decide a fresh ticket", "",
                  "- Find the error code's symptom block above, then match the story in the body to one of its cues.",
                  "- Apply the platform exception if the ticket's `platform` is listed for that cue.",
                  "- The customer's own attempts (restarting, waiting, searching) never change the answer.",
                  "- Names, dates, version patch numbers and wording carry no information.", "",
                  "## Validation (when is a history record the same ticket?)", "",
                  "A history record can only be the same ticket when `product`, `error_code` and `platform` match after",
                  "normalisation: case does not matter, and `E-1042`, `e-1042` and `E1042` are one code. Matching",
                  "fields are necessary, not sufficient: the same code on the same platform with a different story is",
                  "a different ticket with a different resolution.", "",
                  "## Output", "",
                  "Write `answer.json` in this directory:", "", "```json", '{"resolution_id": "R-07"}', "```", "",
                  "Ids are case-insensitive and `R-7` equals `R-07`. Extra keys are ignored.", "",
                  "## Rules", "",
                  "- Do not modify `history.jsonl` or `task.json`; write nothing except `answer.json`.",
                  "- Only `answer.json` is graded. Your final message is not."]
        return "\n".join(lines) + "\n"


SPEC = TicketsSpec()

if __name__ == "__main__":
    sys.exit(common.main(SPEC))
