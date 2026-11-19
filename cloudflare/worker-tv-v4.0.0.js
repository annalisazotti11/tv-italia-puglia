// TV Italia + Puglia 4.0.0 — channel logos, real XMLTV EPG, now/next and accessible live TV guide.
// The original M3U is used exclusively for names, logos and ordering.
// URLs are read only from the GitHub Actions verified snapshot.
const VERSION='4.0.0';
const REPO='https://raw.githubusercontent.com/annalisazotti11/tv-italia-puglia/refs/heads/main';
const CATALOG_ID='tv-italia-puglia';
const CORS={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'GET,HEAD,OPTIONS'};
const MANIFEST={id:'community.tv-italia-puglia',version:VERSION,name:'TV Italia + Puglia',description:'Dirette verificate dalla scansione notturna; canali non verificati nascosti.',resources:['catalog','meta','stream'],types:['tv'],idPrefixes:['tvip_'],catalogs:[{id:CATALOG_ID,type:'tv',name:'TV Italia + Puglia · Canali TV'}]};
const MAX_AGE=36*60*60*1000;
const cache={};

function json(data,status=200,age=0){return new Response(JSON.stringify(data),{status,headers:{...CORS,'Content-Type':'application/json; charset=utf-8','Cache-Control':age?`public, max-age=${age}`:'no-store'}});}
function slug(s){return String(s??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim().replace(/\s+/g,'-')||'canale';}
function attributes(s){return Object.fromEntries([...s.matchAll(/([\w-]+)="([^"]*)"/g)].map(m=>[m[1],m[2]]));}
function xml(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));}
function safeUrl(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password&&!u.search&&!u.hash&&!u.port&&!/^\d+(?:\.\d+){3}$|^\[|(?:^|\.)(?:localhost|local|internal)$/.test(u.hostname)}catch{return false;}}
function order(c){const n=Number(c.number);return n===103?3.5:n>0?n:99999;}
function parseChannels(text){
  if(!text.trimStart().startsWith('#EXTM3U'))throw Error('Playlist non valida');
  const found=new Map();
  for(const line of text.split(/\r?\n/)){
    if(!line.startsWith('#EXTINF:'))continue;
    const a=attributes(line),comma=line.indexOf(',');
    if(comma<0)continue;
    const name=line.slice(comma+1).trim(),number=a['tvg-chno']||'',id=`tvip_${number||slug(name)}_${slug(name)}`;
    if(!found.has(id))found.set(id,{id,name,number,group:a['group-title']||'TV Italia',logo:a['tvg-logo']||''});
  }
  return [...found.values()].sort((a,b)=>order(a)-order(b)||a.name.localeCompare(b.name,'it'));
}
async function readCached(key,path,parse,ttl){
  let slot=cache[key]||(cache[key]={value:null,until:0,pending:null});
  if(slot.value&&Date.now()<slot.until)return slot.value;
  if(slot.pending)return slot.pending;
  slot.pending=(async()=>{
    try{
      const url=REPO+path+`?revision=${VERSION}-${Date.now()}`;
      const response=await fetch(url,{redirect:'manual'});
      if(!response.ok){slot.error=`HTTP ${response.status}`;throw Error('Archivio non disponibile');}
      const text=await response.text();if(text.length>1600000)throw Error('Archivio troppo grande');
      slot.value=parse(text);slot.error=null;slot.until=Date.now()+ttl;return slot.value;
    }catch(e){slot.error=slot.error||e.name||'Error';slot.until=Date.now()+30000;return slot.value;}
  })();
  try{return await slot.pending;}finally{slot.pending=null;}
}
async function channels(){return (await readCached('channels','/TV_Italia_Puglia_con_loghi.m3u',parseChannels,300000))||[];}
async function additionalChannels(){return (await readCached('extra','/data/additional-channels.m3u',parseChannels,300000))||[];}
async function snapshot(){return await readCached('snapshot','/data/verified-streams.json',text=>{const data=JSON.parse(text);if(data.schema!==1||!data.channels||!Number.isFinite(Date.parse(data.generated_at)))throw Error('Snapshot non valido');return data;},120000);}
async function epgGuide(){return await readCached('epg','/data/epg-guide.json',text=>{const data=JSON.parse(text);if(data.schema!==1||!data.channels||!Number.isFinite(Date.parse(data.generated_at)))throw Error('Guida TV non valida');return data;},600000);}
function eligible(snap,id){
  if(!snap||Date.now()-Date.parse(snap.generated_at)>MAX_AGE)return [];
  return (Array.isArray(snap.channels[id]?.verified)?snap.channels[id].verified:[]).filter(s=>safeUrl(s.url)&&Number.isFinite(Date.parse(s.last_ok))&&Date.now()-Date.parse(s.last_ok)<=MAX_AGE).slice(0,5);
}
function poster(c,origin){return 'https://wsrv.nl/?url='+encodeURIComponent(origin+'/poster-v400/'+encodeURIComponent(c.id)+'.svg')+'&w=360&h=540&fit=cover&output=png&v=400';}
function safeLogo(value){
  try{
    if(!safeUrl(value))return false;
    const host=new URL(value).hostname;
    return ['raw.githubusercontent.com','cdn.jsdelivr.net','i.imgur.com','upload.wikimedia.org','images.iptv-org.github.io'].includes(host)&&/\.(png|jpe?g|webp)$/i.test(new URL(value).pathname);
  }catch{return false;}
}
function channelLogo(c,snap){
  const original=c.logo||'',extra=snap?.channels?.[c.id]?.logo||'';
  return safeLogo(original)?original:safeLogo(extra)?extra:'';
}
function groupType(c){
  const n=(c.name||'').toLowerCase(),g=(c.group||'').toLowerCase();
  if(g.includes('puglia')||/\b(puglia|norba|telebari|telerama|antenna sud|teledue)\b/.test(n))return 'puglia';
  if(g.includes('news')||g.includes('informaz')||/\b(tg24|tgcom|rainews|cnbc|bloomberg|euronews|france 24|al jazeera|sky news|camera dei deputati|senato tv)\b/.test(n))return 'news';
  if(g.includes('sport')||/\b(sportitalia|eurosport|supertennis|moto ?gp|sky sport|dazn|sport)\b/.test(n))return 'sport';
  if(g.includes('radio')||/\b(radio|rtl|deejay|kiss kiss|m2o)\b/.test(n))return 'radio';
  if(g.includes('tv italia')||g.includes('rai')||g.includes('mediaset')||g.includes('discovery'))return 'nazionali';
  return 'altro';
}
const ACCENTS={puglia:'#3ad3ba',news:'#6eaaf9',sport:'#6be2a2',radio:'#f4be78',nazionali:'#ac9cf6',altro:'#a8bbd9'};
function guideProgramme(guide,id,now=Date.now()){
  if(!guide||!Number.isFinite(Date.parse(guide.generated_at))||now-Date.parse(guide.generated_at)>48*3600000)
    return {current:null,next:null,progress:0};
  const rows=guide.channels?.[id]?.programmes;
  if(!Array.isArray(rows))return {current:null,next:null,progress:0};
  let current=null,next=null;
  for(const p of rows){
    const start=Date.parse(p.start),end=Date.parse(p.stop);
    if(!Number.isFinite(start)||!Number.isFinite(end)||start>=end)continue;
    if(start<=now&&now<end){current=p;continue;}
    if(start>now&&(!next||start<Date.parse(next.start)))next=p;
  }
  const progress=current?Math.max(0,Math.min(100,Math.round(100*(now-Date.parse(current.start))/(Date.parse(current.stop)-Date.parse(current.start))))):0;
  return {current,next,progress};
}
function hhmm(date){
  try{return new Intl.DateTimeFormat('it-IT',{timeZone:'Europe/Rome',hour:'2-digit',minute:'2-digit'}).format(new Date(date));}
  catch{return '';}
}
function preview(c,origin,guide,snap){
  const epg=guideProgramme(guide,c.id),logo=channelLogo(c,snap);
  const details=[c.number?'Canale '+(Number(c.number)===103?'3 Puglia':c.number)+' · '+(c.group||'TV'):c.group||'TV'];
  if(epg.current){
    details.unshift('ORA IN ONDA · '+hhmm(epg.current.start)+'–'+hhmm(epg.current.stop)+' · '+epg.current.title);
    if(epg.next)details.push('A seguire · '+hhmm(epg.next.start)+' · '+epg.next.title);
  }else{
    details.unshift('Diretta disponibile');
    if(epg.next)details.push('In programma · '+hhmm(epg.next.start)+' · '+epg.next.title);
    else details.push('Programmazione non disponibile');
  }
  return {id:c.id,type:'tv',name:c.name,poster:poster(c,origin),posterShape:'poster',
    description:details.join('\n'),...(logo?{logo}:{}),behaviorHints:{isLive:true}};
}
function b64(bytes){let out='';for(let i=0;i<bytes.length;i+=30000)out+=String.fromCharCode(...bytes.subarray(i,i+30000));return btoa(out);}
async function posterSvg(c){
  const palette=ACCENTS[groupType(c)]||ACCENTS.altro;
  let embedded='';
  if(safeLogo(c.logo)){
    try{
      const r=await fetch(c.logo,{redirect:'manual'});
      const mime=(r.headers.get('content-type')||'').split(';')[0].toLowerCase();
      if(r.ok&&['image/png','image/jpeg','image/webp'].includes(mime)){
        const bytes=new Uint8Array(await r.arrayBuffer());
        if(bytes.length>100&&bytes.length<400000)embedded='data:'+mime+';base64,'+b64(bytes);
      }
    }catch{}
  }
  const title=c.name.length>32?c.name.slice(0,31)+'…':c.name;
  const number=c.number&&(Number(c.number)===103?'3':c.number)||'TV';
  const center=embedded
    ?'<rect x="26" y="182" width="348" height="212" rx="22" fill="#ffffff"/><image href="'+embedded+'" x="51" y="210" width="298" height="155" preserveAspectRatio="xMidYMid meet"/>'
    :'<rect x="26" y="182" width="348" height="212" rx="22" fill="#ffffff" fill-opacity=".075" stroke="#a7bdd9" stroke-opacity=".14"/><text x="200" y="298" text-anchor="middle" fill="#ffffff" font-family="Arial,sans-serif" font-size="'+(c.name.length>18?29:38)+'" font-weight="bold">'+xml(c.name.length>21?c.name.slice(0,20)+'…':c.name)+'</text>';
  return '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="600" viewBox="0 0 400 600">'+
    '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#202e48"/><stop offset=".62" stop-color="#121829"/><stop offset="1" stop-color="#090e1b"/></linearGradient><radialGradient id="glow"><stop stop-color="'+palette+'" stop-opacity=".27"/><stop offset="1" stop-color="'+palette+'" stop-opacity="0"/></radialGradient></defs>'+
    '<rect width="400" height="600" rx="22" fill="url(#bg)"/><ellipse cx="180" cy="226" rx="260" ry="266" fill="url(#glow)"/><rect x="16" y="16" width="368" height="568" rx="19" fill="none" stroke="'+palette+'" stroke-opacity=".35" stroke-width="2"/>'+
    '<rect x="27" y="32" width="9" height="65" rx="4" fill="'+palette+'"/><text x="52" y="98" font-family="Arial,sans-serif" font-size="70" font-weight="800" fill="#f5f7ff">'+xml(String(number))+'</text>'+
    '<rect x="266" y="48" width="101" height="29" rx="8" fill="#13684a"/><circle cx="283" cy="62" r="5" fill="#9dfacf"/><text x="296" y="68" fill="#f4fff8" font-family="Arial,sans-serif" font-size="15" font-weight="bold">LIVE</text>'+
    center+'<path d="M29 423H371" stroke="#8798b4" stroke-opacity=".25"/>'+
    '<text x="200" y="486" text-anchor="middle" font-family="Arial,sans-serif" font-size="'+(title.length>22?22:title.length>16?26:32)+'" font-weight="bold" fill="#ffffff">'+xml(title)+'</text>'+
    '<text x="200" y="542" text-anchor="middle" font-family="Arial,sans-serif" font-size="16" font-weight="bold" fill="'+palette+'">'+xml((c.group||'TV ITALIA').toUpperCase().slice(0,30))+'</text></svg>';
}

async function manifestAvailable(entry){
  try{
    let address=entry.url,r;const originalHost=new URL(address).hostname;
    for(let hop=0;hop<3;hop++){
      r=await fetch(address,{redirect:'manual',headers:{Accept:'application/vnd.apple.mpegurl,application/dash+xml,*/*',Range:'bytes=0-65535'}});
      if(![301,302,303,307,308].includes(r.status))break;
      const location=r.headers.get('location');if(!location||hop===2)return {ok:false,reason:`HTTP ${r.status}`};
      const next=new URL(location,address),h=next.hostname;
      const sameProvider=h===originalHost||(originalHost==='router.xdevel.com'&&/^stream\d*\.xdevel\.com$/.test(h))||(['dd782ed59e2a4e86aabf6fc508674b59.msvdn.net','4c4b867c89244861ac216426883d1ad0.msvdn.net','018e1901ad234f04ae16388eda6778e5.msvdn.net','db142859fd5541b09de25d6507f1f2d3.msvdn.net','b53136fc0d724da78cac7754d601393d.msvdn.net','f5842579ff984c1c98d63b8d789673eb.msvdn.net'].includes(originalHost)&&h.endsWith('.msvdn.net'));
      if(!sameProvider||!safeUrl(next.href))return {ok:false,reason:'Reindirizzamento non consentito'};
      address=next.href;
    }
    if(!r.ok||!r.body)return {ok:false,reason:`HTTP ${r.status}`};
    const reader=r.body.getReader(),decoder=new TextDecoder();let body='',length=0;
    try{while(length<65536){const {value,done}=await reader.read();if(done)break;length+=value.length;body+=decoder.decode(value,{stream:true});}}finally{await reader.cancel();}
    const ok=entry.kind==='HLS'?body.trimStart().startsWith('#EXTM3U')&&/#EXT-X-(?:STREAM-INF|TARGETDURATION|MEDIA|INF)/.test(body)&&!/#EXT-X-SESSION-KEY|#EXT-X-KEY:(?![^\r\n]*METHOD=NONE)/.test(body):entry.kind==='DASH'&&/<MPD[\s>]/i.test(body)&&!/<ContentProtection\b/i.test(body);
    return {ok,reason:ok?'ok':'Manifesto non valido o protetto'};
  }catch(e){return {ok:false,reason:e.name||'Error'};}
}

// Only requests arriving from Italy attempt an extra check for geo-inconclusive
// official/free-to-air streams. A 403 on GitHub is never counted as working.
const regionalMemo={key:'',until:0,pending:null,found:new Map(),tested:0,reason:''};
const MAX_REGIONAL_CHANNELS=14; // max 3 subrequests each, plus 2 GitHub snapshot reads
async function regionalFetch(url,limit=65536){
  if(!safeUrl(url))return {ok:false,reason:'URL non consentito'};
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),2800);
  try{
    const r=await fetch(url,{redirect:'manual',signal:controller.signal,headers:{Range:'bytes=0-'+(limit-1),Accept:'application/vnd.apple.mpegurl,application/dash+xml,video/mp2t,*/*'}});
    if(!r.ok||!r.body)return {ok:false,reason:'HTTP '+r.status};
    const reader=r.body.getReader(),parts=[];let size=0;
    try{
      while(size<limit){
        const {value,done}=await reader.read();if(done)break;
        const bytes=value.subarray(0,limit-size);parts.push(bytes);size+=bytes.length;
      }
    }finally{await reader.cancel();}
    const result=new Uint8Array(size);let offset=0;
    for(const bytes of parts){result.set(bytes,offset);offset+=bytes.length;}
    return {ok:true,bytes:result,type:(r.headers.get('content-type')||'').toLowerCase()};
  }catch(e){return {ok:false,reason:e.name||'Error'};}
  finally{clearTimeout(timer);}
}
function regionalChild(base,line){
  try{
    const child=new URL(line,base),origin=new URL(base);
    return child.origin===origin.origin&&safeUrl(child.href)?child.href:null;
  }catch{return null;}
}
function firstMediaPath(text){
  const rows=text.split(/\r?\n/);
  for(let i=0;i<rows.length-1;i++){
    if(!rows[i].startsWith('#EXTINF'))continue;
    for(let j=i+1;j<rows.length;j++){
      const line=rows[j].trim();
      if(line&&!line.startsWith('#'))return line;
    }
  }
  return null;
}
async function regionPlayable(entry){
  const root=await regionalFetch(entry.url);
  if(!root.ok)return {ok:false,reason:root.reason};
  if(root.type.includes('text/html'))return {ok:false,reason:'HTML anziché video'};
  let text=new TextDecoder().decode(root.bytes).trimStart();
  if(!text.startsWith('#EXTM3U')||!/#EXT-X-(?:STREAM-INF|TARGETDURATION|MEDIA|INF)\b/.test(text))
    return {ok:false,reason:'Manifest HLS assente'};
  if(/#EXT-X-SESSION-KEY|#EXT-X-KEY:(?![^\r\n]*METHOD=NONE)/.test(text))
    return {ok:false,reason:'Contenuto protetto'};
  let base=entry.url;
  if(/#EXT-X-STREAM-INF/.test(text)){
    const rows=text.split(/\r?\n/);let variant=null;
    for(let i=0;i<rows.length;i++)if(rows[i].startsWith('#EXT-X-STREAM-INF')){
      for(let j=i+1;j<rows.length;j++){
        const line=rows[j].trim();
        if(line&&!line.startsWith('#')){variant=regionalChild(base,line);break;}
      }
      if(variant)break;
    }
    if(!variant)return {ok:false,reason:'Variante non accessibile'};
    const second=await regionalFetch(variant);
    if(!second.ok)return {ok:false,reason:second.reason};
    text=new TextDecoder().decode(second.bytes).trimStart();
    base=variant;
  }
  if(!text.startsWith('#EXTM3U')||/#EXT-X-KEY:(?![^\r\n]*METHOD=NONE)/.test(text))
    return {ok:false,reason:'Playlist video non valida'};
  const fragment=firstMediaPath(text);
  if(!fragment)return {ok:false,reason:'Segmento video mancante'};
  const segment=regionalChild(base,fragment);
  if(!segment)return {ok:false,reason:'Segmento su host diverso o non consentito'};
  const sample=await regionalFetch(segment,2048);
  if(!sample.ok)return {ok:false,reason:sample.reason};
  const head=new TextDecoder().decode(sample.bytes.subarray(0,100)).trimStart().toLowerCase();
  if(sample.bytes.length<64||head.startsWith('<html')||head.startsWith('<!doctype')||head.startsWith('{"error"'))
    return {ok:false,reason:'Segmento non riproducibile'};
  return {ok:true,reason:'Manifest e segmento verificati'};
}
async function regionalChecks(request,all,snap,onlyChannelId=null){
  const country=request.cf&&request.cf.country;
  if(country!=='IT'||!snap||Date.now()-Date.parse(snap.generated_at)>MAX_AGE)
    return {found:new Map(),tested:0,reason:country==='IT'?'Dati notturni scaduti':'Controllo disponibile soltanto da connessione italiana'};
  const key=snap.generated_at+'-IT-'+(onlyChannelId||'catalog');
  if(regionalMemo.key===key&&Date.now()<regionalMemo.until)
    return {found:regionalMemo.found,tested:regionalMemo.tested,reason:regionalMemo.reason};
  if(regionalMemo.key===key&&regionalMemo.pending)return regionalMemo.pending;
  regionalMemo.key=key;
  regionalMemo.pending=(async()=>{
    const options=all.filter(c=>(!onlyChannelId||c.id===onlyChannelId)&&!eligible(snap,c.id).length&&Array.isArray(snap.channels[c.id]?.regional_candidates)&&snap.channels[c.id].regional_candidates.length)
      .map(c=>({channel:c,source:snap.channels[c.id].regional_candidates[0]}))
      .filter(x=>safeUrl(x.source.url)&&x.source.url.endsWith('.m3u8'))
      .slice(0,MAX_REGIONAL_CHANNELS);
    const checks=await Promise.all(options.map(async x=>({x,result:await regionPlayable(x.source)})));
    const found=new Map();
    for(const {x,result} of checks)if(result.ok)
      found.set(x.channel.id,{...x.source,url:x.source.url,kind:'HLS',height:0,regional:true});
    regionalMemo.found=found;regionalMemo.tested=checks.length;
    regionalMemo.reason=checks.length?'Rivalutati manifest e segmenti dal nodo Cloudflare':'Nessuna sorgente HLS idonea';
    regionalMemo.until=Date.now()+300000;
    return {found,tested:checks.length,reason:regionalMemo.reason};
  })();
  try{return await regionalMemo.pending;}
  finally{regionalMemo.pending=null;}
}

function guideCard(c,guide,snap){
  const e=guideProgramme(guide,c.id),logo=channelLogo(c,snap),cat=groupType(c);
  const ac=ACCENTS[cat]||ACCENTS.altro,number=c.number?(Number(c.number)===103?'3':c.number):'TV';
  const image=logo?'<img src="'+xml(logo)+'" alt="" loading="lazy" decoding="async"/>':'<b>'+xml(String(number))+'</b>';
  const title=e.current?e.current.title:'Guida TV non disponibile';
  const dates=e.current?hhmm(e.current.start)+' – '+hhmm(e.current.stop):'Diretta disponibile';
  const next=e.next?'<span class="kicker">A seguire · '+xml(hhmm(e.next.start))+'</span><strong>'+xml(e.next.title)+'</strong>':'<span class="unknown">Prossimo programma non disponibile</span>';
  const searching=(c.name+' '+(c.group||'')+' '+title+' '+(e.next?.title||'')).toLocaleLowerCase('it');
  return '<article class="channel" data-search="'+xml(searching)+'" data-group="'+cat+'" style="--accent:'+ac+'">'+
    '<div class="head"><div class="logo">'+image+'</div><div><div class="channel-name">'+xml(c.name)+'</div><div class="channel-meta">'+
    xml(number==='TV'?'TV':('Canale '+number))+' · '+xml(c.group||'TV Italia')+'</div></div><span class="badge-live">LIVE</span></div>'+
    '<section class="program"><div class="kicker">'+(e.current?'Ora in onda':'Diretta TV')+'</div><h2>'+xml(title)+'</h2><div class="time">'+xml(dates)+'</div>'+
    '<div class="track" role="progressbar" aria-label="Avanzamento del programma" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+e.progress+'"><span style="width:'+e.progress+'%"></span></div>'+
    '<div class="next">'+next+'</div></section></article>';
}
async function htmlGuide(all,visible,guide,snap){
  const template=await readCached('ui','/data/guide-ui.html',x=>x,3600000);
  if(!template||!template.includes('<!-- CHANNELS -->'))
    return new Response('<!doctype html><meta charset="utf-8"><h1>Guida TV temporaneamente non disponibile</h1><a href="/manifest.json">Apri il manifest</a>',
      {status:503,headers:{...CORS,'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'}});
  const nowEp=visible.reduce((n,c)=>n+Number(!!guideProgramme(guide,c.id).current),0);
  const checked=snap?.generated_at?hhmm(snap.generated_at)+' del '+new Intl.DateTimeFormat('it-IT',{timeZone:'Europe/Rome',day:'2-digit',month:'2-digit',year:'numeric'}).format(new Date(snap.generated_at)):'non disponibile';
  const html=template.replace('<!-- CHANNELS -->',visible.map(c=>guideCard(c,guide,snap)).join(''))
    .replace('<!-- VISIBLE_COUNT -->',String(visible.length))
    .replace('<!-- EPG_COUNT -->',String(nowEp))
    .replace('<!-- MONITORED_COUNT -->',String(all.length))
    .replace('<!-- LAST_CHECK -->',xml(checked));
  return new Response(html,{headers:{...CORS,'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
}

export default {
  async scheduled(){},
  async fetch(request){
    if(request.method==='OPTIONS')return new Response(null,{status:204,headers:CORS});
    if(!['GET','HEAD'].includes(request.method))return json({error:'Metodo non consentito'},405);
    const u=new URL(request.url),path=u.pathname;
    try{
      if(path==='/manifest.json')return json(MANIFEST,200,60);
      // The same source produces Nuvio metadata and the separate web guide.
      const [original,additional,snap,guide]=await Promise.all([channels(),additionalChannels(),snapshot(),epgGuide()]);
      const existingNumbers=new Set(original.map(c=>c.number).filter(Boolean));
      const all=[...original,...additional.filter(c=>!c.number||!existingNumbers.has(c.number))];
      const included=new Set(all.map(c=>c.id));
      // Keep every monitored channel in diagnostic data, including currently
      // unavailable premium channels. Posters still require a verified stream.
      for(const [id,item] of Object.entries(snap?.channels||{})){
        if(!included.has(id)&&id.startsWith('tvip_')){
          all.push({id,name:item.name||id,number:item.number||'',group:item.group||'Canali TV',logo:safeLogo(item.logo)?item.logo:''});
          included.add(id);
        }
      }
      for(const c of all)if(!safeLogo(c.logo))c.logo=channelLogo(c,snap);
      const regionNeeded=path.startsWith('/catalog/tv/')||path.startsWith('/stream/tv/')||path==='/debug/italia.json';
      const streamId=path.match(/^\/stream\/tv\/([^/]+)\.json$/);
      const regional=regionNeeded?await regionalChecks(request,all,snap,streamId?decodeURIComponent(streamId[1]):null):{found:new Map(),tested:0,reason:'Non richiesto'};
      const visible=all.filter(c=>eligible(snap,c.id).length||regional.found.has(c.id));
      if(path==='/'||path==='/guida'||path==='/guida-tv')return htmlGuide(all,visible,guide,snap);
      if(path==='/api/guida.json')return json({version:VERSION,generatedAt:guide?.generated_at||null,summary:guide?.summary||null,
        channels:visible.map(c=>({id:c.id,name:c.name,group:c.group||'',logo:channelLogo(c,snap),...guideProgramme(guide,c.id)}))},200,60);
      if(path==='/debug/italia.json')return json({version:VERSION,country:request.cf?.country||null,nightlyGeneratedAt:snap?.generated_at||null,regionalTested:regional.tested,recovered:[...regional.found.keys()].map(id=>all.find(c=>c.id===id)?.name||id),reason:regional.reason});
      if(path==='/debug/notte.json'||path==='/debug/channels.json')return json({version:VERSION,active:!!snap,generatedAt:snap?.generated_at||null,summary:snap?.summary||null,epg:{generatedAt:guide?.generated_at||null,summary:guide?.summary||null,sourceStatus:guide?.sources||[]},monitored:all.length,visible:visible.length,hidden:all.length-visible.length,archiveStatus:{channels:cache.channels?.error||'ok',additional:cache.extra?.error||'ok',snapshot:cache.snapshot?.error||'ok'},channels:all.map(c=>({id:c.id,name:c.name,visible:eligible(snap,c.id).length>0,verified:eligible(snap,c.id).length,tested:snap?.channels[c.id]?.tested||0}))});
      const catalog=path.match(/^\/catalog\/tv\/([^/]+)(?:\/[^/]+)?\.json$/);
      if(catalog)return json({metas:decodeURIComponent(catalog[1])===CATALOG_ID?visible.map(c=>preview(c,u.origin,guide,snap)):[]},200,60);
      const posterRoute=path.match(/^\/poster(?:-v\d+)?\/([^/]+)\.svg$/);
      if(posterRoute){const c=all.find(x=>x.id===decodeURIComponent(posterRoute[1]));if(!c)return json({error:'Canale non trovato'},404);return new Response(await posterSvg(c),{headers:{...CORS,'Content-Type':'image/svg+xml; charset=utf-8','Cache-Control':'public, max-age=86400'}});}
      const meta=path.match(/^\/meta\/tv\/([^/]+)\.json$/);
      if(meta){const c=all.find(x=>x.id===decodeURIComponent(meta[1]));return c?json({meta:preview(c,u.origin,guide,snap)}):json({meta:null},404);}
      const stream=path.match(/^\/stream\/tv\/([^/]+)\.json$/);
      if(stream){const id=decodeURIComponent(stream[1]),choices=eligible(snap,id);if(regional.found.has(id))choices.push(regional.found.get(id));const checked=await Promise.all(choices.map(manifestAvailable));const chosen=choices.find((_,i)=>checked[i].ok);return json({streams:chosen?[{name:'Diretta',description:chosen.kind+' · '+(chosen.height||'?')+'p · Stream verificato'+(guideProgramme(guide,id).current?' · In onda: '+guideProgramme(guide,id).current.title:''),url:chosen.url,behaviorHints:{notWebReady:true}}]:[],cacheMaxAge:0,checks:checked.map(x=>x.reason)});}
      return json({error:'Percorso non trovato'},404);
    }catch{return json({error:'Servizio temporaneamente non disponibile'},503);}
  }
};
