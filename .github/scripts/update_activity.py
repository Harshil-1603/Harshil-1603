#!/usr/bin/env python3
"""Render GitHub-owned activity cards and calendar from GitHub GraphQL.

The four overview numbers describe all-time PUBLIC activity. The calendar,
streak and active-day figures describe only the last rolling year.
"""
import datetime as dt
import html
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

LOGIN = os.environ.get("GH_LOGIN", "Harshil-1603")
TOKEN = os.environ["GH_TOKEN"]
QUERY = """
query($login: String!, $prs: String!, $merged: String!, $issues: String!) {
  user(login: $login) {
    repositories(first: 1, ownerAffiliations: OWNER, visibility: PUBLIC) {
      totalCount
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount contributionLevel }
        }
      }
    }
  }
  authoredPRs: search(query: $prs, type: ISSUE, first: 1) { issueCount }
  mergedPRs: search(query: $merged, type: ISSUE, first: 1) { issueCount }
  authoredIssues: search(query: $issues, type: ISSUE, first: 1) { issueCount }
}
"""

def esc(value):
    return html.escape(str(value), quote=True)


variables = {
    "login": LOGIN,
    "prs": f"is:pr author:{LOGIN}",
    "merged": f"is:pr is:merged author:{LOGIN}",
    "issues": f"is:issue author:{LOGIN}",
}
payload = json.dumps({"query": QUERY, "variables": variables}).encode("utf-8")
request = Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": "Bearer " + TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "github-profile-activity-builder",
    },
)
with urlopen(request, timeout=35) as response:
    result = json.load(response)
if result.get("errors"):
    raise RuntimeError("GraphQL errors: " + json.dumps(result["errors"]))
data = result["data"]
if not data.get("user"):
    raise ValueError(f"No GitHub user found for {LOGIN!r}")

calendar = data["user"]["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
days = [day for week in weeks for day in week["contributionDays"]]
counts = {dt.date.fromisoformat(day["date"]): day["contributionCount"] for day in days}
today = dt.datetime.now(dt.timezone.utc).date()
start_day = today if counts.get(today, 0) else today - dt.timedelta(days=1)
current_streak = 0
cursor = start_day
while counts.get(cursor, 0) > 0:
    current_streak += 1
    cursor -= dt.timedelta(days=1)

longest_streak = running = 0
for day in days:
    if day["contributionCount"]:
        running += 1
        longest_streak = max(longest_streak, running)
    else:
        running = 0

total = int(calendar["totalContributions"])
active_days = sum(day["contributionCount"] > 0 for day in days)
prs = int(data["authoredPRs"]["issueCount"])
merged_prs = int(data["mergedPRs"]["issueCount"])
issues = int(data["authoredIssues"]["issueCount"])
public_repos = int(data["user"]["repositories"]["totalCount"])
if merged_prs > prs:
    raise ValueError("Merged PR count cannot exceed opened PR count")

updated_at = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y · %H:%M UTC")
BG = "#0b1220"
PANEL = "#111e30"
BORDER = "#263a53"
TEXT = "#f0f6ff"
MUTED = "#94a9c0"
GREEN = "#62e7c7"
BLUE = "#99b9ff"
AMBER = "#f5be82"
LAVENDER = "#caa5ff"

def svg_begin(height, title):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-label="{esc(title)}">',
        '<defs>',
        '<linearGradient id="back" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0e1a2d"/><stop offset="1" stop-color="#0b1220"/></linearGradient>',
        '<linearGradient id="accent" x1="0" x2="1"><stop offset="0" stop-color="#62e7c7"/><stop offset="1" stop-color="#91b6ff"/></linearGradient>',
        '</defs>',
        '<style>',
        f'.heading{{font:700 20px Arial,Helvetica,sans-serif;fill:{TEXT}}}',
        f'.eyebrow{{font:700 12px Arial,Helvetica,sans-serif;letter-spacing:1.3px;fill:{MUTED}}}',
        f'.number{{font:700 34px Arial,Helvetica,sans-serif;fill:{TEXT}}}',
        f'.caption{{font:500 13px Arial,Helvetica,sans-serif;fill:{MUTED}}}',
        f'.month{{font:12px Arial,Helvetica,sans-serif;fill:{MUTED}}}',
        f'.foot{{font:11px Arial,Helvetica,sans-serif;fill:{MUTED}}}',
        '</style>',
        f'<rect x="1" y="1" width="998" height="{height-2}" rx="18" fill="url(#back)" stroke="{BORDER}"/>',
        '<rect x="22" y="22" width="5" height="18" rx="2" fill="url(#accent)"/>',
    ]

