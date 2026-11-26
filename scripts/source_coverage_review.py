#!/usr/bin/env python3
"""Discovery-only coverage report. Never requests listed media URLs or changes production."""
import argparse
import concurrent.futures
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit
import nightly_check as nightly

ROOT = Path(__file__).resolve().parents[1]
NEW_NAMES = {
    'Nanobuo Italia completa', 'Nanobuo nazionali', 'OnAirTV Italia',
    'Reefquiet Italia', 'CANALI-IPTV Italia', 'Mario Muto Italia',
    'MrWolfJunior Italia', 'Vise950 Italia', 'Giuseppe Italia',
    'CodingMayhem Italia', 'CodingMayhem Italia 2',
}

def identity(url):
    try:
        u = urlsplit(url)
        if (not nightly.safe_url(url) or u.scheme != 'https' or u.query
                or u.fragment or u.port not in (None, 443)
                or not u.path.lower().endswith(('.m3u8', '.m3u', '.mpd'))):
            return None
        return (u.hostname.lower(), u.path)
    except (ValueError, AttributeError):
        return None

def match(entry, names, channels):
    attrs = entry.get('attrs', {})
    country = (attrs.get('tvg-country') or attrs.get('country') or '').strip().lower()
    if country and country not in {'it', 'ita', 'italy', 'italia'}:
        return None
    ids = list(set(names.get(nightly.normalize(entry['name']), [])))
    number = attrs.get('tvg-chno', '').strip()
    if number:
        ids = [cid for cid in ids if not channels[cid].get('number') or channels[cid]['number'] == number]
    return ids[0] if len(ids) == 1 else None

def collect(results, channels, names, snapshot, reviewed, policy):
    old, new = defaultdict(dict), defaultdict(dict)
    status = []
    for source in results:
        matched = set()
        for entry in source.get('candidates', []):
            cid = match(entry, names, channels)
            key = identity(entry.get('url', ''))
            if cid is None or key is None:
                continue
            url = entry['url']
            if key[0] in policy.get('blocked_hosts', []) or url in policy.get('blocked_by_channel', {}).get(cid, []):
                continue
            # Respect channel-level restrictions; don't promote these URLs.
            if cid in policy.get('approved_only', {}) and url not in policy['approved_only'][cid]:
                continue
            dest = new if source['name'] in NEW_NAMES else old
            dest[cid].setdefault(key, set()).add(source['name'])
            matched.add(cid)
        status.append({'name': source['name'], 'read': source['read'],
                       'matched_channels': len(matched), 'new_index': source['name'] in NEW_NAMES})
    rows = []
    for cid, ch in channels.items():
        snap = snapshot.get(cid, {})
        known = set(old[cid])
        for field in ('verified', 'regional_candidates', 'candidates'):
            known.update(k for r in snap.get(field, []) if (k := identity(r.get('url', ''))))
        approved = {k for u in reviewed.get(cid, []) if (k := identity(u))}
        known.update(k for u in policy.get('approved_only', {}).get(cid, []) if (k := identity(u)))
        fresh = set(new[cid]) - known
        old_hosts = {k[0] for k in known}
        all_hosts = {k[0] for k in known | set(new[cid])}
        rows.append({
            'id': cid, 'name': ch['name'], 'number': ch.get('number', ''),
            'audio_video_ready': snap.get('av_ready_count', 0),
            'new_distinct_candidates': len(fresh),
            'new_reviewed_candidates': len(fresh & approved),
            'new_hosts': len(all_hosts - old_hosts),
            'review_required': len(fresh - approved),
            'new_index_count': len(set().union(*new[cid].values())) if new[cid] else 0,
            'publish_allowed': False,
        })
    rows.sort(key=lambda r: (r['audio_video_ready'], -r['new_distinct_candidates'], r['name']))
    return {'mode': 'metadata_only', 'summary': {
        'channels': len(rows), 'indexes_read': sum(s['read'] for s in status),
        'new_indexes_read': sum(s['read'] and s['new_index'] for s in status),
        'channels_with_new_candidates': sum(r['new_distinct_candidates'] > 0 for r in rows),
        'new_channel_url_pairs': sum(r['new_distinct_candidates'] for r in rows),
        'new_reviewed_channel_url_pairs': sum(r['new_reviewed_candidates'] for r in rows),
        'channels_below_three_av_sources': sum(r['audio_video_ready'] < 3 for r in rows),
    }, 'indexes': status, 'channels': rows,
    'note': 'New means absent from the previous indexes and snapshot; not playback, safety, ownership or authorization. Host count does not establish independent operators. No stream was opened or published.'}

def self_test():
    ch = {'a': {'name':'Rai 1', 'number':'1'}}
    names = {'rai 1':['a']}
    def item(url): return {'name':'Rai 1 HD','attrs':{},'url':url}
    def source(name, *urls): return {'name':name,'read':True,'candidates':[item(u) for u in urls]}
    a = 'https://example.org/a.m3u8'
    b = 'https://example.net/b.m3u8'
    c = 'https://blocked.example/c.m3u8'
    report = collect([source('old',a),source('OnAirTV Italia',a,b,b,c)],ch,names,{}, {},{'blocked_hosts':['blocked.example']})
    assert report['summary']['new_channel_url_pairs'] == 1
    assert report['channels'][0]['new_hosts'] == 1
    assert not report['channels'][0]['publish_allowed']
    assert identity('https://example.org/a.m3u8?token=x') is None
    assert match({'name':'Rai 1','attrs':{'tvg-country':'US'}},names,ch) is None
    print('Discovery self-test passed')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/source-coverage-review.json')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    sources = nightly.registered_playlists()
    channels, names = nightly.inventory()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(nightly.fetch_playlist_source, sources))
    snapshot = json.loads((ROOT/'data/verified-streams.json').read_text())['channels']
    reviewed = json.loads((ROOT/'data/source-identity-review.json').read_text())['channels']
    policy = nightly.source_quarantine()
    report = collect(results, channels, names, snapshot, reviewed, policy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False))

if __name__ == '__main__':
    main()
