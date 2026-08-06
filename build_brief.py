"""
Builds the morning brief as an A4 PDF (2 pages, double-sided printable).

USE_SAMPLE_DATA = True lets you preview the design without hitting any
real APIs. Flip it to False once you're running this for real.

Output: briefs/<YYYY-MM-DD>/morning_brief.pdf. The HTML and chart PNGs used
to render the PDF are scratch files -- they're written next to it during
the build and deleted once the PDF exists.
"""

import os
import re
import shutil
import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from weasyprint import HTML

USE_SAMPLE_DATA = False

BRIEFS_DIR = "briefs"
STYLE_PATH = os.path.abspath("style.css")

today = datetime.date.today()
DAY_DIR = os.path.join(BRIEFS_DIR, today.isoformat())
CHARTS_DIR = os.path.join(DAY_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)


# WeasyPrint has no reliable support for color/bitmap emoji fonts: multi-codepoint
# pictographs with a VS16 selector (e.g. the old "🌤️") get rendered as a stray
# image detached from its inline position instead of the intended icon. These
# codepoints are plain (no VS16) and all fall inside DejaVu Sans, which renders
# them as normal monochrome glyphs in the correct place -- and the flatter look
# fits the brief's editorial style better than cartoon emoji anyway.
WEATHER_CODES = {
    0: ("☀", "Clear sky"), 1: ("☀", "Mostly clear"), 2: ("☁", "Partly cloudy"),
    3: ("☁", "Overcast"), 45: ("≈", "Fog"), 48: ("≈", "Fog"),
    51: ("☂", "Light drizzle"), 53: ("☂", "Drizzle"), 55: ("☂", "Dense drizzle"),
    61: ("☂", "Light rain"), 63: ("☂", "Rain"), 65: ("☂", "Heavy rain"),
    71: ("❄", "Light snow"), 73: ("❄", "Snow"), 75: ("❄", "Heavy snow"),
    80: ("☂", "Rain showers"), 81: ("☂", "Rain showers"), 82: ("⛈", "Violent showers"),
    95: ("⛈", "Thunderstorm"), 96: ("⛈", "Thunderstorm w/ hail"), 99: ("⛈", "Thunderstorm w/ hail"),
}


