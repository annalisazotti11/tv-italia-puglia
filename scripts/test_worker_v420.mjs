import assert from 'node:assert/strict';
import worker from '../cloudflare/worker-tv-v4.2.0.js';

const now=new Date().toISOString();
const a='https://raiuno3-live.akamaized.net/live/primary.m3u8';
const b='https://raiuno3-live.akamaized.net/live/backup.m3u8';
const logo='https://raw.githubusercontent.com/xN1ckuz/OpenIPTVItaly/refs/heads/main/Logos/1-rai1hd.png';
const playlist='#EXTM3U\n#EXTINF:-1 tvg-chno="1" tvg-logo="'+logo+'" group-title="TV Italia",Rai 1 HD\n'+a+'\n';
const verified={schema:1,generated_at:now,channels:{
  'tvip_1_rai-1-hd':{name:'Rai 1 HD',number:'1',logo,group:'TV Italia',verified:[
    {url:a,source:'Sorgente primaria',kind:'HLS',height:1080,last_ok:now,score:150},
    {url:b,source:'Sorgente secondaria',kind:'HLS',height:720,last_ok:now,score:135}
  ],regional_candidates:[]},
  'tvip_sky_sky_atlantic':{name:'Sky Atlantic',number:'',group:'Sky',verified:[],regional_candidates:[]}
}};
const guide={schema:1,generated_at:now,channels:{}};
globalThis.fetch=async request=>{
  const url=String(request);
  if(url.includes('TV_Italia_Puglia_con_loghi.m3u'))return new Response(playlist);
  if(url.includes('/data/additional-channels.m3u'))return new Response('#EXTM3U\n');
  if(url.includes('/data/verified-streams.json'))return Response.json(verified);
  if(url.includes('/data/epg-guide.json'))return Response.json(guide);
  if(url===a)return new Response('#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6,\nsegment.ts\n',{status:200});
  if(url===b)return new Response('Forbidden',{status:403});
  if(url===logo){const img=new Uint8Array(128);img[25]=6;return new Response(img,{headers:{'Content-Type':'image/png'}});}
  throw new Error('Unexpected '+url);
};
const get=async path=>worker.fetch(new Request('https://example.com'+path));
let catalog=await(await get('/catalog/tv/tv-italia-puglia.json')).json();
assert.deepEqual(catalog.metas.map(x=>x.name),['Rai 1 HD']);
assert.match(catalog.metas[0].poster,/poster-v420/);
assert.equal(catalog.metas[0].logo,logo);
const p=await(await get('/poster-v420/tvip_1_rai-1-hd.svg')).text();
assert.match(p,/fill="#ffffff"/);
assert.ok(p.includes('data:image/png;base64,'));
assert.ok(!p.includes('removeWhite'));
let streams=await(await get('/stream/tv/tvip_1_rai-1-hd.json')).json();
assert.equal(streams.streams.length,2);
assert.equal(streams.streams[0].url,a);
assert.equal(streams.streams[1].url,b);
assert.match(streams.streams[1].name,/Alternativa/);
console.log('4.2.0 tests passed: white original-logo cards, verified alternatives, correct catalog.');
