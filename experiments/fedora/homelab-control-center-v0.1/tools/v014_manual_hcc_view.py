#!/usr/bin/env python3
"""HCC V0.14 static manual correlation view from V0.13.2a sanitized report.

No browser script, external asset, network, SSH, journal access or VM access.
--self-test is pure; --render-stdin writes one explicitly selected NEW .html file.
"""
import argparse
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path
import re
import sys

MAX_BYTES = 96 * 1024
MAX_GAPS = 128
CLASSES = {
    'FEDORA_SUSPEND_CORRELATED': ('Silna korelacja z uśpieniem', 'host'),
    'FEDORA_INTERBOOT_BOUNDARY_CORRELATED': ('Korelacja między rozruchami', 'host'),
    'FEDORA_MIXED_HOST_RECORD_CORRELATED': ('Mieszane zdarzenia hosta', 'host'),
    'PARTIAL_FEDORA_HOST_CORRELATION': ('Częściowa korelacja hosta', 'partial'),
    'MIXED_HOST_AND_COLLECTOR_EVIDENCE': ('Host i błędy kolektora', 'partial'),
    'COLLECTOR_EXIT_255_OBSERVED': ('Błędy kolektora — exit 255', 'failure'),
    'UNKNOWN_NO_MATCHING_EVIDENCE': ('Brak pasujących dowodów', 'unknown'),
}

class InvalidReport(ValueError):
    pass


def parse_report(raw):
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        raise InvalidReport('INVALID_LENGTH')
    try:
        lines = raw.decode('utf-8').splitlines()
    except UnicodeError as exc:
        raise InvalidReport('INVALID_ENCODING') from exc
    if lines[0] != '=== HCC V0.13.2 / FEDORA HOST + COLLECTOR CORRELATION ===':
        raise InvalidReport('UNEXPECTED_REPORT')
    gaps, header, trailer, current = [], {}, {}, None
    for line in lines[1:]:
        if re.fullmatch(r'--- GAP_\d+ ---', line):
            number = int(line.split('_')[1].split()[0])
            if number != len(gaps) + 1 or number > MAX_GAPS:
                raise InvalidReport('GAP_NUMBER')
            current = {}
            gaps.append(current)
            continue
        if '=' not in line:
            raise InvalidReport('UNEXPECTED_LINE')
        k, v = line.split('=', 1)
        if not re.fullmatch(r'[A-Z0-9_]+', k) or len(v) > 150:
            raise InvalidReport('INVALID_KEY_VALUE')
        destination = (current if current is not None and not k.startswith(('COUNT_', 'V0132_RESULT', 'DEPLOYMENT_GATE', 'TELEMETRY_GAPS_NOT_EQ_', 'JOURNAL_ABSENCE_NOT_', 'ASUS_CONTACT', 'FEDORA_SERVICES_', 'PRODUCTION_CHANGES', 'TERMINAL_DZIALA')) else (trailer if current is not None else header))
        if k in destination:
            raise InvalidReport('DUPLICATE_KEY')
        destination[k] = v
    if header.get('MODE') != 'FEDORA_OFFLINE_MANUAL_READ_ONLY' or header.get('WINDOW') not in {'1h','6h','24h','7d'}:
        raise InvalidReport('INVALID_HEADER')
    if trailer.get('V0132_RESULT') != 'PASS_CORRELATION_ONLY' or trailer.get('DEPLOYMENT_GATE') != 'HOLD' or trailer.get('TELEMETRY_GAPS_NOT_EQ_DNS_OUTAGES') != 'YES':
        raise InvalidReport('INCOMPLETE_VALIDATION')
    try:
        count = int(header['TELEMETRY_GAPS'])
        sample_invalid = int(header['INVALID_SAMPLE_COUNT'])
    except (KeyError, ValueError) as exc:
        raise InvalidReport('MISSING_COUNTS') from exc
    if not 0 < count <= MAX_GAPS or len(gaps) != count or sample_invalid < 0:
        raise InvalidReport('COUNT_MISMATCH')
    counts = Counter()
    parsed = []
    for i, gap in enumerate(gaps, 1):
        try:
            cl = gap['CLASS']
            if cl not in CLASSES:
                raise InvalidReport('INVALID_CLASS')
            start = datetime.fromisoformat(gap['START_WARSAW'])
            end = datetime.fromisoformat(gap['END_WARSAW'])
            duration = float(gap['DURATION_SECONDS'])
            pct = float(gap['HOST_RECORD_OVERLAP_PCT'])
            residual = float(gap['RESIDUAL_NOT_MATCHED_SECONDS'])
            exits = int(gap['COLLECTOR_EXIT_255_EVENTS'])
            if (start.tzinfo is None or end.tzinfo is None or end <= start
                    or duration <= 0 or duration > 700000 or abs((end-start).total_seconds()-duration)>0.01
                    or not 0 <= pct <= 100 or residual < 0 or residual > duration+0.01 or exits < 0 or exits > 10000):
                raise InvalidReport('INVALID_GAP_VALUES')
        except (KeyError, ValueError) as exc:
            raise InvalidReport(f'INVALID_GAP_{i}') from exc
        parsed.append({'n':i,'start':start.isoformat(timespec='seconds'), 'end':end.isoformat(timespec='seconds'),
                       'duration':duration, 'pct':pct, 'residual':residual, 'exits':exits, 'class':cl})
        counts[cl] += 1
    for cl in CLASSES:
        try:
            if int(trailer['COUNT_'+cl]) != counts[cl]:
                raise InvalidReport('SUMMARY_MISMATCH')
        except (KeyError, ValueError) as exc:
            raise InvalidReport('INVALID_SUMMARY') from exc
    return {'window':header['WINDOW'], 'invalid':sample_invalid, 'gaps':parsed, 'counts':counts}


