#!/usr/bin/env python3
"""Private Pi-hole DR backup orchestrator (Fedora side, read-only SSH source).

The router is never modified. Plaintext snapshots and reconstructed archives
exist only in a private tmpfs, then an encrypted GPG archive is exported.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

# Explicit allowlist: do NOT back up Pi-hole query history, Tailscale state,
# secret authentication databases, NVRAM or router-attached user files.
SOURCE_FILES = (
    "opt/etc/pihole/dnsmasq.conf",
    "opt/etc/pihole/pihole.toml",
    "opt/etc/pihole/gravity.db",
    "opt/etc/pihole/hosts/custom.list",
    "opt/etc/init.d/rc.func",
    "opt/etc/init.d/S64pihole-ip",
    "opt/etc/init.d/S65pihole-FTL",
    "opt/bin/pihole-FTL",
    "opt/bin/nonroot",
    "opt/share/pihole/rc.sh",
    "opt/share/pihole/pihole-FTL-prestart.sh",
    "opt/share/pihole/pihole-FTL-poststop.sh",
    "jffs/configs/dnsmasq.conf.add",
    "jffs/scripts/post-mount",
    "jffs/scripts/dnsmasq.postconf",
)

REVIEW_ONLY = {"jffs/scripts/post-mount": "recovery-reference/jffs/scripts/post-mount"}
CRITICAL_METADATA = {
    "opt/etc/pihole/pihole.toml": (999, 999, 0o640),
    "opt/etc/pihole/gravity.db": (999, 999, 0o640),
    "opt/bin/pihole-FTL": (0, 0, 0o755),
    "opt/bin/nonroot": (0, 0, 0o755),
    "opt/etc/init.d/S64pihole-ip": (0, 0, 0o755),
    "opt/etc/init.d/S65pihole-FTL": (0, 0, 0o755),
}
CAP_NAMES = frozenset({
    "cap_chown", "cap_net_bind_service", "cap_net_admin", "cap_net_raw",
    "cap_ipc_lock", "cap_sys_nice", "cap_sys_time",
})


def die(msg: str) -> None:
    raise ValueError(msg)


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(name: str) -> str:
    while name.startswith("./"):
        name = name[2:]
    if name.startswith("/") or ".." in name.split("/") or not name or "\\" in name:
        die("UNSAFE_ARCHIVE_NAME")
    return name.rstrip("/")


def collect_directories() -> tuple[str, ...]:
    directories = {"opt", "jffs", "recovery-reference", "manifest"}
    for p in SOURCE_FILES:
        path = REVIEW_ONLY.get(p, p)
        parts = path.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            directories.add("/".join(parts[:i]))
    return tuple(sorted(directories, key=lambda x: (x.count("/"), x)))


DIRECTORIES = collect_directories()
SOURCE_DIRS = tuple(d for d in DIRECTORIES if d not in {"manifest"} and not d.startswith("recovery-reference"))


def validate_caps(text: str) -> None:
    match = re.fullmatch(r"/opt/bin/pihole-FTL\s+([a-z_,]+)=eip\s*", text)
    if not match or frozenset(match.group(1).split(",")) != CAP_NAMES:
        die("FTL_CAPABILITIES_UNEXPECTED")


def validate_db(path: Path) -> None:
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        journal_mode = con.execute("PRAGMA journal_mode").fetchone()[0].lower()
        if journal_mode != "delete":
            die("GRAVITY_JOURNAL_MODE_NOT_DELETE")
        if con.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            die("GRAVITY_INTEGRITY_CHECK_FAIL")
    finally:
        con.close()


def archive_members(source: Path) -> dict[str, tarfile.TarInfo]:
    found = {}
    with tarfile.open(source, "r:") as tar:
        for member in tar:
            name = normalize(member.name)
            if name not in SOURCE_FILES or not member.isfile():
                die("UNEXPECTED_SOURCE_TAR_MEMBER")
            if name in found:
                die("DUPLICATE_SOURCE_TAR_MEMBER")
            found[name] = member
    if set(found) != set(SOURCE_FILES):
        die("SOURCE_TAR_MEMBER_SET_MISMATCH")
    for path, required in CRITICAL_METADATA.items():
        m = found[path]
        if (m.uid, m.gid, m.mode & 0o7777) != required:
            die("SOURCE_METADATA_DRIFT:" + path)
    return found


def build_archive(source: Path, output: Path, dirs: dict[str, tuple[int, int, int]],
                  account: str, pkg: str, capabilities: str) -> int:
    """Build private plain TAR.GZ from a verified allowlisted source TAR.

    No chmod/chown/capability mutation is performed on source or router.
    """
    validate_caps(capabilities)
    if "uid=999(pihole)" not in account or "gid=999(pihole)" not in account:
        die("PIHOLE_ACCOUNT_DRIFT")
    if not pkg.strip() or "Package: pi-hole" not in pkg:
        die("PIHOLE_PACKAGE_MANIFEST_INVALID")
    found = archive_members(source)
    if dirs.get("opt/etc/pihole") != (999, 999, 0o755):
        die("PIHOLE_DIRECTORY_METADATA_DRIFT")

    # SQLite needs a private named path on Fedora tmpfs for integrity checking.
    gravity_path = output.with_name("gravity-check.db")
    if gravity_path.exists():
        die("GRAVITY_TEMP_COLLISION")
    try:
        with tarfile.open(source, "r:") as input_tar, gravity_path.open("xb") as tmp:
            gravity = input_tar.extractfile(found["opt/etc/pihole/gravity.db"])
            assert gravity is not None
            shutil.copyfileobj(gravity, tmp)
        validate_db(gravity_path)
    finally:
        gravity_path.unlink(missing_ok=True)

    metadata = {}
    for d in DIRECTORIES:
        if d in dirs:
            metadata[d] = dirs[d]
        elif d.startswith("recovery-reference"):
            # Stored for reference only: parent dirs do not become live paths.
            metadata[d] = (0, 0, 0o755)
        elif d == "manifest":
            metadata[d] = (0, 0, 0o700)
        else:
            die("MISSING_DIRECTORY_METADATA:" + d)

    digest_lines = []
    verified_count = 0
    with tarfile.open(source, "r:") as original, tarfile.open(output, "w:gz", format=tarfile.PAX_FORMAT) as built:
        def add_dir(name: str) -> None:
            item = tarfile.TarInfo("./" + name + "/")
            item.type = tarfile.DIRTYPE
            item.uid, item.gid, item.mode = metadata[name]
            item.mtime = int(datetime.now(timezone.utc).timestamp())
            built.addfile(item)

        root = tarfile.TarInfo("./")
        root.type = tarfile.DIRTYPE
        root.mode = 0o700
        built.addfile(root)
        for d in DIRECTORIES:
            add_dir(d)

        members = {normalize(item.name): item for item in original}
        for path in SOURCE_FILES:
            old = members[path]
            content = original.extractfile(old)
            assert content is not None
            target = REVIEW_ONLY.get(path, path)
            header = tarfile.TarInfo("./" + target)
            header.uid, header.gid, header.mode = old.uid, old.gid, old.mode
            header.mtime = old.mtime
            header.size = old.size
            header.type = tarfile.REGTYPE
            built.addfile(header, content)
            digest_lines.append(f"{source_file_digest(source, path)}  ./{target}\n")
            verified_count += 1

        manifest = {
            "manifest/pihole-account.txt": account,
            "manifest/pi-hole-package.txt": pkg,
            "manifest/ftl-capabilities.txt": capabilities,
        }
        for target, value in manifest.items():
            payload = value.encode("utf-8")
            item = tarfile.TarInfo("./" + target)
            item.uid = item.gid = 0
            item.mode = 0o600
            item.size = len(payload)
            built.addfile(item, io.BytesIO(payload))
            digest_lines.append(f"{hashlib.sha256(payload).hexdigest()}  ./{target}\n")
        sums = "".join(sorted(digest_lines)).encode("ascii")
        item = tarfile.TarInfo("./manifest/files.sha256")
        item.uid = item.gid = 0
        item.mode = 0o600
        item.size = len(sums)
        built.addfile(item, io.BytesIO(sums))
    verify_archive(output)
    return verified_count


def source_file_digest(path: Path, member_name: str) -> str:
    with tarfile.open(path, "r:") as source:
        item = source.getmember(member_name)
        stream = source.extractfile(item)
        assert stream is not None
        h = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
        return h.hexdigest()


def verify_archive(path: Path) -> None:
    with tarfile.open(path, "r:gz") as f:
        members = {normalize(x.name): x for x in f if x.isfile()}
        expected_files = {REVIEW_ONLY.get(p, p) for p in SOURCE_FILES}
        expected_files |= {"manifest/pihole-account.txt", "manifest/pi-hole-package.txt", "manifest/ftl-capabilities.txt", "manifest/files.sha256"}
        if set(members) != expected_files:
            die("OUTPUT_ARCHIVE_FILES_UNEXPECTED")
        sums_file = f.extractfile(members["manifest/files.sha256"])
        assert sums_file is not None
        covered = set()
        for line in sums_file.read().decode("ascii").splitlines():
            match = re.fullmatch(r"([0-9a-f]{64})  \./(.+)", line)
            if not match or match.group(2) not in members or match.group(2) in covered:
                die("MANIFEST_SHA256_BAD_LINE")
            covered.add(match.group(2))
            member = f.extractfile(members[match.group(2)])
            assert member is not None
            h = hashlib.sha256()
            for chunk in iter(lambda: member.read(1024 * 1024), b""):
                h.update(chunk)
            if h.hexdigest() != match.group(1):
                die("MANIFEST_FILE_HASH_MISMATCH")
        if covered != set(members) - {"manifest/files.sha256"}:
            die("MANIFEST_FILE_SET_INCOMPLETE")
        d = f.getmember("./opt/etc/pihole/")
        g = members["opt/etc/pihole/gravity.db"]
        if (d.uid, d.gid, d.mode) != (999, 999, 0o755) or (g.uid, g.gid, g.mode) != (999, 999, 0o640):
            die("OUTPUT_METADATA_MISMATCH")
        if "jffs/scripts/post-mount" in members:
            die("POST_MOUNT_AUTORESTORE_UNSAFE")


def validate_runtime_tmpfs() -> Path:
    location = os.environ.get("XDG_RUNTIME_DIR")
    if not location:
        die("PRIVATE_TMPFS_REQUIRED")
    path = Path(location)
    r = subprocess.run(["findmnt", "-n", "-o", "FSTYPE", "-T", str(path)], capture_output=True, text=True, check=True)
    if r.stdout.strip() != "tmpfs" or not path.is_dir():
        die("PRIVATE_TMPFS_REQUIRED")
    if path.stat().st_uid != os.getuid():
        die("PRIVATE_TMPFS_OWNER_MISMATCH")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--router", required=True, help="SSH target, e.g. admin1@192.168.50.1")
    parser.add_argument("--port", type=int, default=1122)
    parser.add_argument("--dest", type=Path, required=True, help="Private off-router encrypted backup directory")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        die("INVALID_SSH_PORT")
    os.umask(0o077)
    runtime = validate_runtime_tmpfs()
    dest = args.dest.expanduser().resolve()
    dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    if dest.stat().st_uid != os.getuid() or dest.stat().st_mode & 0o077:
        die("PRIVATE_DESTINATION_PERMISSIONS_REQUIRED")
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    output = dest / f"pihole-dr-{stamp}-verified.tar.gz.gpg"
    if output.exists() or (dest / (output.name + ".partial")).exists():
        die("DESTINATION_EXISTS")
    ssh = ["ssh", "-n", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-p", str(args.port), args.router]

    def run_remote(command: str, timeout: int = 90) -> str:
        r = subprocess.run(ssh + [command], capture_output=True, text=True, timeout=timeout)
        if r.returncode:
            die(f"SSH_RC={r.returncode}; operation failed")
        return r.stdout

    with tempfile.TemporaryDirectory(prefix="pihole-dr-", dir=runtime) as work_dir:
        work = Path(work_dir)
        paths = " ".join("/" + x for x in SOURCE_FILES)
        sums_cmd = "/opt/bin/sha256sum " + paths
        before = run_remote(sums_cmd, timeout=150)
        account = run_remote("id pihole").strip() + "\n"
        package = run_remote("/opt/bin/opkg status pi-hole", timeout=60)
        capabilities = run_remote("/opt/sbin/getcap /opt/bin/pihole-FTL")
        validate_caps(capabilities)
        dirs_cmd = "/opt/bin/stat -L -c '%n|%u|%g|%a' " + " ".join("/" + d for d in SOURCE_DIRS)
        directory_info = run_remote(dirs_cmd)
        dirs = {}
        for entry in directory_info.splitlines():
            parts = entry.split("|")
            if len(parts) != 4 or parts[0].lstrip("/") not in SOURCE_DIRS:
                die("DIRECTORY_STAT_INVALID")
            dirs[parts[0].lstrip("/")] = (int(parts[1]), int(parts[2]), int(parts[3], 8))
        if set(dirs) != set(SOURCE_DIRS):
            die("DIRECTORY_STAT_INCOMPLETE")
        source = work / "router-snapshot.tar"
        cmd = "/bin/tar -C / -cf - " + " ".join(SOURCE_FILES)
        print("=== READ-ONLY ROUTER SNAPSHOT ===", flush=True)
        with source.open("xb") as stream:
            result = subprocess.run(ssh + [cmd], stdout=stream, stderr=subprocess.PIPE, timeout=180)
        if result.returncode:
            die(f"SOURCE_TAR_SSH_RC={result.returncode}")
        if not source.stat().st_size:
            die("SOURCE_TAR_EMPTY")
        after = run_remote(sums_cmd, timeout=150)
        if before != after:
            die("LIVE_FILES_CHANGED_DURING_BACKUP")
        remote_hashes = {}
        for line in after.splitlines():
            match = re.fullmatch(r"([0-9a-fA-F]{64})\s+/(.+)", line)
            if not match or match.group(2) not in SOURCE_FILES:
                die("LIVE_FILE_HASH_LINE_INVALID")
            remote_hashes[match.group(2)] = match.group(1).lower()
        if set(remote_hashes) != set(SOURCE_FILES):
            die("LIVE_FILE_HASH_SET_MISMATCH")
        archive_members(source)
        for item, expected in remote_hashes.items():
            if source_file_digest(source, item) != expected:
                die("LIVE_VS_SNAPSHOT_HASH_MISMATCH:" + item)
        print("LIVE_SOURCE_SHA256=PASS", flush=True)

        plain = work / "validated.tar.gz"
        print("=== BUILD RECOVERY ARCHIVE ===", flush=True)
        count = build_archive(source, plain, dirs, account, package, capabilities)
        print(f"ARCHIVE_FILES={count}", flush=True)
        print("GRAVITY_INTEGRITY=PASS", flush=True)
        print("METADATA_AND_MANIFEST=PASS", flush=True)

        part = dest / (output.name + ".partial")
        try:
            subprocess.run(["gpg", "--symmetric", "--cipher-algo", "AES256", "--output", str(part), str(plain)], check=True)
            p = subprocess.Popen(["gpg", "--quiet", "--decrypt", str(part)], stdout=subprocess.PIPE)
            assert p.stdout is not None
            h = hashlib.sha256()
            for block in iter(lambda: p.stdout.read(1024 * 1024), b""):
                h.update(block)
            p.stdout.close()
            if p.wait() or h.hexdigest() != sha256_path(plain):
                die("ENCRYPTED_ROUNDTRIP_FAIL")
            part.rename(output)
        finally:
            part.unlink(missing_ok=True)
        os.chmod(output, 0o600)
        sidecar = Path(str(output) + ".sha256")
        with sidecar.open("x", encoding="ascii") as f:
            f.write(f"{sha256_path(output)}  {output}\n")
        os.chmod(sidecar, 0o600)
        print("ENCRYPTED_SHA256_ROUNDTRIP=PASS", flush=True)
        print("ISSUE129_PIHOLE_GENERATOR=PASS", flush=True)
        print("PRIVATE_FILE=" + output.name, flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, tarfile.TarError, sqlite3.Error) as error:
        print(f"ISSUE129_PIHOLE_GENERATOR=FAIL ({error})", file=sys.stderr)
        sys.exit(1)
