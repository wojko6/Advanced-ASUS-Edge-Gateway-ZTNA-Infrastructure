#!/usr/bin/env python3
"""Issue #235 mount-mode repair: unprivileged isolated /tmp-only regression.

Execute: python3 tests/test-issue235-ssd-postmount-mode.py
No root, mounts, SSD, services, router access or real blkid/chmod writes.
This suite rewrites ONLY a temporary COPY of the draft helper to point at a
private synthetic mount table and an isolated mocked blkid executable.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile


REPO = Path(__file__).resolve().parents[1]
HELPER = REPO / "router/scripts/issue235-ssd-mount-mode"
DATA_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
ENTWARE_UUID = "11111111-2222-3333-4444-555555555555"


def put(path: Path, content: str, *, executable: bool = False) -> None:
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def run(script: Path, path: Path, uuid: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/sh", str(script), str(path), uuid],
        capture_output=True,
        text=True,
        timeout=6,
        check=False,
    )


def main() -> int:
    source = HELPER.read_text(encoding="utf-8")
    markers = {
        "MOUNT_ROOT='/tmp/mnt'": "mount root",
        "MOUNT_TABLE='/proc/mounts'": "mount table",
        "PATH=/usr/sbin:/usr/bin:/sbin:/bin": "binary path",
        "EXPECTED_OWNER='0:0'": "ownership",
    }
    for marker, label in markers.items():
        if source.count(marker) != 1:
            raise AssertionError(f"Unrecognized source marker for {label}")

    failures = 0

    def case(name: str, okay: bool) -> None:
        nonlocal failures
        print(f"{name}={'PASS' if okay else 'FAIL'}")
        if not okay:
            failures += 1

    with tempfile.TemporaryDirectory(prefix="issue235-postmount-lab-") as directory:
        tmp = Path(directory)
        mount_root = tmp / "mnt"
        mount_root.mkdir()
        data = mount_root / "ROUTER_DATA"
        entware = mount_root / "ENTWARE"
        table = tmp / "mounts"
        tools = tmp / "tools"
        tools.mkdir()
        helper = tmp / "candidate.sh"

        # No real blkid or real /proc/mounts can be read by the candidate.
        mock_blkid = tools / "blkid"
        put(
            mock_blkid,
            "#!/bin/sh\n"
            '[ "$1" = "-s" ] && [ "$2" = "UUID" ] && '
            '[ "$3" = "-o" ] && [ "$4" = "value" ] || exit 1\n'
            'case "$5" in\n'
            f"    /dev/mock-data) printf '%s\\n' '/dev/mock-data: LABEL=\"ROUTER_DATA\" UUID=\"{DATA_UUID}\"' ;;\n"
            f"    /dev/mock-entware) printf '%s\\n' '/dev/mock-entware: LABEL=\"ENTWARE\" UUID=\"{ENTWARE_UUID}\"' ;;\n"
            '    *) exit 1 ;;\n'
            'esac\n',
            executable=True,
        )

        # Mimic GNUton's ls -ldn output using an isolated local fixture.
        # No host /bin/busybox or early-boot /opt dependency is required.
        mock_busybox = tools / "busybox"
        mock_busybox_source = (
            "#!/usr/bin/env python3\n"
            "import os, stat, sys\n"
            "if len(sys.argv) != 4 or sys.argv[1:3] != ['ls', '-ldn']:\n"
            "    sys.exit(2)\n"
            "path = sys.argv[3]\n"
            "metadata = os.lstat(path)\n"
            "print(f'{stat.filemode(metadata.st_mode)} 2 "
            "{metadata.st_uid} {metadata.st_gid} {metadata.st_size} "
            "Jan 01 00:00 {path}')\n"
        )
        put(mock_busybox, mock_busybox_source, executable=True)
        put(tools / "chmod", '#!/bin/sh\nexec /bin/chmod "$@"\n', executable=True)
        assert "stat -c" not in source
        assert "command -v blkid" not in source
        assert "/opt/bin" not in source

        modified = source
        modified = modified.replace(
            "MOUNT_ROOT='/tmp/mnt'", f"MOUNT_ROOT='{mount_root}'"
        ).replace(
            "MOUNT_TABLE='/proc/mounts'", f"MOUNT_TABLE='{table}'"
        ).replace(
            "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
            f"PATH={tools}:/usr/sbin:/usr/bin:/sbin:/bin",
        ).replace(
            "EXPECTED_OWNER='0:0'",
            f"EXPECTED_OWNER='{os.getuid()}:{os.getgid()}'",
        )
        for before, after in (
            ("BUSYBOX_BIN='/bin/busybox'", f"BUSYBOX_BIN='{mock_busybox}'"),
            ("BLKID_BIN='/sbin/blkid'", f"BLKID_BIN='{mock_blkid}'"),
            ("CHMOD_BIN='/bin/chmod'", f"CHMOD_BIN='{tools / 'chmod'}'"),
        ):
            assert modified.count(before) == 1, f"Tool contract drift: {before}"
            modified = modified.replace(before, after)
        put(helper, modified)

        def reset(mount: Path, root_mode: int = 0o777) -> None:
            if mount.is_symlink():
                mount.unlink()
            elif mount.exists():
                shutil.rmtree(mount)
            mount.mkdir()
            mount.chmod(root_mode)

        def mounts(fs_data: str = "ext4", src_data: str = "/dev/mock-data",
                   include_data: bool = True) -> None:
            records = []
            if include_data:
                records.append(f"{src_data} {data} {fs_data} rw 0 0")
            records.append(f"/dev/mock-entware {entware} ext4 rw 0 0")
            put(table, "\n".join(records) + "\n")

        reset(data)
        reset(entware)
        mounts()
        a = run(helper, data, DATA_UUID)
        b = run(helper, entware, ENTWARE_UUID)
        case(
            "BOTH_ALLOWLISTED_MOUNTS",
            a.returncode == 0 and b.returncode == 0
            and "APPLIED_0755" in a.stdout
            and "APPLIED_0755" in b.stdout
            and mode(data) == mode(entware) == 0o755,
        )

        a = run(helper, data, DATA_UUID)
        case("IDEMPOTENT_REPEATED_RUN",
             a.returncode == 0 and "ALREADY_0755" in a.stdout
             and mode(data) == 0o755)


        # Malformed ls metadata and wrong owners must never authorize chmod.
        reset(data)
        mounts()
        put(mock_busybox, '#!/bin/sh\nprintf "%s\\n" "drwxrwxrwx 2 invalid 0 4096 Jan 01 00:00 fixture"\n',
            executable=True)
        a = run(helper, data, DATA_UUID)
        case("INVALID_LS_OWNER_FAIL_CLOSED", a.returncode != 0
             and mode(data) == 0o777)
        put(mock_busybox, mock_busybox_source, executable=True)

        reset(data)
        mounts()
        put(mock_busybox, '#!/bin/sh\nprintf "%s\\n" "drwxrwxrwx 2"\n',
            executable=True)
        a = run(helper, data, DATA_UUID)
        case("TRUNCATED_LS_RECORD_FAIL_CLOSED", a.returncode != 0
             and mode(data) == 0o777)
        put(mock_busybox, mock_busybox_source, executable=True)

        # GNUton BusyBox ignores -o value: tagged quoted UUID+LABEL arrives.
        # Also support util-linux raw UUID and reject ambiguous/malformed tags.
        def override_blkid(value: str) -> None:
            assert "'" not in value
            put(
                mock_blkid,
                "#!/bin/sh\n"
                '[ "$1" = "-s" ] && [ "$2" = "UUID" ] && '
                '[ "$3" = "-o" ] && [ "$4" = "value" ] || exit 1\n'
                f"printf '%s\\n' '{value}'\n",
                executable=True,
            )

        reset(data)
        mounts()
        override_blkid(DATA_UUID)
        a = run(helper, data, DATA_UUID)
        case("RAW_UUID_BACKWARD_COMPAT", a.returncode == 0
             and "APPLIED_0755" in a.stdout
             and mode(data) == 0o755)

        reset(data)
        mounts()
        override_blkid(
            f'/dev/mock-data: LABEL="ROUTER_DATA" UUID="{DATA_UUID}" '
            f'UUID="{ENTWARE_UUID}"'
        )
        a = run(helper, data, DATA_UUID)
        case("DUPLICATE_UUID_TAG_REJECTED", a.returncode != 0
             and mode(data) == 0o777)

        reset(data)
        mounts()
        override_blkid(f'/dev/mock-data: UUID="{DATA_UUID}')
        a = run(helper, data, DATA_UUID)
        case("UNCLOSED_UUID_TAG_REJECTED", a.returncode != 0
             and mode(data) == 0o777)

        reset(data)
        mounts()
        override_blkid(f'/dev/mock-data: UUID={DATA_UUID}')
        a = run(helper, data, DATA_UUID)
        case("UNQUOTED_UUID_TAG_REJECTED", a.returncode != 0
             and mode(data) == 0o777)

        reset(data)
        mounts()
        override_blkid('/dev/mock-data: LABEL="ROUTER_DATA" UUID="INVALID"')
        a = run(helper, data, DATA_UUID)
        case("INVALID_TAGGED_UUID_REJECTED", a.returncode != 0
             and mode(data) == 0o777)

        # Restore a valid UUID from BusyBox's tagged quoted output so all
        # remaining negative tests exercise their intended independent gate.
        override_blkid(f'/dev/mock-data: LABEL="ROUTER_DATA" UUID="{DATA_UUID}"')

        reset(data)
        mounts()
        a = run(helper, data, ENTWARE_UUID)
        case("WRONG_UUID_FAIL_CLOSED", a.returncode != 0
             and mode(data) == 0o777)

        reset(data)
        mounts(include_data=False)
        a = run(helper, data, DATA_UUID)
        case("MISSING_MOUNT_FAIL_CLOSED", a.returncode != 0
             and mode(data) == 0o777)

        reset(data)
        mounts(fs_data="vfat")
        a = run(helper, data, DATA_UUID)
        case("NON_EXT4_FAIL_CLOSED", a.returncode != 0
             and mode(data) == 0o777)

        reset(data)
        mounts(src_data="tmpfs")
        a = run(helper, data, DATA_UUID)
        case("NON_DEVICE_SOURCE_FAIL_CLOSED", a.returncode != 0
             and mode(data) == 0o777)

        reset(data)
        mounts()
        a = run(helper, data, "invalid-uuid")
        case("INVALID_UUID_FAIL_CLOSED", a.returncode != 0
             and mode(data) == 0o777)

        reset(data, 0o1777)
        mounts()
        a = run(helper, data, DATA_UUID)
        case("UNEXPECTED_MODE_FAIL_CLOSED", a.returncode != 0
             and mode(data) == 0o1777)

        reset(data)
        mounts()
        alternate = tmp / "actual-data"
        if alternate.exists():
            shutil.rmtree(alternate)
        data.rename(alternate)
        data.symlink_to(alternate, target_is_directory=True)
        a = run(helper, data, DATA_UUID)
        case("SYMLINK_BLOCKED", a.returncode != 0
             and data.is_symlink() and mode(alternate) == 0o777)
        data.unlink()
        shutil.rmtree(alternate)

        reset(data)
        mounts()
        untrusted_path = mount_root / "OTHER_DISK"
        reset(untrusted_path)
        a = run(helper, untrusted_path, DATA_UUID)
        case("OTHER_MOUNT_SKIPPED", a.returncode == 0
             and "SKIP_UNMANAGED_MOUNT" in a.stdout
             and mode(untrusted_path) == 0o777)

        reset(data)
        mounts()
        altered_owner = tmp / "wrong-owner.sh"
        put(altered_owner, modified.replace(
            f"EXPECTED_OWNER='{os.getuid()}:{os.getgid()}'",
            "EXPECTED_OWNER='2147483646:2147483646'",
        ))
        a = run(altered_owner, data, DATA_UUID)
        case("WRONG_OWNER_FAIL_CLOSED", a.returncode != 0
             and mode(data) == 0o777)

        reset(data)
        mounts()
        put(mock_blkid, "#!/bin/sh\nexit 9\n", executable=True)
        a = run(helper, data, DATA_UUID)
        case("BLKID_FAILURE_FAIL_CLOSED", a.returncode != 0
             and mode(data) == 0o777)

        reset(data)
        mounts()
        # Verify a failing chmod produces no false success. Restore mock blkid.
        put(mock_blkid,
            "#!/bin/sh\n"
            'printf "%s\\n" "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"\n',
            executable=True)
        put(tools / "chmod", "#!/bin/sh\nexit 9\n", executable=True)
        a = run(helper, data, DATA_UUID)
        case("CHMOD_FAILURE_REPORTED", a.returncode != 0
             and mode(data) == 0o777)

    print("FIXTURE_REMOVED=YES")
    print("ROUTER_MOUNTS_TOUCHED=NO")
    print("PRODUCTION_SERVICES_RESTARTED=NO")
    print(f"ISSUE235_POSTMOUNT_LAB={'PASS' if not failures else 'FAIL'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
