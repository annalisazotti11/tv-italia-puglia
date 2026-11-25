import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('nightly_check', Path(__file__).with_name('nightly_check.py'))
nightly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nightly)

class SourceIdentityTests(unittest.TestCase):
    def test_canale_5_exact_broadcaster_routes(self):
        cid = 'tvip_5_canale-5-hd'
        allowed = nightly.source_quarantine()['approved_only'][cid]
        for url in allowed:
            self.assertTrue(nightly.source_identity_allowed(cid, url))
        self.assertFalse(nightly.source_identity_allowed(cid, 'https://example.com/stream.m3u8'))
        self.assertFalse(nightly.source_identity_allowed(cid, 'https://ch.iptvmate.net/test.m3u8'))
        self.assertFalse(nightly.source_identity_allowed(cid, 'https://live02-seg.msf.cdn.mediaset.net/live/ch-r4/r4-clr.isml/index.m3u8'))

    def test_quarantine_applies_to_every_channel(self):
        for cid in ('tvip_1_rai-1-hd', 'tvip_5_canale-5-hd', 'tvip_103_rai-3-tgr-puglia'):
            self.assertFalse(nightly.source_identity_allowed(cid, 'https://ch.iptvmate.net/test.m3u8'))
        for cid, urls in nightly.source_quarantine()['blocked_by_channel'].items():
            for url in urls:
                self.assertFalse(nightly.source_identity_allowed(cid, url))

    def test_snapshot_has_no_quarantined_entries(self):
        data = json.loads(nightly.OUTPUT.read_text(encoding='utf8'))
        for cid, channel in data['channels'].items():
            for key in ('verified', 'regional_candidates', 'candidates'):
                for entry in channel.get(key, []):
                    self.assertTrue(nightly.source_identity_allowed(cid, entry['url']), cid)

if __name__ == '__main__':
    unittest.main()
