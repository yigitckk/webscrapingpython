import requests
from bs4 import BeautifulSoup
import time
import re


def scrape_reddit_posts(subreddit="ArtificialInteligence", num_posts=50, delay=1):
    """Scrapes post titles from a Reddit subreddit with error handling and rate limiting."""

    url = f"https://www.reddit.com/r/{subreddit}/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        # Additional headers to avoid Reddit blocking the request
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }

    try:
        # First, try to access old Reddit which has a simpler structure
        old_reddit_url = f"https://old.reddit.com/r/{subreddit}/"
        response = requests.get(old_reddit_url, headers=headers)

        # If we can't access old Reddit, try the new one
        if response.status_code != 200:
            response = requests.get(url, headers=headers)

        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        posts = []
        count = 0

        # Try to handle both old and new Reddit
        # For old Reddit
        entries = soup.select('.thing.link')

        if entries:
            for entry in entries:
                if count >= num_posts:
                    break

                title_element = entry.select_one('a.title')
                if title_element:
                    title = title_element.text.strip()
                    posts.append(title)
                    count += 1
        else:
            # For new Reddit (more complex to parse)
            # Look for post titles in the new Reddit interface
            # This is trickier because new Reddit heavily uses JavaScript
            post_elements = soup.find_all("h3")

            for post_element in post_elements:
                if count >= num_posts:
                    break

                if post_element.text and len(post_element.text.strip()) > 0:
                    posts.append(post_element.text.strip())
                    count += 1

        # If we still don't have posts, try to extract from JSON embedded in the page
        if len(posts) == 0:
            # Look for JSON data that might contain posts
            scripts = soup.find_all('script', {'id': 'data'})
            for script in scripts:
                if script.string:
                    # Try to find post titles in the script content
                    titles = re.findall(r'"title":"([^"]+)"', script.string)
                    for title in titles:
                        if count >= num_posts:
                            break
                        posts.append(title)
                        count += 1

        time.sleep(delay)  # Add a delay after getting the page

        return posts

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the subreddit: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


# Example usage
subreddit_name = "ArtificialInteligence"  # Note: This is the correct spelling as in the URL
posts = scrape_reddit_posts(subreddit=subreddit_name, num_posts=50)  # Start with fewer posts for testing

if posts:
    print(f"Retrieved {len(posts)} posts from r/{subreddit_name}:")
    for i, post in enumerate(posts, 1):
        print(f"{i}. {post}")
else:
    print(f"Failed to retrieve posts from r/{subreddit_name}.")
    print("Note: Reddit actively prevents scraping. You might need to use their API instead.")