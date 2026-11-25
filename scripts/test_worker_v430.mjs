import assert from 'node:assert/strict';
import worker from '../cloudflare/worker-tv-v4.3.0.js';
import {readFileSync} from 'node:fs';
const policy=JSON.parse(readFileSync(new URL('../data/source-quarantine.json',import.meta.url),'utf8'));
const id='tvip_5_canale-5-hd';
const direct=policy.approved_only[id][0];
const bad='https://ch.iptvmate.net/fake.m3u8';
const other='https://example.org/c5.m3u8';
const rai='https://tgrpuglia-live.akamaized.net/hls/live/2025570/tgrpuglia/tgrpuglia/playlist.m3u8';
const now=new Date().toISOString();
const e=url=>({url,kind:'HLS',height:720,last_ok:now,source:'Test',score:12});
const snapshot={schema:1,generated_at:now,channels:{
  [id]:{name:'Canale 5 HD',number:'5',verified:[e(bad),e(other),e(direct)],candidates:[],regional_candidates:[]},
  'tvip_103_rai-3-tgr-puglia':{name:'Rai 3 TGR Puglia',number:'103',verified:[e(bad),e(rai)],candidates:[],regional_candidates:[]}
}};
const p='#EXTM3U\n#EXTINF:-1 tvg-chno="5",Canale 5 HD\n'+direct+'\n#EXTINF:-1 tvg-chno="103",Rai 3 TGR Puglia\n'+rai+'\n';
const requested=[];let redirect=false;
globalThis.fetch=async input=>{
  const url=String(input);requested.push(url);
  if(url.includes('TV_Italia_Puglia_con_loghi.m3u'))return new Response(p);
  if(url.includes('/data/additional-channels.m3u'))return new Response('#EXTM3U\n');
  if(url.includes('/data/verified-streams.json'))return Response.json(snapshot);
  if(url.includes('/data/source-quarantine.json'))return Response.json(policy);
  if(url.includes('/data/epg-guide.json'))return Response.json({schema:1,generated_at:now,channels:{}});
  if(url===direct&&redirect)return new Response('',{status:302,headers:{Location:'https://live02-seg.msf.cdn.mediaset.net/live/ch-r4/r4-clr.isml/index.m3u8'}});
  if(url===direct||url===rai)return new Response('#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6,\nsegment.ts\n');
  throw Error('Unexpected URL');
};
const get=async path=>(await worker.fetch(new Request('https://example.com'+path))).json();
assert.deepEqual((await get('/stream/tv/'+id+'.json')).streams.map(x=>x.url),[direct]);
assert.deepEqual((await get('/stream/tv/tvip_103_rai-3-tgr-puglia.json')).streams.map(x=>x.url),[rai]);
redirect=true;
assert.deepEqual((await get('/stream/tv/'+id+'.json')).streams,[]);
assert.ok(!requested.includes(bad)&&!requested.includes(other));
console.log('4.3.0 source quarantine tests passed.');
