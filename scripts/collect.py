"""Check configured sources and emit review-only status. No automatic publishing."""
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sources = json.loads((ROOT / 'research/sources.json').read_text(encoding='utf-8'))
items = sources if isinstance(sources, list) else sources.get('sources', [])
results = []
for item in items:
    if not isinstance(item, dict) or not item.get('url', '').startswith('https://'):
        continue
    row = {'name': item.get('name', '情報源'), 'source_url': item['url'],
           'checked_at': datetime.now(timezone.utc).isoformat(), 'status': 'needs_review'}
    try:
        req = urllib.request.Request(item['url'], headers={'User-Agent': 'SalmonLabResearch/0.2 (source-check)'})
        with urllib.request.urlopen(req, timeout=15) as response:
            row['http_status'] = response.status
            row['content_type'] = response.headers.get('Content-Type', '')
    except Exception as exc:
        row['error'] = str(exc)
    results.append(row)
output = ROOT / 'research/review_candidates.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'情報源確認: {len(results)} 件。結果は承認待ちで、サイトには自動公開しません。')
