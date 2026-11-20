import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).parent / "playback_quality.py"
spec = importlib.util.spec_from_file_location("playback_quality", SCRIPT)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PlaybackQualityTests(unittest.TestCase):
    def test_real_av_beats_fast_manifest_only_hd(self):
        slow1080 = dict(last_ok="2026-11-20T08:00:00Z", audio=True,
                        height=1080, latency_ms=300, bandwidth=9000000,
                        playback_ready=False, probe_ms=1000)
        av720 = dict(last_ok="2026-11-20T08:00:00Z", audio=True,
                     height=720, bandwidth=4000000,
                     playback_ready=True, has_audio=True, has_video=True,
                     startup_ms=1700)
        self.assertGreater(p.rank(av720), p.rank(slow1080))

    def test_probe_results_enrich_and_reorder(self):
        snapshot = {
            "schema": 1, "channels": {
                "tvip_5_canale-5-hd": {
                    "verified": [
                        {"url": "https://example.org/a.m3u8", "height": 1080, "latency_ms": 400,
                         "last_ok": "2026-11-20T08:00:00Z"},
                        {"url": "https://example.org/b.m3u8", "height": 720, "latency_ms": 1200,
                         "last_ok": "2026-11-20T08:00:00Z"}],
                    "candidates": [{"url": "https://example.org/c.m3u8", "height": 0}]
                }
            }, "summary": {}
        }
        def fake(url):
            av = url.endswith("/b.m3u8")
            return {"playback_ready": av, "has_audio": av, "has_video": av,
                    "startup_ms": 1450 if av else None, "probe_ms": 1450 if av else 500,
                    "reason": "audio_video_packets" if av else "ffprobe_error"}
        actual = p.enhance(snapshot, probe=fake)
        c = actual["channels"]["tvip_5_canale-5-hd"]
        self.assertEqual(c["verified"][0]["url"], "https://example.org/b.m3u8")
        self.assertEqual(c["av_ready_count"], 1)
        self.assertEqual(actual["summary"]["audio_video_verified"], 1)
        self.assertEqual(actual["summary"]["playback_probe_count"], 3)

if __name__ == "__main__":
    unittest.main()
