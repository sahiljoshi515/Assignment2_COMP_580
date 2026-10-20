"""Assignment 2 -- hosts: inventory snapshots of one fleet, and the host that drifted.

Concept this file teaches: a fleet is built from one image, so the inventory snapshot of
every host -- packages, kernel parameters, mounts, services, environment -- is the same
hundred lines with a dozen host-specific numbers. Configuration management promises the
hosts are identical; the audit question is always "which one is not, and where". That
is a diff across eight near-identical files, and an agent that reads them all in full
reads one file eight times.

Design rules this file embodies:
  * One template per scenario, one rendering per host. Numbers that honestly differ per
    host (uptime, load, free memory, disk usage, the collection time) differ; every
    other line is shared, so the files are near-duplicates whose exact diff is short.
  * Six planted facts on six different hosts, each one line (or one missing line): a
    package version, the kernel, a kernel parameter, a mount, a service state, and the
    fullest disk, which is a fact about the numbers that are allowed to differ.
  * Numbers carry answers here (a version, a percentage), which is why the content layer
    must fold losslessly: an exact diff shows them, a masked one would not.

Run from the repo root:  /usr/local/bin/python3.13 assignment2/datasets/hosts/generate.py
"""

import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common, corpus  # noqa: E402

ROLES = ["web", "api", "worker", "ingest", "cache", "proxy", "batch", "edge"]
REGIONS = ["eu-central", "us-east", "us-west", "ap-south", "eu-west"]
OS_RELEASES = ["Ubuntu 22.04.4 LTS", "Ubuntu 24.04.1 LTS", "Debian GNU/Linux 12 (bookworm)"]
KERNELS = {"Ubuntu 22.04.4 LTS": ["5.15.0-105-generic", "5.15.0-112-generic", "6.5.0-35-generic"],
           "Ubuntu 24.04.1 LTS": ["6.8.0-41-generic", "6.8.0-45-generic", "6.8.0-48-generic"],
           "Debian GNU/Linux 12 (bookworm)": ["6.1.0-21-amd64", "6.1.0-25-amd64", "6.1.0-28-amd64"]}
PACKAGES = [("openssl", ["3.0.2-0ubuntu1.15", "3.0.2-0ubuntu1.18", "3.0.13-0ubuntu3.4"]),
            ("nginx", ["1.24.0-1", "1.24.0-2", "1.26.1-1"]), ("curl", ["8.5.0-2", "8.5.0-3", "8.9.1-1"]),
            ("python3", ["3.10.12-1", "3.12.3-1", "3.11.2-6"]), ("systemd", ["249.11-0ubuntu3.12", "255.4-1ubuntu8.4", "252.26-1"]),
            ("openssh-server", ["8.9p1-3ubuntu0.10", "9.6p1-3ubuntu13.5", "9.2p1-2+deb12u3"]),
            ("ca-certificates", ["20230311ubuntu0.22.04.1", "20240203", "20230311"]), ("git", ["2.34.1-1ubuntu1.11", "2.43.0-1ubuntu7.1", "2.39.2-1.1"]),
            ("jq", ["1.6-2.1ubuntu3", "1.7.1-3", "1.6-2.1"]), ("vim", ["2:8.2.3995-1ubuntu2.17", "2:9.1.0016-1ubuntu7.3", "2:9.0.1378-2"]),
            ("rsync", ["3.2.7-0ubuntu0.22.04.2", "3.2.7-1ubuntu1", "3.2.7-1"]), ("htop", ["3.0.5-7build2", "3.3.0-4build1", "3.2.2-2"]),
            ("logrotate", ["3.19.0-1ubuntu1.1", "3.21.0-2build1", "3.21.0-1"]), ("chrony", ["4.2-2ubuntu2", "4.5-1ubuntu4", "4.3-2+deb12u1"]),
            ("fail2ban", ["0.11.2-6", "1.0.2-3ubuntu0.1", "1.0.2-2"]), ("node-exporter", ["1.7.0-1", "1.8.1-1", "1.8.2-1"]),
            ("fluent-bit", ["2.2.2-1", "3.0.7-1", "3.1.4-1"]), ("docker-ce", ["5:26.1.3-1", "5:27.0.3-1", "5:27.1.1-1"]),
            ("containerd.io", ["1.6.33-1", "1.7.18-1", "1.7.19-1"]), ("unattended-upgrades", ["2.8ubuntu1", "2.9.1+nmu4ubuntu1", "2.9.1+nmu3"]),
            ("libc6", ["2.35-0ubuntu3.8", "2.39-0ubuntu8.3", "2.36-9+deb12u7"]), ("zlib1g", ["1:1.2.11.dfsg-2ubuntu9.2", "1:1.3.dfsg-3.1ubuntu2.1", "1:1.2.13.dfsg-1"]),
            ("sudo", ["1.9.9-1ubuntu2.4", "1.9.15p5-3ubuntu5", "1.9.13p3-1+deb12u1"]), ("bash", ["5.1-6ubuntu1.1", "5.2.21-2ubuntu4", "5.2.15-2+b7"]),
            ("coreutils", ["8.32-4.1ubuntu1.2", "9.4-3ubuntu6", "9.1-1"]), ("iproute2", ["5.15.0-1ubuntu2", "6.1.0-1ubuntu6", "6.1.0-3"]),
            ("tcpdump", ["4.99.1-3ubuntu0.2", "4.99.4-3ubuntu4", "4.99.3-1"]), ("strace", ["5.16-0ubuntu3", "6.8-0ubuntu2", "6.1-0.1"])]