def md_bold(text):
    """Gemini sometimes returns **bold** markdown; render it as real bold."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


# ----------------------------------------------------------------------
# 1. GATHER DATA
# ----------------------------------------------------------------------

if USE_SAMPLE_DATA:
    import sample_data as data

    riddle_text = data.riddle_text
    concept_text = data.concept_text
    news_raw = data.news_raw
    weather_note, weather_df = data.weather()
    stock_data = data.stocks()
    calendar_text = data.calendar_text
else:
    import geminiAPItest

    riddle_text = geminiAPItest.riddle()
    concept_text = geminiAPItest.conceptOfDay()
    news_raw = geminiAPItest.news()
    weather_note, weather_df = geminiAPItest.weather()
    stock_data = geminiAPItest.stocks()
    calendar_text = geminiAPItest.calender()  # remember: add `return eventsWithTime` in calender()!


# ----------------------------------------------------------------------
# 2. PARSE NEWS TEXT
# ----------------------------------------------------------------------

def parse_news(raw_text):
    top_stories = []
    also_facts = []
    top_part, also_part = (raw_text.split("ALSO:", 1) + [""])[:2] if "ALSO:" in raw_text else (raw_text, "")

    blocks = re.split(r"\n?\d+\.\s*TITLE:", top_part)
    for block in blocks[1:]:
        parts = block.split("SUMMARY:", 1)
        title = parts[0].strip()
        summary = parts[1].strip() if len(parts) > 1 else ""
        top_stories.append((title, summary))

    for line in also_part.splitlines():
        line = line.strip("- \n")
        if line:
            also_facts.append(line)
    return top_stories, also_facts


top_stories, also_facts = parse_news(news_raw)
THUMB_COLORS = ["#5b8def", "#7fb8e0", "#8f9fdc", "#4fb2a3", "#e29b8f", "#a3a0e8"]


# ----------------------------------------------------------------------
# 3. PARSE CALENDAR TEXT ("start until end summary" per line)
# ----------------------------------------------------------------------

def parse_calendar(text):
    events = []
    if not text:
        return events
    for line in text.strip().splitlines():
        if " until " not in line:
            continue
        start, rest = line.split(" until ", 1)
        end, summary = rest.split(" ", 1)
        events.append((start.strip(), end.strip(), summary.strip()))
    return events


calendar_events = parse_calendar(calendar_text)


# ----------------------------------------------------------------------
# 4. CHARTS
# ----------------------------------------------------------------------

plt.rcParams.update({
    "font.family": "sans-serif",
    "axes.edgecolor": "#e4eaf2",
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "grid.color": "#f1f4f9",
    "grid.linewidth": 0.6,
})


def fmt_price(v):
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 100:
        return f"{v:,.1f}"
    return f"{v:,.2f}"


STOCK_AX_RECT = (0.03, 0.05, 0.94, 0.90)  # left, bottom, width, height (figure fractions)


def make_stock_chart(history, color, path):
    """Narrow sparkline sized for the ~17.5%-wide right-hand column. Marks the
    period's high/low so the caller can overlay price labels at those exact
    on-image spots (matplotlib can't be trusted to place small text cleanly
    inside a chart this size)."""
    closes = history["Close"].dropna()
    x = range(len(closes))
    y_min, y_max = float(closes.min()), float(closes.max())
    y_pad = (y_max - y_min) * 0.15 or 1

    ax_left, ax_bottom, ax_width, ax_height = STOCK_AX_RECT
    fig = plt.figure(figsize=(1.55, 0.6), dpi=220)
    ax = fig.add_axes([ax_left, ax_bottom, ax_width, ax_height])

    ax.plot(x, closes.values, color=color, linewidth=1.6,
             solid_capstyle="round", solid_joinstyle="round", zorder=2)
    ax.fill_between(x, closes.values, y_min - y_pad, color=color, alpha=0.10, zorder=1)
    ax.set_xlim(0, len(closes) - 1)
    ax.set_ylim(y_min - y_pad, y_max + y_pad)
    ax.axis("off")

    idx_hi = int(closes.values.argmax())
    idx_lo = int(closes.values.argmin())
    points = []
    for kind, i in (("hi", idx_hi), ("lo", idx_lo)):
        xv, yv = i, float(closes.values[i])
        ax.scatter([xv], [yv], s=14, color=color, zorder=3, edgecolors="#ffffff", linewidths=1.0)
        points.append({
            "kind": kind,
            "left": round((ax_left + (xv / max(len(closes) - 1, 1)) * ax_width) * 100, 2),
            "top": round((1 - (ax_bottom + (yv - (y_min - y_pad)) / ((y_max + y_pad) - (y_min - y_pad)) * ax_height)) * 100, 2),
            "value": fmt_price(yv),
        })

    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    plt.savefig(path)
    plt.close(fig)
    return points


stock_cards_html = ""
for name, info in stock_data.items():
    up = info["change_pct"] >= 0
    color = "#2f9e6f" if up else "#d2585c"
    change_class = "up" if up else "down"
    sign = "+" if up else ""
    img_filename = f"stock_{name.replace('/', '').replace(' ', '')}.png"
    hilo_points = make_stock_chart(info["history"], color, os.path.join(CHARTS_DIR, img_filename))
    stock_points_html = "".join(
        f'<div class="stock-point {p["kind"]}" style="left:{p["left"]}%; top:{p["top"]}%;">{p["value"]}</div>'
        for p in hilo_points
    )

    stock_cards_html += f"""
    <div class="stock-card">
        <div class="stock-left">
            <span class="stock-ticker">{name}</span>
            <div class="stock-explanation">{info['explanation']}</div>
        </div>
        <div class="stock-right">
            <span class="stock-change {change_class}">{sign}{info['change_pct']:.2f}%</span>
            <div class="stock-graph">
                <img src="charts/{img_filename}">
                {stock_points_html}
            </div>
        </div>
    </div>
    """

# ---- Weather: current reading + a temperature graph with labeled points ----

now = weather_df["date"].iloc[len(weather_df) // 2]  # sample data has no real "now"; real code should use pd.Timestamp.now(tz=...)
if not USE_SAMPLE_DATA:
    now = __import__("pandas").Timestamp.now(tz=weather_df["date"].dt.tz)

idx_now = (weather_df["date"] - now).abs().idxmin()
current_temp = round(float(weather_df.loc[idx_now, "temperature_2m"]), 1)
current_code = int(weather_df.loc[idx_now, "weather_code"])
current_emoji, current_label = WEATHER_CODES.get(current_code, ("?", "Unknown"))
day_high = round(float(weather_df["temperature_2m"].max()))
day_low = round(float(weather_df["temperature_2m"].min()))

# Plot the day's temperature curve and hand back the on-image fraction (left/top
# as %) of each labeled hour, so the emoji/temp/time can be overlaid in HTML at
# the exact spot the dot was drawn — matplotlib can't render color emoji reliably.
WEATHER_COLOR = "#2f8f9a"
AX_RECT = (0.03, 0.16, 0.94, 0.76)  # left, bottom, width, height (figure fractions)


def make_weather_chart(df, hours, path, color=WEATHER_COLOR):
    d = df.copy()
    d["hour"] = d["date"].dt.hour + d["date"].dt.minute / 60
    x_min, x_max = 0, 23
    y_min = float(d["temperature_2m"].min()) - 2
    y_max = float(d["temperature_2m"].max()) + 4  # headroom for the labels above the line

    ax_left, ax_bottom, ax_width, ax_height = AX_RECT
    fig = plt.figure(figsize=(2.55, 1.5), dpi=200)
    ax = fig.add_axes([ax_left, ax_bottom, ax_width, ax_height])

    ax.plot(d["hour"], d["temperature_2m"], color=color, linewidth=2,
             solid_capstyle="round", solid_joinstyle="round", zorder=2)
    ax.fill_between(d["hour"], d["temperature_2m"], y_min, color=color, alpha=0.10, zorder=1)

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_yticks([])
    ax.set_xticks(range(0, 24, 6))
    ax.set_xticklabels([f"{h:02d}h" for h in range(0, 24, 6)], fontsize=5, color="#9aa7b6")
    ax.tick_params(axis="x", length=0, pad=2)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#e4eaf2")
    ax.grid(axis="y", color="#f1f4f9", linewidth=0.6)

    points = []
    for h in hours:
        i = (d["hour"] - h).abs().idxmin()
        row = d.loc[i]
        x, y = float(row["hour"]), float(row["temperature_2m"])
        ax.scatter([x], [y], s=22, color=color, zorder=3, edgecolors="#fbfcfe", linewidths=1.2)
        emoji, _ = WEATHER_CODES.get(int(row["weather_code"]), ("?", ""))
        points.append({
            "left": round((ax_left + (x - x_min) / (x_max - x_min) * ax_width) * 100, 2),
            "top": round((1 - (ax_bottom + (y - y_min) / (y_max - y_min) * ax_height)) * 100, 2),
            "hour": int(round(x)),
            "temp": round(y),
            "emoji": emoji,
        })

    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    plt.savefig(path)
    plt.close(fig)
    return points


target_hours = [8, 11, 14, 17, 20, 22]
weather_chart_filename = "weather_chart.png"
weather_points = make_weather_chart(weather_df, target_hours, os.path.join(CHARTS_DIR, weather_chart_filename))

points_html = "".join(f"""
<div class="weather-point" style="left:{p['left']}%; top:{p['top']}%;">
    <span class="wp-emoji">{p['emoji']}</span>
    <span class="wp-temp">{p['temp']}°</span>
    <span class="wp-time">{p['hour']:02d}:00</span>
