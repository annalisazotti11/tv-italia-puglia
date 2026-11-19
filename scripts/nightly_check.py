#!/usr/bin/env python3
"""TV Italia + Puglia: nightly source health index.

Runs in a public GitHub Actions standard Ubuntu runner. Reads the existing M3U,
curated public M3U directories, verifies playable unencrypted HLS/DASH manifests,
and writes a *ranked snapshot* for the Cloudflare Worker. No logins, DRM bypass,
random web crawling or sensitive URLs are used.
"""
from __future__ import annotations

import concurrent.futures
from collections import Counter
import datetime as dt
import ipaddress
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MAIN_M3U = ROOT / 'TV_Italia_Puglia_con_loghi.m3u'
OUTPUT = ROOT / 'data' / 'verified-streams.json'

# Explicitly selected public playlists. Do not accept arbitrary user-supplied URLs.
PUBLIC_PLAYLISTS = [
    ('iptv-org Italy', 'https://iptv-org.github.io/iptv/countries/it.m3u'),
    ('Free-TV Italia', 'https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_italy.m3u8'),
    ('OpenIPTVItaly', 'https://raw.githubusercontent.com/xN1ckuz/OpenIPTVItaly/main/OpenIPTVItaly_No_EPG.m3u'),
    ('Tundrak IPTV-Italia', 'https://raw.githubusercontent.com/Tundrak/IPTV-Italia/main/iptvita.m3u'),
    ('TVITALIA', 'https://raw.githubusercontent.com/maginetweb-arch/TVITALIA/main/iptvit.m3u'),
]
# Additional published, unauthenticated entry for an existing channel only.
# Keep the original M3U unchanged and use the normal HTTPS request.
EXPLICIT_PUBLIC_ALTERNATIVES = [
    ('Rai 5', 'https://raicinque3-live.akamaized.net/hls/live/2018007/raicinque3/raicinque3/playlist.m3u8'),
    ('Rai News 24', 'https://rainews1-live.akamaized.net/hls/live/598326/rainews1/rainews1/playlist.m3u8'),
    ('TGCOM24', 'https://live2-mediaset-it.akamaized.net/Content/hls_h0_clr_vos/live/channel(kf)/index.m3u8'),
]
EXTRA_CHANNELS = [
    ('Sky Cinema Romance', 'sky-cinema-romance'),
    ('Sky Uno', 'sky-uno'),
    ('History', 'history'),
    ('Sky Cinema Family', 'sky-cinema-family'),
    ('Sky Cinema Drama', 'sky-cinema-drama'),
    ('Sky Cinema Comedy', 'sky-cinema-comedy'),
    ('Sky Cinema Action', 'sky-cinema-action'),
    ('Sky Documentaries', 'sky-documentaries'),
    ('Sky Sport Uno', 'sky-sport-uno'),
]

USER_AGENT = 'TVItalia-Puglia-Health/1.0 (+https://github.com/annalisazotti11/tv-italia-puglia)'
HEADERS = {'User-Agent': USER_AGENT, 'Accept': '*/*'}
MAX_PLAYLIST_BYTES = 2_000_000
MAX_MANIFEST_BYTES = 90_000
MAX_CANDIDATES_PER_CHANNEL = 10
MAX_VERIFIED_PER_CHANNEL = 5
WORKERS = 14
TIMEOUT = 5.5
ALIASES = {
    'rai uno': 'rai 1', 'rai due': 'rai 2', 'rai tre': 'rai 3',
    'rete4': 'rete 4', 'retequattro': 'rete 4', 'la 7': 'la7',
    'twentyseven': '27 twentyseven', 'twenty seven': '27 twentyseven',
    'la5': 'la 5', 'rai news24': 'rai news 24',
    'rainews24': 'rai news 24', 'sky tg 24': 'sky tg24',
    'sky sport 1': 'sky sport uno', 'sky sports uno': 'sky sport uno',
    'radio 105': 'radio 105 tv', 'radioitaliatv': 'radio italia tv',
    'rai 3 puglia': 'rai 3 tgr puglia', 'tgr puglia': 'rai 3 tgr puglia',
    'tg norba24': 'tg norba 24', 'radionorba': 'radionorba tv',
    'gambero rosso tv': 'gambero rosso',
    'tgcom 24': 'tgcom24',
}
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
HLS_RE = re.compile(r'^#EXT-X-(?:STREAM-INF|TARGETDURATION|MEDIA|INF|MAP)\b', re.I | re.M)
MED_BROADCAST_CODE = {'ew': '68', 'ec': '66', 'c5': '5', 'r4': '4',
                      'i1': '6', 'lb': '20', 'ki': '22', 'ts': '27',
                      'ka': '30', 'b6': '34', 'fu': '35'}

