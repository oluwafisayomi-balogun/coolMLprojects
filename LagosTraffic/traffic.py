import urllib.parse
import pandas as pd
from playwright.sync_api import sync_playwright
import time  # Import time for pauses

def twitter_login(page, username, password):
    page.goto("https://twitter.com/login")
    page.wait_for_selector('input[name="text"]')
    page.fill('input[name="text"]', username)
    page.keyboard.press("Enter")
    page.wait_for_timeout(5000)
    page.wait_for_selector('input[name="password"]')
    page.fill('input[name="password"]', password)
    page.keyboard.press("Enter")
    page.wait_for_timeout(5000)

def scrape_tweets(query, limit, pause_between_scrolls=15):
    _xhr_calls = []

    def intercept_response(response):
        if response.request.resource_type == "xhr":
            _xhr_calls.append(response)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1100, "height": 750})
        page = context.new_page()

        username = "fisayo_ml" # put the correct username here
        password = "12345" # put the correct password here
        twitter_login(page, username, password)

        page.on("response", intercept_response)

        # URL-encode the query
        formatted_query = urllib.parse.quote(query)
        search_url = f"https://twitter.com/search?q={formatted_query}&f=live"
        page.goto(search_url)

        # Wait for tweets to load
        page.wait_for_selector("div[aria-label='Timeline: Search timeline']", timeout=60000)

        tweet_data = []
        scraped_tweets = set()  # To avoid duplicates
        has_more_tweets = True  # Pagination flag

        while has_more_tweets:
            # Simulate scrolling to load more tweets
            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            page.wait_for_timeout(pause_between_scrolls * 1000)  # Wait before next scroll

            # Process intercepted XHR requests for tweets
            tweet_calls = [f for f in _xhr_calls if "SearchTimeline" in f.url]

            for xhr in tweet_calls:
                try:
                    data = xhr.json()
                    tweets_set1 = data.get("data", {}).get("search_by_raw_query", {}).get("search_timeline", {}).get("timeline", {}).get("instructions", [])
                    for instruction in tweets_set1:
                        if "entries" in instruction:
                            for entry in instruction["entries"]:
                                if entry["entryId"].startswith("tweet-"):
                                    tweet_content = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {})
                                    result = tweet_content.get("result", {})
                      
                                    if result:
                                        tweet_text = result.get("legacy", {}).get("full_text", "")
                                        created_at = result.get("legacy", {}).get("created_at", "")
                                        hashtags = result.get("legacy", {}).get("entities", {}).get("hashtags", [])
                                        hashtags_list = [ht.get("text", "") for ht in hashtags]

                                        # Skip duplicates
                                        tweet_id = entry["entryId"]
                                        if tweet_id not in scraped_tweets:
                                            scraped_tweets.add(tweet_id)
                                            tweet_data.append({"text": tweet_text, "created_at": created_at, "hashtags": hashtags_list})
                                            
                                            # Display the current count of tweets scraped
                                            print(f"Tweets scraped so far: {len(tweet_data)}")

                                        # Stop if the limit is reached
                                        if len(tweet_data) >= limit:
                                            has_more_tweets = False
                                            break
                except Exception as e:
                    print(f"Error processing XHR response: {e}")
                if not has_more_tweets:
                    break

            if len(tweet_calls) == 0:
                # No more tweet data is being loaded
                has_more_tweets = False

        browser.close()
        return tweet_data

if __name__ == "__main__":
    limit = 2500

    query = '(#TrafficUpdates OR #TrafficReports OR #AccidentReport OR #AccidentReports OR #BreakdownReport OR #BreakdownReports OR #IncidentReport OR #IncidentReports OR #LagosTraffic OR #TrafficReport OR #TrafficReports OR #TrafficUpdate OR #TrafficUpdates) from:followlastma'
    
    
    # Scrape tweets for query1
    tweets_query1 = scrape_tweets(query, limit=limit, pause_between_scrolls=15)  # 15-second pause
    df = pd.DataFrame(tweets_query1)
    df.to_csv("df.csv", index=False)
    print('df scraping completed')