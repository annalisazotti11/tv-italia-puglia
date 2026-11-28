"""Render public broadcaster logos, never IPTV stream URLs."""
import concurrent.futures
import io
import json
import pathlib
import re
import urllib.parse
import urllib.request
import warnings
from PIL import Image, ImageOps, ImageChops
import cairosvg
from defusedxml import ElementTree

ROOT = pathlib.Path("complete")
OUT = ROOT / "brand-assets" / "brand"
OUT.mkdir(parents=True, exist_ok=True)
Image.MAX_IMAGE_PIXELS = 20_000_000
warnings.simplefilter("error", Image.DecompressionBombWarning)
candidates = json.loads((ROOT / "brand-candidates.generated.json").read_text())

def load(url):
    req = urllib.request.Request(url, headers={"User-Agent":"TVItaliaComplete/1.4 (public logo rendering)"})
    with urllib.request.urlopen(req, timeout=7) as resp:
        if urllib.parse.urlsplit(resp.geturl()).scheme != "https":
            raise ValueError("HTTPS required")
        raw = resp.read(2_000_001)
        if len(raw)>2_000_000: raise ValueError("Large logo")
    if b"<svg" in raw[:2048].lower():
        root = ElementTree.fromstring(raw)
        # SVG is treated as untrusted artwork: reject external resource references.
        for node in root.iter():
            for k,v in node.attrib.items():
                if k.rsplit("}",1)[-1] in {"href","src"} and not v.startswith(("#","data:image/")):
                    raise ValueError("External SVG reference")
            if node.tag.rsplit("}",1)[-1] in {"script","foreignObject"}:
                raise ValueError("Unsupported SVG element")
        if re.search(rb'@import|url\(\s*["\x27]?\s*(?:https?:|//|file:)',raw,re.I):
            raise ValueError("External SVG resource")
        raw=cairosvg.svg2png(bytestring=raw,output_width=640,output_height=640)
    im=Image.open(io.BytesIO(raw))
    im=ImageOps.exif_transpose(im).convert("RGBA")
    box=im.getchannel("A").getbbox()
    if not box: raise ValueError("Empty logo")
    im=im.crop(box)
    # Preserve the original artwork: fit inside 68% of canvas, never crop.
    im.thumbnail((340,340),Image.Resampling.LANCZOS)
    if min(im.size)<3: raise ValueError("Invalid dimensions")
    # White artwork needs a darker canvas for legibility; preserve its colors.
    opaque=im.convert("RGB")
    extrema=opaque.getextrema()
    white_only=all(lo>=215 for lo,hi in extrema)
    bg=(35,35,35,255) if white_only else (255,255,255,255)
    canvas=Image.new("RGBA",(500,500),bg)
    canvas.alpha_composite(im,((500-im.width)//2,(500-im.height)//2))
    return canvas.convert("RGB")

def build(item):
    key, options=item
    if not re.fullmatch(r"[a-z0-9]+",key): return None
    for opt in options[:4]:
        try:
            img=load(opt["url"])
            img.save(OUT / (key+".png"), optimize=True)
            return key,{"path":"/brand/"+key+".png","logo":opt["url"]}
        except Exception:
            continue
    return None

with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    result=dict(x for x in pool.map(build,candidates.items()) if x)
(ROOT/"brand-assets-index.mjs").write_text("export default "+json.dumps(result,ensure_ascii=False,separators=(",",":"))+";\n")
print(f"PNG generati: {len(result)}/{len(candidates)}. Nessun flusso IPTV contattato.")
if not result:
    raise SystemExit("Nessun logo elaborato; mantengo il deployment precedente.")
