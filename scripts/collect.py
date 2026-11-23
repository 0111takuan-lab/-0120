"""0120' SALMON LAB: source checks and review-only link extraction.

No automatic publication. Uses Python standard library only.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / 'research' / 'sources.json'
OUTPUT = ROOT / 'research' / 'review_candidates.json'
MAX_BYTES = 1_500_000
MAX_LINKS = 80
KEYWORDS = ('サーモンラン', 'シャケ', 'オオモノ', 'タワー', 'カタパッド', 'テッキュウ', 'モグラ', 'ナベブタ', 'ハシラ', 'バクダン', 'ヘビ', 'コウモリ', 'ダイバー', 'テッパン', 'グリル', 'ドスコイ', 'コジャケ', 'イクラ', '武器', 'ブキ', 'ステージ')


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.href = None
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'a' and not self.skip:
            self.href = dict(attrs).get('href')
            self.parts = []

    def handle_data(self, data):
        if self.href is not None and not self.skip:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.href is not None:
            title = re.sub(r'\s+', ' ', ''.join(self.parts)).strip()
            if title:
                self.links.append((title, self.href))
            self.href = None
            self.parts = []
        if tag in ('script', 'style') and self.skip:
            self.skip -= 1


def extract_links(html, base_url):
    parser = LinkParser()
    parser.feed(html)
    seen = set()
    candidates = []
    base_host = urllib.parse.urlsplit(base_url).hostname
    for title, href in parser.links:
        if not any(k in title for k in KEYWORDS):
            continue
        url = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname != base_host:
            continue
        url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ''))
        if url in seen:
            continue
        seen.add(url)
        candidates.append({'title': title[:150], 'url': url, 'status': 'needs_review'})
        if len(candidates) >= MAX_LINKS:
            break
    return candidates


def main():
    raw = json.loads(SOURCE_FILE.read_text(encoding='utf-8'))
    sources = raw if isinstance(raw, list) else raw.get('sources', [])
    results = []
    for item in sources:
        if not isinstance(item, dict) or not isinstance(item.get('url'), str) or not item['url'].startswith('https://'):
            continue
        row = {'name': item.get('name', '情報源'), 'source_url': item['url'],
               'checked_at': datetime.now(timezone.utc).isoformat(),
               'status': 'needs_review', 'page_candidates': []}
        try:
            req = urllib.request.Request(item['url'], headers={'User-Agent': 'SalmonLabResearch/0.3 (research review; no automatic publishing)', 'Accept': 'text/html'})
            with urllib.request.urlopen(req, timeout=20) as response:
                row['http_status'] = response.status
                row['content_type'] = response.headers.get('Content-Type', '')
                final_url = response.geturl()
                raw_html = response.read(MAX_BYTES + 1)
                if len(raw_html) > MAX_BYTES:
                    row['warning'] = 'HTML exceeds size limit; parsed first 1.5 MB only'
                    raw_html = raw_html[:MAX_BYTES]
                if 'html' in row['content_type'].lower():
                    charset = response.headers.get_content_charset() or 'utf-8'
                    html = raw_html.decode(charset, errors='replace')
                    row['page_candidates'] = extract_links(html, final_url)
                else:
                    row['warning'] = 'Not an HTML page'
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            row['error'] = str(exc)
        results.append(row)
        print(f"{row['name']}: HTTP {row.get('http_status', 'ERROR')}; candidate links {len(row['page_candidates'])}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('候補リンクを保存しました。数値・弱点は未抽出で、自動公開はしません。')


if __name__ == '__main__':
    main()
