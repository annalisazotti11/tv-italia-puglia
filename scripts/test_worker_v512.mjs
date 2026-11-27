import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const workerSource = await readFile(
  new URL('../cloudflare/worker-tv-v5.1.2.js', import.meta.url),
  'utf8'
);
const { default: worker } = await import(
  'data:text/javascript;base64,' + Buffer.from(workerSource).toString('base64')
);

const repo = 'https://raw.githubusercontent.com/annalisazotti11/tv-italia-puglia/refs/heads/main';
const now = new Date().toISOString();
const raiId = 'tvip_1_rai-1-hd';
const tv8Id = 'tvip_8_tv8';
const skyId = 'tvip_community_sky_cinema_due';
const daznId = 'tvip_community_dazn_serie_a';
const bestUrl = 'https://cdn.example/rai1/best.m3u8';
const reserveUrl = 'https://cdn2.example/rai1/reserve.m3u8';
const unreviewedUrl = 'https://community.example/sky-cinema-due/master.m3u8';

function row(url, rank) {
  return {
    url,
    source: 'test fixture',
    kind: 'HLS',
    checked_at: now,
    playback_checked_at: now,
    playback_ready: true,
    has_audio: true,
    has_video: true,
    content_status: 'no_high_confidence_flag',
    sampled_frames: 3,
    playback_height: 1080,
    rank_score: rank
  };
}

const audited = {
  schema: 1,
  mode: 'reviewed_visual_gate_v1',
  generated_at: now,
  summary: { visible: 1, monitored_channels: 2 },
  channels: {
    [raiId]: {
      name: 'Rai 1 HD',
      number: '1',
      group: 'Rai',
      verified: [row(reserveUrl, 100), row(bestUrl, 250)]
    },
    [skyId]: {
      name: 'Sky Cinema Due',
      number: '',
      group: 'Canali community da verificare',
      verified: [row(unreviewedUrl, 999)]
    }
  }
};

const policy = {
  schema: 1,
  blocked_hosts: [],
  approved_only: { 'tvip_5_canale-5-hd': [] },
  blocked_by_channel: {}
};

const review = {
  schema: 1,
  channels: { [raiId]: [bestUrl, reserveUrl] },
  identity_required: {}
};

const watchlist = {
  schema: 1,
  channels: [
    {
      id: skyId,
      name: 'Sky Cinema Due',
      group: 'Canali community da verificare',
      premium: true,
      discovery_only: true
    },
    {
      id: daznId,
      name: 'DAZN Serie A',
      group: 'Canali community da verificare',
      premium: true,
      discovery_only: true
    }
  ]
};

const files = new Map([
  ['/data/audited-streams.json', JSON.stringify(audited)],
  ['/data/source-quarantine.json', JSON.stringify(policy)],
  ['/data/source-identity-review.json', JSON.stringify(review)],
  ['/TV_Italia_Puglia_con_loghi.m3u',
    '#EXTM3U\n#EXTINF:-1 tvg-chno="1" group-title="Rai",Rai 1 HD\nhttps://cdn.example/rai1/best.m3u8\n'],
  ['/data/additional-channels.m3u', '#EXTM3U\n#EXTINF:-1 tvg-chno="8" group-title="TV",TV8\nhttps://example.org/unused.m3u8\n'],
  ['/data/channel-watchlist.json', JSON.stringify(watchlist)],
  ['/data/epg-guide.json', JSON.stringify({ schema: 1, channels: {} })]
]);

const originalFetch = globalThis.fetch;
globalThis.fetch = async input => {
  const url = String(input);
  if (!url.startsWith(repo)) throw new Error('Unexpected external request: ' + url);
  const path = url.slice(repo.length);
  if (!files.has(path)) throw new Error('Unexpected repository path: ' + path);
  return new Response(files.get(path), {
    status: 200,
    headers: { 'Content-Type': 'application/json; charset=utf-8' }
  });
};

try {
  let response = await worker.fetch(new Request('https://worker.test/manifest.json'));
  assert.equal(response.status, 200);
  assert.equal((await response.json()).version, '5.1.2');

  response = await worker.fetch(new Request('https://worker.test/debug/channels.json'));
  assert.equal(response.status, 200);
  const debug = await response.json();
  assert.equal(debug.version, '5.1.2');
  assert.equal(debug.watchlistCount, 2);
  assert.equal(debug.discoveryOnlyCount, 2);
  assert.equal(debug.visible, 1);
  assert.equal(debug.directVerified, 1);
  assert.equal(debug.officialWebOnly, 0);
  assert.equal(debug.monitored, 4);

  const sky = debug.channels.find(c => c.id === skyId);
  const dazn = debug.channels.find(c => c.id === daznId);
  assert.ok(sky, 'Sky Cinema Due must be present in the monitored list');
  assert.ok(dazn, 'DAZN Serie A must be present in the monitored list');
  assert.equal(sky.discoveryOnly, true);
  assert.equal(sky.premium, true);
  assert.equal(sky.sources, 0, 'unreviewed community stream must not be exposed');
  assert.equal(dazn.discoveryOnly, true);
  assert.equal(dazn.sources, 0);

  response = await worker.fetch(new Request('https://worker.test/catalog/tv/tv-italia-puglia.json'));
  const catalog = await response.json();
  assert.deepEqual(catalog.metas.map(x => x.id), [raiId],
    'only verified direct streams appear; external pages and unreviewed candidates remain hidden');

  response = await worker.fetch(new Request('https://worker.test/stream/tv/' + raiId + '.json'));
  const best = await response.json();
  assert.equal(best.streams.length, 1, 'only one source may be returned');
  assert.equal(best.streams[0].url, bestUrl, 'highest-ranked reviewed source must win');

  response = await worker.fetch(new Request('https://worker.test/stream/tv/' + tv8Id + '.json'));
  const fallback = await response.json();
  assert.equal(fallback.streams.length, 0, 'no web-only fallback');

  response = await worker.fetch(new Request('https://worker.test/stream/tv/' + skyId + '.json'));
  const hidden = await response.json();
  assert.equal(hidden.streams.length, 0, 'unreviewed candidate must stay hidden');

  console.log('Worker 5.1.2 tests passed: watchlist metadata, visibility gate, identity review and best-source selection.');
} finally {
  globalThis.fetch = originalFetch;
}
