import importlib.util
from pathlib import Path
import unittest
import datetime as dt

spec = importlib.util.spec_from_file_location(
    'update_epg', Path(__file__).parent / 'update_epg.py')
epg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(epg)


class EPGTests(unittest.TestCase):
    def test_timezone_xmltv(self):
        t = epg.parse_time('20261119203000 +0100')
        self.assertEqual(epg.iso(t), '2026-11-19T19:30:00Z')
        self.assertEqual(epg.iso(epg.parse_time('20260819193000 +0200')),
                         '2026-08-19T17:30:00Z')
        self.assertIsNone(epg.parse_time('2026-11-19T19:30:00Z'))

    def test_only_exact_channels_and_no_old_programmes(self):
        now = dt.datetime(2026, 11, 19, 19, 0, tzinfo=dt.timezone.utc)
        xml = b'''<?xml version="1.0"?>
<tv>
  <channel id="rai-1"><display-name>Rai 1 HD</display-name></channel>
  <channel id="rai-2"><display-name>Rai 2</display-name></channel>
  <channel id="sky-cinema-fake"><display-name>Sky Cinema Mystery</display-name></channel>
  <programme channel="rai-1" start="20261119200000 +0100" stop="20261119210000 +0100"><title>Programma A</title></programme>
  <programme channel="rai-2" start="20261119200000 +0100" stop="20261119210000 +0100"><title>Programma B</title></programme>
  <programme channel="rai-1" start="20261119200000 +0100" stop="20261119210000 +0100"><title>Programma A</title></programme>
  <programme channel="rai-1" start="20261117090000 +0100" stop="20261117100000 +0100"><title>Scaduto</title></programme>
  <programme channel="sky-cinema-fake" start="20261119200000 +0100" stop="20261119210000 +0100"><title>Sbagliato</title></programme>
</tv>'''
        result = epg.extract(xml, {'rai 1': 'tvip_1_rai-1-hd', 'rai 2': 'tvip_2_rai-2-hd'}, now)
        self.assertEqual(len(result['tvip_1_rai-1-hd']), 1)
        self.assertEqual(result['tvip_1_rai-1-hd'][0]['title'], 'Programma A')
        self.assertEqual(result['tvip_2_rai-2-hd'][0]['title'], 'Programma B')
        self.assertEqual(len(result), 2)

    def test_ambiguous_channel_not_used(self):
        xml = b'''<tv>
<channel id="alpha"><display-name>Rai 1</display-name><display-name>Rai 2</display-name></channel>
<programme channel="alpha" start="20261119200000 +0100" stop="20261119210000 +0100"><title>Incorrectly shared</title></programme>
</tv>'''
        now = dt.datetime(2026, 11, 19, 19, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(epg.extract(xml, {'rai 1': 'one','rai 2': 'two'}, now), {})

    def test_fallback_to_second_source_only_when_better(self):
        now = dt.datetime(2026, 11, 19, 19, 0, tzinfo=dt.timezone.utc)
        xml = '''<tv><channel id="rai-1"><display-name>Rai 1</display-name></channel>
<programme channel="rai-1" start="20261119190000 +0000" stop="20261119200000 +0000"><title>Real title</title></programme></tv>'''.encode()
        out = epg.build(now=now, download=lambda url: xml)
        self.assertGreaterEqual(out['summary']['with_epg'], 1)
        self.assertEqual(out['channels']['tvip_1_rai-1-hd']['programmes'][0]['title'], 'Real title')
        self.assertIn(out['channels']['tvip_1_rai-1-hd']['source'],
                      ('TvIt / SuperGuidaTV', 'IPTV-EPG Italia'))


if __name__ == '__main__':
    unittest.main()
