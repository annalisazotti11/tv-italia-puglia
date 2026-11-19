import assert from 'node:assert/strict';
import worker from '../cloudflare/worker-tv-v3.9.0.js';

const now=new Date().toISOString();
const hls='https://raiuno3-live.akamaized.net/live/master.m3u8';
const bad='https://raidue3-live.akamaized.net/live/bad.m3u8';
const m3u='#EXTM3U\n'+
 '#EXTINF:-1 tvg-chno="1" group-title="TV Italia",Rai 1 HD\n'+hls+'\n'+
 '#EXTINF:-1 tvg-chno="2" group-title="TV Italia",Rai 2 HD\n'+bad+'\n';
const extra='#EXTM3U\n#EXTINF:-1 tvg-chno="28" group-title="TV Italia",TV2000\nhttps://hls-live-tv2000.akamaized.net/live/tv2000.m3u8\n';
const snapshot={schema:1,generated_at:now,channels:{
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
 if(url.includes('/data/additional-channels.m3u'))return new Response(extra,{status:200});
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
const catalog='/catalog/tv/tv-italia-puglia.json';
let res=await worker.fetch(request(catalog,'DE'));
assert.equal(res.status,200);
assert.deepEqual((await res.json()).metas.map(x=>x.name),['TV2000'],'Extra verified channel visible; original IDs preserved');
res=await worker.fetch(request(catalog,'IT'));
assert.equal(res.status,200);
assert.deepEqual((await res.json()).metas.map(x=>x.name),['Rai 1 HD','TV2000'],'Preserve original channel order, then append verified extras');
assert.equal(probeCount,1);
res=await worker.fetch(request('/debug/italia.json','IT'));
let state=await res.json();
assert.deepEqual(state.recovered,['Rai 1 HD']);
assert.equal(state.regionalTested,2);
res=await worker.fetch(request('/stream/tv/tvip_1_rai-1-hd.json','IT'));
assert.equal(res.status,200);
let stream=await res.json();
assert.equal(stream.streams.length,1);
assert.equal(stream.streams[0].url,hls);
res=await worker.fetch(request('/stream/tv/tvip_2_rai-2-hd.json','IT'));
assert.equal((await res.json()).streams.length,0);
console.log('Expanded catalogue tests passed: extra verified channel, geo segment, 403 rejection, country gating, catalog and stream.');
