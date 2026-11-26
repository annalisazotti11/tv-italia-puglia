import unittest
import audited_streams as a

class AuditTests(unittest.TestCase):
    def test_reviewed_only_and_ambiguous(self):
        good = 'https://example.org/a.m3u8'
        duplicate = 'https://example.org/shared.m3u8'
        blocked = 'https://blocked.example.org/a.m3u8'
        r = {'schema':1, 'channels':{'a':[good,duplicate,blocked], 'b':[duplicate]}}
        p = {'schema':1,'blocked_hosts':['blocked.example.org'],'blocked_by_channel':{},'approved_only':{}}
        self.assertEqual(a.targets(r,p), [('a',good)])
    def test_fail_closed(self):
        row = {'playback_ready':True,'has_video':True,'has_audio':True,
               'content_status':'no_high_confidence_flag','sampled_frames':3,'playback_height':1080}
        self.assertTrue(a.eligible(row))
        for patch in ({'content_status':'explicit_suspected'}, {'content_status':'model_error'},
                      {'sampled_frames':2}, {'has_audio':False}, {'playback_height':0}):
            self.assertFalse(a.eligible(row | patch))
    def test_rank_actual_resolution(self):
        self.assertGreater(a.rank({'playback_height':2160,'startup_ms':10000}),
                           a.rank({'playback_height':1080,'startup_ms':100}))
    def test_no_promotion_of_failed_source(self):
        url='https://example.org/a.m3u8'
        r={'schema':1,'channels':{'a':[url]}}
        p={'schema':1,'blocked_hosts':[],'blocked_by_channel':{},'approved_only':{}}
        snap=a.build(r,p,inspect_fn=lambda t:{'channel':t[0],'url':t[1],
                     'content_status':'explicit_suspected','playback_ready':True})
        self.assertEqual(snap['channels']['a']['verified'],[])
        self.assertEqual(snap['summary']['excluded']['explicit_suspected'],1)
    def test_retry_transient_but_not_forbidden_or_explicit(self):
        for reason, status, expected in (
                ('ffprobe_timeout','uncertain',2),
                ('http_403','uncertain',1),
                ('decode_timeout','explicit_suspected',1)):
            calls = []
            def inspect(target):
                calls.append(target)
                return {'reason':reason,'content_status':status}
            row = a.inspect_retry(('a','https://example.org/a.m3u8'),inspect,lambda _:None)
            self.assertEqual(len(calls),expected)
            self.assertEqual(row['attempts'],expected)
    def test_failure_diagnostics_do_not_expose_url(self):
        url='https://example.org/a.m3u8'
        r={'schema':1,'channels':{'a':[url]}}
        p={'schema':1,'blocked_hosts':[],'blocked_by_channel':{},'approved_only':{}}
        snap=a.build(r,p,inspect_fn=lambda t:{'channel':t[0],'url':t[1],
                     'content_status':'uncertain','reason':'http_403'})
        self.assertEqual(snap['channels']['a']['audit'],{'tested':1,'failed':{'http_403':1}})
        self.assertNotIn(url,str(snap))
    def test_third_party_requires_positive_identity(self):
        row = {'playback_ready':True,'has_video':True,'has_audio':True,
               'content_status':'no_high_confidence_flag','sampled_frames':5,
               'playback_height':720,'identity_required':True,
               'identity_status':'unconfirmed'}
        self.assertFalse(a.eligible(row))
        self.assertEqual(a.failure_reason(row),'channel_identity_unconfirmed')
        self.assertTrue(a.eligible(row | {'identity_status':'reference_scenes_match'}))
        self.assertFalse(a.eligible(row | {'identity_status':'reference_scenes_match',
                                           'content_status':'explicit_suspected'}))
if __name__ == '__main__':
    unittest.main()
