#!/usr/bin/env python3
"""Rank public live TV links by real video/audio packets and startup cost.

Run after nightly_check.py. An HTTPS URL returning a manifest is NOT proof
that video/audio can be decoded; a stream labelled 'playback_ready' must
expose both video and audio packets to FFprobe. The runner is outside Italy:
geo-denied results remain unconfirmed backups, never labelled playable.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import datetime as dt
import json
import shutil
import subprocess
import time
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'data/verified-streams.json'
MAX_ATTEMPTS_PER_CHANNEL = 6
CONCURRENCY = 10
FFPROBE_TIMEOUT = 10.5
PROBE_MAX_AGE_HOURS = 24


def packet_tracks(data):
    """Select only tracks that actually emitted packets; do not assume track 0."""
    packet_indices = {p.get('stream_index') for p in data.get('packets', [])}
    streams = [s for s in data.get('streams', []) if s.get('index') in packet_indices]
    videos = [s for s in streams if s.get('codec_type') == 'video' and int(s.get('height') or 0) > 0]
    audios = [s for s in streams if s.get('codec_type') == 'audio']
    video = max(videos, key=lambda s: int(s.get('height') or 0), default=None)
    audio = next((s for s in audios if s.get('codec_name') == 'aac'), None) or next(iter(audios), None)
    return video, audio


def probe_stream(url: str, *, extended: bool = False) -> dict:
    """Inspect actual *packets*, not only manifest metadata.

    FFprobe opens the stream and reads up to 2s of audio/video packets.
    Failures do not prove the stream unavailable on a different network.
    """
    start = time.monotonic()
    result = {
        'playback_ready': False, 'has_video': False, 'has_audio': False,
        'startup_ms': None, 'probe_ms': None, 'video_codec': None,
        'audio_codec': None, 'playback_height': 0, 'reason': 'unknown'
    }
    try:
        u = urllib.parse.urlsplit(url)
        if (u.scheme != 'https' or not u.hostname or u.username or u.password
                or u.fragment or u.port not in (None, 443, 8080, 8443)):
            result['reason'] = 'unsafe_url'
            return result
        cmd = [
            'ffprobe', '-v', 'error',
            '-rw_timeout', '10000000' if extended else '5000000',
            '-probesize', '2097152' if extended else '524288',
            '-analyzeduration', '5000000' if extended else '1500000',
            '-read_intervals', '%+5' if extended else '%+2',
            '-show_entries',
            'stream=index,codec_type,codec_name,width,height:packet=stream_index',
            '-of', 'json', url
        ]
        run = subprocess.run(
            cmd, capture_output=True, text=True, timeout=25 if extended else FFPROBE_TIMEOUT,
            check=False
        )
        result['probe_ms'] = int((time.monotonic() - start) * 1000)
        if run.returncode != 0 or not run.stdout.strip():
            result['reason'] = 'ffprobe_error'
            return result
        data = json.loads(run.stdout)
        video, audio = packet_tracks(data)
        result['has_video'] = video is not None
        result['has_audio'] = audio is not None
        result['video_codec'] = video.get('codec_name') if video else None
        result['audio_codec'] = audio.get('codec_name') if audio else None
        result['playback_height'] = int((video or {}).get('height') or 0)
        result['playback_ready'] = result['has_video'] and result['has_audio']
        result['reason'] = 'audio_video_packets' if result['playback_ready'] else (
            'video_only' if result['has_video'] else 'audio_only' if
            result['has_audio'] else 'no_packets'
        )
        # Probe time includes analysis of up to two seconds of media: use as a
        # comparative speed indicator, not as literal time-to-first-frame.
        result['startup_ms'] = result['probe_ms'] if result['playback_ready'] else None
    except subprocess.TimeoutExpired:
        result['reason'] = 'ffprobe_timeout'
        result['probe_ms'] = int((time.monotonic() - start) * 1000)
    except (OSError, ValueError, json.JSONDecodeError):
        result['reason'] = 'ffprobe_failed'
    return result


def rank(entry: dict) -> float:
    ready = bool(entry.get('playback_ready'))
    av_tracks = bool(entry.get('has_video')) and bool(entry.get('has_audio'))
    confirmed = bool(entry.get('last_ok'))
    speed = entry.get('startup_ms') or entry.get('latency_ms') or 10000
    height = min(int(entry.get('playback_height') or entry.get('height') or 0), 1080)
    runs = min(int(entry.get('success_runs') or 0), 30)
    bitrate = int(entry.get('bandwidth') or 0)
    # A working, quick 720p A/V stream beats a slow/unknown 1080p link.
    score = (8000 if ready else 1000 if av_tracks else 0)
    score += 300 if confirmed else 0
    score += 80 if entry.get('audio') else 0
    score += runs * 12
    score += min(height, 720) / 10
    score += max(0, min(height - 720, 360)) / 45
    score -= min(float(speed) / 16, 700)
    score -= 60 if bitrate > 7500000 else 0
    score -= 600 if entry.get('stale') else 0
    return round(score, 2)


def enhance(data: dict, probe=probe_stream) -> dict:
    tasks = []
    for cid, channel in data.get('channels', {}).items():
        fresh = channel.get('verified', [])
        candidates = channel.get('candidates', [])
        selected = []
        for source, verified in (
            [(x, True) for x in fresh[:MAX_ATTEMPTS_PER_CHANNEL]] +
            [(x, False) for x in candidates[:(2 if fresh else 4)]]
        ):
            if source.get('url') and source['url'] not in [
                x['url'] for x, _ in selected
            ]:
                selected.append((source, verified))
        for source, verified in selected:
            tasks.append((cid, source, verified))
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        outcomes = list(executor.map(lambda t: probe(t[1]['url']), tasks))
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
    for (cid, source, verified), result in zip(tasks, outcomes):
        source.update(result)
        source['playback_checked_at'] = now
    ready_count = 0
    for channel in data['channels'].values():
        for group in ('verified', 'candidates'):
            for entry in channel.get(group, []):
                entry['rank_score'] = rank(entry)
                if entry.get('playback_ready'):
                    ready_count += 1
            channel[group].sort(
                key=lambda x: x['rank_score'], reverse=True
            )
        channel['av_ready_count'] = sum(
            bool(x.get('playback_ready')) for x in
            channel.get('verified', []) + channel.get('candidates', [])
        )
    data.setdefault('summary', {})['audio_video_verified'] = ready_count
    data['summary']['playback_probe_count'] = len(tasks)
    data['summary']['playback_rank_updated_at'] = now
    return data


def main() -> None:
    if not shutil.which('ffprobe'):
        raise SystemExit('ffprobe required; install ffmpeg package')
    data = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    enhance(data)
    SNAPSHOT.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + '\n',
        encoding='utf-8'
    )
    print('A/V playback probe:',
          data['summary'].get('audio_video_verified', 0), 'ready of',
          data['summary'].get('playback_probe_count', 0), 'tested',
          flush=True)


if __name__ == '__main__':
    main()
