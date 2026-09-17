"""
MusicBrainz is a second, independent credit database. It's also
community-edited, so coverage and lag vary, but it catches some
non-hip-hop / non-US credits that Genius's editor community misses,
which is the point of running both.

MusicBrainz's API etiquette REQUIRES a descriptive User-Agent with
contact info, and asks for no more than ~1 request/second. Both are
handled here -- edit CONTACT below to your own email or site before
running this for real, or MusicBrainz may block the requests.
"""
import os
import sys

from common import DATA_DIR, get_session, load_json, load_watchlist, log, polite_sleep, save_json

CONTACT = "https://ellisofficial.co.uk"  # TODO: replace with your email or site
MB_BASE = "https://musicbrainz.org/ws/2"
ARTIST_IDS_PATH = DATA_DIR / "artist_ids.json"
SEEN_PATH = DATA_DIR / "musicbrainz_seen.json"
NEW_ITEMS_PATH = DATA_DIR / "musicbrainz_new.json"

RELEVANT_RELATION_TYPES = {
    "producer", "mix", "mix-DJ", "programming", "recording",
    "engineer", "co-producer", "remixer", "vocal arranger",
}


def resolve_mbid(session, name, cache):
    key = name.lower()
    if key in cache and cache[key].get("mb_id"):
        return cache[key]["mb_id"]

    resp = session.get(
        f"{MB_BASE}/artist/",
        params={"query": f'artist:"{name}"', "fmt": "json", "limit": 5},
    )
    resp.raise_for_status()
    results = resp.json().get("artists", [])
    if not results:
        return None

    best = max(results, key=lambda a: a.get("score", 0))
    cache.setdefault(key, {})["mb_id"] = best["id"]
    cache[key]["mb_name"] = best.get("name")
    return best["id"]


def fetch_credited_recordings(session, mbid):
    """
    NOTE: the artist-relationship lookup below returns a stripped-down
    "recording" stub (just id/title) that does NOT include the release
    date -- that field only comes back on a direct recording lookup.
    Callers must follow up with fetch_recording_release_date() for any
    recording they actually want to display/sort by date.
    """
    resp = session.get(
        f"{MB_BASE}/artist/{mbid}",
        params={"inc": "recording-rels", "fmt": "json"},
    )
    resp.raise_for_status()
    relations = resp.json().get("relations", [])
    out = []
    for rel in relations:
        if rel.get("target-type") != "recording":
            continue
        if rel.get("type") not in RELEVANT_RELATION_TYPES:
            continue
        rec = rel.get("recording", {})
        out.append({
            "id": rec.get("id"),
            "title": rec.get("title"),
            "role": rel.get("type"),
        })
    return out


def fetch_recording_release_date(session, recording_id):
    """A direct recording lookup DOES include first-release-date."""
    resp = session.get(
        f"{MB_BASE}/recording/{recording_id}",
        params={"fmt": "json"},
    )
    resp.raise_for_status()
    return resp.json().get("first-release-date")


def main():
    session = get_session(f"producer-watch/1.0 ( {CONTACT} )")
    watchlist = load_watchlist()
    id_cache = load_json(ARTIST_IDS_PATH, {})
    seen = load_json(SEEN_PATH, {})
    new_items = []

    for entry in watchlist:
        name = entry["name"]
        try:
            mbid = resolve_mbid(session, name, id_cache)
            polite_sleep()
        except Exception as e:
            log(f"MusicBrainz: failed to resolve '{name}': {e}")
            continue

        if mbid is None:
            log(f"MusicBrainz: no match found for '{name}'")
            continue

        try:
            recordings = fetch_credited_recordings(session, mbid)
            polite_sleep()
        except Exception as e:
            log(f"MusicBrainz: failed to fetch recordings for '{name}' ({mbid}): {e}")
            continue

        seen_ids = set(seen.get(name, []))
        for rec in recordings:
            rid = rec.get("id")
            if rid is None or rid in seen_ids:
                continue
            seen_ids.add(rid)

            release_date = None
            try:
                release_date = fetch_recording_release_date(session, rid)
                polite_sleep()
            except Exception as e:
                log(f"MusicBrainz: couldn't fetch release date for '{rec.get('title')}': {e}")

            new_items.append({
                "source": "musicbrainz",
                "producer": name,
                "title": rec.get("title"),
                "role": rec.get("role"),
                "release_date": release_date,  # None if MusicBrainz has no date on file
                "url": f"https://musicbrainz.org/recording/{rid}",
            })
        seen[name] = sorted(seen_ids)

    save_json(SEEN_PATH, seen)
    save_json(ARTIST_IDS_PATH, id_cache)
    save_json(NEW_ITEMS_PATH, new_items)
    log(f"MusicBrainz: {len(new_items)} new item(s) across {len(watchlist)} producers.")


if __name__ == "__main__":
    main()
