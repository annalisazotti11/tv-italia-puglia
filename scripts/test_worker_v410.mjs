import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import worker from '../cloudflare/worker-tv-v4.1.0.js';

const now=new Date().toISOString();
const hls='https://raiuno3-live.akamaized.net/live/master.m3u8';
const bad='https://raidue3-live.akamaized.net/live/bad.m3u8';
const tgr='https://tgrpuglia-live.akamaized.net/hls/live/2025570/tgrpuglia/tgrpuglia/playlist.m3u8';
const tgrLogo='https://raw.githubusercontent.com/xN1ckuz/OpenIPTVItaly/refs/heads/main/Logos/819-rai3tgrpuglia.png';
const m3u='#EXTM3U\n'+
 '#EXTINF:-1 tvg-chno="103" tvg-logo="'+tgrLogo+'" group-title="TV Italia",Rai 3 TGR Puglia\n'+tgr+'\n'+
 '#EXTINF:-1 tvg-chno="1" group-title="TV Italia",Rai 1 HD\n'+hls+'\n'+
 '#EXTINF:-1 tvg-chno="2" group-title="TV Italia",Rai 2 HD\n'+bad+'\n';
const logo='https://cdn.jsdelivr.net/gh/Tundrak/IPTV-Italia/logos/tv2000.png';
const extra='#EXTM3U\n#EXTINF:-1 tvg-chno="28" tvg-logo="'+logo+'" group-title="TV Italia",TV2000\nhttps://hls-live-tv2000.akamaized.net/live/tv2000.m3u8\n';
const clock=Date.now();
const epg={schema:1,generated_at:now,summary:{monitored:5,with_epg:2,programme_count:4},sources:[{source:'Test XMLTV',ok:true}],
 channels:{'tvip_28_tv2000':{source:'Test XMLTV',programmes:[{start:new Date(clock-600000).toISOString(),stop:new Date(clock+1800000).toISOString(),title:'Programma verificato'},{start:new Date(clock+1800000).toISOString(),stop:new Date(clock+3600000).toISOString(),title:'Programma successivo'}]},
 'tvip_1_rai-1-hd':{source:'Test XMLTV',programmes:[
 {start:new Date(clock-600000).toISOString(),stop:new Date(clock+1800000).toISOString(),title:'Programma verificato'},
 {start:new Date(clock+1800000).toISOString(),stop:new Date(clock+3600000).toISOString(),title:'Programma successivo'}
 ]}}};
