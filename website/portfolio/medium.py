import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
import time

CACHE = {"articles": [], "last_fetch": 0}
ARTICLE_CACHE_DURATION = 604800  # 1 week

MEDIUM_USERNAME = "benmurphy_29746"
FEED_URL = f"https://medium.com/feed/@{MEDIUM_USERNAME}"


def fetch_articles():
    now = time.time()
    if now - CACHE["last_fetch"] <= ARTICLE_CACHE_DURATION:
        return CACHE["articles"]

    feed = feedparser.parse(FEED_URL)
    if not feed.entries:
        print(f"Articles not refreshed, 0 entries returned. Time: {now}")
        return CACHE["articles"]

    articles = []
    for entry in feed.entries:
        soup = BeautifulSoup(entry.summary, "html.parser")
        img_tag = soup.find("img")
        published_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %Z")
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "description": soup.get_text(),
            "published": published_date.strftime("%d %b %Y"),
            "thumbnail": img_tag["src"] if img_tag else None,
        })

    CACHE["articles"] = articles
    CACHE["last_fetch"] = now
    return articles
