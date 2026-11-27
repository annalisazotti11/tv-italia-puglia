import unittest
from datetime import datetime, timezone, timedelta
import audited_streams as a

class AuditTests(unittest.TestCase):
    def test_manifest_standard_get_and_bounded_read(self):
        from unittest.mock import patch, MagicMock
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'#EXTM3U\n#EXT-X-VERSION:3\n'
        with patch.object(a.ci.urllib.request, 'build_opener') as factory:
            opener = factory.return_value
            opener.open.return_value = response
            self.assertEqual(a.ci.manifest_check('https://example.org/live.m3u8'), 'ok')
            req = opener.open.call_args.args[0]
            self.assertEqual(req.get_method(), 'GET')
            self.assertIsNone(req.get_header('Range'))
            response.read.assert_called_once_with(a.ci.MAX_MANIFEST)
    def test_manifest_protected_stream_stays_excluded(self):
        from unittest.mock import patch, MagicMock
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,URI="key"\n'
        with patch.object(a.ci.urllib.request, 'build_opener') as factory:
            factory.return_value.open.return_value = response
            self.assertEqual(a.ci.manifest_check('https://example.org/live.m3u8'), 'protected_manifest')
    def test_reviewed_cdn_redirect_preserves_channel(self):
        check = a.ci.reviewed_redirect_allowed
        base = 'https://router.xdevel.com/video0s123-456/stream/playlist.m3u8'
        self.assertTrue(check(base, 'https://edge.xdevel.com/video0s123-456/stream/playlist.m3u8'))
        self.assertFalse(check(base, 'https://edge.xdevel.com/video0s999-456/stream/playlist.m3u8'))
        self.assertFalse(check(base, 'https://unrelated.example/video0s123-456/stream/playlist.m3u8'))
        self.assertFalse(check(base, 'https://edge.xdevel.com/video0s123-456/stream/playlist.m3u8?token=x'))
        self.assertTrue(check('https://a.msvdn.net/live/S123/path/playlist.m3u8',
                              'https://b.msvdn.net/live/S123/path2/playlist.m3u8'))
        self.assertFalse(check('https://a.msvdn.net/live/S123/path/playlist.m3u8',
                               'https://b.msvdn.net/live/S999/path2/playlist.m3u8'))
        self.assertTrue(check('https://bloomberg.com/media-manifest/eu.m3u8',
                              'https://www.bloomberg.com/media-manifest/eu.m3u8'))

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
    def test_retention_only_recent_reviewed_full_pass_after_timeout(self):
        url='https://example.org/a.m3u8'
        r={'schema':1,'channels':{'a':[url]}}
        p={'schema':1,'blocked_hosts':[],'blocked_by_channel':{},'approved_only':{}}
        now=datetime.now(timezone.utc)
        old={'channel':'a','url':url,'checked_at':now.isoformat(),
             'playback_ready':True,'has_video':True,'has_audio':True,
             'content_status':'no_high_confidence_flag','sampled_frames':3,
             'playback_height':720,'rank_score':7200}
        for reason,status,hours,expected in (
                ('ffprobe_timeout','uncertain',1,True),
                ('http_403','uncertain',1,False),
                ('decode_timeout','explicit_suspected',1,False),
                ('manifest_unavailable','uncertain',37,False)):
            prior=dict(old,checked_at=(now-timedelta(hours=hours)).isoformat())
            result=a.build(r,p,{'channels':{'a':{'verified':[prior]}}},
                inspect_fn=lambda x:{'channel':x[0],'url':x[1],
                                     'reason':reason,'content_status':status})
            rows=result['channels']['a']['verified']
            self.assertEqual(bool(rows),expected)
            if expected:
                self.assertTrue(rows[0]['retained'])
                self.assertEqual(rows[0]['checked_at'],prior['checked_at'])
                self.assertEqual(result['summary']['passed'],0)
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
