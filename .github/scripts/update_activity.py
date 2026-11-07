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
TOKEN = os.environ.get("GH_TOKEN", "")
API = "https://api.github.com"
GRAPHQL = """
query ($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, visibility: PUBLIC) {
      totalCount
      nodes { stargazerCount }
    }
    contributionsCollection {
      totalCommitContributions
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

def render_dashboard(metrics, weeks, last_sync, login=LOGIN):
    """Render the same verified metrics in a compact, neutral dark layout."""
    esc = lambda value: html.escape(str(value), quote=True)
    colors = {
        "NONE": "#1c222b",
        "FIRST_QUARTILE": "#164b43",
        "SECOND_QUARTILE": "#217c68",
        "THIRD_QUARTILE": "#36b394",
        "FOURTH_QUARTILE": "#71e3bd",
    }
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1060" height="616" viewBox="0 0 1060 616" role="img" aria-labelledby="title description" font-family="Arial, Helvetica, sans-serif">',
        '<title id="title">GitHub activity for @' + esc(login) + '</title>',
        '<desc id="description">Contributions and counted commits over the past year; all-time visible pull requests and issues; public repositories, stars, streaks, and a daily contribution calendar.</desc>',
        '<rect x="1" y="1" width="1058" height="614" rx="22" fill="#0d1117" stroke="#30363d"/>',
        '<circle cx="38" cy="36" r="4" fill="#71e3bd"/>',
        '<text x="52" y="41" font-size="12" font-weight="700" letter-spacing="1.6" fill="#a5b1bf">GITHUB ACTIVITY</text>',
        '<text x="1028" y="41" text-anchor="end" font-size="13" fill="#a5b1bf">@' + esc(login) + '</text>',
        '<text x="32" y="87" font-size="30" font-weight="700" letter-spacing="-.6" fill="#ffffff">Building, one contribution at a time.</text>',
    ]
    primary = [
        ("Contributions", "Past 12 months"),
        ("Counted commits", "Past 12 months"),
        ("PRs merged", "All-time visible"),
        ("PRs opened", "All-time visible"),
    ]
    for index, (name, note) in enumerate(primary):
        x = 32 + index * 253
        parts.extend([
            f'<rect x="{x}" y="112" width="237" height="122" rx="12" fill="#161b22" stroke="#30363d"/>',
            f'<text x="{x + 18}" y="139" font-size="14" fill="#c9d1d9">{esc(name)}</text>',
            f'<text x="{x + 18}" y="184" font-size="40" font-weight="700" letter-spacing="-1" fill="#ffffff">{esc(metrics[name])}</text>',
            f'<text x="{x + 18}" y="215" font-size="12" fill="#a5b1bf">{esc(note)}</text>',
        ])
    secondary = ["Open PRs", "Public repos", "Stars received", "Issues opened", "Current streak", "Longest streak"]
    for index, name in enumerate(secondary):
        x = 32 + index * 169
        if index:
            parts.append(f'<path d="M{x - 16} 258v47" stroke="#30363d"/>')
        parts.extend([
            f'<text x="{x}" y="271" font-size="13" fill="#a5b1bf">{esc(name)}</text>',
            f'<text x="{x}" y="302" font-size="25" font-weight="700" fill="#ffffff">{esc(metrics[name])}</text>',
        ])
    parts.extend([
        '<path d="M32 328h996" stroke="#30363d"/>',
        '<text x="32" y="359" font-size="16" font-weight="700" fill="#ffffff">Contribution calendar</text>',
        '<text x="1028" y="359" text-anchor="end" font-size="12" fill="#a5b1bf">Past 12 months</text>',
    ])
    for weekday, label in [(0, "Sun"), (2, "Tue"), (4, "Thu"), (6, "Sat")]:
        parts.append(f'<text x="32" y="{410 + weekday * 18}" font-size="12" fill="#a5b1bf">{label}</text>')
    # GitHub can return 53 or 54 partial weeks. Fit both without clipping.
    pitch = min(18, 948 / max(len(weeks), 1))
    cell = min(14, pitch - 4)
    previous_month = None
    for column, week in enumerate(weeks):
        x = 80 + column * pitch
        for entry in week["contributionDays"]:
            date = dt.date.fromisoformat(entry["date"])
            weekday = (date.weekday() + 1) % 7
            y = 398 + weekday * 18
            count = int(entry["contributionCount"])
            parts.append(
                f'<rect x="{x:.2f}" y="{y}" width="{cell:.2f}" height="14" rx="3" fill="{colors[entry["contributionLevel"]]}">'
                f'<title>{date.isoformat()}: {count} contributions</title></rect>'
            )
        if week["contributionDays"]:
            date = dt.date.fromisoformat(week["contributionDays"][0]["date"])
            month = (date.year, date.month)
            # Leave room at the right edge instead of squeezing in a partial month.
            if month != previous_month and x < 998:
                parts.append(f'<text x="{x:.2f}" y="384" font-size="12" fill="#a5b1bf">{date.strftime("%b")}</text>')
            previous_month = month
    parts.extend([
        '<text x="32" y="554" font-size="12" fill="#a5b1bf">Daily contributions · UTC</text>',
        '<text x="828" y="554" font-size="12" fill="#a5b1bf">Less</text>',
    ])
    for index, color in enumerate(colors.values()):
        parts.append(f'<rect x="{864 + index * 23}" y="542" width="14" height="14" rx="3" fill="{color}"/>')
    parts.extend([
        '<text x="987" y="554" font-size="12" fill="#a5b1bf">More</text>',
        '<path d="M32 574h996" stroke="#30363d"/>',
        '<text x="32" y="598" font-size="11" fill="#a5b1bf">GitHub API · Visible to the workflow token · Streaks within past year</text>',
        '<text x="1028" y="598" text-anchor="end" font-size="11" fill="#a5b1bf">Updated ' + esc(last_sync) + '</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"


def main():
    response = get_json(API + "/graphql", {"query": GRAPHQL, "variables": {"login": LOGIN}})
    if response.get("errors"):
        raise RuntimeError("GitHub GraphQL failure: " + str(response["errors"]))
    calendar = response["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    days = [entry for week in weeks for entry in week["contributionDays"]]
    daily = {dt.date.fromisoformat(entry["date"]): int(entry["contributionCount"]) for entry in days}

    def search_count(extra="", kind="pr"):
        q = "author:" + LOGIN + " is:" + kind + ((" " + extra) if extra else "")
        url = API + "/search/issues?" + urlencode({"q": q, "per_page": "1"})
        response = get_json(url)
        if response.get("incomplete_results"):
            raise RuntimeError("GitHub search returned incomplete results for " + q)
        return int(response["total_count"])

    prs_created = search_count()
    prs_merged = search_count("is:merged")
    prs_open = search_count("is:open")
    issues_opened = search_count(kind="issue")
    repositories = response["data"]["user"]["repositories"]
    public_repos = int(repositories["totalCount"])
    if len(repositories["nodes"]) != public_repos:
        raise RuntimeError("Repository count exceeds 100; refusing a partial stars total")
    stars_received = sum(int(repo["stargazerCount"]) for repo in repositories["nodes"])
    counted_commits = int(response["data"]["user"]["contributionsCollection"]["totalCommitContributions"])
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
    metrics = {
        "Contributions": format(total, ","),
        "Counted commits": format(counted_commits, ","),
        "PRs opened": format(prs_created, ","),
        "PRs merged": format(prs_merged, ","),
        "Open PRs": format(prs_open, ","),
        "Issues opened": format(issues_opened, ","),
        "Public repos": format(public_repos, ","),
        "Stars received": format(stars_received, ","),
        "Current streak": str(current) + "d",
        "Longest streak": str(longest) + "d",
    }
    target = Path("assets/contribution-dashboard.svg")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_dashboard(metrics, weeks, last_sync), encoding="utf-8")
    print(f"Updated {target}: {total} contributions; {counted_commits} counted commits; {prs_created} PRs; {prs_merged} merged; {prs_open} open; {issues_opened} issues; {public_repos} public repos; {stars_received} stars; streak {current} days")


if __name__ == "__main__":
    main()
