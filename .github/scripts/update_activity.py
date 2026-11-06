#!/usr/bin/env python3
"""Build a contribution dashboard from GitHub's own contribution calendar."""
import datetime as dt
import html
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

LOGIN = os.environ.get("GH_LOGIN", "Harshil-1603")
TOKEN = os.environ["GH_TOKEN"]
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount contributionLevel }
        }
      }
    }
  }
}
"""
payload = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
request = Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": "Bearer " + TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "profile-contribution-dashboard",
    },
)
with urlopen(request, timeout=30) as response:
    data = json.load(response)
if data.get("errors"):
    raise RuntimeError("GitHub GraphQL returned errors: " + str(data["errors"]))
calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
days = [day for week in weeks for day in week["contributionDays"]]
daily = {dt.date.fromisoformat(day["date"]): day["contributionCount"] for day in days}
today = dt.datetime.now(dt.timezone.utc).date()
last_day = today if daily.get(today, 0) else today - dt.timedelta(days=1)

current = 0
day = last_day
while daily.get(day, 0) > 0:
    current += 1
    day -= dt.timedelta(days=1)

longest = 0
running = 0
for day in days:
    if day["contributionCount"] > 0:
        running += 1
        longest = max(longest, running)
    else:
        running = 0

colors = {
    "NONE": "#161b22",
    "FIRST_QUARTILE": "#0e4429",
    "SECOND_QUARTILE": "#006d32",
    "THIRD_QUARTILE": "#26a641",
    "FOURTH_QUARTILE": "#39d353",
}
width = 940
height = 280
cells = []
labels = []
seen_months = set()
for col, week in enumerate(weeks):
    for item in week["contributionDays"]:
        date = dt.date.fromisoformat(item["date"])
        weekday = (date.weekday() + 1) % 7
        x = 40 + col * 16
        y = 143 + weekday * 16
        fill = colors[item["contributionLevel"]]
        cells.append(
            f'<rect x="{x}" y="{y}" width="12" height="12" rx="2" fill="{fill}">'
            f'<title>{date.isoformat()}: {item["contributionCount"]} contributions</title></rect>'
        )
        if date.day <= 7 and date.month not in seen_months:
            seen_months.add(date.month)
            labels.append(
                f'<text x="{x}" y="132" class="month">{html.escape(date.strftime("%b"))}</text>'
            )

total = calendar["totalContributions"]
updated = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y, %H:%M UTC")
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="GitHub contributions over the last year: {total} contributions, current streak {current} days, longest streak {longest} days within this year">
<style>
  .heading {{ font: 600 20px Arial,sans-serif; fill: #f0f6fc }}
  .number {{ font: 700 31px Arial,sans-serif; fill: #39d353 }}
  .label {{ font: 13px Arial,sans-serif; fill: #8b949e }}
  .month {{ font: 12px Arial,sans-serif; fill: #8b949e }}
  .footer {{ font: 11px Arial,sans-serif; fill: #8b949e }}
</style>
<rect width="940" height="280" rx="14" fill="#0d1117" stroke="#30363d" />
<text x="25" y="32" class="heading">Contribution activity</text>
<text x="25" y="66" class="number">{total:,}</text>
<text x="25" y="84" class="label">Contributions in the past year</text>
<text x="360" y="66" class="number">{current}</text>
<text x="360" y="84" class="label">Current streak (days)</text>
<text x="660" y="66" class="number">{longest}</text>
<text x="660" y="84" class="label">Longest streak in past year (days)</text>
<text x="25" y="160" class="month">Sun</text>
<text x="25" y="192" class="month">Tue</text>
<text x="25" y="224" class="month">Thu</text>
{''.join(labels)}
{''.join(cells)}
<text x="25" y="268" class="footer">GitHub contribution calendar · refreshed {html.escape(updated)} · streak based on UTC dates · private contributions depend on API visibility</text>
</svg>"""
target = Path("assets/contribution-dashboard.svg")
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(svg, encoding="utf-8")
print(f"Generated {target}: {total} contributions; streak {current}; longest {longest}")
