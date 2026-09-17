"""
Merges today's new items from all three sources into a capped, persistent
history log, then renders that log as a static HTML page in docs/ for
GitHub Pages to serve.
"""
import datetime as dt
import html
import sys

from common import DATA_DIR, ROOT, load_json, log, save_json

HISTORY_PATH = DATA_DIR / "history.json"
DOCS_DIR = ROOT / "docs"
MAX_HISTORY = 500

SOURCE_META = {
    "genius": {"label": "Genius credit", "color": "#E8A33D"},
    "musicbrainz": {"label": "MusicBrainz credit", "color": "#4FA8A0"},
    "press": {"label": "Press mention", "color": "#C77DFF"},
}


def merge_new_items():
    today = dt.date.today().isoformat()
    history = load_json(HISTORY_PATH, [])
    added = 0
    for fname in ("genius_new.json", "musicbrainz_new.json", "news_new.json"):
        items = load_json(DATA_DIR / fname, [])
        for item in items:
            item["logged_on"] = today
            history.append(item)
            added += 1
    # newest first, capped
    history = history[-MAX_HISTORY * 3:]  # generous buffer before final cap below
    save_json(HISTORY_PATH, history)
    log(f"Dashboard: merged {added} new item(s), history now has {len(history)}.")
    return history


def row_html(item):
    meta = SOURCE_META.get(item.get("source"), {"label": item.get("source", "?"), "color": "#888"})
    title = html.escape(item.get("title") or "Untitled")
    producer = html.escape(item.get("producer") or "")
    url = html.escape(item.get("url") or "#")
    release_date = html.escape(str(item.get("release_date") or item.get("logged_on") or ""))
    role = item.get("role")
    role_html = f'<span class="role">{html.escape(role)}</span>' if role else ""
    return f'''
    <a class="row" href="{url}" target="_blank" rel="noopener">
      <span class="tag" style="--tag-color: {meta['color']}">{meta['label']}</span>
      <span class="row-main">
        <span class="row-title">{title}</span>
        <span class="row-sub">{producer}{role_html}</span>
      </span>
      <span class="row-date">{release_date}</span>
    </a>'''


def render(history):
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ordered = list(reversed(history))[:MAX_HISTORY]
    generated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if ordered:
        rows = "\n".join(row_html(i) for i in ordered)
        body = f'<div class="log">{rows}</div>'
    else:
        body = '''
    <div class="empty">
      <p>No new signals logged yet.</p>
      <p class="empty-sub">The first automated run populates this once GitHub Actions is scheduled and running.</p>
    </div>'''

    html_doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Signal &mdash; Producer Watch</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0E0E10;
    --bg-raised: #17171A;
    --text: #F2F0EA;
    --text-dim: #8C8A85;
    --line: #29282C;
    --accent: #E8A33D;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: 'Space Grotesk', sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  header {{
    max-width: 760px;
    margin: 0 auto;
    padding: 64px 20px 32px;
  }}
  header h1 {{
    font-size: 28px;
    font-weight: 600;
    margin: 0 0 8px;
    letter-spacing: -0.01em;
  }}
  header p {{
    color: var(--text-dim);
    font-size: 15px;
    line-height: 1.5;
    margin: 0;
    max-width: 60ch;
  }}
  .updated {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--text-dim);
    margin-top: 20px;
  }}
  main {{
    max-width: 760px;
    margin: 0 auto;
    padding: 0 20px 80px;
  }}
  .log {{
    border-top: 1px solid var(--line);
  }}
  .row {{
    display: flex;
    align-items: baseline;
    gap: 16px;
    padding: 16px 4px;
    border-bottom: 1px solid var(--line);
    text-decoration: none;
    color: inherit;
    transition: background 0.15s ease;
  }}
  .row:hover {{
    background: var(--bg-raised);
  }}
  .tag {{
    flex: 0 0 auto;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: var(--tag-color);
    border: 1px solid var(--tag-color);
    border-radius: 3px;
    padding: 3px 6px;
    white-space: nowrap;
  }}
  .row-main {{
    flex: 1 1 auto;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}
  .row-title {{
    font-size: 15px;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .row-sub {{
    font-size: 13px;
    color: var(--text-dim);
  }}
  .role {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    margin-left: 8px;
  }}
  .row-date {{
    flex: 0 0 auto;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--text-dim);
    white-space: nowrap;
  }}
  .empty {{
    padding: 80px 4px;
    border-top: 1px solid var(--line);
    text-align: left;
  }}
  .empty p {{
    margin: 0 0 6px;
    font-size: 15px;
  }}
  .empty-sub {{
    color: var(--text-dim);
    font-size: 13px;
  }}
  @media (max-width: 560px) {{
    .row {{ flex-wrap: wrap; }}
    .row-date {{ order: 3; margin-left: 48px; }}
  }}
</style>
</head>
<body>
<header>
  <h1>Signal</h1>
  <p>New production and writing credits for the producers and writers on your watchlist, pulled daily from Genius, MusicBrainz, and press coverage.</p>
  <div class="updated">Last updated {generated}</div>
</header>
<main>
  {body}
</main>
</body>
</html>
'''
    (DOCS_DIR / "index.html").write_text(html_doc, encoding="utf-8")
    log(f"Dashboard: wrote docs/index.html with {len(ordered)} row(s).")


def main():
    history = merge_new_items()
    render(history)


if __name__ == "__main__":
    main()
