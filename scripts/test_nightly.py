import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).parent / 'nightly_check.py'
spec = importlib.util.spec_from_file_location('nightly_check', SCRIPT)
nightly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nightly)


class NightlyCheckTests(unittest.TestCase):
    def test_first_scan_can_publish_zero_verified_channels(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'data' / 'verified-streams.json'
            inventory = ({'test': {'id': 'test', 'name': 'Rai 2', 'number': '2',
                                   'urls': [], 'results': []}}, {})
            with patch.object(nightly, 'OUTPUT', output), patch.object(nightly, 'inventory', return_value=inventory), \
                    patch.object(nightly, 'scan_playlists', return_value=[]):
                nightly.main()
            report = json.loads(output.read_text(encoding='utf8'))
            self.assertEqual(report['summary']['visible'], 0)
            self.assertEqual(report['summary']['status'], 'no_verified_streams')
            self.assertFalse(report['channels']['test']['visible'])

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
        self.assertTrue(nightly.permitted_stream_url('Telebari', 'https://w1.mediastreaming.it/telebari/live.m3u8'))
        self.assertFalse(nightly.permitted_stream_url('Telebari', 'https://w1.mediastreaming.it/other/live.m3u8'))
        self.assertFalse(nightly.permitted_stream_url('Radio Norba TV', 'https://router.xdevel.com/another/stream/live.m3u8'))
        self.assertTrue(nightly.permitted_stream_url('NOVE', 'https://streaming.aurora.enhanced.live/live/mpc/public-id/out/v1/IT_SIMULCAST/NOVE/CMAF/index.m3u8'))
        self.assertFalse(nightly.permitted_stream_url('NOVE', 'https://streaming.aurora.enhanced.live/live/mpc/public-id/out/v1/IT_SIMULCAST/DMAX/CMAF/index.m3u8'))

    def test_public_broadcaster_alternatives_are_channel_scoped(self):
        rai_one = ('https://mediapolis.rai.it/relinker/relinkerServlet.htm'
                   '?cont=2606803&output=7&forceUserAgent=rainet/4.0.5')
        self.assertTrue(nightly.permitted_stream_url('Rai 1 HD', rai_one))
        self.assertFalse(nightly.permitted_stream_url('Rai 2 HD', rai_one))
        self.assertFalse(nightly.permitted_stream_url('Rai 1 HD', rai_one + '&token=secret'))
        self.assertTrue(nightly.permitted_stream_url(
            'Rete 4 HD', 'https://live03-col.msf.cdn.mediaset.net/live/ch-r4/r4-clr.isml/manifest.mpd'))
        self.assertTrue(nightly.permitted_stream_url(
            'Canale 5 HD', 'https://live03-col.msf.cdn.mediaset.net/live/ch-c5/c5-clr.isml/manifest.mpd'))
        self.assertFalse(nightly.wrong_channel_redirect(
            'tvip_4_rete-4-hd',
            'https://live03-col.msf.cdn.mediaset.net/live/ch-r4/r4-clr.isml/manifest.mpd'))
        self.assertTrue(nightly.wrong_channel_redirect(
            'tvip_4_rete-4-hd',
            'https://live03-col.msf.cdn.mediaset.net/live/ch-c5/c5-clr.isml/manifest.mpd'))

    def test_tvit_exact_channel_routing(self):
        rai = 'https://tvit.leicaflorianrobert.dev/rai/rai-1/stream.m3u8'
        self.assertTrue(nightly.permitted_stream_url('Rai 1 HD', rai))
        self.assertFalse(nightly.permitted_stream_url('Rai 2 HD', rai))
        self.assertFalse(nightly.permitted_stream_url('Rai 1 HD', rai + '?key=hidden'))
        self.assertFalse(nightly.permitted_stream_url(
            'Rai 1 HD', 'https://tvit.leicaflorianrobert.dev/rai/rai-1/streamX.m3u8'))

    def test_geographic_failures_are_unverified_candidates_only(self):
        source = 'https://raiuno3-live.akamaized.net/live/master.m3u8'
        rows = [
            {'url':source, 'source':'Playlist originale','ok':False,'reason':'HTTP 403'},
            {'url':source, 'source':'Duplicate','ok':False,'reason':'HTTP 403'},
            {'url':'https://raiuno3-live.akamaized.net/live/fake.m3u8?token=123',
             'source':'Untrusted','ok':False,'reason':'HTTP 403'},
            {'url':'https://raiuno3-live.akamaized.net/live/invalid.m3u8',
             'source':'Untrusted','ok':False,'reason':'Not an HLS/DASH manifest'},
        ]
        pending = nightly.regional_candidates('Rai 1 HD', rows, set())
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['url'], source)
        self.assertEqual(pending[0]['reason'], 'HTTP 403')
        self.assertEqual(nightly.regional_candidates('Rai 1 HD', rows, {source}), [])
        self.assertEqual(nightly.regional_candidates('Sky Uno', rows, set()), [])

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