PARAMS = [("net.core.somaxconn", ["1024", "4096", "8192"]), ("net.ipv4.tcp_tw_reuse", ["0", "1"]),
          ("net.ipv4.ip_local_port_range", ["32768 60999", "10240 65535"]), ("vm.swappiness", ["1", "10", "60"]),
          ("vm.max_map_count", ["65530", "262144"]), ("fs.file-max", ["1048576", "2097152"]),
          ("net.ipv4.tcp_keepalive_time", ["300", "600", "7200"]), ("kernel.pid_max", ["32768", "4194304"]),
          ("net.core.netdev_max_backlog", ["1000", "5000", "16384"]), ("vm.dirty_ratio", ["10", "20", "40"]),
          ("net.ipv4.tcp_fin_timeout", ["15", "30", "60"]), ("fs.inotify.max_user_watches", ["8192", "524288"])]
MOUNTS = [("/", "/dev/nvme0n1p2", "ext4", 80), ("/boot/efi", "/dev/nvme0n1p1", "vfat", 1),
          ("/var/lib/docker", "/dev/nvme1n1", "xfs", 400), ("/var/log", "/dev/mapper/vg0-log", "ext4", 50),
          ("/data", "/dev/mapper/vg0-data", "xfs", 1000), ("/mnt/backup", "nas-01.internal:/export/backup", "nfs4", 4000),
          ("/srv/cache", "/dev/mapper/vg0-cache", "ext4", 200)]
SERVICES = ["nginx", "node-exporter", "fluent-bit", "chrony", "fail2ban", "docker", "containerd", "ssh",
            "unattended-upgrades", "cron"]
ENV_VARS = [("APP_ENV", ["production"]), ("REGION", None), ("LOG_LEVEL", ["info"]), ("METRICS_PORT", ["9100"]),
            ("TZ", ["UTC"]), ("JAVA_OPTS", ["-Xms2g -Xmx6g"]), ("FEATURE_FLAGS", ["canary=off,tracing=on"]),
            ("DEPLOY_CHANNEL", ["stable"])]


