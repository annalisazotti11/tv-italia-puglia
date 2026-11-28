import assert from "node:assert/strict";
import {canonicalKey, rankedCombine, entryKey} from "./catalog.mjs";
const pairs=[["Rai Movie G","Rai Movie"],["Rai 3 (geo-blocked)","Rai 3"],["Rai 3 TGR Puglia (HbbTV)","Rai 3 TGR Puglia"],["Canale 5 HD (1080p)","Canale 5"],["4 · Rete 4","Rete 4"],["Rai Sport + HD","Rai Sport"],["Rai 4K (HbbTV)","Rai 4K"],["[IT] Rai 1","Rai 1"],["Rai 1 (not 24/7)","Rai 1"],["Tele Bari TV","Telebari"],["TG Com 24","TGCOM24"],["Nove TV","NOVE"],["Mediaset Italia 1","Italia 1"]];
for(const [a,b] of pairs)assert.equal(canonicalKey(a,{}),canonicalKey(b,{}),a);
for(const [a,b] of [["Rai 3","Rai 3 TGR Puglia"],["Rai 4","Rai 4K"],["Antenna Sud","Antenna Sud Extra"],["Boing","Boing Plus"],["Rai 1 +1","Rai 11"]])assert.notEqual(canonicalKey(a,{}),canonicalKey(b,{}),a);
const e=(name,i,extra={})=>({name,id:"",logo:"",info:"#EXTINF:-1,"+name,source:"fixture",opts:[],url:"https://example.invalid/"+i,...extra});
const result=rankedCombine({lists:{a:[e("Rai Movie G",1),e("Rai Movie FHD",2),e("Rai 3",3),e("Rai 1",4),e("Rai 3 TGR Puglia",5),e("Rai Movie HD (720p)",6)]},geo:{}});
assert.equal(result.groups.filter(g=>g.key==="raimovie").length,1);
assert.equal(result.groups.find(g=>g.key==="raimovie").entries.length,3);
assert.equal(result.groups.find(g=>g.key==="raimovie").entries[0].name,"Rai Movie FHD");
assert.equal(result.groups[0].key,"rai3tgrpuglia");
assert.equal(result.groups.filter(g=>g.key==="rai3").length,1);
assert.equal(entryKey(e("Generic station label",7,{id:"RaiMovie.it"}),{__channelIds:{"raimovie.it":"raimovie"}}),"raimovie");
assert.equal(entryKey(e("Rai 3",8,{id:"RaiMovie.it"}),{__channelIds:{"raimovie.it":"raimovie"}}),"rai3");
console.log("Catalog identity checks passed; no playback requests.");

const ordered=rankedCombine({geo:{},lists:{a:["Rai 1","Rai 2","Rai 3","Rete 4","Canale 5","Telenorba","Italia 1","LA7","TV8","NOVE","Real Time","Rai Movie G","Rai Movie HD","Unknown Station","Sky Uno","Sky Uno +"].map((name,i)=>e(name,100+i))}});
assert.equal(ordered.groups.slice(0,6).map(g=>g.key).join(","),"rai3tgrpuglia,rai1,rai2,rai3,rete4,canale5");
const remaining=ordered.groups.filter(g=>g.section>1);
for(let i=1;i<remaining.length;i++)assert.ok((remaining[i-1].audience??-1)>=(remaining[i].audience??-1),"Audience order");
assert.notEqual(canonicalKey("Sky Uno",{}),canonicalKey("Sky Uno +",{}));
assert.equal(ordered.groups.filter(g=>g.key==="raimovie").length,1);
assert.ok(remaining.some(g=>g.name==="Unknown Station"),"Unknown audience is not excluded");
console.log("Fixed opening, audience ordering and unknown audience checks passed.");

const many=rankedCombine({geo:{},lists:{a:Array.from({length:5000},(_,i)=>e(i%2?"Rai Movie G":"Rai Movie HD",i%250))}});
assert.equal(many.groups.find(g=>g.key==="raimovie").entries.length,250);
assert.equal(many.groups.find(g=>g.key==="raimovie").originalNames.length,2);
console.log("5,000-entry identity fixture passed.");
