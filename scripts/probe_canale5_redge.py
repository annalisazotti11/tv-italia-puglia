#!/usr/bin/env python3
"""Read-only probe of one public Canale 5 HLS candidate.

Fetches only the manifest, one media playlist and at most 4 KiB of one segment.
Never saves media, follows redirects only inside cdn-redge.media, uses no account,
token, proxy, DRM handling or geo-restriction bypass. This is not an authorization
check and GitHub's egress location is not Italy.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

TARGET = "https://n-5-1.eu.cdn-redge.media/livehls/oeu/mt/live/canale_5/live.livx/playlist.m3u8"
SUFFIX = ".cdn-redge.media"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TVItalia-ReadOnly-Stream-Check/1.0)",
    "Accept": "application/vnd.apple.mpegurl, application/x-mpegURL, */*",
}

def safe_url(url):
    try:
        u = urlsplit(url)
        host = (u.hostname or "").lower().rstrip(".")
        return (u.scheme == "https" and host.endswith(SUFFIX)
                and u.username is None and u.password is None
                and u.port in (None, 443) and not u.fragment and not u.query)
    except ValueError:
        return False

class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_url(newurl):
            raise ValueError("redirect_outside_redge_or_signed_url")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

OPENER = build_opener(SafeRedirect)

def get(url, limit=200_000, byte_range=None):
    if not safe_url(url):
        raise ValueError("url_outside_redge_or_signed_url")
    headers = dict(HEADERS)
    if byte_range:
        headers["Range"] = byte_range
    req = Request(url, headers=headers)
    with OPENER.open(req, timeout=12) as response:
        final = response.geturl()
        if not safe_url(final):
            raise ValueError("redirect_outside_redge_or_signed_url")
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("response_too_large")
        return response.status, response.headers.get("Content-Type", ""), final, data

def parse_hls(text, base):
    if "#EXT-X-SESSION-KEY:" in text:
        raise ValueError("protected_session_key")
    for line in text.splitlines():
        if line.startswith("#EXT-X-KEY:") and "METHOD=NONE" not in line:
            raise ValueError("encrypted_hls")
    variants = []
    lines = text.splitlines()
    for i, line in enumerate(lines[:-1]):
        if line.startswith("#EXT-X-STREAM-INF:"):
            nextline = next((x.strip() for x in lines[i+1:] if x.strip() and not x.strip().startswith("#")), None)
            if not nextline:
                continue
            resolution = re.search(r"RESOLUTION=(\d+)x(\d+)", line, re.I)
            height = int(resolution.group(2)) if resolution else 0
            bandwidth = re.search(r"(?:AVERAGE-)?BANDWIDTH=(\d+)", line, re.I)
            variants.append((height, int(bandwidth.group(1)) if bandwidth else 0, urljoin(base, nextline)))
    if variants:
        variants.sort(reverse=True)
        return "master", variants[0][2], variants[0][0]
    if "#EXT-X-TARGETDURATION" in text and "#EXTINF" in text:
        for i, line in enumerate(lines):
            if line.startswith("#EXTINF"):
                segment = next((x.strip() for x in lines[i+1:] if x.strip() and not x.strip().startswith("#")), None)
                if segment:
                    return "media", urljoin(base, segment), 0
    raise ValueError("not_a_recognized_live_hls_playlist")

def main():
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate": TARGET,
        "network": "GitHub-hosted runner; not an Italian residential connection",
        "media_saved": False,
        "authorization_verified": False,
        "publish_allowed": False,
    }
    try:
        status, ctype, final, data = get(TARGET)
        text = data.decode("utf-8-sig", errors="replace").lstrip()
        if status != 200 or not text.startswith("#EXTM3U"):
            raise ValueError("response_not_hls_manifest")
        kind, next_url, height = parse_hls(text, final)
        report.update(manifest_http=status, manifest_content_type=ctype, final_host=urlsplit(final).hostname,
                      manifest_type=kind, declared_height=height or None)
        if kind == "master":
            status2, ctype2, final2, data2 = get(next_url)
            text2 = data2.decode("utf-8-sig", errors="replace").lstrip()
            if status2 != 200 or not text2.startswith("#EXTM3U"):
                raise ValueError("variant_not_hls")
            if "#EXT-X-TARGETDURATION" not in text2 or "#EXTINF" not in text2:
                raise ValueError("variant_not_media_playlist")
            _, segment_url, _ = parse_hls(text2, final2)
            report["variant_http"] = status2
            report["variant_host"] = urlsplit(final2).hostname
        else:
            segment_url = next_url
        seg_status, seg_type, seg_final, sample = get(segment_url, limit=4096, byte_range="bytes=0-4095")
        if seg_status not in (200, 206) or len(sample) < 64:
            raise ValueError("media_segment_not_readable")
        if "text/html" in seg_type.lower() or sample.lstrip().lower().startswith((b"<html", b"<!doctype", b'{"error"')):
            raise ValueError("media_segment_is_not_video_data")
        report.update(status="manifest_and_segment_reachable", segment_http=seg_status,
                      segment_bytes_sampled=len(sample), segment_content_type=seg_type,
                      segment_host=urlsplit(seg_final).hostname)
    except Exception as exc:
        report.update(status="probe_failed", error=type(exc).__name__ + ": " + str(exc)[:180])
    output = Path("artifacts/canale5-redge-probe.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
