import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("nightly_check", Path(__file__).with_name("nightly_check.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SourceDiversityTests(unittest.TestCase):
    def test_new_hosts_beat_duplicate_flood(self):
        items = [{"url": "https://one.example.com/stream" + str(i) + ".m3u8", "source": "Mirror A"} for i in range(50)]
        items += [{"url": "https://two.example.com/live.m3u8", "source": "Mirror B"},
                  {"url": "https://three.example.com/live.m3u8", "source": "Playlist originale"}]
        selected = mod.diverse_channel_sources(items, 6)
        hosts = {mod.urllib.parse.urlsplit(x["url"]).hostname for x in selected}
        self.assertEqual(len(selected), 6)
        self.assertEqual(len(hosts), 3)
        self.assertEqual(selected[0]["source"], "Playlist originale")

    def test_duplicate_urls_not_repeated(self):
        item = {"url":"https://one.example.com/live.m3u8", "source":"Source"}
        self.assertEqual(len(mod.diverse_channel_sources([item,item,item])),1)

    def test_tv8_foreign_cannot_be_misidentified(self):
        self.assertFalse(mod.channel_identity_ok("TV8", "https://cdn4.skygo.mn/live/tv8.m3u8", {}))
        self.assertTrue(mod.channel_identity_ok("TV8", "https://tvit.leicaflorianrobert.dev/sky/tv8/stream.m3u8", {}))
        self.assertTrue(mod.channel_identity_ok("Canale 5", "https://example.com/c5.m3u8", {}))

if __name__ == "__main__":
    unittest.main()