def render(report):
    counts = report['counts']
    totals = len(report['gaps'])
    cols = []
    for cl, (description, style) in CLASSES.items():
        cols.append(f'<div class="metric"><strong>{counts[cl]}</strong><span>{escape(description)}</span></div>')
    rows = []
    for gap in report['gaps']:
        desc, style = CLASSES[gap['class']]
        rows.append('<tr><td>{n}</td><td>{start}</td><td>{end}</td><td>{mins:.1f}</td>'
                    '<td><span class="tag {style}">{desc}</span></td><td>{pct:.1f}%</td><td>{exits}</td>'
                    '<td>{residual:.1f}</td></tr>'.format(
                        n=gap['n'],start=escape(gap['start']),end=escape(gap['end']),
                        mins=gap['duration']/60,style=style,desc=escape(desc),pct=gap['pct'],exits=gap['exits'],residual=gap['residual']))
    return '''<!doctype html><html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>HCC — Ręczna analiza luk telemetrycznych</title>
<style>
:root{color-scheme:light dark;font-family:system-ui,sans-serif}*{box-sizing:border-box}
body{max-width:1200px;margin:auto;padding:32px 22px;line-height:1.45}
header{border-bottom:1px solid #8885;padding-bottom:16px;margin-bottom:22px}
.eyebrow{font-size:.82rem;letter-spacing:.06em;text-transform:uppercase;opacity:.7}
h1{font-size:clamp(1.7rem,3vw,2.6rem);line-height:1.14;margin:12px 0}
.notice{border-left:4px solid #d08b14;padding:14px 17px;background:color-mix(in srgb,#d08b14 12%,transparent);margin:20px 0}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px;margin:22px 0}
.metric{border:1px solid #8886;border-radius:12px;padding:18px;display:grid;gap:4px}
.metric strong{font-size:2rem}.metric span{font-size:.85rem;opacity:.8}
.tablewrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.86rem}
th,td{text-align:left;padding:11px;border-bottom:1px solid #8885;white-space:nowrap}
th{font-weight:650}.tag{display:inline-block;border-radius:8px;padding:4px 8px;border:1px solid #8885}
.host{background:color-mix(in srgb,#219367 15%,transparent)}
.partial{background:color-mix(in srgb,#dea117 15%,transparent)}
.failure{background:color-mix(in srgb,#d05252 15%,transparent)}
.unknown{background:color-mix(in srgb,#888 15%,transparent)}
footer{margin-top:30px;font-size:.85rem;opacity:.75}code{overflow-wrap:anywhere}
</style></head><body><header><div class="eyebrow">Homelab Control Center · tylko odczyt · V0.14</div>
<h1>Korelacja luk telemetrycznych DNS Guard</h1>
<p>Statyczny raport lokalny z ręcznego uruchomienia V0.13.2a. Okno: <strong>''' + escape(report['window']) + '''</strong>. Nie jest to panel stanu DNS w czasie rzeczywistym.</p></header>
<div class="notice"><strong>Brak telemetrii ≠ awaria DNS.</strong> Uśpienie i przerwy pomiędzy zapisami rozruchów nie są dowodem precyzyjnego czasu wyłączenia; błędy kolektora nie dowodzą awarii ASUS-a ani WAN. Nie potwierdzono kompletności dzienników.</div>
<section aria-label="Podsumowanie"><h2>Podsumowanie</h2>
<div class="metrics"><div class="metric"><strong>''' + str(totals) + '''</strong><span>Luki telemetryczne</span></div>
<div class="metric"><strong>''' + str(report['invalid']) + '''</strong><span>Nieprawidłowe próbki</span></div>''' + ''.join(cols) + '''</div></section>
<section><h2>Przedziały</h2><div class="tablewrap"><table>
<thead><tr><th>#</th><th>Od (PL)</th><th>Do (PL)</th><th>Minuty</th><th>Korelacja</th><th>Pokrycie hosta</th><th>Exit 255</th><th>Reszta (s)</th></tr></thead>
<tbody>''' + ''.join(rows) + '''</tbody></table></div></section>
<footer>Źródło: operator-provided, validated V0.13.2a text report; bez surowych logów, klientów, IP i sekretów. <code>ASUS_CONTACT=NO · DEPLOYMENT_GATE=HOLD · SOURCE_COMPLETENESS=NOT_ESTABLISHED</code></footer>
</body></html>'''


