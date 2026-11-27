#!/usr/bin/env python3
"""Nightly playback and content gate for explicitly registered public routes.

Third-party candidates are labelled separately and require positive identity
corroboration. Technical tests do not establish distribution rights. No media
is persisted. No DRM or access-control workarounds.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache
import json
import threading
import time
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

@lru_cache(maxsize=1)
def watermark_references():
    cfg = read(ci.CONFIG)
    refs = {}
    for cid, name in cfg.get('watermark_templates', {}).items():
        if not isinstance(name, str):
            continue
        path = (ROOT / name).resolve()
        if path.is_relative_to(ROOT.resolve()) and path.is_file():
            refs[cid] = path
    return refs

@lru_cache(maxsize=1)
def identity_rules():
    return read(REVIEW).get('identity_required', {})

def corroborate_identity(cid, url, frames, logo, capture=ci.capture_frames):
    rule = identity_rules().get(cid, {}).get(url)
    if rule is None:
        return 'not_required'
    if logo.get('status') == 'logo_observed':
        return 'watermark_observed'
    # Only reference routes already in the channel's technical registry.
    review, policy = read(REVIEW), read(POLICY)
    valid = set(targets(review, policy))
    refs = [ref for ref in rule.get('references', [])
            if (cid, ref) in valid and ref != url
            and urlsplit(ref).hostname != urlsplit(url).hostname
            and ref not in identity_rules().get(cid, {})][:3]
    if not refs:
        return 'unconfirmed'
    with ThreadPoolExecutor(max_workers=3) as pool:
        for ref_frames, _ in pool.map(capture, refs):
            if len(ref_frames) >= 3 and ci.compare_sequences(frames, ref_frames)['corroborated']:
                return 'reference_scenes_match'
    return 'unconfirmed'

def inspect(target, *, extended=False):
    cid, url = target
    now = datetime.now(timezone.utc).isoformat()
    rule = identity_rules().get(cid, {}).get(url)
    row = {'channel': cid, 'url': url, 'checked_at': now,
           'content_status': 'uncertain', 'sampled_frames': 0,
           'identity_required': rule is not None,
           'identity_status': 'unconfirmed' if rule is not None else 'not_required'}
    why = ci.manifest_check(url, timeout=10 if extended else 5, reviewed_redirects=rule is None)
    if why != 'ok':
        return row | {'reason': why}
    quality = pq.probe_stream(url, extended=extended)
    row.update(quality)
    if not quality.get('playback_ready'):
        return row
    frames, why = ci.capture_frames(url, extended=extended, reviewed_redirects=rule is None)
    row['sampled_frames'] = len(frames)
    safety = ci.safety_check(frames, detector())
    row['content_status'] = safety
    # An authentic on-air watermark is supporting evidence, not proof of
    # licensing or identity. Do not substitute a catalog logo or save frames.
    if safety == 'no_high_confidence_flag' and len(frames) >= 3:
        row['watermark'] = ci.logo_check(frames, watermark_references().get(cid))
        row['identity_status'] = corroborate_identity(cid, url, frames, row['watermark'])
    if len(frames) < 3:
        row['reason'] = why
    return row

# A transient failure gets one additional ordinary request. Never retry
# forbidden, protected, mismatched or explicit-content results.
TRANSIENT = {'http_503', 'http_502', 'http_504', 'manifest_unavailable',
             'ffprobe_timeout', 'decode_timeout', 'decode_failed', 'ffprobe_error',
             'no_packets', 'video_only', 'audio_only', 'short_sample'}
# Preserve recent, fully approved results only when ordinary network or
# decoding timeouts recur. Never preserve forbidden or identity/content failures.
GRACE_REASONS = {'http_503', 'http_502', 'http_504', 'manifest_unavailable',
                 'ffprobe_timeout', 'decode_timeout'}
GRACE_SECONDS = 36 * 3600

def inspect_retry(target, inspect_fn=inspect, pause=time.sleep):
    row = inspect_fn(target)
    row['attempts'] = 1
    if (not eligible(row) and row.get('reason') in TRANSIENT and
            (row.get('content_status') in ('uncertain', 'not_sampled') or
             (row.get('content_status') == 'no_high_confidence_flag' and row.get('sampled_frames', 0) < 3))):
        pause(1)
        row = inspect(target, extended=True) if inspect_fn is inspect else inspect_fn(target)
        row['attempts'] = 2
    return row

def failure_reason(row):
    status = row.get('content_status', 'uncertain')
    if status == 'explicit_suspected':
        return status
    if status not in ('uncertain', 'no_high_confidence_flag', 'not_sampled'):
        return status
    if status == 'no_high_confidence_flag' and row.get('sampled_frames', 0) < 3:
        return 'insufficient_frames'
    if row.get('identity_required') and row.get('identity_status') == 'unconfirmed' and row.get('playback_ready') and status == 'no_high_confidence_flag':
        return 'channel_identity_unconfirmed'
    return row.get('reason') or status

def eligible(row):
    return (row.get('playback_ready') is True and row.get('has_video') is True
            and row.get('has_audio') is True
            and row.get('content_status') == 'no_high_confidence_flag'
            and row.get('sampled_frames', 0) >= 3
            and row.get('playback_height', 0) > 0
            and (not row.get('identity_required') or row.get('identity_status') in
                 ('watermark_observed', 'reference_scenes_match')))

def rank(row):
    # Prefer actual resolution after a full A/V and content pass. Stability and
    # measured probe duration break ties; codecs are a compatibility signal.
    h = min(max(int(row.get('playback_height') or 0), 0), 2160)
    runs = min(max(int(row.get('success_runs') or 0), 0), 30)
    delay = min(max(float(row.get('startup_ms') or 15000), 0), 15000)
    return (h * 10 + runs * 5 - delay / 100
            + 20 * (row.get('video_codec') == 'h264')
            + 20 * (row.get('audio_codec') == 'aac'))

def build(review, policy, previous=None, inspect_fn=inspect_retry):
    previous = previous or {}
    prior = { (cid, s['url']): s.get('success_runs', 0)
              for cid, c in previous.get('channels', {}).items()
              for s in c.get('verified', []) }
    last_good = {(cid, s['url']): s
                 for cid, c in previous.get('channels', {}).items()
                 for s in c.get('verified', [])}
    now = datetime.now(timezone.utc)
    jobs = targets(review, policy)
    channels = {cid: {'verified': [], 'audit': {'tested': 0, 'failed': {}}} for cid in review['channels']}
    reasons = Counter()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for row in ex.map(inspect_fn, jobs):
            cid = row['channel']
            audit = channels[cid]['audit']
            audit['tested'] += 1
            if not eligible(row):
                reason = failure_reason(row)
                reasons[reason] += 1
                audit['failed'][reason] = audit['failed'].get(reason, 0) + 1
                old = last_good.get((cid, row['url']))
                # No relaxation of the exact review/quarantine, audio/video,
                # positive identity, or explicit-content requirements.
                if (reason in GRACE_REASONS and
                        row.get('content_status') in ('uncertain', 'not_sampled') and
                        not row.get('identity_required') and
                        row['url'] not in review.get('identity_required', {}).get(cid, {}) and
                        old and not old.get('identity_required') and eligible(old)):
                    try:
                        age = (now - datetime.fromisoformat(old['checked_at'])).total_seconds()
                    except (KeyError, TypeError, ValueError):
                        age = GRACE_SECONDS + 1
                    if 0 <= age < GRACE_SECONDS:
                        channels[cid]['verified'].append(dict(old, retained=True,
                            retained_reason=reason))
                continue
            row['success_runs'] = min(prior.get((cid, row['url']), 0) + 1, 30)
            row['rank_score'] = rank(row)
            row['source'] = ('CDN terza: identità visiva corroborata, diritti non verificati'
                             if row.get('identity_required') else 'Percorso emittente/CDN già revisionato')
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
                        'passed': sum(not s.get('retained') for c in channels.values() for s in c['verified']),
                        'retained_recent': sum(bool(s.get('retained')) for c in channels.values() for s in c['verified']),
                        'excluded': dict(reasons)}}

def annotate_review_queue(result, legacy):
    """Count technically promising routes without exposing their URLs or promoting them."""
    priority = []
    for cid, channel in result['channels'].items():
        old = legacy.get('channels', {}).get(cid, {})
        audit = channel.setdefault('audit', {})
        av = sum(row.get('playback_ready') is True and row.get('has_audio') is True
                 and row.get('has_video') is True for row in old.get('verified', []))
        audit['preliminary_av_count'] = av
        if not channel.get('verified') and av:
            name = channel.get('name') or old.get('name') or cid
            group = channel.get('group') or old.get('group') or ''
            priority.append({'id': cid, 'name': name, 'group': group,
                             'preliminary_av_count': av,
                             'availability': audit.get('availability', 'unknown')})
    def order(item):
        n = item['name'].casefold()
        g = item['group'].casefold()
        primary = n.startswith(('rai', 'canale 5', 'rete 4', 'italia 1', 'la7', 'tv8', 'nove'))
        local = 'puglia' in g or 'puglia' in item['id'] or 'tgr puglia' in n
        return (not primary, not local, -item['preliminary_av_count'], n)
    result['review_queue'] = sorted(priority, key=order)
    result['summary']['preliminary_av_without_final_pass'] = len(priority)
    return result

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
    # Include every monitored channel in the coverage report, without copying
    # any unreviewed playback address from the legacy index.
    if legacy.exists():
        for cid, entry in read(legacy).get('channels', {}).items():
            if cid not in result['channels']:
                result['channels'][cid] = {
                    **{k: entry[k] for k in ('name','number','group','logo')
                       if isinstance(entry.get(k), str)},
                    'verified': [], 'verified_count': 0,
                    'audit': {'tested': 0, 'failed': {}, 'status': 'awaiting_source_review'}}
    # A watchlist update may arrive before the legacy scan finishes. Report the
    # new entries immediately without inheriting any playback address.
    watchlist = ROOT / 'data' / 'channel-watchlist.json'
    if watchlist.exists():
        for entry in read(watchlist).get('channels', []):
            cid = entry.get('id')
            if not isinstance(cid, str) or not cid.startswith('tvip_'):
                continue
            channel = result['channels'].setdefault(cid, {
                'verified': [], 'verified_count': 0,
                'audit': {'tested': 0, 'failed': {}, 'status': 'awaiting_source_review'}})
            for field in ('name', 'number', 'group', 'logo'):
                if field not in channel and isinstance(entry.get(field), str):
                    channel[field] = entry[field]
    # Expose geographic/access uncertainty separately from missing reviews.
    # An HTTP 403 is not proof of a dead stream and never becomes a pass.
    for channel in result['channels'].values():
        audit = channel.setdefault('audit', {})
        failed = audit.get('failed', {})
        tested = audit.get('tested', 0)
        if channel.get('verified'):
            audit['availability'] = 'verified'
        elif not tested:
            audit['availability'] = 'awaiting_source_review'
        elif failed.get('http_403', 0) == tested:
            audit['availability'] = 'access_denied_unconfirmed'
        else:
            audit['availability'] = 'audit_failed'
    result['summary']['availability_counts'] = dict(Counter(
        c['audit']['availability'] for c in result['channels'].values()))
    result['summary']['monitored_channels'] = len(result['channels'])
    result['summary']['awaiting_source_review'] = sum(
        c.get('audit', {}).get('status') == 'awaiting_source_review'
        for c in result['channels'].values())
    annotate_review_queue(result, read(legacy) if legacy.exists() else {})
    tmp = OUTPUT.with_suffix('.tmp')
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    tmp.replace(OUTPUT)
    print(json.dumps(result['summary'], ensure_ascii=False))

if __name__ == '__main__':
    main()
