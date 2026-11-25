
// TV Italia + Puglia 4.9.3 — quarantena e fallback ufficiale Canale 5
// Una sola sorgente per canale: la migliore secondo i test notturni.

const VERSION = '4.9.3';
const C5_ID = 'tvip_5_canale-5-hd';
const C5_OFFICIAL_PAGE = 'https://mediasetinfinity.mediaset.it/diretta/canale5_cC5';
const REPO = 'https://raw.githubusercontent.com/annalisazotti11/tv-italia-puglia/refs/heads/main';
const CATALOG = 'tv-italia-puglia';
const AGE = 72 * 3600000;
const MAX_STREAMS = 1;

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': '*',
  'Access-Control-Allow-Methods': 'GET,HEAD,OPTIONS'
};

const MANIFEST = {
  id: 'community.tv-italia-puglia',
  version: VERSION,
  name: 'TV Italia + Puglia',
  description: 'Dirette italiane e pugliesi: una sola sorgente migliore per canale, scelta con controlli audio/video notturni.',
  resources: ['catalog', 'meta', 'stream'],
  types: ['tv'],
  idPrefixes: ['tvip_'],
  catalogs: [{
    type: 'tv',
    id: CATALOG,
    name: 'TV Italia + Puglia · Canali TV'
  }]
};

const MEMORY = new Map();

function reply(obj, status = 200, seconds = 0) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      ...CORS,
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': seconds
        ? `public, max-age=${seconds}`
        : 'no-store'
    }
  });
}

function escapeXml(v) {
  return String(v ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&apos;'
  }[c]));
}

