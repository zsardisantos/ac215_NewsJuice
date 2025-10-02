
'''
Quick prototype to test news extraction from RSS feeds
'''


import requests, feedparser, trafilatura


# List of news sources

#URL = "http://feeds.bbci.co.uk/news/world/rss.xml" # NO content
URL = "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml" # Contains content
#URL = "https://www.theguardian.com/uk/rss" # No content 
#URL = "http://rss.cnn.com/rss/cnn_topstories.rss" # No content 
#URL =  "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada" # Contains content


#Fetch a webpge

r = requests.get(
    URL,
    timeout=20,
    headers={"User-Agent": "NewsCondenseBot/1.0 (+you@example.com)"}
)
print("HTTP status:", r.status_code)
print("Content-Type:", r.headers.get("Content-Type"))
print("First 120 chars of body:", r.text[:120].replace("\n"," "))

r.raise_for_status()

# Sanity check: are we looking at XML?
is_xmlish = r.headers.get("Content-Type","").lower().find("xml") != -1 or r.text.lstrip().startswith(("<?xml", "<rss", "<feed"))
print("Looks like XML?:", is_xmlish)

feed = feedparser.parse(r.content)
print("Bozo:", feed.bozo, "| Exception:", repr(getattr(feed, "bozo_exception", None)))
print("Feed title:", feed.feed.get("title"))
print("Items:", len(feed.entries))

for e in feed.entries[:10]:
    print("\nFEED ITEM: ")
    print("TITLE:", e.get("title"), "\n-> LINK: ", e.get("link"))
    if "content" in e:
        print("CONTENT: ", e.content[0].value[:200], "...")
    else:
        print("No content available in feed. I try to extract the text from web.")
        url = e.link
        r = requests.get(url, headers={"User-Agent": "NewsCondenseBot/1.0"}, timeout=20)
        full_text = trafilatura.extract(r.text, url=url)
        if full_text:
            print(full_text[:500])  # first 500 chars of article body
        else:
            print("Could not extract full text")
       