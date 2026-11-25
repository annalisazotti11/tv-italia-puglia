#!/usr/bin/env python3
"""Diagnostica privata: esclusivamente campioni locali acquisiti in modo autorizzato.

Non accetta URL, manifest IPTV, playlist o percorsi di rete. Non apre flussi
Internet. Non salva immagini, non trasmette i media, non modifica Nuvio.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import statistics
import subprocess

from PIL import Image, ImageOps

IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
VIDEO_EXT = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.ts', '.m4v'}
WIDTH, HEIGHT = 480, 270
FRAME_BYTES = WIDTH * HEIGHT * 3
EXPLICIT_CLASSES = {'FEMALE_GENITALIA_EXPOSED', 'MALE_GENITALIA_EXPOSED', 'ANUS_EXPOSED',
                    'EXPOSED_GENITALIA_F', 'EXPOSED_GENITALIA_M', 'EXPOSED_ANUS'}


def local_path(value):
    raw = str(value).strip().strip('"')
    if not raw or '://' in raw or raw.startswith(('\\\\', '//')):
        raise ValueError('Accetto soltanto file o cartelle locali, non URL o percorsi di rete.')
    p = Path(raw).expanduser().resolve(strict=True)
    if str(p).startswith(('\\\\', '//')):
        raise ValueError('Percorso di rete non ammesso.')
    if not (p.is_file() or p.is_dir()):
        raise ValueError('Il campione deve essere un file o una cartella di immagini.')
    return p


def normal_image(path):
    if path.suffix.lower() not in IMAGE_EXT:
        raise ValueError('Formato immagine non ammesso.')
    with Image.open(path) as image:
        if image.width * image.height > 30_000_000:
            raise ValueError('Immagine troppo grande; usa un normale fotogramma TV.')
        return ImageOps.fit(ImageOps.exif_transpose(image).convert('RGB'), (WIDTH, HEIGHT), method=Image.Resampling.BILINEAR)


def sample_frames(value):
    path = local_path(value)
    if path.is_dir():
        files = sorted((p for p in path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXT), key=lambda p:p.name)
        return [normal_image(p) for p in files[:5]]
    if path.suffix.lower() in IMAGE_EXT:
        return [normal_image(path)]
    if path.suffix.lower() not in VIDEO_EXT:
        raise ValueError('Usa un video locale (MP4, MKV, MOV) o immagini JPG/PNG. Playlist non accettate.')
    # Only local file and pipe protocols, no network access by FFmpeg.
    args = ['ffmpeg','-nostdin','-hide_banner','-v','error','-protocol_whitelist','file,pipe',
            '-i',str(path),'-map','0:v:0','-an','-sn','-dn','-vf',
            f'fps=1/3,scale={WIDTH}:{HEIGHT}:flags=bilinear','-frames:v','5','-pix_fmt','rgb24',
            '-threads','1','-f','rawvideo','pipe:1']
    try:
        run = subprocess.run(args,capture_output=True,timeout=35,check=False)
    except FileNotFoundError:
        raise ValueError('FFmpeg non trovato. Usa immagini locali oppure installa FFmpeg ufficiale.') from None
    except subprocess.TimeoutExpired:
        raise ValueError('Decodifica scaduta. Prova con un breve campione locale.') from None
    count = min(5,len(run.stdout)//FRAME_BYTES)
    return [Image.frombytes('RGB',(WIDTH,HEIGHT),run.stdout[i*FRAME_BYTES:(i+1)*FRAME_BYTES]) for i in range(count)]


def fingerprint(frame):
    w,h=frame.size
    gray=ImageOps.grayscale(frame.crop((w//10,h//10,w*9//10,h*9//10)))
    values=tuple(gray.resize((16,16),Image.Resampling.BILINEAR).getdata())
    if statistics.pstdev(values)<10:
        return None
    pix=tuple(gray.resize((17,16),Image.Resampling.BILINEAR).getdata())
    bits=0
    for y in range(16):
        for x in range(16):
            bits=(bits<<1)|(pix[y*17+x]>pix[y*17+x+1])
    return bits,values


def distance(a,b):
    if a is None or b is None:
        return 1.0,1.0
    return (a[0]^b[0]).bit_count()/256,sum(abs(x-y) for x,y in zip(a[1],b[1]))/(256*255)


def compare_sequences(ref, cand):
    a,b=list(map(fingerprint,ref)),list(map(fingerprint,cand))
    edges=[]
    for i,x in enumerate(a):
        for j,y in enumerate(b):
            h,m=distance(x,y)
            if h<=.12 and m<=.13:
                edges.append((h+m,i,j))
    pairs=[]
    for _,i,j in sorted(edges):
        if not any(i==x or j==y for x,y in pairs):
            pairs.append((i,j))
    diversity=any(distance(a[i],a[k])[0]>=.09 and distance(b[j],b[l])[0]>=.09
                  for i,j in pairs for k,l in pairs if i!=k)
    return {'matched_frames':len(pairs),'distinct_scenes':bool(diversity),'corroborated':len(pairs)>=2 and bool(diversity)}


def load_detector():
    try:
        from nudenet import NudeDetector
        return NudeDetector()
    except Exception:
        return None


def safety_check(frames,detector):
    if not frames:
        return 'not_sampled'
    if detector is None:
        return 'model_unavailable'
    try:
        for frame in frames:
            buf=io.BytesIO()
            frame.save(buf,format='JPEG',quality=82)
            if any(hit.get('class') in EXPLICIT_CLASSES and float(hit.get('score',0))>=.70
                   for hit in detector.detect(buf.getvalue())):
                return 'explicit_suspected'
        return 'no_high_confidence_flag'
    except Exception:
        return 'model_error'


def report(reference,candidate,detector):
    match=compare_sequences(reference,candidate)
    ref_safety=safety_check(reference,detector)
    cand_safety=safety_check(candidate,detector)
    if ref_safety=='explicit_suspected' or cand_safety=='explicit_suspected':
        status='explicit_suspected_review_required'
    elif not candidate:
        status='reference_only_no_candidate'
    elif len(reference)<3 or len(candidate)<3:
        status='insufficient_frames'
    elif ref_safety!='no_high_confidence_flag' or cand_safety!='no_high_confidence_flag':
        status='uncertain_safety_model'
    elif match['corroborated']:
        status='matching_content_evidence_review_required'
    else:
        status='uncertain_no_match'
    return {'schema':1,'mode':'authorized_local_files_only','generated_at':datetime.now(timezone.utc).isoformat(),
            'reference_frames':len(reference),'candidate_frames':len(candidate),'comparison':match,
            'reference_safety':ref_safety,'candidate_safety':cand_safety,'status':status,'publish_allowed':False,
            'note':'Il campione non certifica la diretta futura. Nessuna sorgente viene pubblicata.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',help='File/cartella locale acquisita dalla diretta autentica')
    p.add_argument('--candidate',help='File/cartella locale acquisita da una fonte autorizzata, nello stesso intervallo')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    ref=args.reference or input('Percorso dei fotogrammi o del video autentico di Canale 5: ')
    candidate=args.candidate
    if candidate is None:
        candidate=input('Percorso campione candidato autorizzato (Invio se non disponibile): ').strip()
    result=report(sample_frames(ref),sample_frames(candidate) if candidate else [],load_detector())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False))
    print('File di esito:',args.output)


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError) as error:
        print('Analisi non completata:',type(error).__name__,str(error))
        raise SystemExit(1)