function slug(v) {
  return String(v ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || 'tv';
}

function attrs(line) {
  return Object.fromEntries(
    [...line.matchAll(/([\w-]+)="([^"]*)"/g)]
      .map(x => [x[1], x[2]])
  );
}

function safeUrl(value) {
  try {
    if (
      typeof value !== 'string' ||
      value.length > 3000 ||
      /[\x00-\x1f]/.test(value)
    ) return false;

    const u = new URL(value);

    if (
      u.protocol !== 'https:' ||
      u.username ||
      u.password ||
      u.hash ||
      (
        u.port &&
        !['443', '8080', '8081', '8443', '1936']
          .includes(u.port)
      ) ||
      /^\d+(?:\.\d+){3}$|^\[|(?:^|\.)(?:localhost|local|internal)$/
        .test(u.hostname)
    ) return false;

    if (!u.search) return true;

    const allowed = {
      '/TACT/11223/tv8web/master.m3u8': true,
      '/TACT/11219/cieloweb/master.m3u8': true,
      '/TACT/12221/web/master.m3u8': true
    };

    if (
      u.hostname !==
        'hlslive-web-gcdn-skycdn-it.akamaized.net' ||
      !allowed[u.pathname]
    ) return false;

    const keys = [...u.searchParams.keys()];

    if (
      keys.length !== 1 ||
      !['hdnts', 'hdnea'].includes(keys[0])
    ) return false;

    const m =
      /^st=(\d{10})~exp=(\d{10})~acl=\/\*~hmac=[a-f0-9]{64}$/i
        .exec([...u.searchParams.values()][0]);

    const now = Math.floor(Date.now() / 1000);

    return !!m &&
      +m[1] <= now + 300 &&
      +m[2] > now + 600 &&
      +m[2] < now + 3 * 365 * 86400;

  } catch {
    return false;
  }
}

function tv8Italy(id, url) {
  if (id !== 'tvip_8_tv8') return true;

  try {
    const u = new URL(url);

    return (
      u.hostname ===
        'hlslive-web-gcdn-skycdn-it.akamaized.net' &&
      u.pathname ===
        '/TACT/11223/tv8web/master.m3u8'
    ) || (
      u.hostname ===
        'tvit.leicaflorianrobert.dev' &&
      u.pathname === '/sky/tv8/stream.m3u8' &&
      !u.search
    );

  } catch {
    return false;
  }
}

function safeLogo(url) {
  try {
    if (!safeUrl(url)) return false;

    const u = new URL(url);

    return [
      'raw.githubusercontent.com',
      'cdn.jsdelivr.net',
      'i.imgur.com',
      'upload.wikimedia.org',
      'images.iptv-org.github.io'
    ].includes(u.hostname) &&
      /\.(?:png|jpe?g|webp)$/i.test(u.pathname);

  } catch {
    return false;
  }
}

// ==============================================
// CACHE GITHUB
// ==============================================

async function load(
  key,
  path,
  parse,
  ms,
  limit = 4500000
) {
  let state = MEMORY.get(key);
  const now = Date.now();

  if (state?.value && state.until > now) {
    return state.value;
  }

  if (state?.pending) return state.pending;

  state = state || {
    value: null,
    until: 0,
    pending: null
  };

  MEMORY.set(key, state);

  state.pending = (async () => {
    try {
      const response = await fetch(REPO + path, {
        cf: {
          cacheEverything: true,
          cacheTtl: Math.max(
            30,
            Math.floor(ms / 1000)
          )
        }
      });

      if (!response.ok) {
        throw Error('HTTP ' + response.status);
      }

      const text = await response.text();

      if (text.length > limit) {
        throw Error('File troppo grande');
      }

      const value = parse(text);

      state.value = value;
      state.until = Date.now() + ms;
      state.error = null;

      return value;

    } catch (e) {
      state.error = e.name || 'error';
      state.until = Date.now() + 30000;
      return state.value;

    } finally {
      state.pending = null;
    }
  })();

  return state.pending;
}

function parseM3U(text) {
  if (!text.trimStart().startsWith('#EXTM3U')) {
    throw Error('M3U non valido');
  }

  const items = new Map();

  for (const line of text.split(/\r?\n/)) {
    if (!line.startsWith('#EXTINF:')) continue;

    const a = attrs(line);
    const p = line.indexOf(',');

    if (p < 0) continue;

    const name = line.slice(p + 1).trim();
    const number = a['tvg-chno'] || '';

    const id =
      `tvip_${number || slug(name)}_${slug(name)}`;

    if (!items.has(id)) {
      items.set(id, {
        id,
        name,
        number,
        group: a['group-title'] || 'TV Italia',
        logo: a['tvg-logo'] || ''
      });
    }
  }

  return [...items.values()];
}

// La verifica audio/video non identifica l'emittente. Applica sempre il
// filtro di identità separato del repository prima di mostrare una sorgente.
function quarantinePolicy() {
  return load('identity', '/data/source-quarantine.json', text => {
    const p = JSON.parse(text);
    if (p.schema !== 1 || !Array.isArray(p.blocked_hosts) ||
        !p.approved_only || !p.blocked_by_channel ||
        !Array.isArray(p.approved_only['tvip_5_canale-5-hd'])) {
      throw Error('Quarantena non valida');
    }
    return p;
  }, 60000, 250000);
}

function identityAllowed(policy, id, url) {
  if (!policy || !safeUrl(url)) return false;
  const u = new URL(url);
  const host = u.hostname.toLowerCase().replace(/\.$/, '');
  if (policy.blocked_hosts.includes(host)) return false;
  if (Object.hasOwn(policy.approved_only, id) &&
      !policy.approved_only[id].includes(url)) return false;
  return !(policy.blocked_by_channel[id] || []).includes(url);
}

async function snapshot() {
  const [raw, policy] = await Promise.all([
    load('snapshot', '/data/verified-streams.json', text => {
      const v = JSON.parse(text);
      if (v.schema !== 1 || !v.channels ||
          !Number.isFinite(Date.parse(v.generated_at))) throw Error('Indice non valido');
      return v;
    }, 60000, 5000000),
    quarantinePolicy()
  ]);
  if (!raw || !policy) return null;
  const owners = new Map();
  const ambiguous = new Set();
  for (const [id, channel] of Object.entries(raw.channels)) {
    for (const key of ['verified', 'candidates', 'regional_candidates']) {
      for (const entry of channel[key] || []) {
        if (!identityAllowed(policy, id, entry.url)) continue;
        if (owners.has(entry.url) && owners.get(entry.url) !== id) ambiguous.add(entry.url);
        else owners.set(entry.url, id);
      }
    }
  }
  const channels = Object.fromEntries(Object.entries(raw.channels).map(([id, c]) => [
    id, {...c, ...Object.fromEntries(
      ['verified', 'candidates', 'regional_candidates'].map(key => [
        key, (c[key] || []).filter(e => identityAllowed(policy, id, e.url) && !ambiguous.has(e.url))
      ])
    )}
  ]));
  return {...raw, channels, identityPolicy: policy};
}

function avConfirmed(s) {
  const t = Date.parse(s.playback_checked_at || '');
  return Number.isFinite(t) && Date.now() - t >= 0 && Date.now() - t < AGE &&
    s.playback_ready === true && s.has_video === true && s.has_audio === true;
}

// Non seguire mai reindirizzamenti di Canale 5. Una sorgente non confermata
// viene nascosta; la verifica non tenta di aggirare DRM o geo-restrizioni.
async function confirmCanale5(s) {
  const abort = new AbortController();
  const timeout = setTimeout(() => abort.abort(), 3000);
  try {
    const r = await fetch(s.url, {
      redirect: 'manual', signal: abort.signal,
      headers: { Range: 'bytes=0-8191', Accept: 'application/vnd.apple.mpegurl,application/dash+xml,*/*' }
    });
    if (!r.ok || !r.body) return false;
    const reader = r.body.getReader();
    try {
      let body = '', bytes = 0;
      const decoder = new TextDecoder();
      while (bytes < 8192) {
        const {value, done} = await reader.read();
        if (done) break;
        const chunk = value.subarray(0, 8192 - bytes);
        bytes += chunk.length;
        body += decoder.decode(chunk, {stream: true});
      }
      const text = body.trimStart();
      if (text.startsWith('#EXTM3U'))
        return /#EXT-X-(?:STREAM-INF|TARGETDURATION|MEDIA|INF)/.test(text) &&
          !/#EXT-X-SESSION-KEY|#EXT-X-KEY:(?![^\r\n]*METHOD=NONE)/.test(text);
      return /<MPD[\s>]/i.test(text) && !/<ContentProtection\b/i.test(text);
    } finally {
      try { await reader.cancel(); } catch {}
    }
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}

function channels() {
  return load(
    'channels',
    '/TV_Italia_Puglia_con_loghi.m3u',
    parseM3U,
    300000
  );
}

function additions() {
  return load(
    'additions',
    '/data/additional-channels.m3u',
    parseM3U,
    300000
  );
}

function epg() {
  return load(
    'epg',
    '/data/epg-guide.json',
    text => {
      const v = JSON.parse(text);

      if (v.schema !== 1 || !v.channels) {
        throw Error('Guida non valida');
      }

      return v;
    },
    600000
  );
}

function guideTemplate() {
  return load(
    'gui',
    '/data/guide-ui.html',
    x => x,
    3600000,
    1500000
  );
}

// ==============================================
// RACCOLTA SORGENTI
// ==============================================

function sourceList(snap, id) {
  if (
    !snap ||
    Date.now() - Date.parse(snap.generated_at) > AGE
  ) return [];

  const c = snap.channels[id] || {};
  const a = [];

  for (const [key, verified] of [
    ['verified', true],
    ['candidates', false]
  ]) {
    for (
      const s of Array.isArray(c[key])
        ? c[key]
        : []
    ) {
      if (
        !identityAllowed(snap.identityPolicy, id, s.url) ||
        !tv8Italy(id, s.url) ||
        (id === 'tvip_5_canale-5-hd' && !avConfirmed(s))
      ) continue;

      if (
        verified &&
        (
          !Number.isFinite(Date.parse(s.last_ok)) ||
          Date.now() - Date.parse(s.last_ok) > AGE
        )
      ) continue;

      if (!a.some(x => x.url === s.url)) {
        a.push({
          ...s,
          confirmed: verified
        });
      }
    }
  }

  if (id === 'tvip_103_rai-3-tgr-puglia') {
    for (const s of c.regional_candidates || []) {
      if (
        identityAllowed(snap.identityPolicy, id, s.url) &&
        !a.some(x => x.url === s.url)
      ) {
        a.push({
          ...s,
          kind: 'HLS',
          confirmed: false
        });
      }
    }
  }

  return a;
}

// ==============================================
// CLASSIFICA QUALITÀ, AUDIO, VIDEO E VELOCITÀ
// ==============================================

function rank(s, id) {
  const measuredAt = Date.parse(
    s.playback_checked_at || ''
  );

  const freshAV =
    Number.isFinite(measuredAt) &&
    Date.now() - measuredAt < AGE;

  const ready =
    freshAV &&
    s.playback_ready === true &&
    s.has_video === true &&
    s.has_audio === true;

  const partial =
    freshAV &&
    s.has_video === true &&
    s.has_audio === true;

  const probeDelay = Number(s.probe_ms || 0);

  const first = Number(
    s.startup_ms ||
    s.latency_ms ||
    8000
  );

  const height = Math.min(
    Number(
      s.playback_height ||
      s.height ||
      0
    ),
    1080
  );

  const runs = Math.min(
    Number(s.success_runs || 0),
    30
  );

  let score = ready
    ? 100000
    : partial
      ? 50000
      : 0;

  score += Number.isFinite(Number(s.rank_score))
    ? Number(s.rank_score)
    : 0;

  score += s.confirmed ? 450 : 0;
  score += s.audio ? 65 : 0;
  score += runs * 11;

  score +=
    Math.min(height, 720) / 10 +
    Math.max(0, height - 720) / 55;

  score -= Math.min(first, 15000) / 13;

  if (s.stale) score -= 400;

  if (Number(s.bandwidth || 0) > 7500000) {
    score -= 110;
  }

  if (!ready && s.reason === 'ffprobe_timeout') {
    score -= 850;
  }

  if (!ready && probeDelay > 8000) {
    score -= 400;
  }

  if (
    s.has_video === true &&
    s.has_audio === false
  ) score -= 3500;

  if (
    s.has_audio === true &&
    s.has_video === false
  ) score -= 3500;

  if (s.video_codec === 'h264') score += 35;
  if (s.audio_codec === 'aac') score += 35;

  if (!s.confirmed) {
    const reason = String(s.reason || '');

    if (/HTTP (?:400|401|404|410)/.test(reason)) {
      score -= 1800;
    }

    if (/HTTP 403|Timeout|URLError/i.test(reason)) {
      score -= 140;
    }
  }

  // Canale 5: priorità a un flusso realmente
  // riproducibile; poi alternative Mediaset.
  if (id === 'tvip_5_canale-5-hd' && !ready) {
    try {
      const u = new URL(s.url);

      if (
        u.hostname ===
          'live02-seg.msf.cdn.mediaset.net' &&
        u.pathname.startsWith('/live/ch-c5/')
      ) score += 1100;

      if (
        u.hostname ===
          'live03-col.msf.cdn.mediaset.net' &&
        u.pathname.startsWith('/live/ch-c5/')
      ) score += 750;

    } catch {}
  }

  return score;
}

// ==============================================
// SOLO LA MIGLIORE SORGENTE PER CANALE
// ==============================================

async function streams(snap, id) {
  if (!/^tvip_[a-z0-9_-]{3,100}$/.test(id)) {
    return reply({ streams: [] }, 400);
  }

  const candidates = sourceList(snap, id)
    .sort((a, b) =>
      rank(b, id) - rank(a, id)
    );

  const usable = candidates;
  const confirmed = id === 'tvip_5_canale-5-hd'
    ? await Promise.all(usable.map(confirmCanale5)) : null;
  const chosen = usable.filter((_, i) => !confirmed || confirmed[i]).slice(0, MAX_STREAMS);

  const result = chosen.map(s => {
    const ready =
      s.playback_ready === true &&
      s.has_video === true &&
      s.has_audio === true;

    const state = ready
      ? 'Audio e video rilevati nel test'
      : s.reason === 'ffprobe_timeout'
        ? 'Test di riproduzione scaduto'
        : s.confirmed
          ? 'Segmento trovato, audio/video da confermare'
          : 'Da provare sulla TV';

    const height =
      s.playback_height ||
      s.height ||
      0;

    return {
      name: 'Diretta TV · migliore disponibile',

      description:
        state +
        ' · ' +
        (s.kind || 'HLS') +
        ' · ' +
        (
          height
            ? height + 'p'
            : 'qualità automatica'
        ) +
        (
          s.audio_codec
            ? ' · ' + s.audio_codec.toUpperCase()
            : ''
        ) +
        ' · ' +
        (s.source || 'Playlist pubblica'),

      url: s.url,

      behaviorHints: {
        notWebReady: true
      }
    };
  });

  // A link to the official page is not a direct media stream. If the
  // native source cannot be verified, let Mediaset handle playback and login.
  if (id === C5_ID && result.length === 0) {
    result.push({
      name: 'Mediaset Infinity · ufficiale',
      title: 'Apri Canale 5 sul sito ufficiale',
      description: 'Diretta ufficiale nel browser · accesso Mediaset se richiesto',
      externalUrl: C5_OFFICIAL_PAGE
    });
  }
  return reply({
    streams: result,
    cacheMaxAge: 0,
    sourceCount: result.length
  });
}

// ==============================================
// CATALOGO CANALI
// ==============================================

function category(c) {
  const s = (
    c.name + ' ' + (c.group || '')
  ).toLowerCase();

  if (
    c.id === 'tvip_103_rai-3-tgr-puglia' ||
    /puglia|norba|telebari|telerama|antenna sud/.test(s)
  ) return 'puglia';

  if (
    /news|tg24|tgcom|rainews|euronews|france 24/.test(s)
  ) return 'news';

  if (
    /sport|dazn|eurosport|supertennis/.test(s)
  ) return 'sport';

  if (
    /radio|rtl|deejay|m2o|kiss kiss/.test(s)
  ) return 'radio';

  return 'nazionali';
}

const SELECTED_LCN = new Set([
  1,2,3,4,5,6,7,8,9,10,
  11,12,13,14,15,16,17,18,19,20,
  21,22,23,24,25,26,27,28,29,30,
  31,32,33,34,35,36,37,38,39,40,
  41,42,43,44,45,46,47,48,49,50,
  51,52,54,55,56,57,58,60,63,64,
  65,66,67,69,70,78,103,145,158
]);

function featured(c) {
  return (
    SELECTED_LCN.has(Number(c.number)) ||
    category(c) === 'puglia' ||
    /^(sky |dazn |eurosport |now |euronews italiano|france 24 italiano)/i
      .test(c.name)
  );
}

function order(c) {
  const n = Number(c.number);
  return n === 103 ? 0.5 : n > 0 ? n : 99999;
}

function program(guide, id) {
  const list = guide?.channels?.[id]?.programmes;

  if (!Array.isArray(list)) {
    return {
      current: null,
      next: null,
      progress: 0
    };
  }

  const now = Date.now();
  let current = null;
  let next = null;

  for (const p of list) {
    const a = Date.parse(p.start);
    const b = Date.parse(p.stop);

    if (
      !Number.isFinite(a) ||
      !Number.isFinite(b) ||
      b <= a
    ) continue;

    if (a <= now && now < b) {
      current = p;
    } else if (
      a > now &&
      (!next || a < Date.parse(next.start))
    ) {
      next = p;
    }
  }

  const progress = current
    ? Math.min(
        100,
        Math.max(
          0,
          Math.round(
            100 *
            (now - Date.parse(current.start)) /
            (
              Date.parse(current.stop) -
              Date.parse(current.start)
            )
          )
        )
      )
    : 0;

  return {
    current,
    next,
    progress
  };
}

function time(date) {
  try {
    return new Intl.DateTimeFormat('it-IT', {
      timeZone: 'Europe/Rome',
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(date));
  } catch {
    return '';
  }
}

function logo(c, snap) {
  const a = c.logo || '';
  const b =
    snap?.channels?.[c.id]?.logo || '';

  return safeLogo(a)
    ? a
    : safeLogo(b)
      ? b
      : '';
}

function imagePoster(c, origin) {
  return 'https://wsrv.nl/?url=' +
    encodeURIComponent(
      origin +
      '/poster-v491/' +
      encodeURIComponent(c.id) +
      '.svg'
    ) +
    '&w=360&h=540&fit=cover&output=png&v=491';
}

function preview(c, origin, guide, snap) {
  const p = program(guide, c.id);
  const l = logo(c, snap);

  const parts = [
    String(c.number) === '103'
      ? 'Rai 3 · TGR Puglia'
      : c.number
        ? 'Canale ' + c.number + ' · ' + c.group
        : c.group
  ];

  if (p.current) {
    parts.unshift(
      'ORA IN ONDA · ' +
      time(p.current.start) +
      '–' +
      time(p.current.stop) +
      ' · ' +
      p.current.title
    );

    if (p.next) {
      parts.push(
        'A seguire · ' +
        time(p.next.start) +
        ' · ' +
        p.next.title
      );
    }
  } else {
    parts.unshift('Diretta TV');
  }

  if (c.id === C5_ID && !sourceList(snap, c.id).length) {
    parts.push('Diretta ufficiale: apri Mediaset Infinity');
  }
  return {
    id: c.id,
    type: 'tv',
    name: c.name,
    poster: imagePoster(c, origin),
    posterShape: 'poster',
    description: parts.join('\n'),
    ...(l ? { logo: l } : {}),
    behaviorHints: {
      isLive: true
    }
  };
}

// ==============================================
// LOCANDINE VIOLA MINIMAL
// ==============================================

function base64(bytes) {
  let out = '';

  for (let i = 0; i < bytes.length; i += 30000) {
    out += String.fromCharCode(
      ...bytes.subarray(i, i + 30000)
    );
  }

  return btoa(out);
}

async function posterSvg(c) {
  let embedded = '';

  for (const url of [c.logo, c.fallbackLogo]) {
    if (!safeLogo(url) || embedded) continue;

    try {
      const r = await fetch(url, {
        redirect: 'manual'
      });

      const mime = (
        r.headers.get('content-type') || ''
      ).split(';')[0].toLowerCase();

      if (
        r.ok &&
        ['image/png', 'image/jpeg', 'image/webp']
          .includes(mime)
      ) {
        const bytes = new Uint8Array(
          await r.arrayBuffer()
        );

        if (
          bytes.length > 100 &&
          bytes.length < 400000
        ) {
          embedded =
            'data:' + mime + ';base64,' + base64(bytes);
        }
      }
    } catch {}
  }

  const number = String(c.number) === '103'
    ? '03'
    : String(c.number || '');

  const art = embedded
    ? '<image href="' + embedded +
      '" x="35" y="177" width="330" height="230" ' +
      'preserveAspectRatio="xMidYMid meet"/>'
    : '<text x="200" y="300" text-anchor="middle" ' +
      'fill="#eae4ff" font-family="Arial" ' +
      'font-size="32" font-weight="700">' +
      escapeXml(c.name.slice(0, 24)) +
      '</text>';

  return (
    '<svg xmlns="http://www.w3.org/2000/svg" ' +
    'width="400" height="600" viewBox="0 0 400 600">' +
    '<defs>' +
    '<linearGradient id="b" x1="0" y1="0" ' +
    'x2="1" y2="1">' +
    '<stop stop-color="#18132f"/>' +
    '<stop offset="1" stop-color="#0c091d"/>' +
    '</linearGradient>' +
    '<radialGradient id="g">' +
    '<stop stop-color="#7255bc" stop-opacity=".35"/>' +
    '<stop offset="1" stop-color="#170c35" stop-opacity="0"/>' +
    '</radialGradient>' +
    '</defs>' +
    '<rect width="400" height="600" rx="22" ' +
    'fill="url(#b)"/>' +
    '<ellipse cx="200" cy="285" rx="180" ry="210" ' +
    'fill="url(#g)"/>' +
    '<rect x="8" y="8" width="384" height="584" rx="18" ' +
    'fill="none" stroke="#77689c" stroke-opacity=".3"/>' +
    (
      number
        ? '<text x="30" y="66" fill="#ded9ed" ' +
          'font-size="38" font-family="Arial">' +
          escapeXml(number) +
          '</text>'
        : ''
    ) +
    art +
    '</svg>'
  );
}

// ==============================================
// GUIDA TV WEB
// ==============================================

function guideCard(c, guide, snap) {
  const p = program(guide, c.id);
  const l = logo(c, snap);
  const g = category(c);
  const externalOnly = c.id === C5_ID && !sourceList(snap, c.id).length;

  const colors = {
    puglia: '#3ad3ba',
    news: '#6eaaf9',
    sport: '#6be2a2',
    radio: '#f4be78',
    nazionali: '#ac9cf6'
  };

  const n = Number(c.number) === 103
    ? '3 Puglia'
    : c.number || 'TV';

  const title =
    p.current?.title ||
    'Guida TV non disponibile';

  const clock = p.current
    ? time(p.current.start) + ' – ' + time(p.current.stop)
    : 'Diretta disponibile';

  const follow = p.next
    ? '<span class="kicker">A seguire · ' +
      escapeXml(time(p.next.start)) +
      '</span><strong>' +
      escapeXml(p.next.title) +
      '</strong>'
    : '<span class="unknown">' +
      'Prossimo programma non disponibile' +
      '</span>';

  return (
    '<article class="channel" data-search="' +
    escapeXml(
      (
        c.name + ' ' +
        (c.group || '') + ' ' +
        title
      ).toLowerCase()
    ) +
    '" data-group="' + g +
    '" style="--accent:' + colors[g] + '">' +
    '<div class="head">' +
    '<div class="logo">' +
    (
      l
        ? '<img src="' + escapeXml(l) +
          '" alt="" loading="lazy"/>'
        : '<b>' + escapeXml(n) + '</b>'
    ) +
    '</div>' +
    '<div><div class="channel-name">' +
    escapeXml(c.name) +
    '</div>' +
    '<div class="channel-meta">' +
    escapeXml(n) + ' · ' +
    escapeXml(c.group || 'TV') +
    '</div></div>' +
    '<span class="badge-live">' + (externalOnly ? 'INFINITY' : 'LIVE') + '</span>' +
    '</div>' +
    '<section class="program">' +
    '<div class="kicker">' +
    (p.current ? 'Ora in onda' : 'Diretta TV') +
    '</div>' +
    '<h2>' + escapeXml(title) + '</h2>' +
    '<div class="time">' + escapeXml(clock) + '</div>' +
    '<div class="track" role="progressbar" ' +
    'aria-valuemin="0" aria-valuemax="100" ' +
    'aria-valuenow="' + p.progress + '">' +
    '<span style="width:' + p.progress + '%"></span>' +
    '</div>' +
    '<div class="next">' + follow + '</div>' +
    (c.id === C5_ID ? '<p><a href="' + escapeXml(C5_OFFICIAL_PAGE) + '" target="_blank" rel="noopener noreferrer">Apri la diretta ufficiale Mediaset Infinity</a></p>' : '') +
    '</section></article>'
  );
}

async function guidePage(all, visible, guide, snap) {
  const t = await guideTemplate();

  if (
    !t ||
    !t.includes('<!-- CHANNELS -->')
  ) {
    return new Response(
      'Guida TV temporaneamente non disponibile',
      {
        status: 503,
        headers: CORS
      }
    );
  }

  const count = visible.filter(c =>
    program(guide, c.id).current
  ).length;

  const html = t
    .replace(
      '<!-- CHANNELS -->',
      visible.map(c =>
        guideCard(c, guide, snap)
      ).join('')
    )
    .replace(
      '<!-- VISIBLE_COUNT -->',
      String(visible.length)
    )
    .replace(
      '<!-- EPG_COUNT -->',
      String(count)
    )
    .replace(
      '<!-- MONITORED_COUNT -->',
      String(all.length)
    )
    .replace(
      '<!-- LAST_CHECK -->',
      escapeXml(
        snap?.generated_at || 'non disponibile'
      )
    );

  return new Response(html, {
    headers: {
      ...CORS,
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff'
    }
  });
}

// ==============================================
// ARCHIVIO CANALI
// ==============================================

function library(original, extra, snap) {
  const lcns = new Set(
    original.map(x => x.number).filter(Boolean)
  );

  const all = [
    ...original,
    ...extra.filter(x =>
      !x.number || !lcns.has(x.number)
    )
  ];

  const ids = new Set(all.map(x => x.id));

  for (
    const [id, v] of Object.entries(snap?.channels || {})
  ) {
    if (!id.startsWith('tvip_') || ids.has(id)) continue;

    all.push({
      id,
      name: v.name || id,
      number: v.number || '',
      group: v.group || 'Canali TV',
      logo: v.logo || ''
    });

    ids.add(id);
  }

  for (const c of all) {
    const originalLogo = c.logo || '';
    const archivedLogo =
      snap?.channels?.[c.id]?.logo || '';

    c.logo = logo(c, snap);

    c.fallbackLogo =
      safeLogo(archivedLogo) &&
      archivedLogo !== c.logo
        ? archivedLogo
        : (
            safeLogo(originalLogo) &&
            originalLogo !== c.logo
              ? originalLogo
              : ''
          );
  }

  return all;
}

// ==============================================
// CLOUDFLARE WORKER
// ==============================================

export default {
  async scheduled() {},

  async fetch(request) {
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: CORS
      });
    }

    if (!['GET', 'HEAD'].includes(request.method)) {
      return reply({
        error: 'Metodo non consentito'
      }, 405);
    }

    const u = new URL(request.url);
    const path = u.pathname;

    if (path === '/manifest.json') {
      return reply(MANIFEST, 200, 120);
    }

    try {
      // Usa lo snapshot e la quarantena. Solo Canale 5 richiede
      // conferma del manifest senza reindirizzamenti.

      const live = path.match(
        /^\/stream\/tv\/([^/]+)\.json$/
      );

      if (live) {
        return streams(
          await snapshot(),
          decodeURIComponent(live[1])
        );
      }

      const needsGuide =
        path === '/' ||
        path === '/guida' ||
        path === '/guida-tv' ||
        path === '/api/guida.json' ||
        path.startsWith('/catalog/') ||
        path.startsWith('/meta/');

      const [
        snap,
        original,
        extra,
        guide
      ] = await Promise.all([
        snapshot(),
        channels(),
        additions(),
        needsGuide
          ? epg()
          : Promise.resolve(null)
      ]);

      const all = library(
        original || [],
        extra || [],
        snap
      );

      const visible = all
        .filter(c =>
          featured(c) &&
          (c.id === C5_ID || sourceList(snap, c.id).length)
        )
        .sort(
          (a, b) =>
            order(a) - order(b) ||
            a.name.localeCompare(b.name, 'it')
        );

      if (
        path === '/' ||
        path === '/guida' ||
        path === '/guida-tv'
      ) {
        return guidePage(all, visible, guide, snap);
      }

      if (path === '/api/guida.json') {
        return reply({
          version: VERSION,
          generatedAt:
            guide?.generated_at || null,
          channels: visible.map(c => ({
            id: c.id,
            name: c.name,
            logo: logo(c, snap),
            ...program(guide, c.id)
          }))
        }, 200, 60);
      }

      if (
        path === '/debug/fonti.json' ||
        path === '/debug/notte.json' ||
        path === '/debug/channels.json'
      ) {
        return reply({
          version: VERSION,
          generatedAt: snap?.generated_at || null,
          summary: snap?.summary || null,
          playlists: snap?.playlists || [],
          sourceIndexCount:
            snap?.summary?.playlists_configured || 0,
          monitored: all.length,
          visible: visible.length,
          channels: all.map(c => ({
            id: c.id,
            name: c.name,
            verified:
              snap?.channels?.[c.id]?.verified?.length || 0,
            candidates:
              snap?.channels?.[c.id]?.candidates?.length || 0,
            avReady:
              snap?.channels?.[c.id]?.av_ready_count || 0,
            sources:
              sourceList(snap, c.id).length,
            officialExternal: c.id === C5_ID
          }))
        });
      }

      if (
        path === '/debug/canale5.json' ||
        path === '/debug/velocita.json'
      ) {
        const id = 'tvip_5_canale-5-hd';

        const ss = sourceList(snap, id)
          .sort((a, b) =>
            rank(b, id) - rank(a, id)
          );

        return reply({
          channel: 'Canale 5',
          lastScan:
            snap?.generated_at || null,
          selected: ss[0]?.url || null,
          sources: ss.map(s => ({
            source: s.source,
            kind: s.kind,
            height:
              s.playback_height || s.height || 0,
            hasAudio: s.has_audio ?? null,
            hasVideo: s.has_video ?? null,
            playbackReady: !!s.playback_ready,
            probeMs: s.probe_ms ?? null,
            rank: rank(s, id),
            reason: s.reason || null,
            url: s.url
          }))
        });
      }

      if (path === '/debug/italia.json') {
        return reply({
          version: VERSION,
          country: request.cf?.country || null,
          note:
            'Controllo A/V notturno. Un solo stream restituito a Nuvio.'
        });
      }

      const cat = path.match(
        /^\/catalog\/tv\/([^/]+)(?:\/[^/]+)?\.json$/
      );

      if (cat) {
        return reply({
          metas:
            decodeURIComponent(cat[1]) === CATALOG
              ? visible.map(c =>
                  preview(c, u.origin, guide, snap)
                )
              : []
        }, 200, 60);
      }

      const post = path.match(
        /^\/poster(?:-v\d+)?\/([^/]+)\.svg$/
      );

      if (post) {
        const c = all.find(x =>
          x.id === decodeURIComponent(post[1])
        );

        return c
          ? new Response(await posterSvg(c), {
              headers: {
                ...CORS,
                'Content-Type':
                  'image/svg+xml; charset=utf-8',
                'Cache-Control':
                  'public, max-age=86400'
              }
            })
          : reply({
              error: 'Canale non trovato'
            }, 404);
      }

      const meta = path.match(
        /^\/meta\/tv\/([^/]+)\.json$/
      );

      if (meta) {
        const c = all.find(x =>
          x.id === decodeURIComponent(meta[1])
        );

        return c
          ? reply({
              meta: preview(
                c, u.origin, guide, snap
              )
            })
          : reply({ meta: null }, 404);
      }

      return reply({
        error: 'Percorso non trovato'
      }, 404);

    } catch {
      return reply({
        error: 'Servizio temporaneamente non disponibile'
      }, 503);
    }
  }
};
