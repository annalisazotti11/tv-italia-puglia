const flat=s=>String(s||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/\b(?:2160|1080|720|576|480)[pi]\b|\b(?:full\s*hd|fhd|uhd|hd|sd|4k|8k)\b/gi,"").replace(/[^a-z0-9]/g,"");
const localMap=new Map([["Telenorba",10],["Teledue",12],["Telerama",15],["Tele Dehon",19],["Canale 7 Puglia",78],["Delta TV",83],["Teleregione Color",0],["Antenna Sud Extra",92],["7 Gold Puglia",84],["BTV",0],["La Nuova TV",0],["Telesveva",18],["Tele Sud Puglia",155],["TRC Puglia",76],["TeleMajg",79],["Teletrullo",80],["Easy TV",81],["Political TV",86],["Mediterranea TV - Video M Italia",89],["Canale 2 TV",90],["Amica 9",91],["Azzurra TV Italia",95],["StarTV",96],["Studio 100",98],["Tele Foggia",88],["Cittadella TV",94]].map(([n,v])=>[flat(n),v]));
const lcnMap=new Map([["Rai 1 HD",1],["Rai 2 HD",2],["Rai 3 HD",3],["Rai 3 TGR Puglia",103],["Rete 4 HD",4],["Canale 5 HD",5],["Italia 1 HD",6],["LA7 HD",7],["TV8",8],["NOVE",9],["Radionorba TV",11],["TG Norba 24",13],["Antenna Sud",14],["Telebari",17],["20 Mediaset HD",20],["Rai 4",21],["Iris",22],["Rai 5",23],["Rai Movie",24],["Cielo",26],["27 Twentyseven",27],["La5",30],["Real Time",31],["Food Network",33],["Cine34",34],["Focus",35],["RTL 102.5",36],["Rai News 24",48],["Sky TG24",50],["TGCOM24",51],["DMAX",52],["Rai Storia",54],["HGTV",56],["Radio 105 TV",66],["Deejay TV HD",69],["RadioItaliaTV",70],["Radio Kiss Kiss TV",158],["Gambero Rosso",257],["Hell's Kitchen Italy",404]].map(([n,v])=>[flat(n),v]));
for(const [k,v] of localMap)if(v)lcnMap.set(k,v);
const alias=new Map([["radioitaliatv","radioitaliatv"],["radioitalia","radioitaliatv"],["la7","la7"],["20mediaset","20mediaset"],["mediaset20","20mediaset"],["canale20","20mediaset"],["rai3puglia","rai3tgrpuglia"],["raitreregionepuglia","rai3tgrpuglia"],["tg3puglia","rai3tgrpuglia"],["raitreregionalepuglia","rai3tgrpuglia"],["telesud","telesudpuglia"],["telebari","telebari"],["tgnorba24","tgnorba24"]]);
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
 const all=[...groups.values()];
 for(const g of all){g.entries.sort(compareQuality);g.number=lcnMap.get(g.key)||g.number||0;}
 all.sort((a,b)=>(a.number||99999)-(b.number||99999)||a.name.localeCompare(b.name,"it",{numeric:true}));
 const used=new Set();let next=1000;
 for(const g of all){if(!g.number||used.has(g.number)){while(used.has(next))next++;g.number=next++;}used.add(g.number);}
 all.sort((a,b)=>a.number-b.number);
 return {groups:all,entries:all.map(g=>({...g.entries[0],number:g.number,displayName:g.name})),alternatives:all.reduce((sum,g)=>sum+g.entries.length,0)};
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
