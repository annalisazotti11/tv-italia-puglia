import PUGLIA_FALLBACK from "./puglia-fallback.mjs";
const flat=s=>String(s||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/\b(?:2160|1080|720|576|480)[pi]\b|\b(?:full\s*hd|fhd|uhd|hd|sd|4k|8k)\b/gi,"").replace(/[^a-z0-9]/g,"");
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
const keyOf=n=>alias.get(flat(n))||flat(n);
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
function reg(e,geo){
 const k=keyOf(e.name), group=e.info.match(/group-title="([^"]*)"/i)?.[1]||"";
 const labels=e.name+" "+group;
 if(geo[e.id]==="other"&&!puglia.test(labels))return "other";
 if(localMap.has(k)||puglia.test(labels)||k==="rai3tgrpuglia"||["radionorbatv","tgnorba24","antennasud","telebari"].includes(k))return "puglia";
 if(regions.test(labels)||/\b(?:regional|regionali|locali|local tv|regional dvb-t)\b/i.test(group))return geo[e.id]==="puglia"||geo[k]==="puglia"?"puglia":"other";
 return geo[e.id]||geo[k]||"national";
}
export function rankedCombine(state){
 const groups=new Map();
 const geo=state.geo||{};
 for(const list of Object.values(state.lists))for(const e of list){
  const key=keyOf(e.name); if(!key||reg(e,geo)==="other")continue;
  if(!groups.has(key))groups.set(key,{id:"tvic:"+encodeURIComponent(e.name.normalize("NFKC").trim().toLowerCase().replace(/\s+(?:fhd|uhd|hd|sd|4k|1080p|720p)$/i,"")),name:e.name,poster:e.logo,entries:[],regional:reg(e,geo)==="puglia",number:0,key});
  const g=groups.get(key); const index=g.entries.findIndex(x=>x.url===e.url);
  if(index<0)g.entries.push(e);else if(compareQuality(e,g.entries[index])<0)g.entries[index]=e;
  if(!g.poster&&e.logo)g.poster=e.logo;
  const l=Number(e.info.match(/(?:tvg-chno|tvg-lcn|channel-number|lcn)="(\d+)"/i)?.[1]||0);
  if(l>0&&(!g.number||l<g.number))g.number=l;
 }
 // Sorgenti singole di riserva solo per canali pugliesi non presenti nelle playlist.
 for(const e of PUGLIA_FALLBACK){
   const key=keyOf(e.name);
   if(!groups.has(key))groups.set(key,{id:"tvic:"+encodeURIComponent(e.name.normalize("NFKC").trim().toLowerCase()),name:e.name,poster:e.logo,entries:[e],regional:true,number:0,key});
 }
 const all=[...groups.values()];
 for(const g of all){
   g.entries.sort(compareQuality);
   const known=lcnMap.get(g.key)||0;
   const dtt=g.entries.some(e=>/\b(?:DTT|DVB-T2?|digitale terrestre)\b/i.test(e.info.match(/group-title="([^"]*)"/i)?.[1]||""));
   g.number=known||(g.regional||dtt?g.number:0);
   g.section=known>=1&&known<=5?0:g.regional?1:known||dtt?2:3;
 }
 // Ordine richiesto, indipendente dal numero LCN: 1–5, Puglia, DTT, extra.
 const compare=(a,b)=>a.section-b.section||(a.number||99999)-(b.number||99999)||a.name.localeCompare(b.name,"it",{numeric:true});
 all.sort(compare);
 const used=new Set();let next=1000;
 for(const g of all){if(!g.number||used.has(g.number)){while(used.has(next))next++;g.number=next++;}used.add(g.number);}
 // Preserve the section order, not the globally ascending LCN.

 return {groups:all,entries:all.map(g=>({...g.entries[0],number:g.number,displayName:g.name})),alternatives:all.reduce((sum,g)=>sum+g.entries.length,0),regionalMissing:[...localMap.keys()].filter(k=>!groups.has(k))};
}
export async function loadGeo(previous={}){
 try{
  const base="https://iptv-org.github.io/api/";
  const get=async p=>{const r=await fetch(base+p,{signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error("metadata");return r.json();};
  const [channels,feeds]=await Promise.all([get("channels.json"),get("feeds.json")]);
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
  return out;
 }catch{return previous;}
}