const page=readFileSync(new URL('../data/guide-ui.html',import.meta.url),'utf8');
const snapshot={schema:1,generated_at:now,channels:{
 'tvip_103_rai-3-tgr-puglia':{name:'Rai 3 TGR Puglia',number:'103',group:'Puglia',logo:tgrLogo,tested:1,verified:[{url:tgr,source:'Originale',kind:'HLS',height:408,last_ok:now}],regional_candidates:[]},
 'tvip_sky_sky_atlantic':{name:'Sky Atlantic',number:'',group:'Intrattenimento Sky',tested:0,verified:[],regional_candidates:[]},
 'tvip_45_boing-plus':{name:'Boing Plus',number:'45',group:'Digitale terrestre',tested:0,verified:[],regional_candidates:[]},
 'tvip_28_tv2000':{name:'TV2000',tested:1,verified:[{url:'https://hls-live-tv2000.akamaized.net/live/tv2000.m3u8',source:'Additional',kind:'HLS',height:720,last_ok:now}],regional_candidates:[]},
 'tvip_1_rai-1-hd':{name:'Rai 1 HD',tested:1,verified:[],regional_candidates:[{url:hls,source:'Playlist originale',reason:'HTTP 403'}]},
 'tvip_2_rai-2-hd':{name:'Rai 2 HD',tested:1,verified:[],regional_candidates:[{url:bad,source:'Playlist originale',reason:'HTTP 403'}]}
},summary:{visible:0,hidden:2}};
const manifest='#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1280x720\nmedia.m3u8\n';
const media='#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6,\nsegment.ts\n';
let probeCount=0;
globalThis.fetch=async (input)=>{
 const url=String(input);
 if(url.includes('TV_Italia_Puglia_con_loghi.m3u'))return new Response(m3u,{status:200});
 if(url.includes('/data/verified-streams.json'))return Response.json(snapshot);
 if(url.includes('/data/epg-guide.json'))return Response.json(epg);
 if(url.includes('/data/guide-ui.html'))return new Response(page,{status:200});
 if(url.includes('/data/additional-channels.m3u'))return new Response(extra,{status:200});
 if(url===tgr)return new Response(manifest,{status:200,headers:{'Content-Type':'application/vnd.apple.mpegurl'}});
 if(url===tgrLogo){const bytes=new Uint8Array(220);bytes[0]=137;bytes[1]=80;bytes[2]=78;bytes[3]=71;bytes[25]=6;return new Response(bytes,{status:200,headers:{'Content-Type':'image/png'}});}
 if(url===hls){probeCount++;return new Response(manifest,{status:200,headers:{'Content-Type':'application/vnd.apple.mpegurl'}});}
 if(url==='https://raiuno3-live.akamaized.net/live/media.m3u8')return new Response(media,{status:200});
 if(url==='https://raiuno3-live.akamaized.net/live/segment.ts')return new Response(new Uint8Array(188).fill(71),{status:200,headers:{'Content-Type':'video/mp2t'}});
 if(url===bad)return new Response('blocked',{status:403});
 throw new Error('Unexpected fetch '+url);
};
const request=(path,country)=>{
 const r=new Request('https://unit.example'+path);
 Object.defineProperty(r,'cf',{value:{country}});
 return r;
};
let diagnostic=await worker.fetch(request('/debug/notte.json','IT'));
assert.equal(diagnostic.status,200);
const report=await diagnostic.json();
assert.equal(report.monitored,6);
assert.equal(report.hidden,4);
assert.equal(report.channels.find(x=>x.id==='tvip_103_rai-3-tgr-puglia').visible,true);
assert.equal(report.channels.find(x=>x.name==='Sky Atlantic').visible,false);
assert.equal(report.channels.find(x=>x.name==='Boing Plus').visible,false);
let pageResp=await worker.fetch(request('/guida','IT'));
assert.equal(pageResp.status,200);
let pageText=await pageResp.text();
assert.ok(pageText.includes('Programma verificato'),'Real now-playing programme in web UI');
assert.ok(pageText.includes('Programma successivo'),'Next programme in web UI');
assert.ok(pageText.includes('LIVE'));
assert.ok(pageText.indexOf('Rai 3 TGR Puglia')<pageText.indexOf('TV2000'),'TGR Puglia must be first');
assert.ok(pageText.includes('id="search"'),'Search input included');
assert.ok(pageText.includes('id="group"'),'Category selector included');
assert.ok(pageText.includes('tv2000.png'),'Channel artwork included');
let epgResp=await worker.fetch(request('/api/guida.json','IT'));
assert.equal(epgResp.status,200);
let api=await epgResp.json();
assert.equal(api.channels.find(c=>c.name==='TV2000').current.title,'Programma verificato');
assert.equal(api.channels.find(c=>c.name==='Sky Atlantic'),undefined);
let meta=await worker.fetch(request('/meta/tv/tvip_28_tv2000.json','IT'));
let m=(await meta.json()).meta;
assert.equal(m.logo,logo);
assert.ok(m.description.includes('ORA IN ONDA'));
assert.ok(m.description.includes('A seguire'));
let poster=await worker.fetch(request('/poster-v410/tvip_28_tv2000.svg','IT'));
assert.equal(poster.status,200);
assert.ok((await poster.text()).includes('LIVE'));
const regionPoster=await worker.fetch(request('/poster-v410/tvip_103_rai-3-tgr-puglia.svg','IT'));
const regionSvg=await regionPoster.text();
assert.equal(regionPoster.status,200);
assert.ok(regionSvg.includes('TGR PUGLIA'));
assert.ok(regionSvg.includes('url(#removeWhite)'));
assert.ok(!regionSvg.includes('x="26" y="182" width="348" height="212"'),'No giant white logo backplate');
const regionMeta=await worker.fetch(request('/meta/tv/tvip_103_rai-3-tgr-puglia.json','IT'));
const regionalMetadata=(await regionMeta.json()).meta;
assert.equal(regionalMetadata.id,'tvip_103_rai-3-tgr-puglia');
assert.ok(regionalMetadata.description.includes('Edizione regionale'));
assert.ok(regionalMetadata.poster.includes('poster-v410'));
const catalog='/catalog/tv/tv-italia-puglia.json';
let res=await worker.fetch(request(catalog,'DE'));
assert.equal(res.status,200);
assert.deepEqual((await res.json()).metas.map(x=>x.name),['Rai 3 TGR Puglia','TV2000'],'TGR Puglia first and regional original ID stable');
res=await worker.fetch(request(catalog,'IT'));
assert.equal(res.status,200);
assert.deepEqual((await res.json()).metas.map(x=>x.name),['Rai 3 TGR Puglia','Rai 1 HD','TV2000'],'Prioritize TGR Puglia and keep other TV channels');
assert.equal(probeCount,1);
res=await worker.fetch(request('/debug/italia.json','IT'));
let state=await res.json();
assert.deepEqual(state.recovered,['Rai 1 HD']);
assert.equal(state.regionalTested,2);
res=await worker.fetch(request('/stream/tv/tvip_1_rai-1-hd.json','IT'));
assert.equal(res.status,200);
let stream=await res.json();
assert.ok(stream.streams[0].description.includes('Programma verificato'));
assert.equal(stream.streams.length,1);
assert.equal(stream.streams[0].url,hls);
res=await worker.fetch(request('/stream/tv/tvip_2_rai-2-hd.json','IT'));
assert.equal((await res.json()).streams.length,0);
console.log('4.1.0 tests passed: TGR Puglia first, dark clean posters, no white backplates, EPG and original IDs.');