# Only accept stable, unauthenticated addresses on the selected broadcaster/CDN
# hosts. Being listed in a public community playlist is not authorization.
APPROVED_STREAM_HOSTS = {
    'rai 1': {'raiuno3-live.akamaized.net'},
    'rai 2': {'raidue3-live.akamaized.net'},
    'rai 3': {'raitre3-live.akamaized.net'},
    'rai 3 tgr puglia': {'tgrpuglia-live.akamaized.net'},
    'rai 4': {'raiquattro3-live.akamaized.net'},
    'rai 5': {'raicinque3-live.akamaized.net'},
    'rai news 24': {'rainews1-live.akamaized.net'},
    'tgcom24': {'live2-mediaset-it.akamaized.net'},
    'rai movie': {'raimovie3-live.akamaized.net'},
    'rai storia': {'raistoria3-live.akamaized.net'},
    'rete 4': {'live02-seg.msf.cdn.mediaset.net'},
    'canale 5': {'live02-seg.msf.cdn.mediaset.net'},
    'italia 1': {'live02-seg.msf.cdn.mediaset.net'},
    '20 mediaset': {'live02-seg.msf.cdn.mediaset.net'},
    '27 twentyseven': {'live02-seg.msf.cdn.mediaset.net'},
    'iris': {'live02-col.msf.cdn.mediaset.net'},
    'la 5': {'live02-col.msf.cdn.mediaset.net'},
    'cine34': {'live02-col.msf.cdn.mediaset.net'},
    'focus': {'live02-col.msf.cdn.mediaset.net'},
    'radio 105 tv': {'live02-seg.msr.cdn.mediaset.net'},
    'tv8': {'hlslive-web-gcdn-skycdn-it.akamaized.net'},
    'cielo': {'hlslive-web-gcdn-skycdn-it.akamaized.net'},
    'sky tg24': {'hlslive-web-gcdn-skycdn-it.akamaized.net'},
    'radio italia tv': {'radioitaliatv.akamaized.net'},
    # Public live services confirmed on the broadcasters' or service providers'
    # sites. These source hosts are already in the user's original playlist.
    'radionorba tv': {'router.xdevel.com'},
    'tg norba 24': {'stream6.xdevel.com'},
    'antenna sud': {'live-antennasud.cdn.netrw.it'},
    'telebari': {'w1.mediastreaming.it'},
    'radio kiss kiss tv': {'kk.fluid.stream'},
    'nove': {'streaming.aurora.enhanced.live'},
    'real time': {'streaming.aurora.enhanced.live'},
    'food network': {'streaming.aurora.enhanced.live'},
    'dmax': {'streaming.aurora.enhanced.live'},
    'hgtv': {'streaming.aurora.enhanced.live'},
    'rtl 102 5': {'dd782ed59e2a4e86aabf6fc508674b59.msvdn.net'},
    'deejay tv': {'4c4b867c89244861ac216426883d1ad0.msvdn.net'},
}

DISCOVERY_ROUTES = {'nove':'NOVE','real time':'REALTIME','food network':'FOODNETWORK','dmax':'DMAX','hgtv':'HGTV'}

# Shared streaming providers must also match this channel's own route.
APPROVED_STREAM_PATH_PREFIXES = {
    'radionorba tv': ('/video0s975885-462/stream/',),
    'tg norba 24': ('/video0s976570-1326/stream/',),
    'antenna sud': ('/antennasud/',),
    'telebari': ('/telebari/',),
    'radio kiss kiss tv': ('/KKMulti/smil:KissKissTV.smil/',),
    'rai news 24': ('/hls/live/598326/rainews1/',),
    'tgcom24': ('/Content/hls_h0_clr_vos/live/channel(kf)/',),
    'rtl 102 5': ('/live/S97044836/',),
    'deejay tv': ('/live/S85984808/',),
}


