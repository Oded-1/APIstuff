import requests
import os
from google import genai
import feedparser
from bidi.algorithm import get_display

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

import yfinance as yf

googleStock = yf.Ticker("GOOG")
print(googleStock.history(period='3d'))


def weather():
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 1800)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 31.9987,
        "longitude": 34.9456,
        "hourly": "temperature_2m",
        "timezone": "Europe/Moscow",
        "forecast_days": 1,
    }
    responses = openmeteo.weather_api(url, params = params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation: {response.Elevation()} m asl")
    print(f"Timezone: {response.Timezone()}{response.TimezoneAbbreviation()}")
    print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
            end =  pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
            freq = pd.Timedelta(seconds = hourly.Interval()),
            inclusive = "left"
        ).tz_convert(response.Timezone().decode())
    }

    hourly_data["temperature_2m"] = hourly_temperature_2m

    hourly_dataframe = pd.DataFrame(data = hourly_data)
    return ("\nHourly data\n", hourly_dataframe)

# os.environ.get("GEMINI_API_KEY")

# url = "https://generativelanguage.googleapis.com/v1beta/interactions"
# h = {"x-goog-api-key": os.getenv("GEMINI_API_KEY"), 
#         "Content-Type": "application/json"}
# d = {"model": "gemini-3.5-flash-lite",
#         "input": "fun and intresting quantum mechanics fact with explaination"}

# answer = requests.post(url, headers=h, json=d)
# print(answer.json()) 
#client = genai.Client()  # automatically reads GEMINI_API_KEY from your environment




def news():
    prompt = "Prompt: You will be given a list of 30+ news article titles from various news channels. Since this " \
            "is accessed via API and billed per token, avoid unnecessary filler — no greetings, no preamble, no " \
            "closing remarks, no restating these instructions. But do not sacrifice depth on the main 6 " \
            "stories for the sake of brevity — the goal is efficient wording, not shallow content." \
            " Task: Identify the 6 most significant and important news items from the list " \
            "(prioritize impact, scale, and relevance over sensationalism). For each of these 6, " \
            "write a deeper summary that goes beyond what the title already tells me. Where relevant, " \
            "address: who is involved, what happened, why it happened or matters, how it unfolded, " \
            "and where/when it took place. Use your own general knowledge to add relevant context or " \
            "background if it helps me understand the story better, not just what's implied by the title. " \
            "After the 6 main summaries, you may optionally add a few more items worth knowing — " \
            "but these must be under one sentence each, just the core fact. Output format " \
            "(plain text, no extra commentary): Top Stories: [Title] [Deeper summary] ... (up to 6) " \
            "Also worth knowing: [One-line fact]  Here are the titles:"
    titles = ""

    sourcesHeb = {"https://www.ynet.co.il/Integration/StoryRss2.xml": 6}
    sourcesEng = {"https://news.google.com/rss/search?q=site:reuters.com&hl=en-IL&gl=IL&ceid=IL:en": 4,
            "https://www.forbes.com/business/feed/": 5,
            "https://techcrunch.com/feed": 5,
            "https://www.marketwatch.com/rss/topstories": 5,
            "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml": 4}

    for url in sourcesHeb:
        for entry in feedparser.parse(url).entries[0:sourcesHeb[url]]:
            titles = titles + entry.title[::-1] + "\n"
    for url in sourcesEng:
        for entry in feedparser.parse(url).entries[0:sourcesEng[url]]:
            titles = titles + entry.title + "\n"

    interaction = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input= prompt+titles
    )
    return interaction.output_text

def riddle():
    interaction = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input="give me a short riddle, max 2 sentences, that will challange and improve my critical thinking. the riddle should be challenging but not so much that I spend more then 10 minutes on it (7/10 difficulty). pick from a large section of riddle types (a few examples could be math riddle, prison riddles, scale and weight riddle, and more) but THE ANSWER for the riddle should be concrete. do not include anything else but the riddle. make sure its a 7/10 difficulty not any easier then that!" #"fun and intresting quantum mechanics fact with explaination"
    )
    return interaction.output_text

def conceptOfDay():
    interaction = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input="I want you to teach me something new. give me an interesting and significant topic in a field of your choosing: philosophy, science(physics), history. and include with a short explanation (2-3 sentences). do not include anything else in the answer."
    )
    return interaction.output_text

