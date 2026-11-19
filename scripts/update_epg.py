#!/usr/bin/env python3
"""Build a small, time-correct Italian TV guide from public XMLTV feeds.

Only use programme titles supplied by the EPG; never fabricate "now playing".
No credentials or scraped playback URLs are embedded in the output.
"""
from __future__ import annotations

from collections import defaultdict
import datetime as dt
import gzip
import io
import json
from pathlib import Path
import re
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'data' / 'verified-streams.json'
OUTPUT = ROOT / 'data' / 'epg-guide.json'
FEEDS = [
    ('TvIt / SuperGuidaTV', 'https://tvit.leicaflorianrobert.dev/epg/list.xml'),
    ('IPTV-EPG Italia', 'https://iptv-epg.org/files/epg-it.xml'),
]
LIMIT_DOWNLOAD = 20 * 1024 * 1024
LIMIT_EXPANDED = 60 * 1024 * 1024
MAX_PER_CHANNEL = 28
UTC = dt.timezone.utc
ALIASES = {
    'rai uno': 'rai 1', 'rai due': 'rai 2', 'rai tre': 'rai 3',
    'rai uno hd': 'rai 1', 'retequattro': 'rete 4', 'rete4': 'rete 4',
    'italia uno': 'italia 1', 'la 7': 'la7', 'sky tg 24': 'sky tg24',
    'radio 105': 'radio 105 tv', 'radioitaliatv': 'radio italia tv',
    'tgnorba24': 'tg norba 24', 'tele norba': 'telenorba',
    'twenty seven': '27 twentyseven', 'twentyseven': '27 twentyseven',
    'la5': 'la 5', 'tgcom 24': 'tgcom24', 'rai news24': 'rai news 24',
    'rainews24': 'rai news 24', 'hgtv home garden': 'hgtv',
    'sky sport 24': 'sky sport24',
}


def norm(value: str) -> str:
    s = unicodedata.normalize('NFD', value or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'(?i)(?:[._ ](?:it|italia|italy))$', '', s)
    s = re.sub(r'[^a-z0-9]+', ' ', s).strip()
    s = re.sub(r'(?:\s+(?:hd|fhd|uhd|sd|4k|1080p|720p))+$', '', s)
    return ALIASES.get(s, s)


def parse_time(raw: str):
    """XMLTV 20261119190000 +0100, with explicit or implicit UTC."""
    m = re.fullmatch(r'(\d{14})(?:\s+([+-]\d{4}))?', (raw or '').strip())
    if not m:
        return None
    try:
        t = dt.datetime.strptime(m.group(1), '%Y%m%d%H%M%S')
        tz = m.group(2) or '+0000'
        sign = 1 if tz[0] == '+' else -1
        offset = sign * (int(tz[1:3]) * 60 + int(tz[3:5]))
        return t.replace(tzinfo=dt.timezone(dt.timedelta(minutes=offset))).astimezone(UTC)
    except ValueError:
        return None


def iso(t):
    return t.isoformat(timespec='seconds').replace('+00:00', 'Z')


def fetch_xml(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'TVItaliaPuglia-EPG/1.0 (public XMLTV client)',
        'Accept': 'application/xml, text/xml, application/gzip, */*',
        'Accept-Encoding': 'gzip',
    })
    with urllib.request.urlopen(req, timeout=22) as response:
        raw = response.read(LIMIT_DOWNLOAD + 1)
        if len(raw) > LIMIT_DOWNLOAD:
            raise ValueError('XMLTV download exceeded safety limit')
        if response.headers.get('Content-Encoding') == 'gzip' or url.endswith('.gz') or raw[:2] == b'\x1f\x8b':
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as z:
                raw = z.read(LIMIT_EXPANDED + 1)
        if len(raw) > LIMIT_EXPANDED:
            raise ValueError('XMLTV expanded data exceeded safety limit')
        if b'<tv' not in raw[:1024] and b'<tv' not in raw[:4096]:
            raise ValueError('Not XMLTV data')
        return raw


