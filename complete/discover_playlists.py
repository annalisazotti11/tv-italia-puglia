"""Daily metadata-only discovery of Italian public-TV playlist projects and directories.
Does not contact media streams, publish discovered URLs as active sources, or access private configuration.
"""
import concurrent.futures
import datetime as dt
import hashlib
import html.parser
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request

ROOT=pathlib.Path("complete")
TODAY=dt.datetime.now(dt.timezone.utc)
DIRS=[
 ("M3U.co.uk","https://www.m3u.co.uk/streams/country/it.html"),
 ("M3UPlayerPro","https://m3uplayerpro.com/free-streams/it"),
 ("Doubo","https://doubo.tv/en/playlists/it/"),
 ("Free-Codecs","https://www.free-codecs.com/app/iptv-finder/playlist/?c=it"),
 ("IPTVTips","https://www.iptvtips.com/it/lista-m3u-canali-italiani"),
]
def read(url,github=False,max_bytes=6000000):
    headers={"User-Agent":"TVItaliaComplete-source-catalog/1.0"}
    if github:
        headers["Accept"]="application/vnd.github+json"
        token=os.environ.get("GITHUB_TOKEN","")
        if token:headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=18) as response:
        data=response.read(max_bytes+1)
        if len(data)>max_bytes:raise ValueError("document too large")
        return data,dict(response.headers.items())

class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            link=dict(attrs).get("href")
            if link:self.links.append(link)

def directory(item):
    name,url=item
    try:
        data,_=read(url)
        parser=Links()
        parser.feed(data.decode("utf-8",errors="replace"))
        links=[]
        for link in parser.links:
            absolute=urllib.parse.urljoin(url,link)
            p=urllib.parse.urlsplit(absolute)
            # Report only project/directory pages, never individual video manifests.
            if p.scheme=="https" and p.netloc and (p.netloc=="github.com" and len(p.path.strip("/").split("/"))==2):
                links.append(absolute)
        return {"name":name,"page":url,"status":"reachable","project_pages":sorted(set(links))}
    except Exception as e:
        return {"name":name,"page":url,"status":type(e).__name__}

def metadata(p):
    try:
        body,headers=read(p["url"])
        raw=body.decode("utf-8-sig",errors="replace")
        if not raw.lstrip().startswith("#EXTM3U"):raise ValueError("not a playlist")
        entries=sum(1 for line in raw.splitlines() if line.startswith("#EXTINF:"))
        return {"name":p["name"],"status":"available","entries":entries,
            "sha256":hashlib.sha256(body).hexdigest(),"last_modified":headers.get("Last-Modified") or headers.get("last-modified")}
    except Exception as e:
        return {"name":p["name"],"status":type(e).__name__}

def search_projects():
    projects={}
    cutoff=TODAY.date().replace(month=1,day=1).isoformat()
    for phrase in ['"free-to-air" IPTV Italia','"canali in chiaro" IPTV','"public TV" Italy IPTV','"official streams" Italian IPTV']:
        q=phrase+" pushed:>="+cutoff+" archived:false fork:false"
        params=urllib.parse.urlencode({"q":q,"sort":"updated","order":"desc","per_page":50})
        try:
            raw,_=read("https://api.github.com/search/repositories?"+params,github=True)
            for p in json.loads(raw).get("items",[]):
                if p.get("private"):continue
                projects[p["full_name"]]={"name":p["full_name"],"project_page":p["html_url"],
                    "description":p.get("description"),"last_push":p.get("pushed_at"),"stars":p.get("stargazers_count"),
                    "review":"not automatically approved"}
        except Exception as e:
            print("GitHub search unavailable:",type(e).__name__)
    return sorted(projects.values(),key=lambda x:x.get("last_push") or "",reverse=True)

def main():
    candidates=json.loads((ROOT/"playlist-candidates.json").read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        inspected=list(pool.map(metadata,candidates))
        dirs=list(pool.map(directory,DIRS))
    available=[p for p in inspected if p["status"]=="available"]
    unique=len({p["sha256"] for p in available})
    report={"generated_at":TODAY.isoformat(),"target":100,"public_candidates":len(candidates),
        "available_public_files":len(available),"byte_distinct_files":unique,
        "note":"Private configured sources are intentionally not inspected. Same bytes do not prove independent providers; repository push date is not necessarily playlist freshness. Unknown sources require review before import. No playback requests.",
        "existing_candidates":inspected,"external_directories":dirs,"github_projects":search_projects()}
    dest=ROOT/"discovery-report.json"
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(f"Public candidates: {len(candidates)}, readable: {len(available)}, different file hashes: {unique}, projects: {len(report['github_projects'])}")
if __name__=="__main__":main()
