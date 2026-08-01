import requests
import os
from google import genai
import feedparser
from bidi.algorithm import get_display
#
# os.environ.get("GEMINI_API_KEY")

# url = "https://generativelanguage.googleapis.com/v1beta/interactions"
# h = {"x-goog-api-key": os.getenv("GEMINI_API_KEY"), 
#         "Content-Type": "application/json"}
# d = {"model": "gemini-3.5-flash-lite",
#         "input": "fun and intresting quantum mechanics fact with explaination"}

# answer = requests.post(url, headers=h, json=d)
# print(answer.json()) 
#client = genai.Client()  # automatically reads GEMINI_API_KEY from your environment
feed = feedparser.parse("https://news.google.com/rss/search?q=site:reuters.com&hl=en-IL&gl=IL&ceid=IL:en")
# https://www.forbes.com/business/feed/
# https://techcrunch.com/feed
feedYnet = feedparser.parse("https://www.ynet.co.il/Integration/StoryRss2.xml")
# https://www.marketwatch.com/rss/topstories

#https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml
for entry in feed.entries[0:15]:
    print(entry.title[::1])

def riddle():
    interaction = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input="give me a short riddle, max 2 sentences, that will challange and improve my critical thinking. the riddle should be challenging but not so much that I spend more then 10 minutes on it (7/10 difficulty). pick from a large section of riddle types (a few examples could be math riddle, prison riddles, scale and weight riddle, and more) but THE ANSWER for the riddle should be concrete. do not include anything else but the riddle. make sure its a 7/10 difficulty not any easier then that!" #"fun and intresting quantum mechanics fact with explaination"
    )
    return "ainteraction.output_text"

def conceptOfDay():
    interaction = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input="I want you to teach me something new. give me an interesting and significant topic in a field of your choosing: philosophy, science(physics), history. and include with a short explanation (2-3 sentences). do not include anything else in the answer."
    )
    return "ainteraction.output_text"

