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
import urllib.error
import time

ROOT=pathlib.Path("complete")
TODAY=dt.datetime.now(dt.timezone.utc)
DIRS=[
 ("M3U.co.uk","https://www.m3u.co.uk/streams/country/it.html"),
 ("M3UPlayerPro","https://m3uplayerpro.com/free-streams/it"),
 ("Doubo","https://doubo.tv/en/playlists/it/"),
 ("Free-Codecs","https://www.free-codecs.com/app/iptv-finder/playlist/?c=it"),
 ("IPTVTips","https://www.iptvtips.com/it/lista-m3u-canali-italiani"),
 ("IPTV-org project","https://github.com/iptv-org/iptv"),
 ("Free-TV project","https://github.com/Free-TV/IPTV"),
 ("Tivùsat channel directory","https://www.tivusat.tv/canali/canali-televisivi.aspx"),
 ("RaiPlay live directory","https://www.raiplay.it/dirette/"),
 ("LA7 live directory","https://tg.la7.it/dirette-tv"),
 ("Broadcast Atlas official","https://broadcastatlas.com/official"),
 ("LegalFreeIPTV","https://biskyt.github.io/legalFreeIPTVplaylist/"),
 ("Doubo Italia public directory","https://doubo.tv/en/lists/iptv-org-it/"),
 ("M3UPlayerPro Italy directory","https://m3uplayerpro.com/free-streams/country/italy"),
 ("Regione Puglia broadcaster registry","https://www.regione.puglia.it/web/comunicazione-istituzionale/anagrafe-centro-media-regionale"),
 ("Free Public IPTV project","https://github.com/freecasthub/public-iptv"),
 ("Nexonic public broadcasts","https://github.com/nexonic-technologies/nexonic-iptv"),
 ("Nanobuo FTA project","https://github.com/Nanobuo/iptv-italia"),
 ("Dearbulut project","https://github.com/dearbulut/iptv"),
 ("OpenIPTVItaly project","https://github.com/xN1ckuz/OpenIPTVItaly"),
 ("European Audiovisual Observatory - Italy public broadcasters","https://mavise.obs.coe.int/f/ondemand/advanced?countryofestablishment=66&statuename=Public"),
 ("EBU members","https://www.ebu.ch/about/members"),
 ("Aeranti-Corallo local broadcasters association","https://www.aeranticorallo.it/"),
 ("Puglia DTT channels inventory","https://www.canalesalento.it/tv-mux-regionale-puglia/"),
 ("OnAirTV public FTA collection","https://github.com/gcardinale/onairtv-playlist"),
 ("FreetuxTV public channel directory","https://database.freetuxtv.net/"),
 ("TV Garden Italy directory","https://tvgarden.world/tv/it"),
 ("LegalFreeIPTV project documentation","https://github.com/biskyt/legalFreeIPTVplaylist"),
 ("mrwolfjunior free-to-air project documentation","https://github.com/mrwolfjunior/IPTV-Italia"),
 ("Italian public broadcaster and service directory","https://www.sky.it/tv/canali"),
 ("Italian TV channel directory MioTV","https://www.miotvonline.com/tv/italia/"),
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
        self.current=None
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            link=dict(attrs).get("href")
            self.current={"href":link,"text":""} if link else None
    def handle_data(self,data):
        if self.current:self.current["text"]+=data
    def handle_endtag(self,tag):
        if tag=="a" and self.current:
            self.links.append(self.current)
            self.current=None

def directory(item):
    name,url=item
    try:
        data,_=read(url)
        parser=Links()
        parser.feed(data.decode("utf-8",errors="replace"))
        projects=set()
        references={}
        for link in parser.links:
            absolute=urllib.parse.urljoin(url,link["href"])
            p=urllib.parse.urlsplit(absolute)
            if p.scheme!="https" or not p.hostname or p.username or p.password:continue
            label=" ".join(link["text"].split())[:140]
            parts=p.path.strip("/").split("/")
            if p.hostname=="github.com" and len(parts)>=2 and parts[0] not in {"topics","search","login","features","orgs","marketplace","settings","sponsors","site","about"}:
                projects.add("https://github.com/"+"/".join(parts[:2]))
            # Record public collection/documentation pages, never individual HLS manifests.
            signal=label+" "+p.path
            if re.search(r"playlist|raccolt|liste?[- ]|directory|canali.in.chiaro|free.to.air|public.tv|italian.tv|tv.italian|emittent",signal,re.I):
                if p.path.lower().endswith((".m3u8",".mpd",".ts",".mp4",".m3u")):continue
                if p.query and re.search(r"token|password|auth|key=",p.query,re.I):continue
                clean=urllib.parse.urlunsplit((p.scheme,p.netloc,p.path,p.query,""))
                references[clean]={"page":clean,"label":label,"review":"directory only; not an approved playlist"}
        return {"name":name,"page":url,"status":"reachable","project_pages":sorted(projects),"collection_pages":list(references.values())[:80]}
    except Exception as e:
        return {"name":name,"page":url,"status":type(e).__name__}

def metadata(p):
    try:
        body,headers=read(p["url"])
        raw=body.decode("utf-8-sig",errors="replace")
        if not raw.lstrip().startswith("#EXTM3U"):raise ValueError("not a playlist")
        entry_lines=[line.strip() for line in raw.splitlines() if line.strip().startswith("#EXTINF:")]
        entries=len(entry_lines)
        if entries==0 or re.search(r"(?m)^#EXT-X-(?:TARGETDURATION|STREAM-INF|MEDIA-SEQUENCE):",raw):raise ValueError("not a channel collection")
        # Split EXTINF at the first unquoted comma, preserving commas in channel titles.
        labels=set()
        for line in entry_lines:
            quoted=False
            separator=None
            for i,ch in enumerate(line):
                if ch=='"':quoted=not quoted
                elif ch==',' and not quoted:
                    separator=i
                    break
            if separator is None:continue
            name=line[separator+1:].strip().casefold()
            name=re.sub(r"\b(?:fhd|uhd|hd|sd|1080p|720p|4k)\b","",name)
            label=re.sub(r"[^a-z0-9]+","",name)
            if label:labels.add(label)
        label_hash=hashlib.sha256("\n".join(sorted(labels)).encode()).hexdigest()
        return {"name":p["name"],"status":"available","entries":entries,"distinct_labels":len(labels),"channel_label_hash":label_hash,
            "sha256":hashlib.sha256(body).hexdigest(),"last_modified":headers.get("Last-Modified") or headers.get("last-modified")}
    except Exception as e:
        return {"name":p["name"],"status":type(e).__name__,"http_status":getattr(e,"code",None),"detail":str(e)[:140] if isinstance(e,ValueError) else None}

def search_projects():
    projects={}
    queries=[]
    errors=[]
    cutoff=TODAY.date().replace(month=1,day=1).isoformat()
    phrases=[
      '"free-to-air" IPTV Italia','"canali in chiaro" IPTV','"public TV" Italy IPTV',
      '"official streams" Italian IPTV','"free TV" Italy M3U','"televisione gratuita" M3U',
      '"emittenti locali" IPTV Italia','"TV locali" Puglia streaming','"digitale terrestre" M3U',
      '"Italian free channels" playlist','"Italy" "free-to-air" playlist',
      '"Italian" "public broadcasters" streaming','"Italia" "free channels" M3U',
      '"televisioni regionali" streaming','"Italia" "canali gratuiti" playlist',
      '"Italy" "public streams" M3U','"FAST" Italy "free TV" playlist',
      'topic:free-tv italy','topic:iptv "free-to-air" italian',
    ]
    # Multilingual public-broadcast discovery, including documentation and international catalogues.
    for country,terms in [
        ("Italy",["free television","public broadcaster","official broadcast","free-to-air","public domain"]),
        ("Italia",["TV in chiaro","emittenti gratuite","dirette ufficiali","televisione pubblica","canali free-to-air"]),
        ("Italie",["chaînes gratuites","télévision publique","diffusion officielle"]),
        ("Italien",["frei empfangbar","öffentlich-rechtlich","kostenloses Fernsehen"]),
        ("Italia",["canales gratuitos","televisión pública","emisiones oficiales"]),
        ("Itália",["canais gratuitos","televisão pública"]),
    ]:
        for term in terms:phrases.append(country+' "'+term+'" M3U in:readme')
    phrases.extend([
      '"free-to-air" "Italy" IPTV in:readme','"canali in chiaro" "Puglia" in:readme',
      '"official broadcaster" "Italy" in:readme','"legal IPTV" "Italy" in:readme',
      '"free television" "Italian" in:readme','"public television" "Italian" in:readme',
      '"official live streams" "Italy" in:readme','"open television" "Italy" in:readme',
      '"FAST" "Italian" "free" in:readme','"public domain" "Italy" television in:readme',
      '"free TV" "Italia" "M3U" in:readme','"free-to-air" "Italia" in:readme',
    ])
    phrases=list(dict.fromkeys(phrases))
    # Rotate order each day so rate limits do not starve later languages.
    offset=TODAY.date().toordinal()%len(phrases)
    phrases=phrases[offset:]+phrases[:offset]
    for phrase in phrases:
        q=phrase+" pushed:>="+cutoff+" archived:false"
        retrieved=0
        try:
            for page in (1,2,3):
                params=urllib.parse.urlencode({"q":q,"sort":"updated","order":"desc","per_page":50,"page":page})
                raw,_=read("https://api.github.com/search/repositories?"+params,github=True)
                payload=json.loads(raw)
                items=payload.get("items",[])
                retrieved+=len(items)
                for p in items:
                    if p.get("private") or p.get("archived"):continue
                    full=p["full_name"]
                    if full not in projects:
                        projects[full]={"name":full,"project_page":p["html_url"],"description":p.get("description"),
                            "last_push":p.get("pushed_at"),"stars":p.get("stargazers_count"),"fork":p.get("fork"),
                            "default_branch":p.get("default_branch"),"matched_queries":[],
                            "review":"not automatically approved"}
                    projects[full]["matched_queries"].append(phrase)
                if len(items)<50 or retrieved>=payload.get("total_count",0):break
                time.sleep(2.5)
            queries.append({"query":phrase,"returned":retrieved})
        except Exception as e:
            errors.append({"query":phrase,"error":type(e).__name__,"http_status":getattr(e,"code",None)})
            if getattr(e,"code",None) in (403,429):break
        time.sleep(2.1)
    return sorted(projects.values(),key=lambda x:x.get("last_push") or "",reverse=True),queries,errors

def project_inventory(project):
    """List public repository collection file names only, without downloading their contents."""
    branch=project.get("default_branch")
    name=project["name"]
    if not branch:return {"name":name,"status":"missing branch"}
    try:
        quoted=urllib.parse.quote(branch,safe="")
        raw,_=read("https://api.github.com/repos/"+name+"/git/trees/"+quoted+"?recursive=1",github=True,max_bytes=8000000)
        tree=json.loads(raw)
        files=[]
        for row in tree.get("tree",[]):
            if row.get("type")!="blob":continue
            path=row.get("path","")
            # File names for Italian collections, not addresses of streams.
            if re.search(r"\.m3u8?$",path,re.I) and re.search(r"ital(?:ia|y|ian)|puglia|(?:^|[/_.-])it(?:a)?(?:[/_.-]|$)|nazionali|regionali|canali.in.chiaro|free.tv",path,re.I):
                files.append({"path":path,"bytes":row.get("size")})
        return {"name":name,"status":"listed","truncated":tree.get("truncated",False),"collection_files":files[:200],"review":"file inventory only"}
    except Exception as e:
        return {"name":name,"status":type(e).__name__,"http_status":getattr(e,"code",None)}


def other_forges():
    """Discover public project descriptions on other code hosts, not stream links."""
    terms=["free-to-air IPTV","public television Italy","canali in chiaro","free TV Italy","Italian public broadcasters","emittenti locali Puglia"]
    found={}
    outcomes=[]
    for host in ("gitlab","codeberg"):
        for term in terms:
            try:
                if host=="gitlab":
                    base="https://gitlab.com/api/v4/projects?"
                    params={"search":term,"visibility":"public","simple":"true","per_page":50,"order_by":"last_activity_at","sort":"desc"}
                else:
                    base="https://codeberg.org/api/v1/repos/search?"
                    params={"q":term,"limit":50}
                raw,_=read(base+urllib.parse.urlencode(params),max_bytes=3000000)
                payload=json.loads(raw)
                items=payload if isinstance(payload,list) else payload.get("data",[])
                for row in items:
                    if row.get("private") or row.get("archived"):continue
                    page=row.get("web_url") or row.get("html_url") or ""
                    if not page.startswith("https://"):continue
                    found[page]={"host":host,"project_page":page,"name":row.get("path_with_namespace") or row.get("full_name") or row.get("name"),
                       "description":row.get("description"),"last_activity":row.get("last_activity_at") or row.get("updated_at"),"review":"not automatically approved"}
                outcomes.append({"host":host,"query":term,"returned":len(items)})
            except Exception as e:
                outcomes.append({"host":host,"query":term,"error":type(e).__name__,"http_status":getattr(e,"code",None)})
                if getattr(e,"code",None) in (403,429):break
            time.sleep(0.4)
    return list(found.values()),outcomes

def seeded_projects(dirs):
    """Resolve project pages identified by directories and verified research seeds."""
    names=set()
    for d in dirs:
        for page in d.get("project_pages",[])+[d.get("page","")]:
            p=urllib.parse.urlsplit(page)
            if p.hostname!="github.com":continue
            parts=p.path.strip("/").split("/")
            if len(parts)!=2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+",part) for part in parts):continue
            if parts[0] in {"topics","features","settings","orgs","sponsors","marketplace","login","search","site","about","security","readme","enterprise","collections"}:continue
            names.add("/".join(parts))
    # Only metadata, no playlist/stream downloads for previously unreviewed projects.
    def resolve(name):
        try:
            raw,_=read("https://api.github.com/repos/"+name,github=True,max_bytes=1000000)
            p=json.loads(raw)
            if p.get("private") or p.get("archived"):return None
            return {"name":p["full_name"],"project_page":p["html_url"],"description":p.get("description"),
                "last_push":p.get("pushed_at"),"stars":p.get("stargazers_count"),"fork":p.get("fork"),
                "default_branch":p.get("default_branch"),"matched_queries":["directory reference"],"review":"not automatically approved"}
        except Exception:return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        return [p for p in pool.map(resolve,sorted(names)[:60]) if p]

def expand_directories(initial):
    """Follow relevant documentation only, within already selected public sites."""
    seen={d.get("page") for d in initial}
    roots={urllib.parse.urlsplit(u).hostname for _,u in DIRS}
    frontier=initial
    extra=[]
    for depth in (1,2):
        batch={}
        for d in frontier:
            for ref in d.get("collection_pages",[]):
                page=ref.get("page","")
                p=urllib.parse.urlsplit(page)
                if p.hostname not in roots or p.hostname=="github.com" or p.query:continue
                if p.scheme!="https" or page in seen:continue
                # Follow only country-relevant directory documentation, not playback pages.
                if not re.search(r"ital(?:ia|y|ian)|puglia|(?:/|-)it(?:/|-|$)|free.to.air|in.chiaro|public.broadcaster",p.path+" "+ref.get("label",""),re.I):continue
                if re.search(r"\.(?:m3u8?|mpd|ts|mp4|zip|pdf)$",p.path,re.I):continue
                batch[page]=("Directory depth "+str(depth),page)
        selected=sorted(batch.values(),key=lambda item:item[1])[:30]
        seen.update(u for _,u in selected)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            frontier=list(pool.map(directory,selected))
        extra.extend(frontier)
        if not frontier:break
    return initial+extra

def repository_summary(projects,inventories):
    """Count unique file paths separately from file hashes and independent publishers."""
    by_name={p["name"]:p for p in projects}
    results=[]
    for inventory in inventories:
        files=inventory.get("collection_files",[])
        if not files:continue
        p=by_name.get(inventory["name"],{})
        results.append({"project":inventory["name"],"files":len(files),
             "last_push":p.get("last_push"),"fork":p.get("fork"),
             "freshness":"repository activity only; playlist update not established",
             "review":"candidate, not approved"})
    return sorted(results,key=lambda x:(not x.get("fork"),x.get("last_push") or "",x["files"]),reverse=True)

# Only public discovery metadata. Never cache private playlist configuration or streams.
HISTORY=ROOT/"discovery-history.json"
def read_history():
    try:
        data=json.loads(HISTORY.read_text())
        return data if isinstance(data,dict) else {}
    except (OSError,ValueError):return {}

def remember(report,old):
    projects={p["name"].lower():p for p in old.get("projects",[]) if p.get("name")}
    for p in report["github_projects"]:
        key=p["name"].lower()
        prior=projects.get(key,{})
        projects[key]={**p,"first_seen":prior.get("first_seen",TODAY.isoformat()),"last_seen":TODAY.isoformat()}
    inventories={p["name"].lower():p for p in old.get("inventories",[]) if p.get("name")}
    for p in report["repository_inventories"]:
        key=p["name"].lower()
        if p.get("status")=="listed":
            inventories[key]={**p,"last_success":TODAY.isoformat()}
    forges={p["project_page"]:p for p in old.get("other_forges",[]) if p.get("project_page")}
    for p in report.get("other_forge_projects",[]):forges[p["project_page"]]=p
    current_projects={p["name"].lower() for p in report["github_projects"]}
    old_projects={p["name"].lower() for p in old.get("projects",[]) if p.get("name")}
    previous_checks={p["name"]:p for p in old.get("public_file_checks",[]) if p.get("name")}
    checks=dict(previous_checks)
    for p in report["existing_candidates"]:
        if p.get("status")!="available":continue
        prior=previous_checks.get(p["name"],{})
        first=prior.get("first_seen",TODAY.isoformat())
        last_change=prior.get("last_observed_change")
        if prior.get("sha256") and prior["sha256"]!=p["sha256"]:last_change=TODAY.isoformat()
        checks[p["name"]]={**p,"first_seen":first,"last_success":TODAY.isoformat(),"last_observed_change":last_change}
    report["history_summary"]={
        "new_projects_this_run":len(current_projects-old_projects),
        "public_files_with_observed_change":sum(bool(p.get("last_observed_change")) for p in checks.values()),
        "github_projects_seen_total":len(projects),
        "other_forge_projects_seen_total":len(forges),
        "historical_file_paths":sum(len(p.get("collection_files",[])) for p in inventories.values()),
        "historical_projects_with_files":sum(bool(p.get("collection_files")) for p in inventories.values()),
        "note":"Cumulative candidates, not active or authorized playlists. Older inventories may be stale."
    }
    report["public_file_checks"]=sorted(checks.values(),key=lambda p:(p.get("last_observed_change") or "",p.get("last_success") or ""),reverse=True)
    HISTORY.write_text(json.dumps({"projects":list(projects.values()),"inventories":list(inventories.values()),"other_forges":list(forges.values()),"public_file_checks":list(checks.values())},ensure_ascii=False,indent=2)+"\n")

def main():
    old=read_history()
    candidates=json.loads((ROOT/"playlist-candidates.json").read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        inspected=list(pool.map(metadata,candidates))
        dirs=list(pool.map(directory,DIRS))
    dirs=expand_directories(dirs)
    available=[p for p in inspected if p["status"]=="available"]
    unique=len({p["sha256"] for p in available})
    fingerprints={}
    for p in available:
        fingerprints.setdefault(p.get("channel_label_hash"),[]).append(p["name"])
    same_lineups=[v for k,v in fingerprints.items() if k and len(v)>1]
    hashes={}
    for p in available:hashes.setdefault(p["sha256"],[]).append(p["name"])
    exact_duplicates=[v for v in hashes.values() if len(v)>1]
    projects,queries,errors=search_projects()
    by_name={p['name'].lower():p for p in projects}
    for p in seeded_projects(dirs):by_name.setdefault(p['name'].lower(),p)
    projects=sorted(by_name.values(),key=lambda x:x.get('last_push') or '',reverse=True)
    # Prefer unseen and not-yet-inspected projects instead of rescanning the same 150.
    seen_inventories={p["name"].lower():p for p in old.get("inventories",[]) if p.get("name")}
    queue={p["name"].lower():p for p in projects}
    for p in old.get("projects",[]):
        if p.get("name"):queue.setdefault(p["name"].lower(),p)
    def scan_priority(p):
        prior=seen_inventories.get(p["name"].lower(),{})
        return (bool(prior),prior.get("last_success",""),p["name"].lower())
    scan_queue=sorted(queue.values(),key=scan_priority)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        inventories=list(pool.map(project_inventory,scan_queue[:150]))
    external_projects,external_queries=other_forges()
    project_summary=repository_summary(list(queue.values()),inventories)
    report={"generated_at":TODAY.isoformat(),"target":100,"public_candidates":len(candidates),
        "available_public_files":len(available),"byte_distinct_files":unique,
        "identical_label_sets":same_lineups,"distinct_label_sets":len(fingerprints),
        "exact_duplicate_files":exact_duplicates,"unique_readable_public_files":unique,
        "gap_to_100_distinct_public_files":max(0,100-unique),
        "unavailable_public_files":len(inspected)-len(available),
        "review_only_sources":[{"project":"OnAirTV","reason":"Declares FTA but contains mixed channel names; authorization not verified","status":"not added to deployment"},{"project":"LegalFreeIPTV","reason":"International collection; Italian coverage and rights need review","status":"not added to deployment"},{"project":"mrwolfjunior/IPTV-Italia","reason":"Fork of TVITALIA; independence and rights need review","status":"not added to deployment"},{"project":"TV Garden Italy","reason":"Documentation directory based on IPTV-org, not an independent M3U","status":"not added to deployment"}],
        "note_label_sets":"Same channel labels suggest overlapping coverage, not identical playback sources or rights.",
        "note":"Private configured sources are intentionally not inspected. Same bytes do not prove independent providers; repository push date is not necessarily playlist freshness. Unknown sources require review before import. No playback requests.",
        "existing_candidates":inspected,"external_directories":dirs,"github_projects":projects,
        "search_queries":queries,"search_errors":errors,"repository_inventories":inventories,
        "other_forge_projects":external_projects,"other_forge_queries":external_queries,
        "distinct_project_count":len(projects)+len(external_projects),
        "directory_pages_examined":len(dirs),
        "projects_with_collection_files":len(project_summary),
        "candidate_projects_ranked":project_summary,
        "gap_to_100_public_readable":max(0,100-len(available)),
        "potential_collection_files":sum(len(x.get("collection_files",[])) for x in inventories),
        "external_collection_pages":len({p["page"] for d in dirs for p in d.get("collection_pages",[])})}
    remember(report,old)
    dest=ROOT/"discovery-report.json"
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(f"Public candidates: {len(candidates)}, readable: {len(available)}, different file hashes: {unique}, projects: {len(report['github_projects'])}")
if __name__=="__main__":main()
