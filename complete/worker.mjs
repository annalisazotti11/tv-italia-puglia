import {rankedCombine, loadGeo, declared} from "./catalog.mjs";
// Personal aggregator: configure only playlists you are authorized to use.
const KEY="complete-v1";
const cors={"Access-Control-Allow-Origin":"*","Access-Control-Allow-Methods":"GET, OPTIONS"};
const json=(x,status=200)=>new Response(JSON.stringify(x),{status,headers:{...cors,"Content-Type":"application/json","Cache-Control":"no-store"}});
const attr=(s,k)=>s.match(new RegExp('(?:^|\\s)'+k+'="([^"]*)"','i'))?.[1]||"";
const normalize=s=>s.normalize("NFKC").trim().toLowerCase().replace(/\s+(?:fhd|uhd|hd|sd|4k|1080p|720p)$/i,"");
function sources(env){
  const a=JSON.parse(env.PLAYLIST_SOURCES||"[]");
  if(!Array.isArray(a)||a.length>30||!a.every(x=>typeof x.name==="string"&&/^https:\/\//i.test(x.url)))throw Error("PLAYLIST_SOURCES: configurazione non valida");
  if(new Set(a.map(x=>x.name)).size!==a.length)throw Error("Nomi sorgente duplicati");
  return a;
}
export function parse(text,source,base){
  const lines=text.replace(/^\uFEFF/,"").split(/\r?\n/);
  if(!lines.shift()?.trim().startsWith("#EXTM3U"))throw Error("Formato M3U non valido");
  const entries=[];let entry;
  for(const raw of lines){const line=raw.trim();if(!line)continue;
    if(line.startsWith("#EXTINF:")){
      let q=false,i=0;for(;i<line.length;i++){if(line[i]==='"')q=!q;if(!q&&line[i]===",")break;}
      entry={name:line.slice(i+1).trim()||attr(line,"tvg-name"),logo:attr(line,"tvg-logo"),id:attr(line,"tvg-id"),info:line,opts:[],source};
    }else if(entry&&line.startsWith("#"))entry.opts.push(line);
    else if(entry){try{const u=new URL(line,base);if(["https:","http:"].includes(u.protocol)&&entry.name)entries.push({...entry,url:u.href});}catch{}entry=null;}
  }return entries;
}
async function refresh(env){
  const configured=sources(env);const old=await env.PLAYLISTS.get(KEY,"json")||{lists:{}};
  const lists={},status={};
  for(let i=0;i<configured.length;i+=5)await Promise.all(configured.slice(i,i+5).map(async s=>{
    try{const r=await fetch(s.url,{signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error("HTTP "+r.status);
      const entries=parse(await r.text(),s.name,s.url);if(!entries.length)throw Error("Playlist vuota");
      lists[s.name]=entries;status[s.name]={count:entries.length,updated:new Date().toISOString()};
    }catch{if(old.lists[s.name])lists[s.name]=old.lists[s.name];status[s.name]={count:lists[s.name]?.length||0,retained:!!lists[s.name]};}
  }));
  const geo=await loadGeo(old.geo||{});
  const state={lists,status,geo,updated:new Date().toISOString()};await env.PLAYLISTS.put(KEY,JSON.stringify(state));return state;
}
export const combine=rankedCombine;
const manifest={id:"it.personal.tvitaliacomplete",version:"1.1.0",name:"TV Italia Complete",description:"Aggregazione M3U personale; nessun test dei flussi.",types:["tv"],resources:["catalog","meta","stream"],idPrefixes:["tvic:"],catalogs:[{type:"tv",id:"italia",name:"TV Italia Complete",extra:[{name:"search",isRequired:false}]}]};
const meta=g=>({id:g.id,type:"tv",name:g.number+" · "+g.name,poster:g.poster||undefined,posterShape:"square",description:declared(g.entries[0])[0]?declared(g.entries[0])[0]+"p (dichiarati)": "Qualità non dichiarata"});
async function handle(req,env){
  const u=new URL(req.url),parts=u.pathname.split("/").filter(Boolean);
  if(!env.ACCESS_TOKEN||env.ACCESS_TOKEN.length<32||parts.shift()!==env.ACCESS_TOKEN)return json({error:"Not found"},404);
  if(req.method==="OPTIONS")return new Response(null,{headers:cors});
  if(req.method!=="GET")return json({error:"Method not allowed"},405);
  const p=parts.join("/");
  if(p==="manifest.json")return json(manifest);
  if(!env.PLAYLISTS)return json({error:"KV non configurato"},503);
  const s=await env.PLAYLISTS.get(KEY,"json")||await refresh(env);
  // Do not expose cached lists that have since been removed from the configuration.
  const allowed=new Set(sources(env).map(x=>x.name));
  const data=combine({geo:s.geo||{},lists:Object.fromEntries(Object.entries(s.lists).filter(([k])=>allowed.has(k)))});
  if(p==="status.json")return json({updated:s.updated,entries:data.entries.length,channels:data.groups.length,alternatives:data.alternatives,sources:Object.fromEntries(Object.entries(s.status).filter(([k])=>allowed.has(k)))});
  if(p==="italia-completa.m3u")return new Response("#EXTM3U\n"+data.entries.map(e=>{let info=e.info;let q=false,i=0;for(;i<info.length;i++){if(info[i]==='"')q=!q;if(!q&&info[i]===",")break;}let head=info.slice(0,i).replace(/\s+(?:tvg-chno|tvg-lcn|channel-number|lcn)="[^"]*"/gi,"");return [head+' tvg-chno="'+e.number+'",'+e.number+" · "+e.displayName,...e.opts,e.url].join("\n");}).join("\n")+"\n",{headers:{...cors,"Content-Type":"audio/x-mpegurl","Cache-Control":"no-store"}});
  if(/^catalog\/tv\/italia(?:\/.*)?\.json$/.test(p)){
    const q=new URLSearchParams(p.replace(/^catalog\/tv\/italia\/?/,"").replace(/\.json$/,"")).get("search")||u.searchParams.get("search")||"";
    return json({metas:data.groups.filter(g=>normalize(g.name).includes(normalize(q))).map(meta)});
  }
  const m=p.match(/^(meta|stream)\/tv\/(.+)\.json$/);if(m){
    let id;try{id=decodeURIComponent(m[2]);}catch{return json({error:"ID non valido"},400);}
    const g=data.groups.find(x=>x.id===m[2]||decodeURIComponent(x.id)===id||x.id===id);
    return m[1]==="meta"?json({meta:g?meta(g):null}):json({streams:g?.entries.slice(0,1).map(e=>({name:e.source,title:e.name+(declared(e)[0]?" · "+declared(e)[0]+"p (dichiarati)":""),url:e.url}))||[]});
  }return json({error:"Not found"},404);
}
export default {fetch:handle,scheduled(_e,env,ctx){ctx.waitUntil(refresh(env));}};