def wrong_channel_redirect(channel_id: str, final_url: str) -> bool:
    # Reject known Mediaset cross-channel redirects even if they return valid video.
    expected = re.search(r'^tvip_(\d+)_', channel_id)
    if not expected:
        return False
    code = re.search(r'/live/ch-([a-z0-9]+)/', urllib.parse.urlsplit(final_url).path, re.I)
    if not code:
        return False
    actual = MED_BROADCAST_CODE.get(code.group(1).lower())
    return actual is not None and actual != expected.group(1)



def normalize(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s or ''))
    s = ''.join(x for x in s if unicodedata.category(x) != 'Mn').lower()
    s = re.sub(r'^[\s\[\(]*(?:it|ita|italy|italia)\s*[:|\]\)\-]+\s*', '', s)
    s = re.sub(r'[^a-z0-9]+', ' ', s).strip()
    # Only remove generic trailing quality labels; don't alter channel identity.
    s = re.sub(r'(?:\s+(?:hd|fhd|uhd|sd|4k|1080p|720p|h265|hevc|italy|italia))+$', '', s)
    return ALIASES.get(s, s)


def slug(s: str) -> str:
    return re.sub(r'\s+', '-', normalize(s)) or 'canale'


def js_slug(s: str) -> str:
    # Worker slug() removes punctuation but not HD from the original title.
    s = unicodedata.normalize('NFD', str(s or ''))
    s = ''.join(x for x in s if unicodedata.category(x) != 'Mn').lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-') or 'canale'


def safe_url(url: str) -> bool:
    if not url or len(url) > 3000 or any(ord(c) < 32 for c in url):
        return False
    try:
        u = urllib.parse.urlsplit(url)
        if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password:
            return False
        host = u.hostname.lower().strip('.')
        if host == 'localhost' or host.endswith(('.local', '.internal', '.localhost')):
            return False
        try:
            addr = ipaddress.ip_address(host)
            if not addr.is_global:
                return False
        except ValueError:
            pass
        return True
    except ValueError:
        return False


