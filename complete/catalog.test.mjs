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
const remaining=ordered.groups.filter(g=>g.orderBlock===4);
for(let i=1;i<remaining.length;i++)assert.ok((remaining[i-1].audience??-1)>=(remaining[i].audience??-1),"Audience order");
assert.notEqual(canonicalKey("Sky Uno",{}),canonicalKey("Sky Uno +",{}));
assert.equal(ordered.groups.filter(g=>g.key==="raimovie").length,1);
assert.ok(remaining.some(g=>g.name==="Unknown Station"),"Unknown audience is not excluded");
console.log("Fixed opening, audience ordering and unknown audience checks passed.");

const many=rankedCombine({geo:{},lists:{a:Array.from({length:5000},(_,i)=>e(i%2?"Rai Movie G":"Rai Movie HD",i%250))}});
assert.equal(many.groups.find(g=>g.key==="raimovie").entries.length,250);
assert.equal(many.groups.find(g=>g.key==="raimovie").originalNames.length,2);
console.log("5,000-entry identity fixture passed.");

const regional=rankedCombine({geo:{},lists:{a:[
e("Rai 1",201,{info:'#EXTINF:-1 group-title="Puglia",Rai 1'}),
e("Italia 1",202,{info:'#EXTINF:-1 group-title="Puglia",Italia 1'}),
e("Telenorba",203),
e("Local Puglia Test Station",204,{info:'#EXTINF:-1 tvg-chno="6" group-title="Puglia",Local Puglia Test Station'})
]}});
assert.equal(regional.groups.find(g=>g.key==="italia1").regional,false);
assert.equal(regional.groups.find(g=>g.key==="telenorba").regional,true);
assert.equal(regional.groups.find(g=>g.key==="italia1").number,6);
assert.notEqual(regional.groups.find(g=>g.key==="localpugliateststation").number,6);
const equalQuality=[e("Rai Movie HD",301,{source:"B"}),e("Rai Movie HD",302,{source:"A"})];
const best=list=>rankedCombine({geo:{},lists:{a:list}}).groups.find(g=>g.key==="raimovie").entries[0].source;
assert.equal(best(equalQuality),"A");
assert.equal(best([...equalQuality].reverse()),"A");
console.log("Regional classification, reserved LCN and stable tie-breaking checks passed.");

const sky=rankedCombine({geo:{},lists:{a:["Rai 1","Rai 2","Rai 3","Rete 4","Canale 5","Sky 1","Sky Uno HD","Telenorba","Italia 1","LA7","TV8","NOVE","Sky Sport Uno","Sky Cinema Uno","Sky Atlantic","Sky TG24","Real Time","Sky Uno +","Sky Sport 251"].map((n,i)=>e(n,600+i))}});
assert.equal(sky.groups.slice(0,7).map(g=>g.key).join(","),"rai3tgrpuglia,rai1,rai2,rai3,rete4,canale5,skyuno");
assert.equal(sky.groups.filter(g=>g.key==="skyuno").length,1);
const pos=k=>sky.groups.findIndex(g=>g.key===k);
assert.ok(pos("skyuno")<pos("telenorba"));
assert.ok(pos("telenorba")<pos("italia1"));
assert.ok(pos("nove")<pos("skysportuno"));
assert.ok(pos("skycinemauno")<pos("realtime"));
assert.ok(pos("realtime")<pos("skysport251"));
assert.ok(pos("skyunoplus")>pos("skyuno"));
console.log("Sky priority and fixed DTT ordering passed.");

for(const [a,b] of [["Rai1HD","Rai 1"],["Canale5FHD","Canale 5"],["SkyUnoHD","Sky Uno"],["TelebariHD","Telebari"]])assert.equal(canonicalKey(a,{}),canonicalKey(b,{}),a);
assert.notEqual(canonicalKey("Boing Plus",{}),canonicalKey("Boing",{}));
assert.notEqual(canonicalKey("Sky Sport 4K",{}),canonicalKey("Sky Sport",{}));
assert.ok(Array.isArray(sky.displayConflicts));
console.log("Joined quality suffix and display collision checks passed.");