def kinds():
    def package_drift(state, target):
        return {"host": state["hosts"][state["package_host"]], "package": state["package_name"]}

    def kernel_drift(state, target):
        return {"host": state["hosts"][state["kernel_host"]], "kernel": state["kernel_other"]}

    def param_drift(state, target):
        return {"host": state["hosts"][state["param_host"]], "parameter": state["param_name"]}

    def missing_mount(state, target):
        return {"host": state["hosts"][state["mount_host"]], "mount": state["mount_path"]}

    def service_down(state, target):
        return {"host": state["hosts"][state["service_host"]], "service": state["service_name"]}

    def fullest_disk(state, target):
        host = max(state["hosts"], key=lambda h: (state["root_used"][h], h))
        return {"host": host, "used_pct": state["root_used"][host]}

    def uptime_of(state, target):
        return {"host": target, "days": state["uptime"][target]}

    def two_hosts(state):
        return state["targets"]

    return (
        corpus.Kind("package_drift", "which host has a different package version",
                    ["Every host of the {service} fleet should run the same package versions. One host has a different version of one package. Which host, and which package?",
                     "Please compare the [packages] sections of the {service} inventory snapshots and name the host whose version of one package differs from all the others, with the package name.",
                     "One {service} host was patched out of band and now runs a package version the rest of the fleet does not. Find the host and the package."],
                    ["The snapshots are in inventory/, one file per host; packages are listed as name = version.",
                     "Each file under inventory/ has a [packages] section with one line per package.",
                     "Only one host differs, on exactly one package."],
                    package_drift, ("host", "package"), example={"host": "web-03", "package": "openssl"}),
        corpus.Kind("kernel_drift", "which host runs a different kernel",
                    ["Which {service} host runs a kernel version different from the rest of the fleet, and which kernel is it?",
                     "One {service} host did not reboot after the kernel update, or rebooted into something else. Name the host and the kernel it reports.",
                     "Compare the kernel line of every {service} snapshot and report the host that differs together with its kernel string."],
                    ["The kernel is the `kernel =` line of the [system] section.",
                     "Look at `kernel =` under [system] in each inventory file.",
                     "Report the kernel string exactly as written."],
                    kernel_drift, ("host", "kernel"), example={"host": "web-05", "kernel": "5.15.0-105-generic"}),
        corpus.Kind("param_drift", "which host has a different kernel parameter",
                    ["The {service} fleet shares one sysctl profile. One host has one kernel parameter set differently. Which host, and which parameter?",
                     "Find the {service} host whose [kernel.params] section differs from the others and name the parameter that differs.",
                     "One kernel parameter on one {service} host does not match the fleet profile. Which host and which parameter (full dotted name)?"],
                    ["Parameters are listed under [kernel.params] as name = value.",
                     "Every snapshot carries the same parameters; compare their values.",
                     "Report the parameter by its full dotted name, e.g. vm.swappiness."],
                    param_drift, ("host", "parameter"), example={"host": "web-02", "parameter": "net.core.somaxconn"}),
        corpus.Kind("missing_mount", "which host is missing a mount",
                    ["Every {service} host should have the same mounts. One host is missing one. Which host, and which mount point?",
                     "Compare the [mounts] sections of the {service} snapshots and report the host with a mount missing, and the mount point that is absent.",
                     "One {service} host lacks a filesystem the others all mount. Name the host and the mount point."],
                    ["Mounts are listed under [mounts], one line per mount point.",
                     "The missing line is simply absent from that host's [mounts] section.",
                     "Report the mount point path, e.g. /var/log."],
                    missing_mount, ("host", "mount"), example={"host": "web-07", "mount": "/mnt/backup"}),
        corpus.Kind("service_down", "which host has a service that is not running",
                    ["All services listed in the {service} snapshots should be active on every host. One host has one service inactive. Which host, and which service?",
                     "Find the {service} host with a service reported as inactive in its [services] section and name the service.",
                     "One service is down on one {service} host. Which host and which service?"],
                    ["Services are listed under [services] as name = active or name = inactive.",
                     "Every other host reports that service as active.",
                     "Report the service name as written in the snapshot."],
                    service_down, ("host", "service"), example={"host": "web-01", "service": "fluent-bit"}),
        corpus.Kind("fullest_disk", "which host has the fullest root filesystem",
                    ["Which {service} host has the highest usage on its root filesystem (/), and what percentage is used?",
                     "Across the {service} fleet, find the host whose / mount is fullest and report the used percentage.",
                     "Please report the {service} host with the most-used root filesystem and its used percentage."],
                    ["Usage is the used_pct value on the / line of the [mounts] section.",
                     "Compare the / lines under [mounts]; the highest value is unique.",
                     "The percentage is an integer in the snapshot."],
                    fullest_disk, ("host", "used_pct"), example={"host": "web-04", "used_pct": 83}),
        corpus.Kind("uptime_of", "how long has {target} been up",
                    ["How many days has the {service} host {target} been up according to its snapshot?",
                     "Please read inventory/{target}.txt and report its uptime in days.",
                     "What is the uptime_days value in the {service} snapshot of {target}?"],
                    ["The value is uptime_days under [system].",
                     "It is the integer on the uptime_days line.",
                     "Only that host's file matters for this one."],
                    uptime_of, ("host", "days"), targets=two_hosts, example={"host": "web-06", "days": 41}),
    )


