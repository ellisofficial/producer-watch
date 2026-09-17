import fetch_genius
import fetch_musicbrainz
import fetch_news
import build_dashboard
from common import log

if __name__ == "__main__":
    log("Starting daily run...")
    fetch_genius.main()
    fetch_musicbrainz.main()
    fetch_news.main()
    build_dashboard.main()
    log("Done.")
