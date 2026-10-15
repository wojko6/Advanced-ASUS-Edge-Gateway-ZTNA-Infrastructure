#!/usr/bin/env python3
"""Unprivileged synthetic post-mount composition test for Issue #235.

Mocks post-mount, swap, AMTM, mounts, blkid, and private UUIDs under /tmp.
Does not execute or read the real private ASUS hook or actual block devices.
"""
import os
from pathlib import Path
import stat
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]
HELPER = REPO / "router/scripts/issue235-ssd-mount-mode"
SNIPPET = REPO / "router/scripts/issue235-postmount-integration.snippet"
UUID_D = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
UUID_E = "11111111-2222-3333-4444-555555555555"


def write(p, s, perms=None):
    p.write_text(s, encoding="utf-8")
    if perms is not None:
        p.chmod(perms)


def main():
    helper = HELPER.read_text(encoding="utf-8")
    snippet = SNIPPET.read_text(encoding="utf-8")
    fails = 0

    def verify(label, success):
        nonlocal fails
        print(f"{label}={'PASS' if success else 'FAIL'}")
        if not success:
            fails += 1

    with tempfile.TemporaryDirectory(prefix="issue235-composed-") as td:
        root = Path(td)
        mount_root = root / "mnt"
        mount_root.mkdir()
        paths = {name: mount_root / name for name in ("ROUTER_DATA", "ENTWARE", "OTHER")}
        for p in paths.values():
            p.mkdir()
            p.chmod(0o777)

        private = root / "private"
        private.mkdir(mode=0o700)
        write(private / "router-data.uuid", UUID_D + "\n", 0o600)
        write(private / "entware.uuid", UUID_E + "\n", 0o600)
        tools = root / "tools"
        tools.mkdir()
        table = root / "mounts"
        events = root / "events"
        script = root / "fake-post-mount.sh"
        amtm = root / "fake-amtm.sh"
        staged_helper = root / "mode-helper"

        write(table, "\n".join([
            f"/dev/mock-data {paths['ROUTER_DATA']} ext4 rw 0 0",
            f"/dev/mock-entware {paths['ENTWARE']} ext4 rw 0 0",
            f"/dev/mock-other {paths['OTHER']} ext4 rw 0 0",
        ]) + "\n")
        write(tools / "blkid", (
            "#!/bin/sh\n"
            'case "$5" in\n'
            f'  /dev/mock-data) printf \'%s\\n\' \'/dev/mock-data: LABEL="ROUTER_DATA" UUID="{UUID_D}"\' ;;\n'
            f'  /dev/mock-entware) printf \'%s\\n\' \'/dev/mock-entware: LABEL="ENTWARE" UUID="{UUID_E}"\' ;;\n'
            "  *) exit 9 ;;\n"
            "esac\n"
        ), 0o755)
        write(tools / "swapon", (
            "#!/bin/sh\n"
            'printf "SWAP\\n" >> "$ISSUE235_LAB_EVENTS"\n'
        ), 0o755)
        write(amtm, (
            'printf "AMTM:%s\\n" "$(stat -c %a "$1")" >> "$ISSUE235_LAB_EVENTS"\n'
        ))

        # Isolated firmware-shaped numeric ls output; no host BusyBox needed.
        mock_busybox = tools / "busybox"
        write(mock_busybox, (
            "#!/usr/bin/env python3\n"
            "import os, stat, sys\n"
            "if len(sys.argv) != 4 or sys.argv[1:3] != ['ls', '-ldn']:\n"
            "    sys.exit(2)\n"
            "path = sys.argv[3]\n"
            "metadata = os.lstat(path)\n"
            "print(f'{stat.filemode(metadata.st_mode)} 2 "
            "{metadata.st_uid} {metadata.st_gid} {metadata.st_size} "
            "Jan 01 00:00 {path}')\n"
        ), 0o755)
        write(tools / "chmod", '#!/bin/sh\nexec /bin/chmod "$@"\n', 0o755)

        for before, after in (
            ("BUSYBOX_BIN='/bin/busybox'", f"BUSYBOX_BIN='{mock_busybox}'"),
            ("BLKID_BIN='/sbin/blkid'", f"BLKID_BIN='{tools / 'blkid'}'"),
            ("CHMOD_BIN='/bin/chmod'", f"CHMOD_BIN='{tools / 'chmod'}'"),
            ("MOUNT_ROOT='/tmp/mnt'", f"MOUNT_ROOT='{mount_root}'"),
            ("MOUNT_TABLE='/proc/mounts'", f"MOUNT_TABLE='{table}'"),
            ("PATH=/usr/sbin:/usr/bin:/sbin:/bin", f"PATH={tools}:/usr/sbin:/usr/bin:/sbin:/bin"),
            ("EXPECTED_OWNER='0:0'", f"EXPECTED_OWNER='{os.getuid()}:{os.getgid()}'"),
        ):
            assert helper.count(before) == 1, f"Helper contract drift: {before}"
            helper = helper.replace(before, after)
        write(staged_helper, helper, 0o755)

        for before, after in (
            ("ISSUE235_SSD_HELPER='/jffs/addons/asus-edge/bin/issue235-ssd-mount-mode'",
             f"ISSUE235_SSD_HELPER='{staged_helper}'"),
            ("ISSUE235_SSD_UUID_ROOT='/jffs/addons/asus-edge/private'",
             f"ISSUE235_SSD_UUID_ROOT='{private}'"),
            ("/tmp/mnt/ROUTER_DATA", str(paths["ROUTER_DATA"])),
            ("/tmp/mnt/ENTWARE", str(paths["ENTWARE"])),
        ):
            assert snippet.count(before) >= 1, f"Snippet contract drift: {before}"
            snippet = snippet.replace(before, after)

        # Synthetic control flow models the observed nested IFs closed
        # before the free insertion slot, and sourced AMTM afterwards.
        fixture = (
            "#!/bin/sh\n"
            'if [ -n "${1-}" ]; then\n'
            '  if [ -f "$1/myswap.swp" ]; then\n'
            '    swapon "$1/myswap.swp" >/dev/null 2>&1\n'
            '  fi\n'
            'fi\n'
            'if [ -n "${1-}" ]; then :; else :; fi\n'
            + snippet + "\n"
            + f'. "{amtm}"\n'
            + 'printf "END\\n" >> "$ISSUE235_LAB_EVENTS"\n'
        )
        write(script, fixture, 0o755)
        syntax = subprocess.run(["/bin/sh", "-n", str(script)], capture_output=True)
        verify("COMPOSED_SHELL_SYNTAX", syntax.returncode == 0)
        verify("SWAP_BEFORE_HELPER_BEFORE_AMTM_TEXT",
               fixture.index("swapon") < fixture.index("ISSUE235_SSD_HELPER=")
               < fixture.index(f'. "{amtm}"'))

        def run(path, swap=True):
            events.write_text("", encoding="utf-8")
            swapfile = path / "myswap.swp"
            if swap:
                swapfile.touch(exist_ok=True)
            elif swapfile.exists():
                swapfile.unlink()
            env = dict(os.environ, PATH=f"{tools}:/usr/sbin:/usr/bin:/sbin:/bin",
                       ISSUE235_LAB_EVENTS=str(events))
            out = subprocess.run(["/bin/sh", str(script), str(path)],
                                 env=env, capture_output=True, text=True,
                                 timeout=8, check=False)
            return out.returncode, out.stdout, events.read_text(
                encoding="utf-8").splitlines()

        for name in ("ROUTER_DATA", "ENTWARE"):
            p = paths[name]
            p.chmod(0o777)
            code, stdout, history = run(p)
            verify(name + "_HARDEN_BEFORE_AMTM",
                   code == 0 and stat.S_IMODE(p.stat().st_mode) == 0o755
                   and "ISSUE235_MOUNT_MODE=APPLIED_0755" in stdout
                   and history == ["SWAP", "AMTM:755", "END"])

        code, stdout, history = run(paths["ROUTER_DATA"])
        verify("ALREADY_HARDENED_IDEMPOTENT",
               code == 0 and "ISSUE235_MOUNT_MODE=ALREADY_0755" in stdout
               and history == ["SWAP", "AMTM:755", "END"])

        # A failed UUID gate must never prevent swap or AMTM startup.
        data = paths["ROUTER_DATA"]
        data.chmod(0o777)
        write(private / "router-data.uuid", UUID_E + "\n", 0o600)
        code, stdout, history = run(data)
        verify("WRONG_UUID_NO_CHMOD_AMTM_CONTINUES",
               code == 0 and stat.S_IMODE(data.stat().st_mode) == 0o777
               and "ISSUE235_POSTMOUNT_REPAIR=REVIEW" in stdout
               and history == ["SWAP", "AMTM:777", "END"])

        (private / "router-data.uuid").unlink()
        code, stdout, history = run(data)
        verify("MISSING_UUID_NO_CHMOD_AMTM_CONTINUES",
               code == 0 and stat.S_IMODE(data.stat().st_mode) == 0o777
               and "ISSUE235_POSTMOUNT_REPAIR=NOT_READY" in stdout
               and history == ["SWAP", "AMTM:777", "END"])

        write(private / "external-uuid", UUID_D + "\n", 0o600)
        (private / "router-data.uuid").symlink_to(private / "external-uuid")
        code, stdout, history = run(data)
        verify("SYMLINK_UUID_REJECTED_AMTM_CONTINUES",
               code == 0 and stat.S_IMODE(data.stat().st_mode) == 0o777
               and "ISSUE235_POSTMOUNT_REPAIR=NOT_READY" in stdout
               and history == ["SWAP", "AMTM:777", "END"])

        other = paths["OTHER"]
        code, stdout, history = run(other, swap=False)
        verify("OTHER_MOUNT_LEFT_UNCHANGED",
               code == 0 and stat.S_IMODE(other.stat().st_mode) == 0o777
               and "ISSUE235_POSTMOUNT_REPAIR" not in stdout
               and history == ["AMTM:777", "END"])

    print("FIXTURE_REMOVED=YES")
    print("REAL_ASUS_HOOK_READ_OR_MODIFIED=NO")
    print("REAL_SSD_AND_SWAP_TOUCHED=NO")
    print(f"ISSUE235_POSTMOUNT_COMPOSED_LAB={'PASS' if not fails else 'FAIL'}")
    return 1 if fails else 1 if syntax.returncode else 0


if __name__ == "__main__":
    raise SystemExit(main())