class HostsSpec(corpus.CorpusSpec):
    NAME = "hosts"
    FILE = __file__
    TITLE = "Fleet inventory audit"
    ROLE = ("You are auditing a fleet. One request is in `task.json`; answer it from the inventory snapshots in\n"
            "`inventory/` and write the answer to `answer.json`.")
    FILE_LAYOUT = ("`inventory/<host>.txt`: one snapshot per host of the fleet, same sections in every file "
                   "([system], [kernel.params], [packages], [mounts], [services], [environment], [load]).")
    KINDS = kinds()
    SCENARIOS = 24
    SCENARIO_PREFIX = "FLT"
    DEFAULT_SEED = 73

    def service_of(self, state):
        return state["role"]

    def scenario_state(self, sid, rng):
        role = common.pick(rng, ROLES)
        region = common.pick(rng, REGIONS)
        n = rng.randrange(6, 10)
        hosts = ["%s-%02d" % (role, i + 1) for i in range(n)]
        os_release = common.pick(rng, OS_RELEASES)
        kernels = list(KERNELS[os_release])
        kernel = common.pick(rng, kernels)
        kernel_other = common.pick(rng, [k for k in kernels if k != kernel])
        roles = rng.sample(range(n), 5)
        packages = [(name, common.pick(rng, versions)) for name, versions in PACKAGES]
        pkg_index = rng.randrange(len(PACKAGES))
        pkg_name, versions = PACKAGES[pkg_index]
        pkg_other = common.pick(rng, [v for v in versions if v != packages[pkg_index][1]])
        params = [(name, common.pick(rng, values)) for name, values in PARAMS]
        param_index = rng.randrange(len(PARAMS))
        param_name, values = PARAMS[param_index]
        param_other = common.pick(rng, [v for v in values if v != params[param_index][1]])
        mounts = [m for m in MOUNTS if m[0] in ("/", "/boot/efi")] + rng.sample([m for m in MOUNTS if m[0] not in ("/", "/boot/efi")], 4)
        mounts.sort()
        mount_path = common.pick(rng, [m[0] for m in mounts if m[0] not in ("/", "/boot/efi")])
        services = sorted(rng.sample(SERVICES, 8))
        service_name = common.pick(rng, services)
        day = datetime.date(2026, 1, 12) + datetime.timedelta(days=rng.randrange(0, 120))
        root_used = {}
        used_values = rng.sample(range(31, 90), n)
        for host, value in zip(hosts, used_values):
            root_used[host] = value
        uptime = {host: rng.randrange(3, 190) for host in hosts}
        return {"scenario": sid, "role": role, "region": region, "hosts": hosts, "os": os_release, "kernel": kernel,
                "kernel_other": kernel_other, "packages": packages, "package_host": roles[0], "package_index": pkg_index,
                "package_name": pkg_name, "package_other": pkg_other, "kernel_host": roles[1], "params": params,
                "param_host": roles[2], "param_index": param_index, "param_name": param_name, "param_other": param_other,
                "mounts": mounts, "mount_host": roles[3], "mount_path": mount_path, "services": services,
                "service_host": roles[4], "service_name": service_name, "day": day.isoformat(),
                "root_used": root_used, "uptime": uptime, "targets": rng.sample(hosts, 2),
                "cpus": common.pick(rng, [4, 8, 16]), "memory_mb": common.pick(rng, [16384, 32768, 65536]),
                "agent_version": "1.%d.%d" % (rng.randrange(5, 12), rng.randrange(0, 9)),
                "cert_expiry": (day + datetime.timedelta(days=rng.randrange(40, 300))).isoformat()}

    def render_host(self, state, index):
        host = state["hosts"][index]
        rng = common.sub_rng(self.NAME + "-host", state["scenario"], host)
        lines, marks = [], []
        day = datetime.date.fromisoformat(state["day"])
        lines.append("# host: %s.%s.example.net" % (host, state["region"]))
        lines.append("# collected: %s by inventory-agent %s" % (corpus.ts(day, 2, rng.randrange(0, 20), rng.randrange(0, 60)), state["agent_version"]))
        lines.append("")
        lines.append("[system]")
        lines.append("hostname = %s" % host)
        lines.append("role = %s" % state["role"])
        lines.append("region = %s" % state["region"])
        lines.append("os = %s" % state["os"])
        kernel = state["kernel_other"] if index == state["kernel_host"] else state["kernel"]
        lines.append("kernel = %s" % kernel)
        if index == state["kernel_host"]:
            marks.append(len(lines))
        lines.append("arch = x86_64")
        lines.append("timezone = UTC")
        lines.append("cpus = %d" % state["cpus"])
        lines.append("memory_mb = %d" % state["memory_mb"])
        lines.append("memory_free_mb = %d" % rng.randrange(1200, state["memory_mb"] // 2))
        lines.append("uptime_days = %d" % state["uptime"][host])
        marks.append(len(lines))
        lines.append("")
        lines.append("[kernel.params]")
        for i, (name, value) in enumerate(state["params"]):
            if index == state["param_host"] and i == state["param_index"]:
                value = state["param_other"]
                marks.append(len(lines) + 1)
            lines.append("%s = %s" % (name, value))
        lines.append("")
        lines.append("[packages]")
        for i, (name, version) in enumerate(state["packages"]):
            if index == state["package_host"] and i == state["package_index"]:
                version = state["package_other"]
                marks.append(len(lines) + 1)
            lines.append("%s = %s" % (name, version))
        lines.append("")
        lines.append("[mounts]")
        for path, device, fstype, size in state["mounts"]:
            if index == state["mount_host"] and path == state["mount_path"]:
                continue
            used = state["root_used"][host] if path == "/" else rng.randrange(5, 95)
            lines.append("%s  %s  %s  size_gb=%d  used_pct=%d" % (path, device, fstype, size, used))
            if path == "/":
                marks.append(len(lines))
        lines.append("")
        lines.append("[services]")
        for name in state["services"]:
            status = "inactive" if index == state["service_host"] and name == state["service_name"] else "active"
            lines.append("%s = %s" % (name, status))
            if status == "inactive":
                marks.append(len(lines))
        lines.append("")
        lines.append("[environment]")
        for name, values in ENV_VARS:
            lines.append("%s = %s" % (name, state["region"] if values is None else values[0]))
        lines.append("")
        lines.append("[certificates]")
        lines.append("/etc/ssl/certs/%s.pem  expires=%s  issuer=internal-ca" % (state["role"], state["cert_expiry"]))
        lines.append("")
        lines.append("[load]")
        lines.append("load_1m = %.2f" % (rng.randrange(5, 400) / 100.0))
        lines.append("load_5m = %.2f" % (rng.randrange(5, 400) / 100.0))
        lines.append("processes = %d" % rng.randrange(120, 480))
        lines.append("open_files = %d" % rng.randrange(2000, 40000))
        lines.append("tcp_established = %d" % rng.randrange(20, 900))
        return lines, sorted(set(marks))

    def scenario_files(self, state):
        files = {}
        for index, host in enumerate(state["hosts"]):
            lines, _ = self.render_host(state, index)
            files["inventory/%s.txt" % host] = "\n".join(lines) + "\n"
        return files

    def content_truth(self, state, files):
        answer_lines = {}
        for index, host in enumerate(state["hosts"]):
            _, marks = self.render_host(state, index)
            answer_lines["inventory/%s.txt" % host] = marks
        return {"groups": [{"name": "fleet-inventory", "files": sorted(files)}], "answer_lines": answer_lines}

    def domain_instructions(self):
        return ["## The scenario", "",
                "`inventory/` holds one snapshot per host of one fleet, all built from the same image and written by",
                "the same agent, so the files share their sections and most of their lines: [system] facts, the",
                "[kernel.params] profile, the [packages] list (`name = version`), [mounts] (`path device fstype",
                "size_gb=N used_pct=N`), [services] (`name = active|inactive`), [environment], [certificates] and",
                "[load]. Uptime, free memory, disk usage and load differ per host and are not drift.", "",
                "## How to decide", "",
                "- Drift is one host differing from every other on a line that should be the same: a package",
                "  version, the kernel, a kernel parameter, a missing mount, an inactive service.",
                "- Report hosts by their short name (`web-03`), packages, parameters and services by the name on the",
                "  line, kernels and versions exactly as written, percentages and days as integers."]


SPEC = HostsSpec()

if __name__ == "__main__":
    sys.exit(corpus.main(SPEC))
