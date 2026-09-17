#!/usr/bin/env python3
"""Execute production shell scripts against disposable filesystem fixtures.

Only filesystem roots, command lookup and the UID probe are redirected in the
test copies. No installer, restore or healthcheck touches the host router paths.
"""
import hashlib
import io
import os
import re
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.commands = self.root / "commands"
        self.commands.mkdir()
        for directory in ("scripts", "router", "config"):
            shutil.copytree(REPO / directory, self.project / directory)
        for directory in ("jffs/scripts", "jffs/configs", "opt/etc/unbound", "tmp"):
            (self.root / directory).mkdir(parents=True)
        self.command("service", "exit 0")

    def command(self, name, body):
        path = self.commands / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def script(self, name):
        path = self.project / "scripts" / name
        content = path.read_text()
        content = re.sub(r"(?<![A-Za-z0-9_}])/(?:jffs|opt|tmp)",
                         lambda match: str(self.root) + match.group(), content)
        content = content.replace('"/$destination/"', '"' + str(self.root) + '/$destination/"')
        content = content.replace('live_path="/$relative_path"',
                                  'live_path="' + str(self.root) + '/$relative_path"')
        content = content.replace('uid="$(current_uid)"', 'uid="0"')
        content = content.replace(
            'PATH="' + str(self.root) + '/opt/sbin:',
            'PATH="' + str(self.commands) + ':' + str(self.root) + '/opt/sbin:')
        content = content.replace("for executable_dir in ",
                                  "for executable_dir in " + shlex.quote(str(self.commands)) + " ")
        path.write_text(content)
        return path

    def run_script(self, path, *args, env=None):
        test_env = dict(os.environ)
        test_env["EDGE_TEST_ROOT"] = str(self.root)
        test_env.update(env or {})

        return subprocess.run(["sh", str(path), *map(str, args)],
                              capture_output=True, text=True,
                              env=test_env, timeout=20)

    def archive(self, files, manifest=None, link=False):
        if manifest is None:
            manifest = "".join(hashlib.sha256(data).hexdigest() + "  ./" + name + "\n"
                               for name, data in files.items())
        archive = self.root / "backup.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            for name, data in dict(files, SHA256SUMS=manifest.encode()).items():
                entry = tarfile.TarInfo("snapshot/" + name)
                entry.size = len(data)
                entry.mode = 0o600
                tar.addfile(entry, io.BytesIO(data))
            if link:
                entry = tarfile.TarInfo("snapshot/jffs/link")
                entry.type = tarfile.SYMTYPE
                entry.linkname = "/etc/passwd"
                tar.addfile(entry)
        return archive

    def test_restore_valid_and_unlisted_payload(self):
        restore = self.script("restore.sh")
        files = {"jffs/configs/asus-edge.conf": b"original\n"}
        valid = self.run_script(restore, self.archive(files), "--apply")
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual((self.root / "jffs/configs/asus-edge.conf").read_bytes(), b"original\n")
        manifest = hashlib.sha256(b"ok\n").hexdigest() + "  README.txt\n"
        invalid = self.run_script(restore, self.archive({
            "README.txt": b"ok\n", "jffs/configs/unlisted": b"extra\n"}, manifest))
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("every payload file", invalid.stderr)

    def test_restore_rejects_unsafe_manifest_and_links(self):
        restore = self.script("restore.sh")
        for path in ("../outside", "/etc/passwd", "jffs/../outside"):
            with self.subTest(path=path):
                manifest = "0" * 64 + "  " + path + "\n"
                result = self.run_script(restore, self.archive({"README.txt": b"ok"}, manifest))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("invalid manifest", result.stderr)
        result = self.run_script(restore, self.archive({"README.txt": b"ok"}, link=True))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("regular files", result.stderr)

    def test_restore_snapshot_failure_does_not_start_apply(self):
        restore = self.script("restore.sh")
        live = self.root / "jffs/configs/asus-edge.conf"
        live.write_text("before\n")
        files = {"jffs/configs/asus-edge.conf": b"after\n"}
        self.command("cp", "exit 1")
        result = self.run_script(restore, self.archive(files), "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("restore not started", result.stderr)
        self.assertEqual(live.read_text(), "before\n")
        self.assertNotIn("Restore completed", result.stdout)

    def test_restore_partial_apply_rolls_back_all_previous_files(self):
        restore = self.script("restore.sh")
        jffs_file = self.root / "jffs/configs/asus-edge.conf"
        opt_file = self.root / "opt/etc/unbound/unbound.conf"
        jffs_file.write_text("old-jffs\n")
        opt_file.write_text("old-opt\n")
        files = {
            "jffs/configs/asus-edge.conf": b"new-jffs\n",
            "opt/etc/unbound/unbound.conf": b"new-opt\n",
        }
        counter = self.root / "cp-count"
        self.command("cp", f'''count=0
[ ! -f {shlex.quote(str(counter))} ] || count="$(cat {shlex.quote(str(counter))})"
count=$((count + 1))
printf '%s\\n' "$count" > {shlex.quote(str(counter))}
if [ "$count" -eq 4 ]; then
    exit 1
fi
exec /bin/cp "$@"
''')
        result = self.run_script(restore, self.archive(files), "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rolling back pre-restore state", result.stderr)
        self.assertIn("Rollback completed", result.stderr)
        self.assertEqual(jffs_file.read_text(), "old-jffs\n")
        self.assertEqual(opt_file.read_text(), "old-opt\n")
        self.assertNotIn("Restore completed", result.stdout)

    def test_backup_restore_roundtrip(self):
        config = self.root / "jffs/configs/asus-edge.conf"
        config.write_text("EDGE_ALLOW_ROUTER_SSH=0\n")
        backup = self.run_script(self.script("backup.sh"), self.root / "backups")
        self.assertEqual(backup.returncode, 0, backup.stderr)
        archive = backup.stdout.strip()
        config.write_text("changed\n")
        restore = self.run_script(self.script("restore.sh"), archive, "--apply")
        self.assertEqual(restore.returncode, 0, restore.stderr)
        self.assertEqual(config.read_text(), "EDGE_ALLOW_ROUTER_SSH=0\n")

    def test_backup_copy_failure_is_not_success(self):
        (self.root / "jffs/configs/asus-edge.conf").write_text("config\n")
        self.command("cp", "exit 1")
        result = self.run_script(self.script("backup.sh"), self.root / "backups")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(list((self.root / "backups").glob("*.tar.gz")))

    def prepare_install(self):
        (self.project / "config/edge.conf").write_text("EDGE_RUN_LEGACY_HOOKS=0\n")
        (self.project / "router/scripts/firewall-start").write_text("#!/bin/sh\nexit 1\n")
        return self.script("install.sh")

    def test_failed_upgrade_restores_all_previous_files(self):
        previous = {
            "jffs/configs/asus-edge.conf": "OLD=1\n",
            "jffs/scripts/firewall-start": "#!/bin/sh\n# ASUS_EDGE_MANAGED_HOOK\nexit 0\n",
            "jffs/scripts/services-start": "#!/bin/sh\n# ASUS_EDGE_MANAGED_HOOK\nexit 0\n",
            "jffs/addons/asus-edge/bin/firewall-start": "old firewall\n",
            "jffs/addons/asus-edge/bin/services-start": "old services\n",
            "jffs/addons/asus-edge/legacy/firewall-start": "old legacy\n",
        }
        for name, content in previous.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            path.chmod(0o700)
        result = self.run_script(self.prepare_install(), "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("restoring complete snapshot", result.stderr)
        for name, content in previous.items():
            self.assertEqual((self.root / name).read_text(), content, name)
            self.assertEqual((self.root / name).stat().st_mode & 0o777, 0o700)
        self.assertFalse((self.root / "jffs/addons/asus-edge/bin/healthcheck.sh").exists())

    def test_failed_first_install_removes_new_live_files(self):
        result = self.run_script(self.prepare_install(), "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("restoring complete snapshot", result.stderr)
        for name in ("jffs/configs/asus-edge.conf", "jffs/scripts/firewall-start",
                     "jffs/scripts/services-start", "jffs/addons/asus-edge/bin",
                     "jffs/addons/asus-edge/legacy"):
            self.assertFalse((self.root / name).exists(), name)

    def test_snapshot_failure_does_not_change_existing_config(self):
        config = self.root / "jffs/configs/asus-edge.conf"
        config.write_text("old\n")
        self.command("cp", "exit 1")
        result = self.run_script(self.prepare_install(), "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(config.read_text(), "old\n")
        self.assertFalse((self.root / "jffs/scripts/firewall-start").exists())

    def test_symlink_hook_is_rejected_without_touching_target(self):
        target = self.root / "outside-target"
        target.write_text("DO NOT TOUCH\n")
        hook = self.root / "jffs/scripts/firewall-start"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.symlink_to(target)
        result = self.run_script(self.prepare_install())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite symlink", result.stderr)
        self.assertTrue(hook.is_symlink())
        self.assertEqual(hook.resolve(), target)
        self.assertEqual(target.read_text(), "DO NOT TOUCH\n")

    def test_symlink_install_file_is_rejected_without_touching_target(self):
        target = self.root / "outside-config-target"
        target.write_text("DO NOT TOUCH\n")
        config = self.root / "jffs/configs/asus-edge.conf"
        config.parent.mkdir(parents=True, exist_ok=True)
        if config.exists() or config.is_symlink():
            config.unlink()
        config.symlink_to(target)
        result = self.run_script(self.prepare_install())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite symlink", result.stderr)
        self.assertTrue(config.is_symlink())
        self.assertEqual(config.resolve(), target)
        self.assertEqual(target.read_text(), "DO NOT TOUCH\n")

    def test_healthcheck_detects_bypass_and_missing_drop(self):
        for name in ("opkg", "ip", "unbound-control"):
            self.command(name, "exit 0")
        self.command("pidof", r'''
case "$1" in
    tailscaled|unbound|syslog-ng) exit 0 ;;
    lpd|u2ec)
        case "$SCENARIO:$1" in
            lpd_running:lpd|u2ec_running:u2ec) exit 0 ;;
            *) exit 1 ;;
        esac ;;
    *) exit 1 ;;
esac
''')
        self.command("nvram", r'''
if [ "$1" = get ] && [ "$2" = usb_printer ]; then
    [ "$SCENARIO" = usb_printer_enabled ] && echo 1 || echo 0
    exit 0
fi
exit 1
''')
        self.command("netstat", r'''
echo 'Active Internet connections (only servers)'
echo 'Proto Recv-Q Send-Q Local Address           Foreign Address         State'
[ "$SCENARIO" = port515_open ] && echo 'tcp        0      0 192.168.50.1:515        0.0.0.0:*               LISTEN'
exit 0
''')
        self.command("tailscale", r"""
case " $* " in
    *" debug prefs "*)
        if [ "$SCENARIO" = "netfilter_on" ]; then
            echo '"NetfilterMode": 2,'
        else
            echo '"NetfilterMode": 0,'
        fi
        ;;
esac
exit 0
""")
        self.command("dig", "echo ';; flags: qr rd ra ad;' ")
        opkg = self.root / "opt/bin/opkg"
        opkg.parent.mkdir(parents=True)
        opkg.write_text("#!/bin/sh\nexit 0\n")
        opkg.chmod(0o755)
        (self.root / "opt/etc/unbound/unbound.conf").write_text("# fixture\n")
        config = self.root / "jffs/configs/asus-edge.conf"
        config.write_text('EDGE_INTERCEPT_DNS=0\nEDGE_REQUIRE_SWAP=0\n'
                          'EDGE_PRINTER_TS_SOURCES="192.0.2.95/32"\n'
                          'EDGE_PRINTER_LAN_IP="198.51.100.140"\n'
                          'EDGE_PRINTER_TCP_PORTS="80"\nEDGE_PRINTER_UDP_PORTS=" "\n')
        self.command("iptables", r'''
chain="$4"
case "$chain" in
    INPUT|FORWARD)
        [ "$SCENARIO" != "bypass" ] || echo "-A $chain -j ACCEPT"
        suffix="$chain"
        echo "-A $chain -i tailscale0 -j EDGE_TS_$suffix" ;;
    PREROUTING) echo '-A PREROUTING -i tailscale0 -j EDGE_TS_PREROUTING' ;;
    ts-input|ts-forward|ts-postrouting)
        [ "$SCENARIO" = "native_chain" ] && exit 0
        exit 1 ;;
    EDGE_TS_INPUT|EDGE_TS_FORWARD)
        echo "-A $chain -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT"
        if [ "$chain" = EDGE_TS_FORWARD ]; then
            port=80
            [ "$SCENARIO" != wrong_port ] || port=8080
            echo "-A $chain -s 192.0.2.95/32 -d 198.51.100.140/32 -i tailscale0 -o br0 -p tcp --dport $port -j ACCEPT"
        fi
        [ "$SCENARIO" = missing_drop ] || echo "-A $chain -j DROP" ;;
esac
exit 0
''')
        self.command("ip6tables", r'''
case "$4" in
    INPUT|FORWARD) echo "-A $4 -i tailscale0 -j EDGE_TS6_$4" ;;
    EDGE_TS6_INPUT|EDGE_TS6_FORWARD) echo "-A $4 -j DROP" ;;
esac
''')
        health = self.script("healthcheck.sh")
        for scenario, expected in (
                ("valid", "Summary: 0 failure(s)"),
                ("netfilter_on", "Tailscale netfilter mode is not off"),
                ("native_chain", "competing Tailscale netfilter chains present: 3"),
                ("bypass", "is not the first parent rule"),
                ("missing_drop", "missing terminal DROP"),
                ("wrong_port", "missing printer TCP/80 rule"),
                ("usb_printer_enabled", "ASUS USB print server enabled or unknown in NVRAM: 1"),
                ("lpd_running", "lpd process running"),
                ("u2ec_running", "u2ec process running"),
                ("port515_open", "router TCP/515 listener present")):
            with self.subTest(scenario=scenario):
                result = self.run_script(health, env={"SCENARIO": scenario})
                self.assertIn(expected, result.stdout, result.stderr)
                self.assertEqual(result.returncode == 0, scenario == "valid", result.stdout)


if __name__ == "__main__":
    unittest.main()
