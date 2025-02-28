import requests
from bs4 import BeautifulSoup
import feedparser
import sqlite3
import time
import json
import re
from datetime import datetime, timedelta
import os
import schedule


# Database setup
def setup_database():
    conn = sqlite3.connect('news_aggregator.db')
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        url TEXT UNIQUE NOT NULL,
        source TEXT NOT NULL,
        published_date TEXT,
        summary TEXT,
        category TEXT,
        added_date TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create table for keywords/tags
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS article_tags (
        article_id INTEGER,
        tag TEXT,
        PRIMARY KEY (article_id, tag),
        FOREIGN KEY (article_id) REFERENCES articles(id)
    )
    ''')

    conn.commit()
    return conn, cursor


# HackerNews scraper (improved version of your existing code)
def fetch_hackernews(conn, cursor, num_posts=30):
    print("Fetching HackerNews posts...")
    url = "https://news.ycombinator.com/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Get titles and links
        items = []
        rows = soup.select("tr.athing")

        for row in rows[:num_posts]:
            title_element = row.select_one(".titleline > a")
            if not title_element:
                continue

            title = title_element.text.strip()
            link = title_element.get('href', '')

            # Handle relative URLs
            if link.startswith('item?'):
                link = f"{url}{link}"

            item_id = row.get('id')

            # Get points from the following row
            subtext_row = soup.select_one(f"tr#score_{item_id}")
            points = 0
            if subtext_row:
                points_element = subtext_row.select_one(".score")
                if points_element:
                    points_text = points_element.text.strip()
                    points = int(re.search(r'\d+', points_text).group()) if re.search(r'\d+', points_text) else 0

            # Insert into database
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO articles (title, url, source, published_date, category) VALUES (?, ?, ?, ?, ?)",
                    (title, link, "HackerNews", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Tech")
                )

                # If insertion was successful, get the article_id and add tags
                if cursor.rowcount > 0:
                    article_id = cursor.lastrowid

                    # Extract potential tags from title
                    tags = extract_tags(title)
                    for tag in tags:
                        cursor.execute(
                            "INSERT OR IGNORE INTO article_tags (article_id, tag) VALUES (?, ?)",
                            (article_id, tag)
                        )
            except sqlite3.IntegrityError:
                # URL already exists in database
                pass

            items.append({"title": title, "url": link, "points": points})

        conn.commit()
        print(f"Added {len(items)} HackerNews posts")
        return items

    except Exception as e:
        print(f"Error fetching HackerNews: {e}")
        return []


# Reddit scraper (improved version of your existing code)
def fetch_reddit(conn, cursor, subreddit="ArtificialInteligence", num_posts=30):
    print(f"Fetching Reddit r/{subreddit} posts...")

    # Use Reddit's JSON API instead of scraping HTML
    url = f"https://www.reddit.com/r/{subreddit}/.json?limit={num_posts}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        posts = []
        for post in data['data']['children']:
            post_data = post['data']
            title = post_data['title']
            url = post_data['url']
            created = datetime.fromtimestamp(post_data['created_utc']).strftime("%Y-%m-%d %H:%M:%S")
            score = post_data['score']
            selftext = post_data.get('selftext', '')[:500]  # Limit summary length

            # Insert into database
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO articles (title, url, source, published_date, summary, category) VALUES (?, ?, ?, ?, ?, ?)",
                    (title, url, f"Reddit/r/{subreddit}", created, selftext, "AI")
                )

                # If insertion was successful, get the article_id and add tags
                if cursor.rowcount > 0:
                    article_id = cursor.lastrowid

                    # Extract potential tags from title
                    tags = extract_tags(title)
                    for tag in tags:
                        cursor.execute(
                            "INSERT OR IGNORE INTO article_tags (article_id, tag) VALUES (?, ?)",
                            (article_id, tag)
                        )
            except sqlite3.IntegrityError:
                # URL already exists in database
                pass

            posts.append({"title": title, "url": url, "score": score, "created": created})

        conn.commit()
        print(f"Added {len(posts)} Reddit posts from r/{subreddit}")
        return posts

    except Exception as e:
        print(f"Error fetching Reddit: {e}")
        return []


# ArXiv API for AI/ML papers
def fetch_arxiv(conn, cursor, num_papers=20):
    print("Fetching ArXiv papers...")
    categories = ["cs.AI", "cs.LG", "cs.CL"]  # AI, Machine Learning, Computational Linguistics

    base_url = "http://export.arxiv.org/api/query?"
    query_params = {
        "search_query": f"cat:{' OR cat:'.join(categories)}",
        "start": 0,
        "max_results": num_papers,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }

    query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
    url = base_url + query_string

    try:
        response = requests.get(url)
        response.raise_for_status()

        # Parse the XML response
        soup = BeautifulSoup(response.content, "xml")
        entries = soup.find_all("entry")

        papers = []
        for entry in entries:
            title = entry.title.text.strip().replace("\n", " ")
            url = entry.id.text.strip()
            published = entry.published.text.strip()
            summary = entry.summary.text.strip().replace("\n", " ")[:500]  # Limit summary length

            # Get categories/tags
            categories = [category.get("term") for category in entry.find_all("category")]

            # Insert into database
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO articles (title, url, source, published_date, summary, category) VALUES (?, ?, ?, ?, ?, ?)",
                    (title, url, "ArXiv", published, summary, "Research")
                )

                # If insertion was successful, get the article_id and add tags
                if cursor.rowcount > 0:
                    article_id = cursor.lastrowid

                    # Add ArXiv categories as tags
                    for category in categories:
                        cursor.execute(
                            "INSERT OR IGNORE INTO article_tags (article_id, tag) VALUES (?, ?)",
                            (article_id, category)
                        )

                    # Extract additional tags from title
                    title_tags = extract_tags(title)
                    for tag in title_tags:
                        cursor.execute(
                            "INSERT OR IGNORE INTO article_tags (article_id, tag) VALUES (?, ?)",
                            (article_id, tag)
                        )
            except sqlite3.IntegrityError:
                # URL already exists in database
                pass

            papers.append({"title": title, "url": url, "published": published})

        conn.commit()
        print(f"Added {len(papers)} ArXiv papers")
        return papers

    except Exception as e:
        print(f"Error fetching ArXiv: {e}")
        return []


# RSS Feed parser for tech news sites
def fetch_rss_feeds(conn, cursor):
    print("Fetching RSS feeds...")
    feeds = [
        {"url": "https://techcrunch.com/feed/", "name": "TechCrunch", "category": "Tech News"},
        {"url": "https://www.wired.com/feed/rss", "name": "Wired", "category": "Tech News"},
        {"url": "https://www.technologyreview.com/feed/", "name": "MIT Technology Review", "category": "Tech News"},
        {"url": "https://dev.to/feed/", "name": "Dev.to", "category": "Programming"}
    ]

    all_entries = []

    for feed in feeds:
        try:
            news_feed = feedparser.parse(feed["url"])

            for entry in news_feed.entries[:15]:  # Limit to 15 most recent entries per feed
                title = entry.title
                link = entry.link
                published = entry.get("published", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                summary = entry.get("summary", "")[:500]  # Limit summary length

                # Insert into database
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO articles (title, url, source, published_date, summary, category) VALUES (?, ?, ?, ?, ?, ?)",
                        (title, link, feed["name"], published, summary, feed["category"])
                    )

                    # If insertion was successful, get the article_id and add tags
                    if cursor.rowcount > 0:
                        article_id = cursor.lastrowid

                        # Extract tags from title
                        tags = extract_tags(title)
                        for tag in tags:
                            cursor.execute(
                                "INSERT OR IGNORE INTO article_tags (article_id, tag) VALUES (?, ?)",
                                (article_id, tag)
                            )
                except sqlite3.IntegrityError:
                    # URL already exists in database
                    pass

                all_entries.append({"title": title, "url": link, "source": feed["name"]})

            print(f"Added entries from {feed['name']}")
        except Exception as e:
            print(f"Error fetching {feed['name']} RSS: {e}")

    conn.commit()
    print(f"Added {len(all_entries)} RSS feed entries")
    return all_entries


# Helper: Extract potential tags from text
def extract_tags(text):
    # List of common tech/programming/AI terms to look for
    tech_terms = ["AI", "ML", "Python", "JavaScript", "React", "Angular", "Vue", "Node.js",
                  "Data Science", "Deep Learning", "Neural Network", "NLP", "Computer Vision",
                  "Cloud", "AWS", "Azure", "GCP", "DevOps", "Docker", "Kubernetes",
                  "Blockchain", "Crypto", "API", "Microservices", "SQL", "NoSQL", "Database"]

    tags = []
    text_lower = text.lower()

    for term in tech_terms:
        if term.lower() in text_lower:
            tags.append(term)

    # Add any hashtags found in the text
    hashtags = re.findall(r'#(\w+)', text)
    tags.extend(hashtags)

    return list(set(tags))  # Remove duplicates


# Get recent news
def get_recent_news(conn, cursor, days=7, limit=50):
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    cursor.execute('''
    SELECT a.id, a.title, a.url, a.source, a.published_date, a.summary, a.category, GROUP_CONCAT(t.tag, ',') as tags
    FROM articles a
    LEFT JOIN article_tags t ON a.id = t.article_id
    WHERE DATE(a.added_date) >= ?
    GROUP BY a.id
    ORDER BY a.added_date DESC
    LIMIT ?
    ''', (cutoff_date, limit))

    results = cursor.fetchall()

    news_items = []
    for row in results:
        tags = row[7].split(',') if row[7] else []
        news_items.append({
            "id": row[0],
            "title": row[1],
            "url": row[2],
            "source": row[3],
            "published_date": row[4],
            "summary": row[5],
            "category": row[6],
            "tags": tags
        })

    return news_items


# Run all fetchers
def fetch_all_sources():
    conn, cursor = setup_database()

    # Run all fetchers
    fetch_hackernews(conn, cursor)
    fetch_reddit(conn, cursor, "ArtificialInteligence")
    fetch_reddit(conn, cursor, "programming")
    fetch_reddit(conn, cursor, "MachineLearning")
    fetch_arxiv(conn, cursor)
    fetch_rss_feeds(conn, cursor)

    # Get recent news for display
    recent_news = get_recent_news(conn, cursor)

    # Save to JSON file for simple frontend access
    with open('recent_news.json', 'w') as f:
        json.dump(recent_news, f, indent=2)

    # Print stats
    cursor.execute("SELECT COUNT(*) FROM articles")
    total_articles = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM articles WHERE DATE(added_date) = DATE('now')")
    new_today = cursor.fetchone()[0]

    print(f"Database stats: {total_articles} total articles, {new_today} new today")

    conn.close()
    print("Fetch complete!")


# Schedule automatic runs
def setup_schedule():
    # Run every 6 hours
    schedule.every(6).hours.do(fetch_all_sources)

    print("Scheduler started. Press Ctrl+C to exit.")

    # Run once immediately
    fetch_all_sources()

    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    setup_schedule()