def permitted_stream_url(name: str, url: str) -> bool:
    if not safe_url(url):
        return False
    u = urllib.parse.urlsplit(url)
    canonical = normalize(name)
    prefixes = APPROVED_STREAM_PATH_PREFIXES.get(canonical)
    if canonical in DISCOVERY_ROUTES and not re.fullmatch(r'/live/mpc/[^/]+/out/v1/IT_SIMULCAST/' + DISCOVERY_ROUTES[canonical] + r'/CMAF/[^/]+\.m3u8', u.path):
        return False
    return (u.scheme == 'https' and not u.query and not u.fragment
            and u.hostname in APPROVED_STREAM_HOSTS.get(canonical, set())
            and (not prefixes or u.path.startswith(prefixes)))


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_url(newurl):
            raise urllib.error.HTTPError(newurl, 403, 'Blocked redirect target', headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(SafeRedirect)


def get(url: str, max_bytes: int = MAX_MANIFEST_BYTES, timeout: float = TIMEOUT) -> tuple[bytes, str, str]:
    if not safe_url(url):
        raise ValueError('Unsupported or unsafe URL')
    req = urllib.request.Request(url, headers={**HEADERS, 'Range': f'bytes=0-{max_bytes-1}'})
    with OPENER.open(req, timeout=timeout) as r:
        final_url = r.geturl()
        if not safe_url(final_url):
            raise ValueError('Unsafe final URL')
        data = r.read(max_bytes)
        return data, (r.headers.get('content-type') or '').lower(), final_url


def parse_m3u(text: str):
    entry = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('#EXTINF:'):
            name = line.split(',', 1)[1].strip() if ',' in line else ''
            attrs = dict(ATTR_RE.findall(line))
            entry = (name, attrs)
        elif entry and line and not line.startswith('#'):
            if safe_url(line):
                yield {'name': entry[0], 'attrs': entry[1], 'url': line}
            entry = None


def inventory():
    contents = MAIN_M3U.read_text(encoding='utf-8-sig')
    if not contents.startswith('#EXTM3U'):
        raise ValueError('Invalid main M3U')
    ids, by_name = {}, {}
    for item in parse_m3u(contents):
        name = item['name']
        n = item['attrs'].get('tvg-chno', '')
        cid = 'tvip_' + (n or js_slug(name)) + '_' + js_slug(name)
        if cid not in ids:
            ids[cid] = {'id': cid, 'name': name, 'number': str(n), 'urls': [], 'results': []}
        if permitted_stream_url(name, item['url']):
            ids[cid]['urls'].append({'url': item['url'], 'source': 'Playlist originale'})
        by_name.setdefault(normalize(name), []).append(cid)
    for name, code in EXTRA_CHANNELS:
        cid = 'tvip_sky_' + code.replace('-', '_')
        ids[cid] = {'id': cid, 'name': name, 'number': '', 'urls': [], 'results': []}
        by_name.setdefault(normalize(name), []).append(cid)
    return ids, by_name


def assign_candidate(channels, by_name, name, attrs, url, provider):
    if not permitted_stream_url(name, url):
        return
    label = normalize(name)
    matched = by_name.get(label, [])
    if not matched:
        return
    chno = str(attrs.get('tvg-chno', '')).strip()
    # A claimed number must agree with the target (except extra channels without a number).
    for cid in matched:
        ch = channels[cid]
        if chno and ch['number'] and chno != ch['number']:
            continue
        if len(ch['urls']) >= MAX_CANDIDATES_PER_CHANNEL:
            break
        if not any(x['url'] == url for x in ch['urls']):
            ch['urls'].append({'url': url, 'source': provider})


def scan_playlists(channels, by_name):
    status = []
    for name, url in PUBLIC_PLAYLISTS:
        try:
            raw, _ct, _url = get(url, MAX_PLAYLIST_BYTES, timeout=12)
            text = raw.decode('utf-8-sig', errors='replace')
            if not text.startswith('#EXTM3U'):
                raise ValueError('Missing EXTM3U')
            n = 0
            for item in parse_m3u(text):
                assign_candidate(channels, by_name, item['name'], item['attrs'], item['url'], name)
                n += 1
            status.append({'name': name, 'read': True, 'entries': n})
        except Exception as exc:
            status.append({'name': name, 'read': False, 'reason': type(exc).__name__})
    for name, url in EXPLICIT_PUBLIC_ALTERNATIVES:
        assign_candidate(channels, by_name, name, {}, url, 'Fonte HTTPS pubblicata')
    return status


def hls_variants(master: str, origin: str):
    items = []
    lines = master.splitlines()
    for i, line in enumerate(lines[:-1]):
        if line.startswith('#EXT-X-STREAM-INF:'):
            res = re.search(r'RESOLUTION=(\d+)x(\d+)', line, re.I)
            bw = re.search(r'(?:AVERAGE-)?BANDWIDTH=(\d+)', line, re.I)
            codes = re.search(r'CODECS="([^"]+)"', line, re.I)
            for nextline in lines[i + 1:]:
                nextline = nextline.strip()
                if nextline and not nextline.startswith('#'):
                    u = urllib.parse.urljoin(origin, nextline)
                    if safe_url(u):
                        items.append((int(res.group(2)) if res else 0,
                                      int(bw.group(1)) if bw else 0,
                                      bool(codes and re.search(r'mp4a|ac-3|ec-3|opus', codes.group(1), re.I)),
                                      u))
                    break
    return sorted(items, reverse=True)


def media_segment_url(body: str, base: str):
    lines = body.splitlines()
    if any('#EXT-X-KEY:' in line and 'METHOD=NONE' not in line for line in lines):
        raise ValueError('Encrypted HLS')
    if '#EXT-X-TARGETDURATION' not in body or '#EXTINF' not in body:
        raise ValueError('Not a media playlist')
    for i, line in enumerate(lines):
        if line.startswith('#EXTINF'):
            for nextline in lines[i+1:]:
                segment = nextline.strip()
                if segment and not segment.startswith('#'):
                    result = urllib.parse.urljoin(base, segment)
                    if safe_url(result):
                        return result
                    break
    raise ValueError('Missing segment URL')


def probe_one(cid: str, item: dict):
    started = time.monotonic()
    source = item['url']
    out = {'channel_id': cid, 'source': item['source'], 'url': source, 'ok': False, 'reason': None}
    try:
        raw, ctype, actual = get(source)
        if wrong_channel_redirect(cid,actual):
            raise ValueError('Redirect to different channel')
        body = raw.decode('utf-8-sig', errors='replace').lstrip()
        if body.lower().startswith(('<html', '<!doctype html')):
            raise ValueError('HTML instead of manifest')
        height = bandwidth = 0
        audio = False
        kind = ''
        if body.startswith('#EXTM3U') and HLS_RE.search(body):
            kind = 'HLS'
            if '#EXT-X-SESSION-KEY' in body:
                raise ValueError('HLS protected session')
            variants = hls_variants(body, actual)
            if variants:
                # Try at most two profiles; one may be geo-blocked.
                last_error = None
                for h, bw, a, variant in variants[:2]:
                    try:
                        media, _mime, resolved = get(variant)
                        media_text = media.decode('utf-8-sig', errors='replace')
                        segment = media_segment_url(media_text, resolved)
                        sample, sample_ct, _final = get(segment, max_bytes=4096)
                        if len(sample) < 64 or 'text/html' in sample_ct or sample.lstrip()[:80].lower().startswith((b'<html',b'<!doctype',b'{\"error\"')):
                            raise ValueError('No media segment bytes')
                        height, bandwidth, audio = h, bw, a
                        last_error = None
                        break
                    except Exception as exc:
                        last_error = exc
                if last_error is not None:
                    raise ValueError(f'Unplayable HLS variant: {type(last_error).__name__}')
            else:
                segment = media_segment_url(body, actual)
                sample, sample_ct, _final = get(segment, max_bytes=4096)
                if len(sample) < 64 or 'text/html' in sample_ct or sample.lstrip()[:80].lower().startswith((b'<html',b'<!doctype',b'{\"error\"')):
                    raise ValueError('No media segment bytes')
        elif re.search(r'<MPD(?:\s|>)', body, re.I) and re.search(r'<Period(?:\s|>)', body, re.I):
            if re.search(r'<ContentProtection\b', body, re.I):
                raise ValueError('Protected DASH')
            if not re.search(r'<AdaptationSet\b|<Representation\b', body, re.I):
                raise ValueError('Missing DASH tracks')
            if not re.search(r'contentType="video"|mimeType="video/|\bheight="\d+"|avc1|hvc1', body, re.I):
                raise ValueError('DASH not recognized as video')
            kind = 'DASH'
            heights = [int(x) for x in re.findall(r'\bheight="(\d+)"', body, re.I)]
            bws = [int(x) for x in re.findall(r'\bbandwidth="(\d+)"', body, re.I)]
            height = max(heights, default=0)
            bandwidth = max(bws, default=0)
            audio = bool(re.search(r'contentType="audio"|mimeType="audio/|mp4a|ac-3|ec-3', body, re.I))
        else:
            raise ValueError('Not an HLS/DASH manifest')
        latency_ms = int((time.monotonic() - started) * 1000)
        score = (100 if kind == 'HLS' else 80) + min(height, 1080)/18 + (
            18 if audio else 0) + (8 if source.startswith('https:') else 0) - min(latency_ms/250, 20)
        out.update(ok=True, kind=kind, height=height, bandwidth=bandwidth, audio=audio,
                   latency_ms=latency_ms, score=round(score, 2))
    except urllib.error.HTTPError as exc:
        out['reason'] = f'HTTP {exc.code}'
    except ValueError as exc:
        # Our validation errors contain no addresses or content from the source.
        known = ('Unsupported or unsafe URL', 'Unsafe final URL', 'Redirect to different channel', 'HTML instead of manifest', 'HLS protected session', 'Encrypted HLS', 'Not a media playlist', 'Missing segment URL', 'No media segment bytes', 'Protected DASH', 'Missing DASH tracks', 'DASH not recognized as video', 'Not an HLS/DASH manifest')
        reason = str(exc)
        out['reason'] = reason if reason in known or reason.startswith('Unplayable HLS variant: ') else 'ValueError'
    except Exception as exc:
        out['reason'] = type(exc).__name__
    return out


def main():
    channels, names = inventory()
    playlist_status = scan_playlists(channels, names)
    jobs = [(cid, candidate) for cid, c in channels.items() for candidate in c['urls']]
    print(f'Candidates: {len(jobs)} across {len(channels)} configured channels', flush=True)
    for p in playlist_status:
        print(f"Playlist {p['name']}: " + (f"{p['entries']} entries" if p['read'] else f"unavailable ({p.get('reason', 'unknown')})"), flush=True)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for result in ex.map(lambda pair: probe_one(*pair), jobs):
            results.append(result)
    for result in results:
        channels[result['channel_id']]['results'].append(result)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    stamped = now.isoformat().replace('+00:00', 'Z')
    previous = {}
    if OUTPUT.exists():
        try:
            previous = json.loads(OUTPUT.read_text(encoding='utf-8')).get('channels', {})
        except (OSError, ValueError):
            previous = {}
    snapshot = {'schema': 1, 'generated_at': stamped, 'playlists': playlist_status, 'channels': {}}
    verified_count = 0
    for cid, ch in channels.items():
        verified = sorted((x for x in ch['results'] if x['ok']), key=lambda x: x['score'], reverse=True)
        verified_count += len(verified)
        entries = [{k: x[k] for k in ('url','source','kind','height','bandwidth','audio','latency_ms','score')}
                   | {'last_ok': stamped, 'stale': False}
                   for x in verified[:MAX_VERIFIED_PER_CHANNEL]]
        # Geography-specific 403 / timeout in the GitHub runner is NOT proof of a dead stream.
        # Retain an earlier success for a maximum of 36 hours; a hard HTTP 404/HTML does not get grace.
        prior = previous.get(cid, {}).get('verified', [])
        fresh_urls = {x['url'] for x in entries}
        current = {x['url']: x for x in ch['results']}
        for old in prior:
            if len(entries) >= MAX_VERIFIED_PER_CHANNEL:
                break
            url = old.get('url')
            if not url or url in fresh_urls or not permitted_stream_url(ch['name'], url):
                continue
            result = current.get(url)
            reason = str(result.get('reason') or '') if result else ''
            uncertain = not result or reason in ('TimeoutError','URLError','ConnectionResetError') or reason in ('HTTP 403','HTTP 429')
            if not uncertain:
                continue
            try:
                last = dt.datetime.fromisoformat(old['last_ok'].replace('Z','+00:00'))
                if last.tzinfo is None or (now-last).total_seconds() > 36*3600:
                    continue
            except (KeyError, ValueError, TypeError):
                continue
            entries.append({**old, 'stale': True})
            fresh_urls.add(url)
        # Do not publish long-lived unverified URLs or error-bearing tokens in reports.
        snapshot['channels'][cid] = {
            'name': ch['name'], 'verified': entries, 'tested': len(ch['results']),
            'visible': bool(entries), 'checked_at': stamped,
            'failures': dict(Counter(x.get('reason') or 'Unknown' for x in ch['results'] if not x['ok'])),
        }
    snapshot['summary'] = {
        'channels': len(channels), 'visible': sum(bool(x['visible']) for x in snapshot['channels'].values()),
        'hidden': sum(not x['visible'] for x in snapshot['channels'].values()),
        'sources_verified': verified_count, 'links_tested': len(jobs),
        'playlists_loaded': sum(p['read'] for p in playlist_status),
        'failure_reasons': dict(Counter(x.get('reason') or 'Unknown' for x in results if not x['ok'])),
    }
    # The first run must publish a truthful snapshot even if no links work.
    # On later runs, previously verified links may only survive via the 36-hour
    # grace rule above; never republish an old catalog indefinitely.
    visible_count = snapshot['summary']['visible']
    snapshot['summary']['status'] = 'ok' if visible_count >= 3 else ('degraded' if visible_count else 'no_verified_streams')
    if visible_count < 3:
        print(f'WARNING: only {visible_count} visible channel(s); publishing diagnostic snapshot with no unverified links', flush=True)
    print('Probe failure reasons: ' + json.dumps(snapshot['summary']['failure_reasons']), flush=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(f'Wrote {OUTPUT}: {json.dumps(snapshot["summary"], ensure_ascii=False)}')


if __name__ == '__main__':
    main()
