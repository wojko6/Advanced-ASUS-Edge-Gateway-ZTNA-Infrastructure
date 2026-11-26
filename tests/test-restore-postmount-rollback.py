#!/usr/bin/env python3
"""Issue #276: synthetic RED mutation control + GREEN alternate-root rollback.

Runs only with a disposable target under /tmp, without sudo, router access
or real backup archives. Fault injection affects a temporary script copy.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

RESTORE = Path(__file__).resolve().parent.parent / "scripts" / "restore.sh"
APPLICABLE = 'done <"$APPLICABLE_MANIFEST"'
ORIGINAL = 'done <"$TMP_DIR/manifest-paths"'
COPY = '        if ! cp -Rp "$ROOT/$destination/." "$target_destination"; then'
INJECT = "ISSUE276_SYNTHETIC_SECOND_COPY_FAILURE"


def check(value, label):
    if not value:
        raise AssertionError(label)
    print("PASS: " + label)


def archive_and_target(case, legacy, reference, live_hook):
    payload = case / "payload" / "synthetic-archive"
    (payload / "jffs" / "configs").mkdir(parents=True)
    (payload / "opt" / "etc").mkdir(parents=True)
    (payload / "jffs" / "configs" / "unit.conf").write_text("UPDATED_JFFS\n")
    (payload / "opt" / "etc" / "unit.conf").write_text("UPDATED_OPT\n")
    if legacy:
        d = payload / "jffs" / "scripts"
        d.mkdir()
        (d / "post-mount").write_text("ARCHIVED_LEGACY_HOOK\n")
    if reference:
        d = payload / "recovery-reference" / "jffs" / "scripts"
        d.mkdir(parents=True)
        (d / "post-mount").write_text("REFERENCE_ONLY_HOOK\n")
    files = sorted(p for p in payload.rglob("*") if p.is_file())
    (payload / "SHA256SUMS").write_text("".join(
        hashlib.sha256(p.read_bytes()).hexdigest() + "  "
        + p.relative_to(payload).as_posix() + "\n" for p in files
    ))
    archive = case / "synthetic.tar.gz"
    with tarfile.open(archive, "w:gz") as writer:
        writer.add(payload, arcname=payload.name)

    target = case / "alternate-root"
    (target / "jffs" / "scripts").mkdir(parents=True)
    (target / "jffs" / "configs").mkdir(parents=True)
    (target / "opt" / "etc").mkdir(parents=True)
    files = {
        "jffs": target / "jffs" / "configs" / "unit.conf",
        "opt": target / "opt" / "etc" / "unit.conf",
        "hook": target / "jffs" / "scripts" / "post-mount",
    }
    files["jffs"].write_text("ORIGINAL_JFFS\n")
    files["opt"].write_text("ORIGINAL_OPT\n")
    if live_hook:
        files["hook"].write_text("ORIGINAL_LIVE_HOOK\n")
    return archive, target, files


def run_case(root, source, label, *, legacy, reference=False, live_hook=True,
             failure=False, negative_control=False):
    folder = root / label
    folder.mkdir(mode=0o700)
    archive, target, files = archive_and_target(folder, legacy, reference, live_hook)
    before = {k: p.read_bytes() if p.exists() else None for k, p in files.items()}
    if failure:
        check(source.count(COPY) == 1, label + " injection anchor")
        # Inject failure immediately before the OPT copy, after JFFS has copied.
        source = source.replace(COPY,
            '        if [ "$destination" = "opt" ]; then\n'
            '            echo "' + INJECT + '" >&2\n'
            '            rollback_restore || true\n'
            '            exit 1\n'
            '        fi\n' + COPY)
    script = folder / "restore-fixture.sh"
    script.write_text(source)
    check(subprocess.run(["sh", "-n", str(script)], capture_output=True).returncode == 0,
          label + " POSIX syntax")
    env = dict(os.environ)
    env["EDGE_RESTORE_ROOT"] = str(target)
    output = subprocess.run(["sh", str(script), str(archive), "--apply"],
                            cwd=folder, env=env, capture_output=True,
                            text=True, timeout=30)
    after = {k: p.read_bytes() if p.exists() else None for k, p in files.items()}
    check((output.returncode != 0) == failure, label + " exit status")
    check((INJECT in output.stderr) == failure, label + " controlled second-copy failure")
    check((after["jffs"] == before["jffs"]) == failure, label + " JFFS state")
    check((after["opt"] == before["opt"]) == failure, label + " OPT state")
    if negative_control:
        check(before["hook"] is not None and after["hook"] is None,
              label + " RED: old rollback deleted existing hook")
        check("rollback encountered errors" in output.stderr,
              label + " RED: missing snapshot")
    else:
        check(after["hook"] == before["hook"], label + " original hook unchanged")
        if failure:
            check("Rollback completed; pre-restore state recovered." in output.stderr,
                  label + " GREEN: rollback completed")
            check("rollback encountered errors" not in output.stderr,
                  label + " GREEN: no missing snapshot")
        else:
            check("Restore completed." in output.stdout, label + " normal restore")
    check(not (target / "recovery-reference").exists(),
          label + " reference not automatically applied")


def main():
    if not sys.platform.startswith("linux") or os.geteuid() == 0:
        print("FAIL: requires nonroot Linux", file=sys.stderr)
        return 2
    check(RESTORE.is_file() and not RESTORE.is_symlink(),
          "regular repository restore script")
    original_hash = hashlib.sha256(RESTORE.read_bytes()).hexdigest()
    source = RESTORE.read_text()
    check(source.count(APPLICABLE) == 2,
          "both rollback and snapshot use applicable paths")
    check('jffs/scripts/post-mount" &&' in source,
          "review-only hook excluded from applicable paths")
    check(source.count('jffs/scripts/post-mount) continue ;;') == 1,
          "snapshot loop retains explicit hook skip")
    check(source.count(COPY) == 1, "copy loop uniquely identified")
    # Negative mutation-control reinstates the historical bad rollback only
    # inside a synthetic script copy, never in the repository source.
    pos = source.rfind(APPLICABLE)
    check(pos >= 0, "rollback input located")
    regressed = source[:pos] + ORIGINAL + source[pos + len(APPLICABLE):]
    with tempfile.TemporaryDirectory(prefix="issue276-pr-regression-", dir="/tmp") as temp:
        root = Path(temp).resolve(strict=True)
        check(root.parent == Path("/tmp") and root.name.startswith("issue276-pr-regression-"),
              "test root confined to disposable /tmp directory")
        root.chmod(0o700)
        run_case(root, regressed, "red-control", legacy=True,
                 failure=True, negative_control=True)
        run_case(root, source, "legacy-failure", legacy=True, failure=True)
        run_case(root, source, "legacy-success", legacy=True)
        run_case(root, source, "reference-failure", legacy=False,
                 reference=True, failure=True)
        run_case(root, source, "absent-hook-failure", legacy=False,
                 live_hook=False, failure=True)
        run_case(root, source, "absent-hook-success", legacy=False, live_hook=False)
    check(hashlib.sha256(RESTORE.read_bytes()).hexdigest() == original_hash,
          "repository source unchanged by tests")
    print("ISSUE276=PASS_FEDORA_ROOTLESS_MUTATION_AND_ROLLBACK_REGRESSION")
    print("ASUS_CONTACTED=NO")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, OSError, subprocess.TimeoutExpired, tarfile.TarError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
