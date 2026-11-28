import BRAND_REGISTRY from "./brand-registry.mjs";
import PUGLIA_FALLBACK from "./puglia-fallback.mjs";
export function cleanName(value){
 let s=String(value||"").normalize("NFKC").replace(/[\u200b-\u200f\u202a-\u202e\u2060\ufeff©®™]/g," ").trim();
 s=s.replace(/^(?:IT|ITA|ITALY|ITALIA)\s*[:|–-]\s*/i,"").replace(/^\[(?:IT|ITA|ITALY|ITALIA)\]\s*/i,"");
 // Playlist position labels are not channel identity. Preserve numbers in channel names.
 for(let i=0;i<6;i++){
   const previous=s;
   s=s.replace(/^\s*\[\s*\d{1,5}\s*\]\s*(?:[-:|·–—]\s*)?/,"")
      .replace(/^\s*\(\s*\d{1,5}\s*\)\s*(?:[-:|·–—]\s*)?/,"")
      .replace(/^\s*\d{1,5}\s*[·|:–—]\s*/,"")
      .replace(/^\s*(?:IT|ITA|ITALY|ITALIA)\s*[:|–-]\s*/i,"")
      .replace(/^\s*\[(?:IT|ITA|ITALY|ITALIA)\]\s*/i,"").trim();
   if(previous===s)break;
 }
 // A platform label is distribution metadata, not an editorial channel name.
 // Require a separator or parentheses; do not strip brand names from real titles.
 const platform=/(?:Pluto\s*TV(?:\s*(?:Italia|Italy|IT))?|Samsung\s*TV\s*Plus|Rakuten\s*TV|LG\s*Channels|Plex(?:\s*TV)?|TCL\s*Channel|Xiaomi\s*TV\+|CHILI|DistroTV|Freevee|VIDAA\s*Channels)/i;
 for(let i=0;i<4;i++){
   const old=s;
   s=s.replace(new RegExp("\\s*(?:[-–—|·:]\\s*"+platform.source+"|\\(\\s*"+platform.source+"\\s*\\)|\\[\\s*"+platform.source+"\\s*\\])\\s*$","i"),"").trim();
   s=s.replace(new RegExp("^\\s*(?:"+platform.source+"\\s*[-–—|·:]\\s*|\\[\\s*"+platform.source+"\\s*\\]\\s*)","i"),"").trim();
   if(s===old)break;
 }
 // Remove only technical annotations, not programme/channel variants (+1, Cinema, Sport, regional editions).
 const tech=/^(?:\s*(?:\d{3,4}[pi]?|[248]k|uhd|fhd|full\s*hd|hd\+?|sd|hevc|h\.?26[45]|avc|aac|hdr10?|dolby\s*vision|\d+(?:\.\d+)?\s*fps|[0-9.]+\s*[mk]bps|[x×]\s*\d+|[-/|,;:+×x\s])+)\s*$/i;
 s=s.replace(/^(rai|sky sport)\s*[(\[]\s*4k\s*[)\]]/i,"$1 4K");
 s=s.replace(/\(([^()]*)\)|\[([^\[\]]*)\]/g,(m,a,b)=>tech.test(a??b)?" ":m);
 s=s.replace(/\s*(?:\((?:not\s*24\/7|geo[- ]?blocked|geo[- ]?block|backup|hbbtv|test stream)\)|\[(?:not\s*24\/7|geo[- ]?blocked|geo[- ]?block|backup|hbbtv|test stream)\])\s*/gi," ").trim();
 const dedicated4k=/^(?:rai|sky sport)\s*4k$/i.test(s);
 let old;
 if(!dedicated4k)do{old=s;s=s.replace(/(?:[\s|–—:;,.-]+)(?:\d{3,4}[pi]|\d{3,4}\s*[x×]\s*\d{3,4}|[248]k|uhd|fhd|full\s*hd|hd\+?|sd|hevc|h\.?26[45]|avc|hdr10?|\d+(?:\.\d+)?\s*fps)\s*$/i,"").replace(/[\s|–—:;,.-]+$/g,"").trim();}while(s!==old);
 return s.replace(/\s+/g," ").trim();
}
const flat=s=>cleanName(s).normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/\+\s*(?=\d|$)/g,"plus").replace(/[^a-z0-9]/g,"");
const localMap=new Map([["Telenorba",10],["Teledue",12],["Telerama",15],["Tele Dehon",19],["Canale 7 Puglia",78],["Delta TV",83],["Teleregione Color",0],["Antenna Sud Extra",92],["7 Gold Puglia",84],["BTV",0],["La Nuova TV",0],["Telesveva",18],["Tele Sud Puglia",155],["TRC Puglia",76],["TeleMajg",79],["Teletrullo",80],["Easy TV",81],["Political TV",86],["Mediterranea TV - Video M Italia",89],["Canale 2 TV",90],["Amica 9",91],["Azzurra TV Italia",95],["StarTV",96],["Studio 100",98],["Tele Foggia",88],["Cittadella TV",94]].map(([n,v])=>[flat(n),v]));
const lcnMap=new Map([["Rai 1 HD",1],["Rai 2 HD",2],["Rai 3 HD",3],["Rai 3 TGR Puglia",103],["Rete 4 HD",4],["Canale 5 HD",5],["Italia 1 HD",6],["LA7 HD",7],["TV8",8],["NOVE",9],["Radionorba TV",11],["TG Norba 24",13],["Antenna Sud",14],["Telebari",17],["20 Mediaset HD",20],["Rai 4",21],["Iris",22],["Rai 5",23],["Rai Movie",24],["Cielo",26],["27 Twentyseven",27],["La5",30],["Real Time",31],["Food Network",33],["Cine34",34],["Focus",35],["RTL 102.5",36],["Rai News 24",48],["Sky TG24",50],["TGCOM24",51],["DMAX",52],["Rai Storia",54],["HGTV",56],["Radio 105 TV",66],["Deejay TV HD",69],["RadioItaliaTV",70],["Radio Kiss Kiss TV",158],["Gambero Rosso",257],["Hell's Kitchen Italy",404]].map(([n,v])=>[flat(n),v]));
// LCN nazionali novembre 2026 e mappa regionale Puglia.
for(const [n,v] of [["Rai Premium",25],["TV2000",28],["LA7 Cinema",29],["QVC",32],["Discovery",37],["Giallo",38],["Top Crime",39],["Boing",40],["K2",41],["Rai Gulp",42],["Rai YoYo",43],["Frisbee",44],["Boing Plus",45],["Cartoonito",46],["Super!",47],["Mediaset Italia 2",49],["Italia 53",53],["Mediaset Extra",55],["Italiana",57],["Rai Sport",58],["Arte Italia 124",124],["Radio 2 Visual",202],["Parole di Vita",245],["Radiofreccia",258],["Byoblu",262],["RDS Social TV",265]])lcnMap.set(flat(n),v);
for(const [n,v] of [["Rai 3 TGR Puglia",819],["Radionorba TV",11],["TG Norba 24",13],["Antenna Sud",14],["TRM H24",16],["Telebari",17],["Padre Pio TV",75],["Teleregione Color",77],["La Nuova TV",82],["BTV",85],["Puglia 7",87],["New Media",93],["Foggia TV",99],["Bari News",111]])localMap.set(flat(n),v);
lcnMap.delete("hellskitchenitaly");
for(const [n,v] of [["Italia Channel",123],["Arte Italia 125",125],["Gold TV Italia",128],["La 4 Italia",129],["Rete Italia",131],["Telecampione",138],["Prim aset",149],["EQUtv",151],["Tesory Channel",152],["Orler TV",166],["Prima Free",170],["Match Music",232],["Cusano News 7",234],["Man-ga",236],["BeJoy Kids",247],["Radio Radio TV",253],["Maria Vision",255],["Radio Zeta",266],["Arteora TV",267],["2Settanta TV",270],["Italian Fishing TV",441]])lcnMap.set(flat(n),v);
for(const [k,v] of localMap)if(v)lcnMap.set(k,v);
const alias=new Map([["radioitaliatv","radioitaliatv"],["radioitalia","radioitaliatv"],["la7","la7"],["20mediaset","20mediaset"],["mediaset20","20mediaset"],["canale20","20mediaset"],["rai3puglia","rai3tgrpuglia"],["raitreregionepuglia","rai3tgrpuglia"],["tg3puglia","rai3tgrpuglia"],["raitreregionalepuglia","rai3tgrpuglia"],["telebari","telebari"],["tgnorba24","tgnorba24"]]);
for(const [a,b] of [["radio norba television","Radionorba TV"],["radio norba tv","Radionorba TV"],["T.R. Padre Pio","Padre Pio TV"],["Teleradio Padre Pio","Padre Pio TV"],["Tele Radio Padre Pio","Padre Pio TV"],["TRM h24","TRM H24"],["Delta TV 1","Delta TV"],["Tele Regione Color","Teleregione Color"],["Rai 3 TGR Puglia 819","Rai 3 TGR Puglia"],["Italia 2","Mediaset Italia 2"],["Mediaset Italia Due","Mediaset Italia 2"],["La7d","LA7 Cinema"],["Rai Radio 2 Visual","Radio 2 Visual"],["27","27 Twentyseven"],["Twentyseven","27 Twentyseven"],["Tg Norba 24","TG Norba 24"],["Casa Italia 53","Italia 53"]])alias.set(flat(a),flat(b));
// Recognize provider suffixes only when the remaining name is a known channel.
for(const [a,b] of [["Rai Uno","Rai 1"],["Rai Due","Rai 2"],["Rai Tre","Rai 3"],["Rete Quattro","Rete 4"],["Canale Cinque","Canale 5"],["Italia Uno","Italia 1"],["Rai News","Rai News 24"],["Rai Movie Italia","Rai Movie"],["TGR Puglia","Rai 3 TGR Puglia"],["Rai Tre TGR Puglia","Rai 3 TGR Puglia"],["Rai 3 Regione Puglia","Rai 3 TGR Puglia"],["Rai 3 Puglia TGR","Rai 3 TGR Puglia"],["Rai 3 TGR Puglia (HbbTV)","Rai 3 TGR Puglia"]])alias.set(flat(a),flat(b));
for(const [a,b] of [["Rai Sport +","Rai Sport"],["Rai Sport Plus","Rai Sport"],["Rai Sport 1","Rai Sport"],["Rai 4K HbbTV","Rai 4K"],["Rai 3 TGR Puglia 103","Rai 3 TGR Puglia"],["Rai 3 Puglia 819","Rai 3 TGR Puglia"],["Rai 3 TGR Puglia 3","Rai 3 TGR Puglia"],["Rai 3 TGR Puglia (Italia)","Rai 3 TGR Puglia"],["Rai3 TGR Puglia","Rai 3 TGR Puglia"],["Rai News 24 TV","Rai News 24"],["TG Com 24","TGCOM24"],["Mediaset TGCOM24","TGCOM24"],["Mediaset Rete 4","Rete 4"],["Mediaset Canale 5","Canale 5"],["Mediaset Italia 1","Italia 1"],["La 5 Mediaset","La5"],["20 Mediaset Italia","20 Mediaset"],["27 Twenty Seven","27 Twentyseven"],["Twenty Seven","27 Twentyseven"],["Nove TV","NOVE"],["TV 8 Italia","TV8"],["Dmax Italia","DMAX"],["Real Time Italia","Real Time"],["Food Network Italia","Food Network"],["Discovery Italia","Discovery"],["Discovery Italy","Discovery"],["Discovery Channel Italia","Discovery"],["Discovery Channel Italy","Discovery"],["Radio Italia TV","RadioItaliaTV"],["Radio Italia Television","RadioItaliaTV"],["Radio Italia Solo Musica Italiana TV","RadioItaliaTV"],["Radio Kiss Kiss Television","Radio Kiss Kiss TV"],["Radio Norba","Radionorba TV"],["Tele Norba","Telenorba"],["Tele Norba 1","Telenorba"],["Tele Due","Teledue"],["Tele Rama","Telerama"],["TRM 24","TRM H24"],["TRM H 24","TRM H24"],["Antenna Sud TV","Antenna Sud"],["Antenna Sud 14","Antenna Sud"],["Antenna Sud Extra 92","Antenna Sud Extra"],["Tele Bari TV","Telebari"],["Teleradio Padre Pio TV","Padre Pio TV"]])alias.set(flat(a),flat(b));
for(const [a,b] of [["20","20 Mediaset"],["Italia 2 Mediaset","Mediaset Italia 2"],["HGTV Home & Garden","HGTV"],["Sky TG24 (50)","Sky TG24"],["Rai Sport HD","Rai Sport"],["Rai3 TGR Puglia HD","Rai 3 TGR Puglia"]])alias.set(flat(a),flat(b));
for(const [a,b] of [["Sky 1","Sky Uno"],["Sky Uno Italia","Sky Uno"],["Sky Uno Italy","Sky Uno"]])alias.set(flat(a),flat(b));
// Explicit aliases for the Italian FAST brands observed in the catalogue.
for(const [a,b] of [["Affare Fatto Pluto TV","Affare Fatto"],["Affare Fatto Italia","Affare Fatto"],["Affare Fatto Italy","Affare Fatto"],["Affare Fatto IT","Affare Fatto"],["Andromeda Pluto TV","Andromeda"],["Andromeda Italia","Andromeda"],["Andromeda Italy","Andromeda"],["Andromeda IT","Andromeda"],["Andromeda (Italia)","Andromeda"],["Andromeda (Italy)","Andromeda"],["Andromeda (IT)","Andromeda"],["Andromeda [IT]","Andromeda"]])alias.set(flat(a),flat(b));
const SKY_MAIN=new Set(["Sky Sport Uno","Sky Sport 24","Sky TG24","Sky Cinema Uno","Sky Atlantic","Sky Serie","Sky Sport F1","Sky Sport Moto GP","Sky Sport Tennis","Sky Sport Arena","Sky Sport Max","Sky Sport Basket","Sky Cinema Due","Sky Cinema Action","Sky Cinema Comedy","Sky Cinema Family","Sky Cinema Collection","Sky Cinema Stories","Sky Cinema Romance","Sky Cinema Drama","Sky Cinema Suspense","Sky Investigation","Sky Crime","Sky Nature","Sky Documentaries","Sky Arte"].map(flat));
const knownNames=new Set([...lcnMap.keys(),...localMap.keys(),...SKY_MAIN,...alias.values(),...BRAND_REGISTRY.map(b=>flat(b.name))]);
const keyOf=n=>{
 let s=cleanName(n);
 let k=flat(s);
 const plain=alias.get(k)||k;
 if(alias.has(k)||lcnMap.has(k)||localMap.has(k))return plain;
 const isKnown=t=>knownNames.has(t)||alias.has(t)||knownNames.has(alias.get(t));
 // Numeric channel prefixes may be playlist numbering, not part of the channel name.
 const prefix=s.match(/^(\d{1,4})\s*(?:[.·:|–-]\s*|\s+)(.+)$/);
 if(prefix){
   const t=flat(prefix[2]),a=alias.get(t)||t;
   if(isKnown(t)&&(lcnMap.get(a)===Number(prefix[1])||/^0\d|^\d{3,4}\s/.test(s)))return a;
 }
 for(let i=0;i<6;i++){
   const candidate=s.replace(/\s*(?:\((?:G|GEO|GEO[- ]?BLOCKED|GEO[- ]?BLOCK|IT|ITA|ITALIA|ITALY|BACKUP|HBBTV|NOT\s*24\/7)\)|\[(?:G|GEO|GEO[- ]?BLOCKED|GEO[- ]?BLOCK|IT|ITA|ITALIA|ITALY|BACKUP|HBBTV|NOT\s*24\/7)\]|[\s|–—:;,.-]+(?:G|GEO|GEO[- ]?BLOCKED|GEO[- ]?BLOCK|IT|ITA|ITALIA|ITALY|BACKUP|HBBTV|NOT\s*24\/7))\s*$/i,"").trim();
   if(candidate===s)break;
   s=candidate;const t=flat(s),a=alias.get(t)||t;
   if(isKnown(t))return a;
 }
 // Resolve glued quality labels only when the base station is known.
 const glued=k.match(/^(.+?)(?:fullhd|fhd|uhd|hd|sd|1080p|720p|576p|480p)$/);
 if(glued&&isKnown(glued[1]))return alias.get(glued[1])||glued[1];
 return alias.get(k)||k;
};
const curated=new Map(BRAND_REGISTRY.map(b=>[keyOf(b.name),{name:cleanName(b.name),logo:b.logo}]));
const preferred=new Map([["rai1","Rai 1"],["rai2","Rai 2"],["rai3","Rai 3"],["rete4","Rete 4"],["canale5","Canale 5"],["italia1","Italia 1"],["raimovie","Rai Movie"],["raipremium","Rai Premium"],["rai3tgrpuglia","Rai 3 TGR Puglia"],["la7","LA7"],["tv8","TV8"],["nove","NOVE"],["skyuno","Sky Uno"],["affarefatto","Affare Fatto"],["andromeda","Andromeda"]]);
export const canonicalKey=(n,geo)=>{
 const k=keyOf(n);
 if(lcnMap.has(k)||localMap.has(k)||preferred.has(k)||SKY_MAIN.has(k))return k;
 return keyOf(geo?.__identities?.[k]||k);
};
const identified=k=>lcnMap.has(k)||localMap.has(k)||curated.has(k)||preferred.has(k)||SKY_MAIN.has(k);
export function entryKey(e,geo={}){
 const key=canonicalKey(e.name,geo);
 const named=e.info?.match(/(?:^|\s)tvg-name="([^"]+)"/i)?.[1];
 const alt=named?canonicalKey(named,geo):"";
 const id=String(e.id||"").trim().toLowerCase();
 const exactId=geo.__channelIds?.[id]||"";
 // Only use alternate names and trusted exact IDs when they do not conflict with a known name.
 if(identified(key))return key;
 // Explicit editorial variants must not be collapsed by a generic TVG identifier.
 if(/(?:\b(?:plus|extra)\b|\+\s*\d*\s*$|\b(?:tgr|regione)\b)/i.test(cleanName(e.name)))return key;
 // A trusted channel name in the independent identity directory outranks playlist labels.
 if(geo.__brands?.[key])return key;
 if(alt&&identified(alt)&&!exactId&&!/(?:\b(?:plus|extra|cinema|sport|news|puglia)\b|\+\s*\d+)/i.test(e.name))return alt;
 if(exactId&&(!identified(alt)||alt===exactId))return exactId;
 return key;
}
export function findLogo(g,geo){
 const b=geo.__brands?.[g.key]||curated.get(g.key);
 return b?.logo||g.entries.map(e=>e.logo).find(u=>/^https:\/\//i.test(u||""))||"";
}
export function posterUrl(logo){
 if(!/^https:\/\//i.test(logo||""))return undefined;
 // Normalize the original logo as a centered square PNG; only the public logo URL is sent to the image service.
 return "https://wsrv.nl/?url="+encodeURIComponent(logo)+"&w=500&h=500&fit=contain&cbg=white&output=png&v=130";
}
const regions=/\b(?:abruzzo|basilicata|calabria|campania|emilia(?: romagna)?|friuli(?: venezia giulia)?|lazio|liguria|lombardia|marche|molise|piemonte|sardegna|sicilia|toscana|trentino(?: alto adige)?|umbria|valle d[’' ]aosta|veneto|sudtirol)\b/i;
const puglia=/\b(?:puglia|apulia|salento|bari|barletta|andria|trani|brindisi|foggia|lecce|taranto|norba)\b/i;
export function declared(e){
 const n=[e.name,e.info.match(/(?:tvg-resolution|resolution|quality)="([^"]+)"/i)?.[1],e.quality].filter(Boolean).join(" ");
 const h=Number(n.match(/\b(4320|2160|1440|1080|720|576|540|480|360|240)[pi]?\b/i)?.[1])||(/\b8k\b/i.test(n)?4320:/\b(?:4k|uhd)\b/i.test(n)?2160:/\b(?:fhd|full\s*hd)\b/i.test(n)?1080:/\bhd\b/i.test(n)?720:/\bsd\b/i.test(n)?480:0);
 const fps=Number(e.info.match(/(?:tvg-fps|fps|framerate)="([\d.]+)"/i)?.[1]||n.match(/\b(\d+(?:\.\d+)?)\s*fps\b/i)?.[1]||0);
 const b=e.info.match(/(?:tvg-bitrate|bitrate|bandwidth)="([\d.]+)\s*(mbps|kbps|bps)?"/i);const br=b?Number(b[1])*(b[2]?.toLowerCase()==="mbps"?1e6:b[2]?.toLowerCase()==="kbps"?1e3:1):0;
 return [h,fps,br];
}
export function compareQuality(a,b){const x=declared(a),y=declared(b);return y[0]-x[0]||y[1]-x[1]||y[2]-x[2];}
function reg(e,geo,k=entryKey(e,geo)){
 const group=e.info.match(/group-title="([^"]*)"/i)?.[1]||"";
 const labels=e.name+" "+group;
 if(localMap.has(k)||k==="rai3tgrpuglia")return "puglia";
 if(geo[e.id]==="other"&&!puglia.test(e.name))return "other";
 if((lcnMap.has(k)||k==="skyuno"||SKY_MAIN.has(k))&&!localMap.has(k)&&geo[e.id]!=="puglia")return "national";
 if(puglia.test(labels))return "puglia";
 if(regions.test(labels)||/\b(?:regional|regionali|locali|local tv|regional dvb-t)\b/i.test(group))return geo[e.id]==="puglia"||geo[k]==="puglia"?"puglia":"other";
 return geo[e.id]||geo[k]||"national";
}
// Personal catalogue exclusions: requested Medjugorje variants and non-programming extras.
// Keep Italian terrestrial/local channels and unknown-audience broadcasters.
export function unwantedChannel(g){
 const names=[g.name,...(g.originalNames||g.entries.map(e=>e.name))].map(n=>String(n||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLowerCase());
 if(names.some(n=>/medj?ugorj[ei]|medugorje|međugorje|medjugorie/i.test(n)))return true;
 if(g.section!==3)return false;
 return names.some(n=>/^(?:test(?: channel| card| pattern| stream| signal)?|no signal|segnale assente|canale test|monoscopio|test tecnico)(?:\s*[- #]?\d+)?$/i.test(cleanName(n))||
 /\b(?:web\s*cam|live\s*cam|telecamera)\b.*\b(?:santuario|santuari|chiesa|basilica|grotta|cappella|lourdes|fatima)\b|\b(?:santuario|santuari|chiesa|basilica|grotta|cappella|lourdes|fatima)\b.*\b(?:web\s*cam|live\s*cam|telecamera)\b/i.test(n));
}
export function rankedCombine(state){
 const groups=new Map();
 const geo=state.geo||{};
 const nameKeys=new Map();
 const prepared=[];
 const observed=new Map();
 const ambiguousNames=new Set();
 // Learn exact alternate labels within this catalogue only, never use fuzzy name similarity alone.
 for(const list of Object.values(state.lists))for(const e of list){
   const a=canonicalKey(e.name,geo),b=entryKey(e,geo);
   if(!b)continue;
   const region=reg(e,geo,b);
   const stats=observed.get(b)||{entries:0,excludedRegion:0,sourceNames:new Set()};
   stats.entries++;if(region==="other")stats.excludedRegion++;
   if(e.source)stats.sourceNames.add(e.source);
   observed.set(b,stats);
   if(region==="other")continue;
   prepared.push({e,base:b,region});
   if(!a||a===b||identified(a)||geo.__brands?.[a])continue;
   if(nameKeys.has(a)&&nameKeys.get(a)!==b)ambiguousNames.add(a);else nameKeys.set(a,b);
 }
 for(const a of ambiguousNames)nameKeys.delete(a);
 for(const {e,base,region} of prepared){
  const key=nameKeys.get(base)||base;
  if(!groups.has(key))groups.set(key,{id:"tvic:"+encodeURIComponent(key),name:cleanName(e.name),poster:"",entries:[],urlIndex:new Map(),names:new Set(),regional:region==="puglia",number:0,key});
  const g=groups.get(key);
  g.names.add(e.name);
  const index=g.urlIndex.get(e.url);
  if(index===undefined){g.urlIndex.set(e.url,g.entries.length);g.entries.push(e);}
  else if(compareQuality(e,g.entries[index])<0)g.entries[index]=e;
  if(region==="puglia")g.regional=true;
  const l=Number(e.info.match(/(?:tvg-chno|tvg-lcn|channel-number|lcn)="(\d+)"/i)?.[1]||0);
  if(l>0&&(!g.number||l<g.number))g.number=l;
 }
 // Sorgenti singole di riserva solo per canali pugliesi non presenti nelle playlist.
 for(const e of PUGLIA_FALLBACK){
   const key=canonicalKey(e.name,geo);
   if(!groups.has(key))groups.set(key,{id:"tvic:"+encodeURIComponent(key),name:cleanName(e.name),poster:"",entries:[e],regional:true,number:0,key});
 }
 let all=[...groups.values()];
 for(const g of all){
   g.entries.sort((a,b)=>compareQuality(a,b)||String(a.source||"").localeCompare(String(b.source||""),"it")||String(a.url).localeCompare(String(b.url)));
   g.originalNames=g.names?[...g.names]:[...new Set(g.entries.map(e=>e.name))];
   delete g.urlIndex;delete g.names;
   g.name=preferred.get(g.key)||geo.__brands?.[g.key]?.name||curated.get(g.key)?.name||g.originalNames.map(cleanName).sort((a,b)=>a.length-b.length||a.localeCompare(b,"it"))[0]||g.name;
   g.poster=findLogo(g,geo);
   g.publicLogo=geo.__brands?.[g.key]?.logo||curated.get(g.key)?.logo||"";
   const known=lcnMap.get(g.key)||0;
   g.lcn=known||null;
   const dtt=g.entries.some(e=>/\b(?:DTT|DVB-T2?|digitale terrestre)\b/i.test(e.info.match(/group-title="([^"]*)"/i)?.[1]||""));
   g.number=known||(g.regional||dtt?g.number:0);
   g.section=g.key==="rai3tgrpuglia"?-1:known>=1&&known<=5?0:g.regional?1:known||dtt?2:3;
 }
 const excluded=all.filter(unwantedChannel).map(g=>g.name);
 all=all.filter(g=>!unwantedChannel(g));
 // Ordine richiesto, indipendente dal numero LCN: 1–5, Puglia, DTT, extra.
 // Auditel Total Audience, 4–31 ottobre 2026, AM giornata intera (02:00–25:59).
 // https://www.auditel.it/wp-content/uploads/2026/11/Sintesi-Mensile-Ottobre-2026_TA47.xlsx-Sola-lettura.pdf
 const audiences=new Map([["Sky Sport Uno",44801],["Sky Uno",43329],["Discovery Turbo",27775],["Sky Sport 24",27681],["Sky Sport F1",27671],["Discovery",26912],["Supertennis",18173],["Sky Serie",14663],["Sky Cinema Uno",13451],["Sky Investigation",12694],["Sky Sport 251",12294],["Sky Sport Tennis",11877],["Sky Collection",7550],["Sky Atlantic",7487],["Sky Cinema Collection",6477],["Sky Sport Arena",6068],["Sky Sport 4K",5806],["Sky Cinema Action",5369],["Sky Cinema Comedy",5340],["Sky Sport 252",5026],["Sky Sport Moto GP",4846],["Sky Cinema Stories",4729],["Sky Nature",4291],["Sky Cinema Family",3852],["Sky Sport Basket",3695],["History HD",3688],["Sky Crime",3653],["DAZN 1",3456],["Sky Cinema Romance",3311],["Sky Cinema Uno +24",2983],["Sky Sport 253",2956],["Sky Cinema Suspense",2921],["Sky Adventure",2717],["Sky Documentaries",2619],["Sky Sport Max",2274],["Sky Cinema Drama",2038],["Gambero Rosso",1476],["Disney Junior",1375],["DeA Junior",1188],["Comedy Central",1108],["Sky Sport 254",1005],["Sky Sport Golf",725],["DeAKids",656],["Nick Jr.",459],["Sky Sport 255",364],["Nickelodeon",363],["Cartoon Network",351],["Sky Sport 256",251],["Boomerang",219],["Sky Sport 257",201],["Sky Sport 258",169],["DAZN 2",82],["Sky Sport 259",50]].map(([n,v])=>[keyOf(n),v]));
 for(const [name,value] of [["Italia 1",375333],["La7",366293],["NOVE",211867],["TV8",202951],["Real Time",146214],["Rai 4",134654],["Top Crime",103584],["La5",94448],["27 Twentyseven",90890],["Cine34",90245],["20 Mediaset",88394],["Iris",87040],["Rai Premium",84594],["Rai Movie",72608],["Giallo",68133],["DMAX",67980],["Mediaset Extra",66091],["Focus",60987],["Cielo",59644],["Food Network",51953],["LA7 Cinema",48178],["Rai News 24",45715],["TGCOM24",44149],["Rai 5",37059],["Sky TG24",32351],["Rai YoYo",32566],["Rai Sport",31302],["Boing",30291],["Mediaset Italia 2",27809],["Frisbee",27531],["HGTV",25851],["K2",24435],["RadioItaliaTV",22412],["Sportitalia",21704],["Boing Plus",20662],["Cartoonito",19872],["Italiana",12569],["RTL 102.5",11432],["Rai Gulp",10845],["Rai Storia",9667],["Padre Pio TV",9633],["Deejay TV",3394]])audiences.set(keyOf(name),value);
 // Unknown audience remains null unless a documented value is available.
 const audience=g=>audiences.get(g.key)??audiences.get(keyOf(g.name))??null;
 for(const g of all)g.audience=audience(g);
 // Preserve original sections for existing exclusion rules; rank all remaining national/extra channels together.
 const block=g=>g.section<1?g.section:g.key==="skyuno"?0.5:g.section===1?1:([6,7,8,9].includes(g.lcn)?2:SKY_MAIN.has(g.key)?3:4);
 const compare=(a,b)=>block(a)-block(b)||(block(a)>=3?((b.audience??-1)-(a.audience??-1)||((a.number||99999)-(b.number||99999))):((a.number||99999)-(b.number||99999)))||a.name.localeCompare(b.name,"it",{numeric:true})||a.key.localeCompare(b.key);
 for(const g of all)g.orderBlock=block(g);
 all.sort(compare);
 for(const [i,g] of all.entries())g.position=i;
 const used=new Set(),reserved=new Set(all.map(g=>g.lcn).filter(Boolean));let next=1000;
 for(const g of all){if(!g.number||used.has(g.number)||(!g.lcn&&reserved.has(g.number))){while(used.has(next)||reserved.has(next))next++;g.number=next++;}used.add(g.number);}
 // Preserve the section order, not the globally ascending LCN.
 const displayGroups=new Map();
 for(const g of all){const label=flat(g.name);if(!displayGroups.has(label))displayGroups.set(label,[]);displayGroups.get(label).push(g.name);}
 const displayConflicts=[...displayGroups.values()].filter(v=>v.length>1);
 const sameLogo=new Map();
 for(const g of all){if(!g.poster)continue;if(!sameLogo.has(g.poster))sameLogo.set(g.poster,[]);sameLogo.get(g.poster).push(g.name);}
 const sharedLogoGroups=[...sameLogo.values()].filter(v=>v.length>1);
 const priorityMissing=["rai3tgrpuglia","rai1","rai2","rai3","rete4","canale5","skyuno"].filter(k=>!all.some(g=>g.key===k)).map(k=>preferred.get(k)||k);
 const priorityDiagnostics=["rai3tgrpuglia","rai1","rai2","rai3","rete4","canale5","skyuno"].map(k=>{const g=all.find(x=>x.key===k),o=observed.get(k);return {name:preferred.get(k)||k,present:!!g,position:g?.position??null,alternatives:g?.entries.length??0,observedEntries:o?.entries??0,observedCollections:o?.sourceNames.size??0,excludedByRegion:o?.excludedRegion??0,reason:g?"present":!o?"not_found_in_loaded_collections":o.excludedRegion===o.entries?"regional_classification":"not_in_final_catalogue"};});
 return {groups:all,displayConflicts,sharedLogoGroups,priorityMissing,priorityDiagnostics,entries:all.map(g=>({...g.entries[0],number:g.number,displayName:g.name,brandLogo:g.poster})),alternatives:all.reduce((sum,g)=>sum+g.entries.length,0),mergedNames:all.map(g=>({name:g.name,variants:g.originalNames||[]})).filter(g=>g.variants.length>1),identityConflicts:[...ambiguousNames],excluded,regionalMissing:[...localMap.keys()].filter(k=>!groups.has(k))};
}
export async function loadGeo(previous={}){
 try{
  const base="https://iptv-org.github.io/api/";
  const get=async p=>{const r=await fetch(base+p,{signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error("metadata");return r.json();};
  const [channels,feeds,logos]=await Promise.all([get("channels.json"),get("feeds.json"),get("logos.json").catch(()=>null)]);
  const italian=new Map(channels.filter(c=>c.country==="IT").map(c=>[c.id,c]));
  const by=new Map(),out={};
  for(const f of feeds){if(!italian.has(f.channel))continue;
    const ar=f.broadcast_area||[];const isP=ar.some(x=>/^s\/IT-(?:75|BA|BT|BR|FG|LE|TA)$/i.test(x));
    const isLocal=ar.some(x=>/^s\/IT-|^ct\/IT/i.test(x)); const nat=ar.includes("c/IT")&&!isLocal;
    const k=isP?"puglia":isLocal?"other":nat?"national":null;
    if(!k)continue;
    out[f.channel+"@"+f.id]=k;
    const old=by.get(f.channel); if(!old||k==="national"||old==="other"&&k==="puglia")by.set(f.channel,k);
  }
  for(const [id,k] of by){const c=italian.get(id);out[id]=k;for(const n of [c.name,...(c.alt_names||[])])out[keyOf(n)]=k;}
  const identities={},ambiguous=new Set(),brands={},channelIds={};
  const logoBy=new Map();
  for(const l of logos||[]){
    if(!l.in_use||!italian.has(l.channel)||!/^https:\/\//i.test(l.url||"")||l.feed)continue;
    const tags=l.tags||[];
    const score=(tags.includes("color")?8:0)+(tags.includes("horizontal")?2:0)-(tags.includes("white")?8:0)+(l.format==="PNG"?3:l.format==="SVG"?2:0)+Math.min(Number(l.width)||0,1000)/1000;
    if(!logoBy.has(l.channel)||logoBy.get(l.channel).score<score)logoBy.set(l.channel,{url:l.url,score});
  }
  for(const [id,c] of italian){
    const k=keyOf(c.name);if(!k)continue;
    channelIds[id.toLowerCase()]=k;
    const logo=logoBy.get(id)?.url||previous.__brands?.[k]?.logo;
    if(logo)brands[k]={name:cleanName(c.name),logo};
    for(const n of [c.name,...(c.alt_names||[])]){
      const a=keyOf(n);if(!a||a===k||localMap.has(a)||lcnMap.has(a))continue;
      if(identities[a]&&identities[a]!==k)ambiguous.add(a);
      else identities[a]=k;
    }
  }
  for(const a of ambiguous)delete identities[a];
  out.__identities=identities;out.__brands=brands;out.__channelIds=channelIds;
  return out;
 }catch{return previous;}
}
