
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

SOURCES = Path("research/sources.json")
OUTPUT = Path("research/review_candidates.json")


def load_sources():
    if not SOURCES.exists():
        raise FileNotFoundError(
            "research/sources.json がありません"
        )

    data = json.loads(SOURCES.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("sources", "enemies"):
            if isinstance(data.get(key), list):
                return data[key]

    raise ValueError("sources.json の形式を確認してください")


def collect():
    results = []

    for item in load_sources():
        if not isinstance(item, dict):
            continue

        name = item.get("name", item.get("title", "名称未設定"))
        url = item.get("url", "")

        if not url:
            continue

        entry = {
            "name": name,
            "source_url": url,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": "needs_review"
        }

        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "SalmonLabResearch/0.1"}
            )

            with urllib.request.urlopen(request, timeout=15) as response:
                entry["http_status"] = response.status
                entry["content_type"] = response.headers.get(
                    "Content-Type", ""
                )

        except Exception as error:
            entry["error"] = str(error)

        results.append(entry)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"確認した情報源: {len(results)} 件")
    print(f"保存先: {OUTPUT}")


if __name__ == "__main__":
    collect()
