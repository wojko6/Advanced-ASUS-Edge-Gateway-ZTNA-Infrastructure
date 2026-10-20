# Issue #235 — original Canonical Manifest C / ZIP provenance V2.5 (2026-10-20)

> **Type:** Source-dependency discovery + standalone **read-only Fedora preflight**. Original C/ZIP not found as actual files in the available Library, so original input attestation is **PENDING OPERATOR FEDORA RUN**. `PRIVILEGED_EXECUTION_TRUST_GATE=HOLD`; `DEPLOYMENT_GATE=HOLD`.

## Provenance

The previously recovered, historic `issue235-trusted-pin-injection-lab-v1.py` specifies two immutable fixed input locations on the operator's Fedora:

- `~/Pobrane/issue235-stageb-manifest-v1-lab/manifest-v1-lab.c`; expected **18,074 bytes**, approved laboratory source SHA-256 `76f6d4eb2adad3c61c87c86231af617f8bd71a4d1867d566657832c60afd3cc9`.
- `~/Pobrane/issue235-stageb-manifest-v1-lab.zip`; bounded **2,000,000 bytes compressed and uncompressed total, at most 30 entries**. Requires exactly one C member whose basename is `manifest-v1-lab.c` with exact matching bytes and exactly one synthetically formatted nine-line baseline manifest.

The original `.c` and ZIP were **not recovered** from the available Library. The earlier Stage B v1.3–v1.5 C/Python source artifacts **were** recovered and hash-checked separately in [V2.4](issue-235-trusted-publisher-evidence-gap-review-v24.md). This is a missing historical prerequisite, not reason to generate substitute C or ZIP bytes.

## New safe V2.5 helper

- Local standalone script: `issue235_original_manifest_readonly_attest_v25.py`.
- SHA-256: `8c1c5af596576911142b599f6361cdafefbb55ea8f233253a22c68b2c625d9aa`.
- **10/10 local synthetic self-tests PASS**: valid synthetic C/ZIP match, changed C, changed ZIP member, duplicate C member, absent synthetic baseline, corrupt ZIP, fixed pin/size/names and no network/process dependency.
- `--audit` **NOT RUN on operator Fedora**. Runs as nonroot only. No arguments allow arbitrary external file paths. Opens fixed inputs using `O_NOFOLLOW`, directory descriptors, bounded reads and before/after metadata; checks the original source pin, ZIP source byte match, and unique synthetic baseline.
- **No extraction, compilation, process execution, `sudo`, SSH, router read, Cron, JFFS, SSD or RouterCloud changes.** Reports sanitized status and `HOLD` when prerequisites are missing.
- Success would be a **point-in-time source identity proof for the *SSD PR #245* historical laboratory only**, not an independent signed operator trust root, approved two-script manifest, actual ARMv7/JFFS2 publisher or production authorization. A passed metadata snapshot does not prove continuous protection against same-UID writers.

Run on operator Fedora after checksum verification:

```bash
cd ~/Pobrane
printf '%s  %s\n' '8c1c5af596576911142b599f6361cdafefbb55ea8f233253a22c68b2c625d9aa' 'issue235_original_manifest_readonly_attest_v25.py' | sha256sum -c - &&
python3 -B issue235_original_manifest_readonly_attest_v25.py --self-test &&
python3 -B issue235_original_manifest_readonly_attest_v25.py --audit
echo "ATTESTATION_EXIT_CODE=$?"
```

**No artifact substitution or automatic fixes on failure.** Reuse the original pinned files or retain `ORIGINAL_C_ZIP_ATTESTATION=HOLD`. The three-role SSD Stage B contract (scope `pr245-ssd-mount-roots`) must **not** authorize `services-start` / `dns-guard` publication under Issue #235. All deployment gates remain HOLD.
