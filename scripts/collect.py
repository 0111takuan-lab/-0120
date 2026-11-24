"""0120' SALMON LAB: source checks and review-only link extraction.

No automatic publication. Uses Python standard library only.
"""
import json
import time
import unicodedata
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


# Ver.3: bounded, review-only extraction of explicitly labelled HP values.
ENEMIES = ('コジャケ','ドスコイ','シャケ','バクダン','ヘビ','テッパン','タワー','モグラ','カタパッド','コウモリ','ハシラ','ダイバー','テッキュウ','ナベブタ','グリル','キンシャケ','ヨコヅナ','タツ','ジョー','シャケコプター','ハコビヤ','ドロシャケ')
MAX_DETAIL_PAGES = 4
STATE = ROOT / "research" / "collection_state.json"
INTERVAL = 15


class DetailParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.parts = []
        self.skip = 0
        self.heading = ''
    def flush(self):
        text = re.sub(r'\s+', ' ', ''.join(self.parts)).strip()
        if text:
            self.blocks.append((self.heading, text))
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','nav'):
            self.skip += 1
        if self.skip:
            return
        if tag in ('h1','h2','h3','h4','p','tr','li','br'):
            self.flush()
        if tag in ('td','th'):
            self.parts.append(' ')
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
    def handle_endtag(self, tag):
        if tag in ('script','style','nav'):
            self.skip = max(0,self.skip-1)
            return
        if self.skip:
            return
        if tag in ('h1','h2','h3','h4'):
            self.heading = ''.join(self.parts).strip()
        if tag in ('h1','h2','h3','h4','p','tr','li'):
            self.flush()


def extract_hp(html, url, title):
    parser = DetailParser()
    parser.feed(html)
    parser.flush()
    found = []
    seen = set()
    for heading, block in parser.blocks:
        block = unicodedata.normalize('NFKC', block)
        # Only explicit labels followed by a number; no inferred values.
        matches = list(re.finditer(r'(?:HP|体力|耐久値)\s*[:：=]?\s*([0-9][0-9,]*)(?![0-9,.])', block, re.I))
        if not matches:
            continue
        names = [n for n in ENEMIES if n in heading or n in block]
        names = [n for n in names if not any(n != m and n in m for m in names)]
        if not names and title.strip() in ENEMIES:
            names = [title.strip()]
        if len(names) != 1:
            continue
        for match in matches:
            hp = int(match.group(1).replace(',', ''))
            key = (names[0], hp, url)
            if hp <= 0 or key in seen:
                continue
            seen.add(key)
            found.append({'name': names[0], 'hp_candidate': hp, 'source_url': url,
                          'checked_at': datetime.now(timezone.utc).isoformat(),
                          'status': 'needs_review', 'matched_label': match.group(0)[:40],
                          'section': heading[:100]})
    return found


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(STATE)


def cooldown(exc):
    from email.utils import parsedate_to_datetime
    value = exc.headers.get('Retry-After', '') if exc.headers else ''
    try:
        seconds = int(value)
    except ValueError:
        try:
            seconds = parsedate_to_datetime(value).timestamp() - time.time()
        except (ValueError, TypeError, OverflowError):
            seconds = 0
    return time.time() + max(3600, seconds)


def collect_details(row, state):
    saved = state.setdefault('sources', {}).setdefault(row['source_url'], {'done': {}, 'links': []})
    done = saved['done']
    links = [x for x in row['page_candidates'] if any(n in x['title'] for n in ENEMIES) or 'オオモノ' in x['title']]
    links.sort(key=lambda x: (x['title'] not in ENEMIES, 'シャケについて' not in x['title']))
    if links:
        saved['links'] = links
    links = saved['links']
    row['detail_checks'] = []
    for link in [x for x in links if x['url'] not in done][:MAX_DETAIL_PAGES]:
        if time.time() < state.get('blocked_until', 0):
            break
        time.sleep(INTERVAL)
        check = {'url': link['url'], 'title': link['title']}
        try:
            req = urllib.request.Request(link['url'], headers={'User-Agent': 'SalmonLabResearch/0.4 (review only)', 'Accept': 'text/html'})
            with urllib.request.urlopen(req, timeout=20) as response:
                check['http_status'] = response.status
                if urllib.parse.urlsplit(response.geturl()).hostname != urllib.parse.urlsplit(row['source_url']).hostname:
                    raise ValueError('Unexpected redirect host')
                if 'html' not in response.headers.get('Content-Type','').lower():
                    raise ValueError('Not HTML')
                data = response.read(MAX_BYTES+1)
                if len(data)>MAX_BYTES:
                    raise ValueError('Page exceeds size limit')
                candidates = extract_hp(data.decode(response.headers.get_content_charset() or 'utf-8', errors='replace'), response.geturl(), link['title'])
                check['candidate_count'] = len(candidates)
                done[link['url']] = candidates
        except urllib.error.HTTPError as exc:
            check['http_status'] = exc.code
            check['error'] = str(exc)
            if exc.code in (403, 429, 503):
                state['blocked_until'] = cooldown(exc)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            check['error'] = str(exc)
        row['detail_checks'].append(check)
        save_state(state)
    unique = {}
    for candidates in done.values():
        for c in candidates:
            unique[(c['name'], c['hp_candidate'], c['source_url'])] = c
    row['enemy_candidates'] = list(unique.values())
    row['progress'] = {'checked_pages': sum(x['url'] in done for x in links), 'total_pages': len(links), 'blocked_until': state.get('blocked_until', 0)}
    row['detail_status'] = 'needs_review' if unique else 'no_candidates'


def main():
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
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
            if time.time() < state.get('blocked_until', 0):
                raise ValueError('Cooldown active; no network request')
            time.sleep(INTERVAL)
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
        except urllib.error.HTTPError as exc:
            row['http_status'] = exc.code
            row['error'] = str(exc)
            if exc.code in (403, 429, 503):
                state['blocked_until'] = cooldown(exc)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            row['error'] = str(exc)
        row['collector_version'] = 4
        collect_details(row, state)
        save_state(state)
        results.append(row)
        print(f"{row['name']}: HTTP {row.get('http_status', 'ERROR')}; candidate links {len(row['page_candidates'])}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Ver.4: 候補リンクとHP候補を保存しました。自動公開はしません。')


if __name__ == '__main__':
    main()
