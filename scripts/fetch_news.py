"""
Catches the announcement itself -- often faster than either credit
database gets formally updated, at the cost of more noise. No API key
needed: Google News publishes a searchable RSS feed for free.

This is the noisiest of the three sources by design. The dashboard
labels items from here as "press" so you can weight them accordingly.
"""
import sys
import urllib.parse
import xml.etree.ElementTree as ET

from common import DATA_DIR, get_session, load_json, load_watchlist, log, save_json

SEEN_PATH = DATA_DIR / "news_seen.json"
NEW_ITEMS_PATH = DATA_DIR / "news_new.json"

QUERY_TERMS = '(produced OR "new single" OR songwriter OR "co-wrote" OR "out now")'


def build_url(name):
    q = f'"{name}" {QUERY_TERMS} when:2d'
    return f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-US&gl=US&ceid=US:en"


def main():
    session = get_session("producer-watch/1.0")
    watchlist = load_watchlist()
    seen = load_json(SEEN_PATH, {})
    new_items = []

    for entry in watchlist:
        name = entry["name"]
        try:
            resp = session.get(build_url(name), timeout=20)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as e:
            log(f"News: failed to fetch/parse feed for '{name}': {e}")
            continue

        seen_links = set(seen.get(name, []))
        for item in root.findall(".//item"):
            link = (item.findtext("link") or "").strip()
            title = (item.findtext("title") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            new_items.append({
                "source": "press",
                "producer": name,
                "title": title,
                "url": link,
                "release_date": pub_date,
            })
        seen[name] = sorted(seen_links)

    save_json(SEEN_PATH, seen)
    save_json(NEW_ITEMS_PATH, new_items)
    log(f"News: {len(new_items)} new item(s) across {len(watchlist)} producers.")


if __name__ == "__main__":
    main()