const numbered=[["[36] RTL 102.5","RTL 102.5"],["[37] Warner TV","Warner TV"],["[38] Giallo","Giallo"],["[39] Top Crime","Top Crime"],["[40] Boing","Boing"],["[41] K2","K2"],["[42] Rai Gulp","Rai Gulp"],["[43] Rai Yoyo","Rai Yoyo"],["[44] Frisbee","Frisbee"],["1043 · [38] Giallo","Giallo"],["[IT] [1] Rai 1 HD","Rai 1"],["[108] Unknown Station","Unknown Station"]];
for(const [a,b] of numbered)assert.equal(canonicalKey(a,{}),canonicalKey(b,{}),a);
const screenshot=rankedCombine({geo:{},lists:{a:numbered.flatMap(([a,b],i)=>[e(a,i+800),e(b,i+900)])}});
assert.equal(screenshot.groups.filter(g=>g.key==="giallo").length,1);
assert.equal(screenshot.groups.find(g=>g.key==="giallo").number,38);
assert.equal(screenshot.groups.find(g=>g.key==="giallo").name,"Giallo");
assert.ok(screenshot.groups.find(g=>g.key==="giallo").poster);
assert.ok(screenshot.priorityMissing.includes("Sky Uno"));
assert.notEqual(canonicalKey("[20] 20 Mediaset",{}),canonicalKey("Mediaset Extra",{}));
assert.notEqual(canonicalKey("[1] Rai 1",{}),canonicalKey("Rai 2",{}));
console.log("Screenshot regression, logos, canonical numbers and missing-priority diagnostics passed.");

assert.equal(canonicalKey("Rai (4K)",{}),canonicalKey("Rai 4K",{}));
assert.equal(canonicalKey("Sky Sport [4K]",{}),canonicalKey("Sky Sport 4K",{}));
assert.equal(canonicalKey("038 Giallo",{}),"giallo");
assert.equal(canonicalKey("1038 Giallo",{}),"giallo");
assert.notEqual(canonicalKey("27 Twentyseven",{}),canonicalKey("Twentyseven Plus",{}));
assert.equal(entryKey(e("Example Plus",5001,{id:"RaiMovie.it"}),{__channelIds:{"raimovie.it":"raimovie"}}),"exampleplus");
assert.equal(screenshot.priorityDiagnostics.find(g=>g.name==="Sky Uno").present,false);
assert.equal(sky.priorityDiagnostics.find(g=>g.name==="Sky Uno").position,6);
console.log("Number variants, protected editorial identities and priority diagnostics passed.");

const fastAliases=[["Affare Fatto – Pluto TV","Affare Fatto"],["Affare Fatto (Samsung TV Plus)","Affare Fatto"],["Affare Fatto Pluto TV","Affare Fatto"],["Andromeda - Rakuten TV","Andromeda"],["Andromeda Italia","Andromeda"],["Andromeda (IT)","Andromeda"],["Andromeda Italy","Andromeda"],["[Pluto TV] Andromeda","Andromeda"],["Film d'autore – Plex","Film d'autore"]];
for(const [a,b] of fastAliases)assert.equal(canonicalKey(a,{}),canonicalKey(b,{}),a);
for(const [a,b] of [["Andromeda English","Andromeda"],["Affare Fatto +1","Affare Fatto"],["Pluto TV Cinema","Pluto TV Serie"],["Antenna Sud Extra","Antenna Sud"]])assert.notEqual(canonicalKey(a,{}),canonicalKey(b,{}),a);
const fast=rankedCombine({geo:{},lists:{a:fastAliases.flatMap(([a,b],i)=>[e(a,i+5100),e(b,i+5200)])}});
assert.equal(fast.groups.filter(g=>g.key==="affarefatto").length,1);
assert.equal(fast.groups.filter(g=>g.key==="andromeda").length,1);
assert.equal(fast.groups.find(g=>g.key==="andromeda").name,"Andromeda");
const logoShared=rankedCombine({geo:{},lists:{a:[e("Test Alpha",5300,{logo:"https://example.invalid/logo.png"}),e("Test Beta",5301,{logo:"https://example.invalid/logo.png"})]}});
assert.ok(logoShared.sharedLogoGroups.some(v=>v.includes("Test Alpha")&&v.includes("Test Beta")));
assert.ok(logoShared.groups.some(g=>g.key==="testalpha")&&logoShared.groups.some(g=>g.key==="testbeta"));
console.log("FAST platform variants, distinct programming and shared-logo diagnostics passed.");

assert.equal(screenshot.priorityDiagnostics.find(g=>g.name==="Sky Uno").reason,"not_found_in_loaded_collections");
assert.equal(sky.priorityDiagnostics.find(g=>g.name==="Sky Uno").observedEntries,2);
assert.equal(sky.priorityDiagnostics.find(g=>g.name==="Sky Uno").reason,"present");
console.log("Priority presence diagnostics passed; no stream URLs inspected.");
