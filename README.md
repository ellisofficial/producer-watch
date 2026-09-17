# Producer Watch

Daily-refreshed dashboard tracking new production/writing credits for a
watchlist of producers and writers, pulled from three sources:

- **Genius** — official API, artist credit pages (producer role included)
- **MusicBrainz** — official API, relationship-credited recordings
- **Press** — Google News RSS, catches the announcement itself

No Instagram, no scraping, nothing that breaks a ToS. Runs free on GitHub
Actions, publishes to a static page via GitHub Pages.

## Known limitations (read this first)

- **Lag is real.** Genius and MusicBrainz are community-edited. A brand
  new release might not show a producer credit for hours or weeks,
  depending on how actively that person's page gets edited. Press
  mentions are usually faster but noisier.
- **Name resolution is best-effort.** Neither Genius nor MusicBrainz has
  an official "give me the artist ID for this exact name" search. The
  scripts do their best match and cache it. Check
  `data/genius_needs_review.json` after the first run — anything in
  there was a fuzzy fallback match, not a confirmed one.
- **Coverage varies by genre and how billed someone is.** Session
  writers with thin Genius/MusicBrainz pages will produce fewer hits
  than someone like Max Martin.

This is the realistic DIY ceiling without paying for Chartmetric/Soundcharts
— treat it as a first-pass radar, not a guarantee you'll never miss anything.

## One-time setup

### 1. Get a Genius API token (free, no approval wait)
1. Go to `genius.com/api-clients`, sign in, click "New API Client"
2. App name/URL can be anything (e.g. "Producer Watch" / your site)
3. Generate a **Client Access Token** — this is what the script needs

### 2. Create the GitHub repo
1. Create a new **private** repo on GitHub
2. Push this entire folder to it (`git init && git add . && git commit -m "init" && git remote add origin <your-repo-url> && git push -u origin main`)

### 3. Add the Genius token as a secret
Repo → Settings → Secrets and variables → Actions → New repository secret
- Name: `GENIUS_ACCESS_TOKEN`
- Value: the token from step 1

### 4. Set your MusicBrainz contact info
Open `scripts/fetch_musicbrainz.py` and replace the `CONTACT` value at the
top with your email or a site of yours. MusicBrainz requires this in the
User-Agent header or it may block requests — it's not optional.

### 5. Enable GitHub Pages
Repo → Settings → Pages → Source: **Deploy from a branch** → Branch:
`main` → Folder: `/docs` → Save. Your dashboard will be live at
`https://<your-username>.github.io/<repo-name>/` within a minute or two.

### 6. Trigger the first run
Repo → Actions tab → "Daily producer watch" → Run workflow (the manual
`workflow_dispatch` trigger). After it finishes, check:
- The Actions log for errors (missing matches, rate limits, etc.)
- `data/genius_needs_review.json` and `data/artist_ids.json` for bad matches
- The Pages URL to see the dashboard

After that it runs automatically every day at 08:00 UTC — no further
action needed. Bookmark the Pages URL.

## Fixing a bad name match

If a producer resolved to the wrong Genius/MusicBrainz artist:
1. Open `data/artist_ids.json`
2. Find their entry (lowercased name is the key)
3. Manually replace `genius_id` or `mb_id` with the correct ID
   - Genius: visit their real page on genius.com, the ID is in the page URL's underlying data (view page source, search for `"id":`) or ask me to look it up for you
   - MusicBrainz: visit `musicbrainz.org`, search the name, the ID is the UUID in the artist page URL
4. Commit the fix — the script won't overwrite an ID that's already cached

## Editing the watchlist

Add or remove people in `config/watchlist.json`. New entries get resolved
automatically on the next run.

## Local testing (optional)

```bash
pip install -r requirements.txt
export GENIUS_ACCESS_TOKEN=your_token_here
cd scripts
python run_all.py
```

Then open `docs/index.html` directly in a browser.