def card(x, y, width, height, value, label, accent):
    return [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" fill="{PANEL}" stroke="{BORDER}"/>',
        f'<rect x="{x+17}" y="{y+17}" width="6" height="6" rx="3" fill="{accent}"/>',
        f'<text x="{x+17}" y="{y+53}" class="number">{esc(f"{value:,}")}</text>',
        f'<text x="{x+17}" y="{y+77}" class="caption">{esc(label)}</text>',
    ]

# First image: explicit all-time, public counts. No third-party stats API.
stat_svg = svg_begin(184, f"{LOGIN} GitHub overview: {prs} opened PRs, {merged_prs} merged, {issues} issues, {public_repos} public repositories")
stat_svg += [
    '<text x="39" y="38" class="heading">GitHub at a glance</text>',
    '<text x="975" y="36" text-anchor="end" class="eyebrow">ALL-TIME / PUBLIC</text>',
]
overview = [
    (prs, "Pull requests opened", GREEN),
    (merged_prs, "Pull requests merged", BLUE),
    (issues, "Issues opened", AMBER),
    (public_repos, "Public repositories", LAVENDER),
]
for i, (value, label, accent) in enumerate(overview):
    stat_svg.extend(card(24 + 245*i, 59, 223, 100, value, label, accent))
stat_svg += ['</svg>']

# Second image: true day-of-week alignment, one color legend and a well-spaced grid.
activity_svg = svg_begin(412, f"{LOGIN} GitHub activity: {total} contributions in the last year, current streak {current_streak} days, longest streak {longest_streak} days in the last year")
activity_svg += [
    '<text x="39" y="38" class="heading">Contribution activity</text>',
    '<text x="975" y="36" class="eyebrow" text-anchor="end">ROLLING 12 MONTHS</text>',
]
summaries = [
    (total, "Contributions / year", GREEN),
    (current_streak, "Current streak / days", BLUE),
    (longest_streak, "Longest streak / year", AMBER),
    (active_days, "Active days / year", LAVENDER),
]
for i, (value, label, accent) in enumerate(summaries):
    activity_svg.extend(card(24 + 245*i, 59, 223, 100, value, label, accent))

activity_svg.extend([
    f'<rect x="24" y="177" width="952" height="186" rx="12" fill="{PANEL}" stroke="{BORDER}"/>',
    '<text x="41" y="200" class="eyebrow">DAILY CONTRIBUTIONS</text>',
    '<text x="961" y="200" text-anchor="end" class="month">Each square represents one day</text>',
    '<text x="48" y="252" class="month">Sun</text>',
    '<text x="48" y="284" class="month">Tue</text>',
    '<text x="48" y="316" class="month">Thu</text>',
])

# Square width 11 + gap 5 = 16. 53-week calendars fit in 1000px.
colors = {
    "NONE": "#1c2d42",
    "FIRST_QUARTILE": "#13564f",
    "SECOND_QUARTILE": "#17877a",
    "THIRD_QUARTILE": "#28b79e",
    "FOURTH_QUARTILE": "#72efc8",
}
last_month = None
for col, week in enumerate(weeks):
    for item in week["contributionDays"]:
        date = dt.date.fromisoformat(item["date"])
        weekday = (date.weekday() + 1) % 7  # GitHub weeks begin on Sunday.
        x, y = 91 + 16 * col, 240 + 16 * weekday
        fill = colors[item["contributionLevel"]]
        activity_svg.append(
            f'<rect x="{x}" y="{y}" width="12" height="12" rx="2.5" fill="{fill}">'
            f'<title>{esc(date.isoformat())}: {item["contributionCount"]} contributions</title></rect>'
        )
        key = (date.year, date.month)
        if key != last_month:
            if col > 0:  # The first partial month does not need a label.
                activity_svg.append(
                    f'<text x="{x}" y="228" class="month">{esc(date.strftime("%b"))}</text>'
                )
            last_month = key

activity_svg.append(f'<text x="28" y="392" class="foot">Refreshed {esc(updated_at)} · GitHub-reported contribution days</text>')
activity_svg.append('<text x="769" y="391" class="foot">Less</text>')
for i, fill in enumerate(colors.values()):
    activity_svg.append(
        f'<rect x="{802 + 19*i}" y="380" width="12" height="12" rx="2.5" fill="{fill}"/>'
    )
activity_svg.append('<text x="911" y="391" class="foot">More</text>')
activity_svg.append('</svg>')

out_dir = Path("assets")
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "github-metrics.svg").write_text("\n".join(stat_svg) + "\n", encoding="utf-8")
(out_dir / "contribution-dashboard.svg").write_text("\n".join(activity_svg) + "\n", encoding="utf-8")
print(f"{LOGIN}: {prs} PRs opened; {merged_prs} merged; {issues} issues; {public_repos} public repos")
print(f"Last year: {total} contributions; current streak {current_streak}; longest {longest_streak}; {active_days} active days")
