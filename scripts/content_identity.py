#!/usr/bin/env python3
"""Shadow-mode live TV identity audit. No frames or stream URLs are published.

Only exact, explicitly reviewed, unauthenticated broadcaster routes are opened.
Uncertain/unreviewed candidates stay in the review queue; this tool cannot
change the playback catalogue or lift a quarantine. No DRM or geo workarounds.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import statistics
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'data/content-identity-pilot-config.json'
POLICY = ROOT / 'data/source-quarantine.json'
REVIEWED = ROOT / 'data/source-identity-review.json'
WIDTH, HEIGHT = 480, 270
FRAME_MS = WIDTH * HEIGHT * 3
MAX_FRAMES = 5
CAPTURE_TIMEOUT = 24
MAX_MANIFEST = 131072
EXPLICIT_CLASSES = {'FEMALE_GENITALIA_EXPOSED', 'MALE_GENITALIA_EXPOSED', 'ANUS_EXPOSED',
                    'EXPOSED_GENITALIA_F', 'EXPOSED_GENITALIA_M', 'EXPOSED_ANUS'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def allowed_url(url):
    try:
        u = urllib.parse.urlsplit(url)
        return (u.scheme == 'https' and u.hostname and not u.username and
                not u.password and not u.query and not u.fragment and
                u.port in (None, 443) and not re.fullmatch(r'[\d.]+', u.hostname)
                and ':' not in u.hostname)
    except ValueError:
        return False


def manifest_check(url):
    """No redirects, protected manifests or arbitrary schemes."""
    if not allowed_url(url):
        return 'unsafe_url'
    opener = urllib.request.build_opener(NoRedirect())
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'TVIdentityPilot/1.0',
            'Accept': 'application/vnd.apple.mpegurl,application/dash+xml,*/*',
            'Range': f'bytes=0-{MAX_MANIFEST - 1}'})
        with opener.open(req, timeout=5) as response:
            data = response.read(MAX_MANIFEST).decode('utf-8-sig', errors='replace').lstrip()
        if data.startswith('#EXTM3U') and '#EXT-X-' in data:
            if '#EXT-X-SESSION-KEY' in data or re.search(r'#EXT-X-KEY:(?![^\r\n]*METHOD=NONE)', data):
                return 'protected_manifest'
            return 'ok'
        if re.search(r'<MPD[\s>]', data, re.I):
            return 'protected_manifest' if re.search(r'<ContentProtection\b', data, re.I) else 'ok'
        return 'not_a_manifest'
    except urllib.error.HTTPError as e:
        return f'http_{e.code}'
    except (OSError, ValueError):
        return 'manifest_unavailable'


def capture_frames(url):
    """Decode a short bounded sample into RAM, never display or persist media."""
    why = manifest_check(url)
    if why != 'ok':
        return [], why
    cmd = ['ffmpeg', '-nostdin', '-hide_banner', '-v', 'error',
           '-rw_timeout', '5000000', '-protocol_whitelist', 'https,tls,tcp',
           '-i', url, '-map', '0:v:0', '-an', '-sn', '-dn',
           '-vf', f'fps=1/3,scale={WIDTH}:{HEIGHT}:flags=bilinear',
           '-frames:v', str(MAX_FRAMES), '-pix_fmt', 'rgb24', '-threads', '1',
           '-f', 'rawvideo', 'pipe:1']
    try:
        run = subprocess.run(cmd, capture_output=True, timeout=CAPTURE_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        return [], 'decode_timeout'
    except OSError:
        return [], 'ffmpeg_unavailable'
    count = min(MAX_FRAMES, len(run.stdout) // FRAME_MS)
    if count == 0:
        # Classify failures without publishing stderr (which can contain media URLs).
        err = getattr(run, 'stderr', b'').decode('utf-8', errors='replace').lower()
        if '403 forbidden' in err or 'server returned 403' in err:
            return [], 'decode_http_403'
        if 'not on whitelist' in err or 'protocol not found' in err:
            return [], 'nested_protocol_not_allowed'
        if 'stream map' in err or 'does not contain any stream' in err:
            return [], 'no_decodable_video'
        return [], 'decode_failed'
    frames = [Image.frombytes('RGB', (WIDTH, HEIGHT), run.stdout[i*FRAME_MS:(i+1)*FRAME_MS])
              for i in range(count)]
    return frames, 'sampled' if count >= 3 else 'short_sample'


def fingerprint(frame):
    """Small luminance fingerprint and dHash; ignore edges/watermarks for scene match."""
    w, h = frame.size
    if min(w, h) < 32:
        return None
    gray = ImageOps.grayscale(frame.crop((w//10, h//10, w*9//10, h*9//10)))
    pixels = tuple(gray.resize((16, 16), Image.Resampling.BILINEAR).getdata())
    if statistics.pstdev(pixels) < 10:
        return None  # skip black/slates, not meaningful proof
    bits = tuple(gray.resize((17, 16), Image.Resampling.BILINEAR).getdata())
    dhash = 0
    for y in range(16):
        for x in range(16):
            dhash = (dhash << 1) | (bits[y*17+x] > bits[y*17+x+1])
    return dhash, pixels


def similarity(a, b):
    if a is None or b is None:
        return 1.0, 1.0
    hamming = (a[0] ^ b[0]).bit_count() / 256
    mae = sum(abs(x-y) for x, y in zip(a[1], b[1])) / (256*255)
    return hamming, mae


def compare_sequences(left, right):
    """Find two distinct, non-static matching scenes; never infer mismatch from absence."""
    a, b = list(map(fingerprint, left)), list(map(fingerprint, right))
    possible = []
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            dh, mae = similarity(x, y)
            if dh <= .12 and mae <= .13:
                possible.append((dh+mae, i, j))
    chosen = []
    for _, i, j in sorted(possible):
        if any(i == x or j == y for x, y in chosen):
            continue
        chosen.append((i, j))
    diversity = any(similarity(a[x], a[y])[0] >= .09 and
                    similarity(b[u], b[v])[0] >= .09
                    for x, u in chosen for y, v in chosen if x != y)
    return {'matched_frames': len(chosen), 'distinct_scenes': bool(diversity),
            'corroborated': len(chosen) >= 2 and bool(diversity)}


def load_detector():
    """Local detector; no network inference or external uploads."""
    try:
        from nudenet import NudeDetector
        return NudeDetector()
    except Exception:
        return None


def safety_check(frames, detector):
    if not frames:
        return 'not_sampled'
    if detector is None:
        return 'model_unavailable'
    try:
        for frame in frames:
            buf = io.BytesIO()
            frame.save(buf, format='JPEG', quality=82)
            for hit in detector.detect(buf.getvalue()):
                if hit.get('class') in EXPLICIT_CLASSES and float(hit.get('score', 0)) >= .70:
                    return 'explicit_suspected'
        return 'no_high_confidence_flag'
    except Exception:
        return 'model_error'


def logo_check(frames, template):
    """Optional manually-approved on-air watermark template; never uses generic branding as proof."""
    if not template:
        return {'status':'reference_missing','matches':0}
    if not frames:
        return {'status':'not_sampled','matches':0}
    try:
        import cv2
        import numpy as np
        stamp = cv2.imread(str(template), cv2.IMREAD_GRAYSCALE)
        if stamp is None or min(stamp.shape) < 8:
            return {'status':'invalid_reference','matches':0}
        matches = 0
        for image in frames:
            gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
            h, w = gray.shape
            score = 0.0
            for scale_width in (24, 36, 48, 60, 72, 96):
                scale_height = max(8, round(stamp.shape[0] * scale_width / stamp.shape[1]))
                if scale_height >= h//3:
                    continue
                t = cv2.Canny(cv2.resize(stamp, (scale_width, scale_height)), 40, 100)
                if float(t.std()) < 4:
                    continue
                for corner in (gray[:h//3,:w//3], gray[:h//3,-w//3:],
                               gray[-h//3:,:w//3], gray[-h//3:,-w//3:]):
                    edge = cv2.Canny(corner, 40, 100)
                    if edge.shape[0] < t.shape[0] or edge.shape[1] < t.shape[1]:
                        continue
                    value = cv2.minMaxLoc(cv2.matchTemplate(edge, t, cv2.TM_CCOEFF_NORMED))[1]
                    score = max(score, value)
            matches += score >= .78
        return {'status':'logo_observed' if matches >= 3 else 'inconclusive', 'matches':int(matches)}
    except Exception:
        return {'status':'logo_check_unavailable','matches':0}


def source_id(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def approved_targets(config, policy, reviewed):
    if config.get('schema') != 1 or policy.get('schema') != 1 or reviewed.get('schema') != 1:
        raise ValueError('Unexpected configuration schema')
    targets = []
    for cid in config.get('pilot_channels', []):
        for url in policy.get('approved_only', {}).get(cid, []):
            if (allowed_url(url) and urllib.parse.urlsplit(url).hostname not in policy['blocked_hosts']
                and url not in policy.get('blocked_by_channel', {}).get(cid, [])):
                targets.append({'channel':cid, 'url':url, 'role':'pilot'})
    for item in config.get('controls', []):
        cid, url = item.get('channel'), item.get('url')
        if (url in reviewed.get('channels', {}).get(cid, []) and allowed_url(url) and
            urllib.parse.urlsplit(url).hostname not in policy['blocked_hosts'] and
            url not in policy.get('blocked_by_channel', {}).get(cid, [])):
            targets.append({'channel':cid, 'url':url, 'role':'control'})
    return list({t['url']:t for t in targets}.values())[:8]


def audit(config, policy, reviewed, capture=capture_frames, detector=None):
    targets = approved_targets(config, policy, reviewed)
    now = datetime.now(timezone.utc).isoformat()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda t: capture(t['url']), targets))
    frames = [pair[0] for pair in results]
    safety = [safety_check(f, detector) for f in frames]
    rows = []
    for i,t in enumerate(targets):
        url, cid = t['url'], t['channel']
        host = urllib.parse.urlsplit(url).hostname
        good, other = [], []
        for j,ref in enumerate(targets):
            if i == j or not frames[j] or safety[j] != 'no_high_confidence_flag':
                continue
            # Self/identical-host comparisons are not independent evidence.
            if host == urllib.parse.urlsplit(ref['url']).hostname:
                continue
            evidence = compare_sequences(frames[i], frames[j])
            if evidence['corroborated']:
                entry = {'channel':ref['channel'], 'source_id':source_id(ref['url']), 'frames':evidence['matched_frames']}
                (good if ref['channel']==cid else other).append(entry)
        template = config.get('watermark_templates', {}).get(cid)
        path = (ROOT / template).resolve() if template else None
        # Only explicit local reference files inside the repository are accepted.
        if path and (not path.is_relative_to(ROOT.resolve()) or not path.is_file()):
            path = None
        logo = logo_check(frames[i], path)
        if safety[i] == 'explicit_suspected':
            status, reason = 'blocked_explicit_suspected', 'local_detector_flag'
        elif len(frames[i]) < 3:
            status, reason = 'uncertain', results[i][1]
        elif safety[i] != 'no_high_confidence_flag':
            status, reason = 'uncertain', safety[i]
        elif good and not other:
            status, reason = 'identity_evidence_confirmed', 'independent_official_routes_agree'
        elif other and not good:
            status, reason = 'suspected_mismatch', 'other_channel_scenes_match_review_required'
        else:
            status, reason = 'uncertain', 'insufficient_or_ambiguous_content_evidence'
        rows.append({'channel':cid,'role':t['role'],'host':host,'source_id':source_id(url),
                     'status':status,'reason':reason,'sampled_frames':len(frames[i]),'safety':safety[i],
                     'logo':logo,'expected_matches':good,'other_matches':other,
                     'publish_allowed':False})
    return {'schema':1,'mode':'shadow_review_only','generated_at':now, 'sources':rows,
            'review_queue':config.get('review_queue', []),
            'summary':{'checked':len(rows),'sampled':sum(bool(r['sampled_frames']) for r in rows),
                       'identity_evidence_confirmed':sum(r['status']=='identity_evidence_confirmed' for r in rows),
                       'uncertain':sum(r['status']=='uncertain' for r in rows),
                       'suspected_mismatch':sum(r['status']=='suspected_mismatch' for r in rows),
                       'explicit_suspected':sum(r['status']=='blocked_explicit_suspected' for r in rows)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'data/content-identity-pilot-report.json')
    args = parser.parse_args()
    report = audit(read_json(CONFIG), read_json(POLICY), read_json(REVIEWED), detector=load_detector())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
