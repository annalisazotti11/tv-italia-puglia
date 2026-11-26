#!/usr/bin/env python3
"""Nightly playback gate for existing reviewed broadcaster routes.

Never opens a newly discovered community URL. Existing reviewed routes are a
technical identity baseline, not a blanket license. No media is persisted.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import threading
from urllib.parse import urlsplit

import content_identity as ci
import playback_quality as pq

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'audited-streams.json'
REVIEW = ROOT / 'data' / 'source-identity-review.json'
POLICY = ROOT / 'data' / 'source-quarantine.json'
WORKERS = 6
LOCAL = threading.local()

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def targets(review, policy):
    if review.get('schema') != 1 or policy.get('schema') != 1:
        raise ValueError('Invalid review or policy schema')
    owners = {}
    for cid, urls in review['channels'].items():
        for url in urls:
            owners.setdefault(url, set()).add(cid)
    out = []
    for cid, urls in review['channels'].items():
        for url in sorted(set(urls)):
            if not ci.allowed_url(url) or len(owners[url]) != 1:
                continue
            if urlsplit(url).hostname in policy['blocked_hosts']:
                continue
            if url in policy['blocked_by_channel'].get(cid, []):
                continue
            if cid in policy['approved_only'] and url not in policy['approved_only'][cid]:
                continue
            out.append((cid, url))
    return out

def detector():
    if not hasattr(LOCAL, 'model'):
        LOCAL.model = ci.load_detector()
    return LOCAL.model

def inspect(target):
    cid, url = target
    now = datetime.now(timezone.utc).isoformat()
    row = {'channel': cid, 'url': url, 'checked_at': now,
           'content_status': 'uncertain', 'sampled_frames': 0}
    why = ci.manifest_check(url)
    if why != 'ok':
        return row | {'reason': why}
    quality = pq.probe_stream(url)
    row.update(quality)
    if not quality.get('playback_ready'):
        return row
    frames, why = ci.capture_frames(url)
    row['sampled_frames'] = len(frames)
    safety = ci.safety_check(frames, detector())
    row['content_status'] = safety
    if len(frames) < 3:
        row['reason'] = why
    return row

def eligible(row):
    return (row.get('playback_ready') is True and row.get('has_video') is True
            and row.get('has_audio') is True
            and row.get('content_status') == 'no_high_confidence_flag'
            and row.get('sampled_frames', 0) >= 3
            and row.get('playback_height', 0) > 0)

def rank(row):
    # Prefer actual resolution after a full A/V and content pass. Stability and
    # measured probe duration break ties; codecs are a compatibility signal.
    h = min(max(int(row.get('playback_height') or 0), 0), 2160)
    runs = min(max(int(row.get('success_runs') or 0), 0), 30)
    delay = min(max(float(row.get('startup_ms') or 15000), 0), 15000)
    return (h * 10 + runs * 5 - delay / 100
            + 20 * (row.get('video_codec') == 'h264')
            + 20 * (row.get('audio_codec') == 'aac'))

def build(review, policy, previous=None, inspect_fn=inspect):
    previous = previous or {}
    prior = { (cid, s['url']): s.get('success_runs', 0)
              for cid, c in previous.get('channels', {}).items()
              for s in c.get('verified', []) }
    jobs = targets(review, policy)
    channels = {cid: {'verified': []} for cid in review['channels']}
    reasons = Counter()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for row in ex.map(inspect_fn, jobs):
            if not eligible(row):
                reasons[row.get('content_status') if row.get('content_status') != 'uncertain'
                        else row.get('reason', 'unknown')] += 1
                continue
            cid = row['channel']
            row['success_runs'] = min(prior.get((cid, row['url']), 0) + 1, 30)
            row['rank_score'] = rank(row)
            row['source'] = 'Percorso emittente/CDN già revisionato'
            row['kind'] = 'DASH' if '.mpd' in urlsplit(row['url']).path.lower() else 'HLS'
            row['playback_checked_at'] = row['checked_at']
            row['last_ok'] = row['checked_at']
            channels[cid]['verified'].append(row)
    for c in channels.values():
        c['verified'].sort(key=lambda s: (-s['rank_score'], s['url']))
        c['verified_count'] = len(c['verified'])
    return {'schema': 1, 'mode': 'reviewed_visual_gate_v1',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'channels': channels,
            'summary': {'reviewed_channels': len(channels), 'tested': len(jobs),
                        'visible': sum(bool(c['verified']) for c in channels.values()),
                        'passed': sum(len(c['verified']) for c in channels.values()),
                        'excluded': dict(reasons)}}

def main():
    review, policy = read(REVIEW), read(POLICY)
    previous = read(OUTPUT) if OUTPUT.exists() else {}
    # Refuse to generate a misleading pass when the detector cannot initialize.
    if ci.load_detector() is None:
        raise SystemExit('Visual detector unavailable')
    result = build(review, policy, previous)
    # Preserve existing catalog metadata, never copy playback URLs from the
    # legacy snapshot. The old scanner and this gate remain independent.
    legacy = ROOT / 'data' / 'verified-streams.json'
    if legacy.exists():
        for cid, entry in read(legacy).get('channels', {}).items():
            if cid in result['channels']:
                for field in ('name', 'number', 'group', 'logo'):
                    if isinstance(entry.get(field), str):
                        result['channels'][cid][field] = entry[field]
    tmp = OUTPUT.with_suffix('.tmp')
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    tmp.replace(OUTPUT)
    print(json.dumps(result['summary'], ensure_ascii=False))

if __name__ == '__main__':
    main()
