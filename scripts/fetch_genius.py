"""
Pulls each watchlist producer's Genius artist page and reports any songs
we haven't seen before.

Genius credits producers/writers on Genius artist pages even when they've
never been billed as the main performing artist. BUT: the official Genius
API has no "search artist by name" endpoint. The only way to resolve a
name to an artist ID is to run a general /search query and look at the
artists attached to the results, which is a best-effort match, not a
guarantee. Resolved IDs are cached in data/artist_ids.json after the
first run -- check that file once after your first GitHub Action run and
fix any wrong matches by hand (see README).
"""
import os
import sys

from common import DATA_DIR, get_session, load_json, load_watchlist, log, save_json

GENIUS_BASE = "https://api.genius.com"
ARTIST_IDS_PATH = DATA_DIR / "artist_ids.json"
SEEN_PATH = DATA_DIR / "genius_seen.json"
NEW_ITEMS_PATH = DATA_DIR / "genius_new.json"
NEEDS_REVIEW_PATH = DATA_DIR / "genius_needs_review.json"


def resolve_artist_id(session, name, cache):
    key = name.lower()
    if key in cache and cache[key].get("genius_id"):
        return cache[key]["genius_id"], False

    resp = session.get(f"{GENIUS_BASE}/search", params={"q": name})
    resp.raise_for_status()
    hits = resp.json().get("response", {}).get("hits", [])

    best = None
    for hit in hits:
        result = hit.get("result", {})
        primary = result.get("primary_artist", {})
        if primary.get("name", "").lower() == name.lower():
            best = primary
            break
        # Producer/writer credits sometimes surface as a featured artist
        # on the matching song even when they're not the primary artist.
        for feat in result.get("featured_artists", []):
            if feat.get("name", "").lower() == name.lower():
                best = feat
                break
        if best:
            break

    if best is None and hits:
        # No exact name match -- fall back to the first hit's primary
        # artist and flag it for manual review rather than silently
        # trusting a fuzzy match.
        best = hits[0]["result"]["primary_artist"]
        cache.setdefault("_needs_review", []).append(
            {"searched_for": name, "matched": best.get("name"), "id": best.get("id")}
        )

    if best is None:
        return None, False

    cache.setdefault(key, {})["genius_id"] = best["id"]
    cache[key]["genius_name"] = best.get("name")
    return best["id"], True


def fetch_artist_songs(session, artist_id):
    songs = []
    page = 1
    while True:
        resp = session.get(
            f"{GENIUS_BASE}/artists/{artist_id}/songs",
            params={"sort": "release_date", "per_page": 50, "page": page},
        )
        resp.raise_for_status()
        body = resp.json().get("response", {})
        batch = body.get("songs", [])
        songs.extend(batch)
        nxt = body.get("next_page")
        if not nxt or page >= 4:  # cap at 200 songs/producer to stay light
            break
        page = nxt
    return songs


def main():
    token = os.environ.get("GENIUS_ACCESS_TOKEN")
    if not token:
        log("GENIUS_ACCESS_TOKEN not set -- skipping Genius fetch.")
        save_json(NEW_ITEMS_PATH, [])
        return

    session = get_session("producer-watch/1.0")
    session.headers["Authorization"] = f"Bearer {token}"

    watchlist = load_watchlist()
    id_cache = load_json(ARTIST_IDS_PATH, {})
    seen = load_json(SEEN_PATH, {})
    new_items = []

    for entry in watchlist:
        name = entry["name"]
        try:
            artist_id, newly_resolved = resolve_artist_id(session, name, id_cache)
        except Exception as e:
            log(f"Genius: failed to resolve '{name}': {e}")
            continue

        if artist_id is None:
            log(f"Genius: no match found for '{name}'")
            continue

        try:
            songs = fetch_artist_songs(session, artist_id)
        except Exception as e:
            log(f"Genius: failed to fetch songs for '{name}' ({artist_id}): {e}")
            continue

        seen_ids = set(seen.get(name, []))
        for song in songs:
            sid = song.get("id")
            if sid is None or sid in seen_ids:
                continue
            seen_ids.add(sid)
            new_items.append({
                "source": "genius",
                "producer": name,
                "title": song.get("title_with_featured", song.get("title")),
                "url": song.get("url"),
                "release_date": song.get("release_date"),
                "art": song.get("song_art_image_thumbnail_url"),
            })
        seen[name] = sorted(seen_ids)

    save_json(SEEN_PATH, seen)
    save_json(ARTIST_IDS_PATH, id_cache)
    save_json(NEW_ITEMS_PATH, new_items)
    if "_needs_review" in id_cache:
        save_json(NEEDS_REVIEW_PATH, id_cache["_needs_review"])
    log(f"Genius: {len(new_items)} new item(s) across {len(watchlist)} producers.")


if __name__ == "__main__":
    main()
