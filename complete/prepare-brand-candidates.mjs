import fs from "node:fs";
import registry from "./brand-registry.mjs";
import {canonicalKey, cleanName} from "./catalog.mjs";
const out={};
function add(name,url,score){
 const k=canonicalKey(name,{});
 if(!k||!/^https:\/\//i.test(url||""))return;
 (out[k]??=[]).push({url,score,name:cleanName(name)});
}
for(const b of registry)add(b.name,b.logo,10);
// Independent original logo directory; do not access any stream or playlist.
try{
 const base="https://iptv-org.github.io/api/";
 const get=async file=>{const r=await fetch(base+file,{signal:AbortSignal.timeout(30000)});if(!r.ok)throw Error("HTTP "+r.status);return r.json();};
 const [channels,logos]=await Promise.all([get("channels.json"),get("logos.json")]);
 const names=new Map(channels.filter(c=>c.country==="IT").map(c=>[c.id,c.name]));
 for(const l of logos){
   if(!l.in_use||l.feed||!names.has(l.channel))continue;
   const t=(l.tags||[]).map(x=>String(x).toLowerCase());
   const score=30+(t.includes("color")?12:0)-(t.includes("white")?20:0)+(t.includes("horizontal")?3:0)+Math.min(Number(l.width)||0,1000)/1000;
   add(names.get(l.channel),l.url,score);
 }
}catch(e){console.warn("Directory loghi non disponibile; uso registro locale:",e.message);}
for(const [key,list] of Object.entries(out)){list.sort((a,b)=>b.score-a.score);out[key]=list.filter((v,i,a)=>a.findIndex(x=>x.url===v.url)===i);}
fs.writeFileSync("complete/brand-candidates.generated.json",JSON.stringify(out));
console.log("Identità con loghi candidati:",Object.keys(out).length);
