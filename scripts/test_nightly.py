import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).parent / 'nightly_check.py'
spec = importlib.util.spec_from_file_location('nightly_check', SCRIPT)
nightly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nightly)


class NightlyCheckTests(unittest.TestCase):
    def test_ids_and_aliases(self):
        self.assertEqual(nightly.js_slug('Rai 1 HD'), 'rai-1-hd')
        self.assertEqual(nightly.normalize('IT: Sky Sport Uno HD'), 'sky sport uno')
        self.assertEqual(nightly.normalize('Rai Uno'), 'rai 1')
        self.assertEqual(nightly.normalize('Sky Sport 24'), 'sky sport 24')

    def test_url_safety(self):
        for bad in ('file:///etc/passwd', 'http://127.0.0.1/a', 'http://192.168.1.10/live',
                    'http://localhost/live', 'https://user:pass@example.org/media.m3u8',
                    'ftp://example.org/live'):
            self.assertFalse(nightly.safe_url(bad), bad)
        self.assertTrue(nightly.safe_url('https://example.org/live.m3u8'))
        self.assertFalse(nightly.permitted_stream_url('Sky Sport Uno', 'https://example.org/live.m3u8'))
        self.assertFalse(nightly.permitted_stream_url('Rai 2', 'https://raidue3-live.akamaized.net/live.m3u8?token=secret'))
        self.assertTrue(nightly.permitted_stream_url('Rai 2', 'https://raidue3-live.akamaized.net/live.m3u8'))

    def test_playlist_matching_is_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            m3u = Path(tmp) / 'base.m3u'
            m3u.write_text('#EXTM3U\n#EXTINF:-1 tvg-chno="1",Rai 1 HD\n'
                           'https://raiuno3-live.akamaized.net/rai.m3u8\n'
                           '#EXTINF:-1 tvg-chno="50",Sky TG24\n'
                           'https://example.org/tg24.m3u8\n', encoding='utf8')
            with patch.object(nightly, 'MAIN_M3U', m3u):
                channels, by_name = nightly.inventory()
            self.assertIn('tvip_1_rai-1-hd', channels)
            n = len(channels['tvip_1_rai-1-hd']['urls'])
            nightly.assign_candidate(channels, by_name, 'Rai Uno HD', {'tvg-chno': '2'},
                                     'https://raiuno3-live.akamaized.net/invalid.m3u8', 'test')
            self.assertEqual(len(channels['tvip_1_rai-1-hd']['urls']), n)
            nightly.assign_candidate(channels, by_name, 'Rai Uno HD', {'tvg-chno': '1'},
                                     'https://raiuno3-live.akamaized.net/valid.m3u8', 'test')
            self.assertEqual(len(channels['tvip_1_rai-1-hd']['urls']), n + 1)
            nightly.assign_candidate(channels, by_name, 'Sky Sport 24', {},
                                     'https://example.org/wrong.m3u8', 'test')
            self.assertFalse(any('wrong' in c['url'] for c in channels['tvip_sky_sky_sport_uno']['urls']))

    def test_probe_validates_actual_segment(self):
        def fake_get(url, max_bytes=nightly.MAX_MANIFEST_BYTES, timeout=nightly.TIMEOUT):
            if url.endswith('master.m3u8'):
                return (b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=4000000,RESOLUTION=1920x1080,CODECS="avc1.42e01e,mp4a.40.2"\n'
                        b'video.m3u8\n', 'application/vnd.apple.mpegurl', url)
            if url.endswith('video.m3u8'):
                return (b'#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6,\nsegment.ts\n',
                        'application/vnd.apple.mpegurl', url)
            if url.endswith('segment.ts'):
                return (b'\x47' * 188, 'video/mp2t', url)
            if url.endswith('bad.m3u8'):
                return (b'<html>login required</html>', 'text/html', url)
            raise AssertionError(url)
        with patch.object(nightly, 'get', fake_get):
            r = nightly.probe_one('test', {'url':'https://example.org/master.m3u8','source':'fixture'})
            self.assertTrue(r['ok'], r)
            self.assertEqual(r['height'], 1080)
            bad = nightly.probe_one('test', {'url':'https://example.org/bad.m3u8','source':'fixture'})
            self.assertFalse(bad['ok'])


if __name__ == '__main__':
    unittest.main()
