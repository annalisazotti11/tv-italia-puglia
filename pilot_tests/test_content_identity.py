# Kept outside the production nightly test discovery: the pilot has its own dependencies.
import random
import unittest
from unittest.mock import patch

from PIL import Image

import content_identity as c


def scene(seed):
    rng = random.Random(seed)
    return Image.frombytes('L', (24, 24), bytes(rng.randrange(256) for _ in range(576))).resize((480,270)).convert('RGB')


class Detector:
    def __init__(self, hits=None):
        self.hits = hits or []
    def detect(self, _):
        return self.hits


class ContentIdentityTests(unittest.TestCase):
    def setUp(self):
        self.one = 'https://one.example/one.m3u8'
        self.two = 'https://two.example/two.m3u8'
        self.three = 'https://three.example/three.m3u8'
        self.control = 'https://control.example/tgr.m3u8'
        self.blocked = 'https://blocked.example/bad.m3u8'
        self.config = {'schema':1,'pilot_channels':['c5'], 'controls':[{'channel':'tgr','url':self.control}],
                       'review_queue':[{'source':'metadata-only candidate'}]}
        self.policy = {'schema':1,'approved_only':{'c5':[self.one,self.two,self.three,self.blocked]},
                       'blocked_hosts':['blocked.example'],'blocked_by_channel':{}}
        self.review = {'schema':1,'channels':{'tgr':[self.control]}}
        self.good = [scene(i) for i in (11,12,13,14,15)]
        self.other = [scene(i) for i in (51,52,53,54,55)]

    def test_same_content_matches_distinct_scenes(self):
        result = c.compare_sequences(self.good, self.good[1:])
        self.assertTrue(result['corroborated'])
        self.assertGreaterEqual(result['matched_frames'], 2)
        self.assertFalse(c.compare_sequences(self.good, self.other)['corroborated'])

    def test_static_image_or_dark_slate_not_enough(self):
        self.assertFalse(c.compare_sequences([self.good[0]]*5,[self.good[0]]*5)['corroborated'])
        black = Image.new('RGB',(480,270),'black')
        self.assertFalse(c.compare_sequences([black]*5,[black]*5)['corroborated'])

    def test_audit_never_fetches_quarantine_and_never_publishes(self):
        called = []
        def capture(url):
            called.append(url)
            return (self.good if url in (self.one,self.two) else self.other), 'sampled'
        result = c.audit(self.config,self.policy,self.review,capture,Detector())
        rows = {x['source_id']:x for x in result['sources']}
        self.assertNotIn(self.blocked,called)
        self.assertEqual(rows[c.source_id(self.one)]['status'],'identity_evidence_confirmed')
        self.assertEqual(rows[c.source_id(self.two)]['status'],'identity_evidence_confirmed')
        self.assertEqual(rows[c.source_id(self.three)]['status'],'suspected_mismatch')
        self.assertTrue(all(not x['publish_allowed'] for x in result['sources']))
        self.assertEqual(result['review_queue'],self.config['review_queue'])
        self.assertTrue(all('url' not in x for x in result['sources']))

    def test_explicit_flag_veto_and_no_model_uncertain(self):
        capture=lambda url:(self.good,'sampled')
        flagged = c.audit(self.config,self.policy,self.review,capture,Detector([{'class':'FEMALE_GENITALIA_EXPOSED','score':.96}]))
        self.assertTrue(all(x['status']=='blocked_explicit_suspected' for x in flagged['sources']))
        missing = c.audit(self.config,self.policy,self.review,capture,None)
        self.assertTrue(all(x['status']=='uncertain' for x in missing['sources']))

    def test_geo_or_decode_failure_is_uncertain_not_mismatch(self):
        report = c.audit(self.config,self.policy,self.review,lambda url:([],'http_403'),Detector())
        self.assertEqual(report['summary']['uncertain'],4)
        self.assertEqual(report['summary']['sampled'],0)

    def test_manifest_failure_prevents_decoding(self):
        with patch.object(c,'manifest_check',return_value='http_403'), patch.object(c.subprocess,'run') as runner:
            self.assertEqual(c.capture_frames(self.one),([], 'http_403'))
            runner.assert_not_called()

    def test_capture_bytes_decoded_to_frames_without_files(self):
        class Result:
            stdout = bytes([37]) * (3*c.FRAME_MS)
        with patch.object(c,'manifest_check',return_value='ok'), patch.object(c.subprocess,'run',return_value=Result()):
            frames, status = c.capture_frames(self.one)
        self.assertEqual(len(frames),3)
        self.assertEqual(frames[0].size,(480,270))
        self.assertEqual(status,'sampled')


if __name__ == '__main__':
    unittest.main()