def self_test():
    basic = '''=== HCC V0.13.2 / FEDORA HOST + COLLECTOR CORRELATION ===
MODE=FEDORA_OFFLINE_MANUAL_READ_ONLY
WINDOW=7d
TELEMETRY_GAPS=1
INVALID_SAMPLE_COUNT=0
--- GAP_1 ---
START_WARSAW=2026-10-28T17:04:26+01:00
END_WARSAW=2026-10-28T17:25:04+01:00
DURATION_SECONDS=1238.000
CLASS=COLLECTOR_EXIT_255_OBSERVED
HOST_RECORD_OVERLAP_PCT=0.0
RESIDUAL_NOT_MATCHED_SECONDS=1238.000
COLLECTOR_EXIT_255_EVENTS=18
'''
    for cl in CLASSES:
        basic += 'COUNT_' + cl + '=' + ('1' if cl=='COLLECTOR_EXIT_255_OBSERVED' else '0') + '\n'
    basic += 'TELEMETRY_GAPS_NOT_EQ_DNS_OUTAGES=YES\nDEPLOYMENT_GATE=HOLD\nV0132_RESULT=PASS_CORRELATION_ONLY\n'
    parsed = parse_report(basic.encode())
    html = render(parsed)
    assert parsed['gaps'][0]['exits'] == 18
    assert '<script' not in html.lower() and '<iframe' not in html.lower() and 'Brak telemetrii' in html
    try:
        parse_report(basic.replace('V0132_RESULT=PASS_CORRELATION_ONLY','V0132_RESULT=NO').encode())
    except InvalidReport:
        pass
    else:
        raise AssertionError('INVALID_PASS_ACCEPTED')
    try:
        parse_report(basic.replace('COUNT_COLLECTOR_EXIT_255_OBSERVED=1','COUNT_COLLECTOR_EXIT_255_OBSERVED=0').encode())
    except InvalidReport:
        pass
    else:
        raise AssertionError('INVALID_COUNTS_ACCEPTED')
    print('V014_MANUAL_VIEW_SELFTEST=PASS')
    print('NO_NETWORK_NO_SUBPROCESS_NO_FILES_WRITTEN=YES')
    print('DEPLOYMENT_GATE=HOLD')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--self-test', action='store_true')
    mode.add_argument('--render-stdin', action='store_true')
    p.add_argument('--output', type=Path)
    a=p.parse_args()
    if a.self_test:
        self_test(); return 0
    if a.output is None or a.output.suffix.lower() != '.html':
        p.error('explicit --output PATH.html is required')
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        page = render(parse_report(raw))
        with a.output.open('x', encoding='utf-8') as f:
            f.write(page)
        print('V014_MANUAL_VIEW=CREATED_LOCAL_HTML')
        print('OUTPUT=' + str(a.output))
        print('ASUS_CONTACT=NO PRODUCTION_CHANGES=NO DEPLOYMENT_GATE=HOLD')
        return 0
    except (InvalidReport, ValueError, OSError):
        print('V014_RESULT=REJECTED_OR_OUTPUT_UNAVAILABLE',file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())