def extract(raw: bytes, wanted: dict, now: dt.datetime):
    root = ET.fromstring(raw)
    if root.tag != 'tv':
        raise ValueError('Expected tv root element')
    epg_to_ours = {}
    names_by_channel = defaultdict(set)
    for channel in root.findall('channel'):
        epg_id = channel.attrib.get('id', '')
        if not epg_id:
            continue
        keys = {norm(epg_id)}
        keys.update(norm(v.text or '') for v in channel.findall('display-name'))
        keys.discard('')
        targets = {wanted[k] for k in keys if k in wanted and wanted[k]}
        if len(targets) == 1:
            cid = next(iter(targets))
            epg_to_ours[epg_id] = cid
            names_by_channel[cid].add(epg_id)
    result = defaultdict(list)
    low = now - dt.timedelta(minutes=90)
    high = now + dt.timedelta(hours=72)
    for pr in root.findall('programme'):
        cid = epg_to_ours.get(pr.attrib.get('channel', ''))
        if not cid:
            continue
        start, stop = parse_time(pr.attrib.get('start', '')), parse_time(pr.attrib.get('stop', ''))
        if not start or not stop or not (start < stop) or stop < low or start > high:
            continue
        title = ((pr.findtext('title') or '')).strip()
        if not title:
            continue
        title = re.sub(r'\s+', ' ', title)[:110]
        if norm(title) in {'no data', 'n a', 'tba', 'no information', 'unknown', 'nessun dato', 'programma non disponibile'}:
            continue
        item = {'start': iso(start), 'stop': iso(stop), 'title': title}
        subtitle = re.sub(r'\s+', ' ', pr.findtext('sub-title') or '').strip()[:85]
        if subtitle:
            item['subtitle'] = subtitle
        result[cid].append(item)
    for cid, values in result.items():
        seen = set()
        clean = []
        for x in sorted(values, key=lambda e: (e['start'], e['stop'])):
            key = (x['start'], x['stop'], x['title'])
            if key in seen:
                continue
            seen.add(key)
            clean.append(x)
        result[cid] = clean[:MAX_PER_CHANNEL]
    return dict(result)


def build(now=None, download=fetch_xml):
    now = now or dt.datetime.now(UTC)
    watched = json.loads(SNAPSHOT.read_text(encoding='utf-8')).get('channels', {})
    normalized = defaultdict(set)
    for cid, channel in watched.items():
        normalized[norm(channel.get('name', ''))].add(cid)
    wanted = {key: next(iter(values)) for key, values in normalized.items()
              if key and len(values) == 1}
    selected = {}
    feed_status = []
    for source, url in FEEDS:
        try:
            entries = extract(download(url), wanted, now)
            matches = 0
            for cid, schedule in entries.items():
                if cid in selected and len(selected[cid]['programmes']) >= 4:
                    continue
                # Replacement is only allowed when the second feed provides
                # more programming; never combine contradictory broadcasters.
                if cid not in selected or len(schedule) > len(selected[cid]['programmes']):
                    selected[cid] = {'source': source, 'programmes': schedule}
                    matches += 1
            feed_status.append({'source': source, 'ok': True, 'matched': len(entries),
                                'selected': matches})
        except Exception as exc:
            feed_status.append({'source': source, 'ok': False,
                                'reason': type(exc).__name__})
    if not selected:
        raise RuntimeError('All XMLTV feeds failed or matched no channels')
    output = {
        'schema': 1, 'generated_at': iso(now),
        'sources': feed_status,
        'channels': selected,
        'summary': {'monitored': len(watched), 'with_epg': len(selected),
                    'programme_count': sum(len(c['programmes']) for c in selected.values())}
    }
    return output


def main():
    try:
        data = build()
    except RuntimeError as exc:
        print(f'WARNING: EPG not replaced: {exc}', file=sys.stderr, flush=True)
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n',
                      encoding='utf-8')
    print('EPG updated: ' + json.dumps(data['summary']) + ', '
          + json.dumps(data['sources']), flush=True)


if __name__ == '__main__':
    main()
