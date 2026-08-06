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

import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

client = genai.Client()  # automatically reads GEMINI_API_KEY from your environment


def calender():
  """Shows basic usage of the Google Calendar API.
  Prints the start and name of the next 10 events on the user's calendar.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("calendar", "v3", credentials=creds)
     
    # Call the Calendar API
    today = datetime.datetime.now(tz=datetime.timezone.utc).replace(hour = 0, minute = 0, second =0)
    xHr = 48
    afterXhr = today + datetime.timedelta(hours=xHr)

    today = today.isoformat()
    afterXhr = afterXhr.isoformat()

    print(today, afterXhr)

    print("Getting the upcoming events for the next ",xHr," hrs")
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=today,
            timeMax=afterXhr,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    events_result = (
        service.events()
        .list(
            calendarId="4349a07cc75de41880123696fc22ee4379a57509f673d4db9629138cb1aa28b5@group.calendar.google.com",
            timeMin=today,
            singleEvents=True,
            timeMax=afterXhr,
        )
        .execute()
    )

    events = events + (events_result.get("items", []))

    if not events:
      print("No upcoming events found.")
      return

    # returns the start and name of the next 10 events
    events.sort(key=lambda e: e["start"].get("dateTime", e["start"].get("date")))

    eventsWithTime = ""
    for event in events:
      start = event["start"].get("dateTime", event["start"].get("date"))
      end = event["end"].get("dateTime", event["end"].get("date"))
      eventsWithTime = eventsWithTime + f"{start} until {end} {event['summary']}\n"

    return(eventsWithTime)
  
  except HttpError as error:
    print(f"An error occurred: {error}")


def stocks():
    tickers = {
        "GOOG": "GOOG",
        "S&P500": "^GSPC",
        "USD/ILS": "ILS=X",
        "Nvidia": "NVDA",
    }

    histories = {
        name: yf.Ticker(symbol).history(period='3d', interval='30m', rounding=True)
        for name, symbol in tickers.items()
    }

    moves = {
        name: (history["Close"].iloc[-1] / history["Close"].iloc[0] - 1) * 100
        for name, history in histories.items()
    }

    prompt = "Prompt: Below are tickers I track with their % price change over the last 3 days. Since " \
            "this is accessed via API and billed per token, avoid unnecessary filler — no greetings, no " \
            "preamble, no closing remarks, no restating these instructions. But do not sacrifice depth " \
            "for the sake of brevity — the goal is efficient wording, not shallow content. Task: for " \
            "each ticker, give an information-dense explanation (up to 4 sentences) of what's driving " \
            "its recent movement — recent news, earnings, macro factors, sector trends, whatever is " \
            "most relevant(try focusing on today's movment). Use your own general knowledge to add relevant context or background if it " \
            "helps me understand the move better. Output format (plain text, no extra commentary): " \
            "[Ticker]: [explanation] — one line per ticker, in the order given, nothing else. Here are " \
            "the tickers:\n"
    prompt += "\n".join(f"{name}: {change_pct:+.2f}%" for name, change_pct in moves.items())

    interaction = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input=prompt
    )

    explanations = {}
    for line in interaction.output_text.strip().splitlines():
        if ":" in line:
            name, explanation = line.split(":", 1)
            explanations[name.strip()] = explanation.strip()

    return {
        name: {
            "history": histories[name],
            "change_pct": moves[name],
            "explanation": explanations.get(name, ""),
        }
        for name in tickers
    }

WEATHER_CODES = {
    0: ("☀️", "Clear sky"),
    1: ("🌤️", "Mostly clear"),
    2: ("⛅", "Partly cloudy"),
    3: ("☁️", "Overcast"),
    45: ("🌫️", "Fog"),
    48: ("🌫️", "Fog"),
    51: ("🌦️", "Light drizzle"),
    53: ("🌦️", "Drizzle"),
    55: ("🌧️", "Dense drizzle"),
    61: ("🌧️", "Light rain"),
    63: ("🌧️", "Rain"),
    65: ("🌧️", "Heavy rain"),
    71: ("🌨️", "Light snow"),
    73: ("🌨️", "Snow"),
    75: ("❄️", "Heavy snow"),
    80: ("🌦️", "Rain showers"),
    81: ("🌧️", "Rain showers"),
    82: ("⛈️", "Violent showers"),
    95: ("⛈️", "Thunderstorm"),
    96: ("⛈️", "Thunderstorm w/ hail"),
    99: ("⛈️", "Thunderstorm w/ hail"),
}

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
        "hourly": "temperature_2m,weather_code",
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
    hourly_weather_code = hourly.Variables(1).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
            end =  pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
            freq = pd.Timedelta(seconds = hourly.Interval()),
            inclusive = "left"
        ).tz_convert(response.Timezone().decode())
    }

    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["weather_code"] = hourly_weather_code

    hourly_dataframe = pd.DataFrame(data = hourly_data)

    for _, row in hourly_dataframe.iterrows():
        code = int(row["weather_code"])
        emoji, description = WEATHER_CODES.get(code, ("", f"Unknown code {code}"))
        print(f"{row['date']}: {row['temperature_2m']}°C {emoji} {description} (code {code})")

    return ("\nHourly data\n", hourly_dataframe)

# os.environ.get("GEMINI_API_KEY")

# url = "https://generativelanguage.googleapis.com/v1beta/interactions"
# h = {"x-goog-api-key": os.getenv("GEMINI_API_KEY"), 
#         "Content-Type": "application/json"}
# d = {"model": "gemini-3.5-flash-lite",
#         "input": "fun and intresting quantum mechanics fact with explaination"}

# answer = requests.post(url, headers=h, json=d)
# print(answer.json()) 




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
            "but these must be under one sentence each, just the core fact. Output format must follow " \
            "this exact structure, with no deviation and no extra commentary: for each of the 6 stories, " \
            "one line reading '<N>. TITLE: <title>' immediately followed by a line reading " \
            "'SUMMARY: <deeper summary>' (N starting at 1). After all 6, a line containing only 'ALSO:', " \
            "followed by one '- <one-line fact>' line per additional item. Example shape:\n" \
            "1. TITLE: Example headline\n" \
            "SUMMARY: Example deeper summary.\n" \
            "2. TITLE: Example headline two\n" \
            "SUMMARY: Example deeper summary two.\n" \
            "ALSO:\n" \
            "- Example one-line fact.\n" \
            "Here are the titles:"
    titles = ""

    
    sources = {"https://news.google.com/rss/search?q=site:reuters.com&hl=en-IL&gl=IL&ceid=IL:en": 4,
            "https://www.forbes.com/business/feed/": 5,
            "https://techcrunch.com/feed": 5,
            "https://www.marketwatch.com/rss/topstories": 5,
            "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml": 4,
            "https://www.ynet.co.il/Integration/StoryRss2.xml": 6}

    
    for url in sources:
        for entry in feedparser.parse(url).entries[0:sources[url]]:
            titles = titles + entry.title + "\n"

    print(prompt+titles)
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

print(calender())