# Polish ASUS WebUI localization overlay

## Scope

Issue #133 tracks a project-owned Polish localization layer for the ASUS/GNUton
WebUI used by the reference TUF-AX5400.

The complete firmware WebUI resources are **not** stored in this repository.
Source control contains only project-authored localization metadata and unified
patch deltas. During installation or update, the project reconstructs the
version-pinned Polish artifacts from the exact firmware baseline and verifies
their expected SHA-256 hashes before they can be used.

Reference baseline:

- firmware: `3004.388.11_1-gnuton1_tuf`;
- `EN.dict`: 4686 lines, SHA-256
  `6ef410026f3237503d245ce6fd5b4e6c82ee7887deda62f10cb34b6454c12567`;
- `PL.dict`: 4686 lines, SHA-256
  `cad0a4766bfd2bb7e0faa0fc63638b84ab65ee30bc56b0b5755b7e32f7506719`.

The dictionaries are positional resources. A line insertion or deletion would
shift every following translation, so line-count and baseline-hash checks are
hard gates.

## Safety model

`scripts/asus-webui-pl-overlay.py` refuses to build against an unrecognized
baseline. For every reviewed override it also preserves the source line's:

- HTML tag sequence and attributes;
- HTML entities;
- printf-style placeholders;
- `$name$` placeholders;
- `ZV...VZ` firmware tokens;
- literal escaped `\\n` tokens.

The generated dictionary must keep all 4686 positions, UTF-8 BOM and the
baseline trailing-newline contract.

This does not write to `/www`, flash storage or the firmware image.

## Local workflow on Fedora

Collect the exact dictionaries from the router:

```bash
mkdir -p /tmp/asus-webui-i18n

scp -P 1122 admin1@192.168.50.1:/www/EN.dict \
  /tmp/asus-webui-i18n/EN.dict
scp -P 1122 admin1@192.168.50.1:/www/PL.dict \
  /tmp/asus-webui-i18n/PL.dict
```

Audit the pinned baseline:

```bash
python3 scripts/asus-webui-pl-overlay.py audit \
  /tmp/asus-webui-i18n/EN.dict \
  /tmp/asus-webui-i18n/PL.dict
```

Build a candidate:

```bash
python3 scripts/asus-webui-pl-overlay.py build \
  /tmp/asus-webui-i18n/EN.dict \
  /tmp/asus-webui-i18n/PL.dict \
  /tmp/asus-webui-i18n/PL.generated.dict
```

Verify it independently:

```bash
python3 scripts/asus-webui-pl-overlay.py verify \
  /tmp/asus-webui-i18n/EN.dict \
  /tmp/asus-webui-i18n/PL.dict \
  /tmp/asus-webui-i18n/PL.generated.dict
```

This Fedora workflow remains the authoring and review path for dictionary
changes. The production installation path uses the reviewed unified patches and
the fail-closed router-side builder described below.

## Initial reviewed batch

`config/asus-webui-pl-overrides.json` contains the first reviewed correction
batch. It includes high-visibility untranslated UI strings and repairs known
mixed/structurally broken Polish entries, including the duplicated
English+Polish Trend Micro notice and the missing opening `<p>` in the DDNS
description.

The manifest contains only project-authored Polish replacement text plus line
numbers and baseline metadata. It does not contain a copy of either firmware
dictionary.

## Firmware upgrades

A firmware update that changes either dictionary hash intentionally causes the
build to stop. The new dictionaries must be collected, line alignment audited
again, and the manifest rebased before any overlay is enabled.

## Repository patch artifacts

The repository stores reviewed unified deltas under:

```text
router/webui/patches/PL.dict.patch
router/webui/patches/help.js.patch
router/webui/patches/Tools_Sysinfo.asp.patch
router/webui/patches/Tools_OtherSettings.asp.patch
```

These are deltas against the pinned ASUS/GNUton firmware resources, not copies
of the complete firmware files.

`router/scripts/webui-pl-build` applies the patches with GNU `patch` during
installation or update. The builder is fail-closed:

- every input firmware resource must match its pinned baseline SHA-256 or the
  already validated Polish SHA-256;
- every generated result must match its exact expected Polish SHA-256;
- an unknown firmware/resource revision aborts the build instead of applying a
  fuzzy or unverified modification;
- `patch` is required during installation/update only and is not a boot-time
  dependency.

The validated Polish artifact hashes are:

```text
PL.dict                  4af3d9df6633a1885b949c2d6f7bfa35663a867990230daf35a0f3319ab90bcb
help.js                  7da975a69b1237499ee238e93ede215c3e235c5b34a5d87ab507d45a4e063778
Tools_Sysinfo.asp        3dbef5d95c02561baf920a6b2014ed34d021eb5ce6723c076ddecf9072d839df
Tools_OtherSettings.asp  6cee7405bcc556ac3af1baee418a2ffa85cad39b37c3f76e340ef2a8297595c6
```

## Runtime persistence

Generated resources are stored below
`/jffs/addons/asus-edge/webui/pl/`. At runtime,
`router/scripts/webui-pl-mount` validates the prepared files and exposes them
through bind mounts over the corresponding WebUI resources.

The early-boot mount path deliberately does **not** depend on Entware GNU
`patch`. SHA-256 verification can use the firmware-provided
`/usr/sbin/openssl`, allowing localization to be mounted before `/opt` becomes
available.

The project `webui-mount` lifecycle integrates the localization helper:

- mount the project Edge Gateway page and menu integration;
- activate the validated Polish WebUI overlay;
- localize the generated Merlin menu tree without replacing its inode;
- remove the Polish bind mounts before releasing the project WebUI integration
  during unmount/uninstall.

## Validation

The reference TUF-AX5400 passed the following controlled checks on
2026-09-29:

- exact patch reproduction for all four resources;
- install-time build while the Polish overlay was already active;
- install-time build directly from the stock firmware baselines;
- mount -> unmount -> remount lifecycle;
- one active bind mount per managed resource;
- persistence after reboot;
- final project health check with `0 failure(s), 0 warning(s)`;
- repository static test suite with exit status `0`.

The production build therefore reproduces the same byte-identical resources
that were validated during the live runtime and reboot tests.
