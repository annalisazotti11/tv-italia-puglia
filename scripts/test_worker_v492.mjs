import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const policy=JSON.parse(readFileSync(new URL('../data/source-quarantine.json',import.meta.url),'utf8'));
const c5='tvip_5_canale-5-hd', tgr='tvip_103_rai-3-tgr-puglia', one='tvip_1_rai-1-hd', two='tvip_2_rai-2-hd';
const direct=policy.approved_only[c5][0];
const other='https://example.org/suspect.m3u8';
const blocked='https://ch.iptvmate.net/suspect.m3u8';
const duplicate='https://example.org/shared.m3u8';
const regional='https://tgrpuglia-live.akamaized.net/hls/live/2025570/tgrpuglia/tgrpuglia/playlist.m3u8';
const now=new Date().toISOString();
const e=(url,ready=true)=>({url,source:'Test',last_ok:now,playback_checked_at:now,kind:'HLS',playback_ready:ready,has_video:ready,has_audio:ready,score:10});
const make=(name,verified,candidates=[])=>({name,verified,candidates,regional_candidates:[]});
let snap={schema:1,generated_at:now,channels:{
  [c5]:make('Canale 5 HD',[e(other),e(blocked)],[e(direct,false)]),
  [tgr]:make('Rai 3 TGR Puglia',[e(regional),e(blocked)]),
  [one]:make('Rai 1',[e(duplicate)]),
  [two]:make('Rai 2',[e(duplicate)])
}};
let redirect=false, failPolicy=false;
const fetched=[];
globalThis.fetch=async input=>{
  const url=String(input);fetched.push(url);
  if(url.includes('/data/source-quarantine.json'))return failPolicy?new Response('',{status:503}):Response.json(policy);
  if(url.includes('/data/verified-streams.json'))return Response.json(snap);
  if(url===direct&&redirect)return new Response('',{status:302,headers:{Location:other}});
  if(url===direct)return new Response('#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6,\nsegment.ts\n');
  throw Error('Unexpected fetch');
};
let seq=0;
const init=async()=> (await import('../cloudflare/worker-tv-v4.9.2.js?run='+seq++)).default;
let worker=await init();
const get=async(id)=>(await worker.fetch(new Request('https://example.com/stream/tv/'+id+'.json'))).json();
assert.deepEqual((await get(c5)).streams,[]);
assert.deepEqual((await get(tgr)).streams.map(x=>x.url),[regional]);
assert.deepEqual((await get(one)).streams,[]);
assert.deepEqual((await get(two)).streams,[]);
snap.channels[c5].candidates=[e(direct,true)];
worker=await init();
assert.deepEqual((await get(c5)).streams.map(x=>x.url),[direct]);
redirect=true;
assert.deepEqual((await get(c5)).streams,[]);
assert.ok(!fetched.includes(other)&&!fetched.includes(blocked)&&!fetched.includes(duplicate));
failPolicy=true;
worker=await init();
assert.deepEqual((await get(tgr)).streams,[]);
assert.equal((await (await worker.fetch(new Request('https://example.com/manifest.json'))).json()).version,'4.9.2');
console.log('4.9.2: quarantena, duplicati, Canale 5 A/V + redirect e TGR Puglia: OK');
