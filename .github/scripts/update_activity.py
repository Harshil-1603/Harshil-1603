#!/usr/bin/env python3
"""Render a profile activity dashboard using GitHub's contribution and PR APIs.

Use PROFILE_STATS_TOKEN (repository Actions secret) for private-repository
visibility. Without it, GITHUB_TOKEN may only see public contributions.
"""
import datetime as dt
import html
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LOGIN = os.environ.get("GH_LOGIN", "Harshil-1603")
TOKEN = os.environ["GH_TOKEN"]
API = "https://api.github.com"
GRAPHQL = """
query ($login: String!) {
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

def get_json(url, payload=None):
    headers = {
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/vnd.github+json",
        "User-Agent": "Harshil-profile-activity",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(payload).encode("utf-8")
    with urlopen(Request(url, data=payload, headers=headers), timeout=35) as response:
        return json.load(response)

response = get_json(API + "/graphql", {"query": GRAPHQL, "variables": {"login": LOGIN}})
if response.get("errors"):
    raise RuntimeError("GitHub GraphQL failure: " + str(response["errors"]))
calendar = response["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
days = [entry for week in weeks for entry in week["contributionDays"]]
daily = {dt.date.fromisoformat(entry["date"]): int(entry["contributionCount"]) for entry in days}

def search_count(extra=""):
    q = "author:" + LOGIN + " is:pr" + ((" " + extra) if extra else "")
    url = API + "/search/issues?" + urlencode({"q": q, "per_page": "1"})
    response = get_json(url)
    if response.get("incomplete_results"):
        raise RuntimeError("GitHub search returned incomplete results for " + q)
    return int(response["total_count"])

prs_created = search_count()
prs_merged = search_count("is:merged")
prs_open = search_count("is:open")
if prs_merged + prs_open > prs_created:
    raise RuntimeError("PR totals are inconsistent; refusing to publish a misleading dashboard")

today = dt.datetime.now(dt.timezone.utc).date()
last_active = today if daily.get(today, 0) else today - dt.timedelta(days=1)
current = 0
date = last_active
while daily.get(date, 0):
    current += 1
    date -= dt.timedelta(days=1)

longest = running = 0
for entry in days:
    if int(entry["contributionCount"]):
        running += 1
        longest = max(longest, running)
    else:
        running = 0

total = int(calendar["totalContributions"])
last_sync = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y · %H:%M UTC")
esc = lambda s: html.escape(str(s), quote=True)

# Dark indigo / emerald / cyan palette, using accessible contrast and an even grid.
colors = {
    "NONE": "#172438",
    "FIRST_QUARTILE": "#155e53",
    "SECOND_QUARTILE": "#0d9488",
    "THIRD_QUARTILE": "#2dd4bf",
    "FOURTH_QUARTILE": "#86efac",
}
parts = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="1060" height="570" viewBox="0 0 1060 570" role="img" '
    'aria-label="GitHub activity: contribution calendar, pull request totals, and streaks">',
    '<defs>',
    '<linearGradient id="background" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1020"/>'
    '<stop offset="1" stop-color="#102238"/></linearGradient>',
    '<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2dd4bf"/>'
    '<stop offset=".52" stop-color="#86efac"/><stop offset="1" stop-color="#818cf8"/></linearGradient>',
    '</defs>',
    '<style>'
    '.eyebrow{font:700 12px Arial,sans-serif;letter-spacing:2px;fill:#5eead4}'
    '.heading{font:700 30px Arial,sans-serif;fill:#f1f5f9}'
    '.muted{font:13px Arial,sans-serif;fill:#9baec3}'
    '.metric{font:700 32px Arial,sans-serif}'
    '.metric-label{font:600 13px Arial,sans-serif;fill:#dce8f4}'
    '.metric-note{font:11px Arial,sans-serif;fill:#91a4ba}'
    '.chart-head{font:700 13px Arial,sans-serif;letter-spacing:1.2px;fill:#edf5ff}'
    '.axis{font:12px Arial,sans-serif;fill:#a3b4c8}'
    '.foot{font:11px Arial,sans-serif;fill:#889eb4}'
    '</style>',
    '<rect x="1" y="1" width="1058" height="568" rx="20" fill="url(#background)" stroke="#263b52"/>',
    '<rect x="28" y="24" width="49" height="4" rx="2" fill="url(#accent)"/>',
    '<text class="eyebrow" x="88" y="33">GITHUB / CONTRIBUTION SIGNAL</text>',
    '<text class="heading" x="28" y="76">Developer activity</text>',
    '<text class="muted" x="1030" y="67" text-anchor="end">@' + esc(LOGIN) + '</text>',
]

stats = [
    ("Contributions", format(total, ","), "GitHub calendar · past year", "#86efac"),
    ("Pull requests", format(prs_created, ","), "Created · accessible repos", "#7dd3fc"),
    ("Merged PRs", format(prs_merged, ","), "Merged · accessible repos", "#c4b5fd"),
    ("Current streak", str(current) + "d", "Today or yesterday · UTC", "#fcd34d"),
    ("Longest streak", str(longest) + "d", "Longest in the past year", "#a5b4fc"),
    ("Open PRs", format(prs_open, ","), "Currently open", "#5eead4"),
]
for index, (name, value, note, color) in enumerate(stats):
    col = index % 3
    row = index // 3
    x, y = 28 + col * 342, 98 + row * 102
    parts.extend([
        f'<rect x="{x}" y="{y}" width="320" height="92" rx="14" fill="#111f31" stroke="#2b4057"/>',
        f'<rect x="{x + 14}" y="{y + 15}" width="4" height="20" rx="2" fill="{color}"/>',
        f'<text x="{x + 29}" y="{y + 28}" class="metric-label">{esc(name)}</text>',
        f'<text x="{x + 17}" y="{y + 66}" class="metric" fill="{color}">{esc(value)}</text>',
        f'<text x="{x + 127}" y="{y + 66}" class="metric-note">{esc(note)}</text>',
    ])

parts.extend([
    '<rect x="28" y="310" width="1004" height="229" rx="15" fill="#0c1727" stroke="#2b4057"/>',
    '<text x="48" y="340" class="chart-head">CONTRIBUTION CALENDAR</text>',
    '<text x="1012" y="340" class="axis" text-anchor="end">Last 12 months · Sunday–Saturday</text>',
])
for weekday, label in [(0, "Sun"), (2, "Tue"), (4, "Thu"), (6, "Sat")]:
    parts.append(f'<text x="57" y="{393 + weekday * 16}" class="axis">{label}</text>')

month_labels = set()
for column, week in enumerate(weeks):
    x = 127 + column * 16
    for entry in week["contributionDays"]:
        date = dt.date.fromisoformat(entry["date"])
        weekday = (date.weekday() + 1) % 7
        y = 382 + weekday * 16
        level = entry["contributionLevel"]
        count = int(entry["contributionCount"])
        parts.append(
            f'<rect x="{x}" y="{y}" width="12" height="12" rx="3" fill="{colors[level]}">'
            f'<title>{date.isoformat()}: {count} contributions</title></rect>'
        )
        month = (date.year, date.month)
        if date.day <= 7 and month not in month_labels:
            month_labels.add(month)
            parts.append(f'<text x="{x}" y="372" class="axis">{esc(date.strftime("%b"))}</text>')

parts.extend([
    '<text x="48" y="518" class="foot">Includes contributions visible to this workflow token</text>',
    '<text x="831" y="518" class="axis">Less</text>',
])
for index, color in enumerate(colors.values()):
    parts.append(f'<rect x="{863 + index * 22}" y="507" width="14" height="14" rx="3" fill="{color}"/>')
parts.extend([
    '<text x="981" y="518" class="axis">More</text>',
    '<text x="28" y="559" class="foot">Data: GitHub GraphQL + Search API</text>',
    '<text x="1030" y="559" class="foot" text-anchor="end">Refreshed ' + esc(last_sync) + '</text>',
    '</svg>',
])
target = Path("assets/contribution-dashboard.svg")
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text("\n".join(parts) + "\n", encoding="utf-8")
print(f"Updated {target}: {total} contributions; {prs_created} PRs; {prs_merged} merged; {prs_open} open; streak {current} days")
