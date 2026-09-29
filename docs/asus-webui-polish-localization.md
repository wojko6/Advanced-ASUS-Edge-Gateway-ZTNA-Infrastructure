# Polish ASUS WebUI localization overlay

## Scope

Issue #133 tracks a project-owned Polish localization layer for the ASUS/GNUton
WebUI used by the reference TUF-AX5400.

The firmware dictionaries are **not** stored in this repository. The workflow
operates on copies collected from the deployed router and produces a generated
candidate outside source control.

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

Only after these checks pass should the candidate be staged on the router for
a read-only comparison and later a controlled bind-mount test.

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
