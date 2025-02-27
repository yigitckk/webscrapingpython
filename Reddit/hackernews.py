import requests
from bs4 import BeautifulSoup
import time


def scrape_hacker_news_headlines(url="https://news.ycombinator.com/", num_headlines=30, delay=0.5):
    """Scrapes headlines from Hacker News with error handling and rate limiting."""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        headlines = []
        # Updated selector: HN uses 'titleline' class but not inside a span with that class
        title_elements = soup.select(".titleline > a")

        count = 0
        for title in title_elements:
            if count >= num_headlines:
                break
            headlines.append(title.text.strip())
            count += 1

        # No need to sleep between parsing elements from the same page
        # Only add delay if you're making multiple page requests

        return headlines

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the page: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


# Example usage
headlines = scrape_hacker_news_headlines(num_headlines=30)  # Start with fewer headlines for testing

if headlines:
    print(f"Retrieved {len(headlines)} headlines:")
    for i, headline in enumerate(headlines, 1):
        print(f"{i}. {headline}")
else:
    print("Failed to retrieve headlines.")