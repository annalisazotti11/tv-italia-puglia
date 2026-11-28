import json
import os
import pathlib
import urllib.request
import urllib.error
import re

def required(key):
    val=os.environ.get(key,"").strip()
    if not val:
        raise SystemExit(f"Manca {key}: configura il repository secret / variable.")
    return val

account=required("CLOUDFLARE_ACCOUNT_ID")
api_token=required("CLOUDFLARE_API_TOKEN")
access=required("TV_COMPLETE_ACCESS_TOKEN")
if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}",access):
    raise SystemExit("TV_COMPLETE_ACCESS_TOKEN: usa 32-128 caratteri alfanumerici, trattini o underscore.")
try:
    playlists=json.loads(required("TV_COMPLETE_PLAYLIST_SOURCES"))
    assert isinstance(playlists,list) and 1<=len(playlists)<=30
    assert all(isinstance(p,dict) and isinstance(p.get("name"),str) and p["name"].strip() and isinstance(p.get("url"),str) and p["url"].startswith("https://") for p in playlists)
    assert len({p["name"] for p in playlists})==len(playlists)
except (ValueError,AssertionError):
    raise SystemExit("TV_COMPLETE_PLAYLIST_SOURCES: array JSON con 1-30 coppie name/url HTTPS e nomi univoci.")

# The existing private configuration remains the primary source list.
# Additional Italian playlist endpoints are maintained in the repository.
extra=json.loads(pathlib.Path("complete/playlist-candidates.json").read_text())
urls={p["url"].lower() for p in playlists}
names={p["name"] for p in playlists}
for p in extra:
    if len(playlists)>=30: break
    if p["url"].lower() in urls or p["name"] in names: continue
    playlists.append(p)
    urls.add(p["url"].lower())
    names.add(p["name"])
print(f"Playlist configurate: {len(playlists)} (disponibilità dei file non ancora accertata).")

def api(path,method="GET",body=None):
    url=f"https://api.cloudflare.com/client/v4/accounts/{account}/storage/kv/namespaces{path}"
    req=urllib.request.Request(url,method=method,headers={"Authorization":"Bearer "+api_token,"Content-Type":"application/json"},data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req,timeout=30) as res:
            result=json.load(res)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"API KV: HTTP {e.code}. Verifica permesso Workers KV Storage Edit del token Cloudflare.") from None
    if not result.get("success"):
        raise SystemExit("API KV: richiesta non riuscita")
    return result

title="tv-italia-complete"
page=1
namespace=None
while True:
    res=api(f"?page={page}&per_page=100")
    items=res["result"]
    namespace=next((x["id"] for x in items if x["title"]==title),None)
    if namespace or page>=res.get("result_info",{}).get("total_pages",1) or not items: break
    page+=1
if not namespace:
    namespace=api("",method="POST",body={"title":title})["result"]["id"]
folder=pathlib.Path("complete")
config={"name":"tv-italia-complete","main":"worker.mjs","compatibility_date":"2026-11-27","workers_dev":True,"triggers":{"crons":["17 * * * *"]},"kv_namespaces":[{"binding":"PLAYLISTS","id":namespace}]}
(folder/"wrangler.generated.json").write_text(json.dumps(config))
secret_path=pathlib.Path(os.environ["RUNNER_TEMP"])/"tv-complete-secrets.json"
secret_path.touch(mode=0o600,exist_ok=True)
secret_path.write_text(json.dumps({"ACCESS_TOKEN":access,"PLAYLIST_SOURCES":json.dumps(playlists)}))
print("Configurazione dedicata pronta; nessun dato segreto pubblicato.")
