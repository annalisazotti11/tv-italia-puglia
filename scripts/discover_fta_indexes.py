#!/usr/bin/env python3
"""Daily public FTA index discovery, metadata only. Never auto-import unreviewed URLs."""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUERIES = (
    'Italy "free-to-air" IPTV in:name,description,readme',
    'Italia "free-to-air" playlist in:name,description,readme',
    '"Puglia" "free-to-air" television in:description,readme',
)

def search(query):
    params = urllib.parse.urlencode(dict(q=query, sort='updated', order='desc', per_page=30))
    headers = {'Accept':'application/vnd.github+json', 'User-Agent':'TV-Italia-Puglia-FTA-index-discovery'}
    token = os.environ.get('GH_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    with urllib.request.urlopen(urllib.request.Request('https://api.github.com/search/repositories?' + params, headers=headers), timeout=20) as response:
        return json.load(response).get('items', [])

def main():
    rows, errors = {}, []
    for q in QUERIES:
        try:
            for item in search(q):
                name = item.get('full_name','')
                if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', name) or item.get('archived') or item.get('private'):
                    continue
                rows[name] = {'repository': name, 'updated_at': item.get('updated_at'), 'state':'review_required'}
        except Exception as exc:
            errors.append(type(exc).__name__)
    output = ROOT / 'data/fta-index-discovery.json'
    # Preserve earlier discoveries when a query is rate limited or unavailable.
    if output.exists():
        old = json.loads(output.read_text(encoding='utf-8'))
        for row in old.get('repositories', []):
            rows.setdefault(row['repository'], row)
    report = {'schema':1,'generated_at':datetime.now(timezone.utc).isoformat(),
              'mode':'metadata_only','queries':len(QUERIES),'errors':errors,
              'repositories':sorted(rows.values(), key=lambda x: x.get('updated_at') or '', reverse=True)[:250]}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('FTA index candidates:',len(report['repositories']),'query errors:',len(errors))

if __name__ == '__main__':
    main()
