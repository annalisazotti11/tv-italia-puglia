import random
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import local_content_compare as a


def scene(seed):
    rng=random.Random(seed)
    return Image.frombytes('L',(24,24),bytes(rng.randrange(256) for _ in range(576))).resize((480,270)).convert('RGB')


class ClearDetector:
    def detect(self,_):
        return []


class LocalTests(unittest.TestCase):
    def test_network_and_playlist_rejected(self):
        for path in ('https://example.org/manifest.m3u8','//host/share/video.mp4',r'\\host\share\video.mp4'):
            with self.assertRaises(ValueError): a.local_path(path)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sample.m3u8';path.write_text('#EXTM3U')
            with self.assertRaises(ValueError): a.sample_frames(path)

    def test_local_images_and_identity_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            for i in range(5):scene(i).save(path/f'{i}.png')
            frames=a.sample_frames(path)
            self.assertEqual(len(frames),5)
            result=a.report(frames,frames,ClearDetector())
            self.assertEqual(result['status'],'matching_content_evidence_review_required')
            self.assertFalse(result['publish_allowed'])

    def test_different_or_single_sample_not_certain(self):
        ref=[scene(i) for i in range(5)]
        other=[scene(i) for i in range(100,105)]
        self.assertEqual(a.report(ref,other,ClearDetector())['status'],'uncertain_no_match')
        self.assertEqual(a.report(ref,[],ClearDetector())['status'],'reference_only_no_candidate')
        self.assertEqual(a.report(ref,ref,None)['status'],'uncertain_safety_model')

    def test_ffmpeg_no_network_protocols(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'video.mp4';file.touch()
            class Result:
                stdout=b'\0'*(3*a.FRAME_BYTES)
            with patch.object(a.subprocess,'run',return_value=Result()) as run:
                self.assertEqual(len(a.sample_frames(file)),3)
                args=run.call_args.args[0]
                self.assertEqual(args[args.index('-protocol_whitelist')+1],'file,pipe')
                self.assertEqual(args[args.index('-i')+1],str(file.resolve()))


if __name__=='__main__':
    unittest.main()