</div>
""" for p in weather_points)


# ----------------------------------------------------------------------
# 5. NEWS + FACTS HTML
# ----------------------------------------------------------------------

story_col_html = ["", ""]
split = (len(top_stories) + 1) // 2  # left column gets the extra story when the count is odd
for i, (title, summary) in enumerate(top_stories):
    color = THUMB_COLORS[i % len(THUMB_COLORS)]
    initial = title.strip()[0].upper() if title.strip() else "?"
    col = 0 if i < split else 1
    story_col_html[col] += f"""
    <div class="story">
        <div class="story-thumb" style="background:{color};">{initial}</div>
        <div class="story-body">
            <h3>{title}</h3>
            <p>{summary}</p>
        </div>
    </div>
    """

facts_html = ""
if also_facts:
    facts_html = '<ul class="fact-list">\n' + "".join(f"<li>{fact}</li>\n" for fact in also_facts) + "</ul>"

cal_html = ""
if calendar_events:
    days = {}  # date -> [(time_str, summary), ...], insertion order = event order
    for start, end, summary in calendar_events:
        if "T" in start:
            dt = datetime.datetime.fromisoformat(start)
            date_key = dt.date()
            t = dt.strftime("%H:%M")
        else:
            date_key = datetime.date.fromisoformat(start)  # all-day event: date only, no time
            t = "All day"
        days.setdefault(date_key, []).append((t, summary))

    for date_key in sorted(days):
        if date_key == today:
            label = "Today"
        elif date_key == today + datetime.timedelta(days=1):
            label = "Tomorrow"
        else:
            label = date_key.strftime("%A")
        cal_html += f'<div class="cal-day-heading">{label} &middot; {date_key.strftime("%b %d")}</div>\n'
        for t, summary in days[date_key]:
            cal_html += f'<div class="cal-event"><div class="cal-time">{t}</div><div>{summary}</div></div>\n'
else:
    cal_html = '<div class="cal-empty">Nothing on the calendar — clear day.</div>'

gen_dt = datetime.datetime.now()
today_str = today.strftime("%A, %B %d, %Y")
subline_str = f"{today_str} &middot; {gen_dt.strftime('%H:%M')}"


# ----------------------------------------------------------------------
# 6. FULL HTML
# ----------------------------------------------------------------------

html_doc = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="file://{STYLE_PATH}">
</head>
<body>

<div class="masthead">
    <div class="title">The Morning Brief</div>
    <div class="subline">{subline_str}</div>
</div>

<div class="mind-strip">
    <div class="mind-box">
        <div class="heading">Riddle of the Day</div>
        <p>{md_bold(riddle_text)}</p>
    </div>
    <div class="mind-box">
        <div class="heading">Worth Knowing</div>
        <p>{md_bold(concept_text)}</p>
    </div>
</div>

<div class="section-label label-news">Top Stories</div>
<div class="story-grid">
    <div class="story-col">{story_col_html[0]}</div>
    <div class="story-col">{story_col_html[1]}</div>
</div>
{facts_html}

<div class="brief-row">
    <div class="col">
        <div class="weather-box">
            <div class="section-label label-weather">Weather</div>
            <div class="weather-now">
                <span class="weather-emoji">{current_emoji}</span>
                <span class="weather-temp">{current_temp}°C</span>
            </div>
            <div class="weather-meta">{current_label} &middot; High <b>{day_high}°</b> &middot; Low <b>{day_low}°</b></div>
            <div class="weather-graph">
                <img src="charts/{weather_chart_filename}">
                {points_html}
            </div>
        </div>
    </div>
    <div class="col">
        <div class="calendar-box">
            <div class="section-label label-calendar">Today &amp; Tomorrow</div>
            {cal_html}
        </div>
    </div>
</div>

<hr class="hairline">

<div class="markets-block">
    <div class="section-label label-news">Markets</div>
    {stock_cards_html}

    <div class="section-label label-mind">Top 3 Priorities Today</div>
    <div class="priority-list">
        <div class="priority-line"><span class="priority-num">1</span><span class="priority-rule"></span></div>
        <div class="priority-line"><span class="priority-num">2</span><span class="priority-rule"></span></div>
        <div class="priority-line"><span class="priority-num">3</span><span class="priority-rule"></span></div>
        <div class="footer-note">Generated {gen_dt.strftime("%Y-%m-%d %H:%M")}</div>
    </div>
</div>

</body>
</html>
"""

html_path = os.path.join(DAY_DIR, "brief.html")
pdf_path = os.path.join(DAY_DIR, "morning_brief.pdf")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_doc)

HTML(html_path).write_pdf(pdf_path)

# The HTML and chart PNGs only exist to feed WeasyPrint -- the PDF has
# everything baked in, so there's no reason to keep them around.
os.remove(html_path)
shutil.rmtree(CHARTS_DIR)

print(f"Done -> {pdf_path}")
