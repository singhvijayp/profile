#!/usr/bin/env python3
"""
Pulls contribution / language data from the GitHub GraphQL API and writes
stats.svg, streak.svg, langs.svg, and year.svg to the repo root.

Usage:
    GITHUB_TOKEN=xxxx GITHUB_LOGIN=singhvijayp python3 scripts/generate_stats.py
    python3 scripts/generate_stats.py --demo      # writes demo/placeholder data, no network

Run on a schedule via .github/workflows/stats.yml, which commits only
what changed so the repo doesn't get a noisy commit every single day.
"""
import argparse
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from svg_builders import stat_card, streak_card, lang_bar, year_ramp

GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes {
        stargazerCount
        languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
  }
}
"""


def fetch_live(login: str, token: str) -> dict:
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{login}-profile-stats",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]


def compute_streaks(days: list) -> tuple:
    """days: list of {date, contributionCount} oldest -> newest."""
    counts = [d["contributionCount"] for d in days]
    longest = cur = 0
    for c in counts:
        if c > 0:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    # current streak = trailing run of active days up to the most recent day
    current = 0
    for c in reversed(counts):
        if c > 0:
            current += 1
        else:
            break
    return current, longest


def levels_from_counts(counts: list) -> list:
    if not counts:
        return []
    m = max(counts) or 1
    levels = []
    for c in counts:
        if c == 0:
            levels.append(0)
        elif c <= m * 0.33:
            levels.append(1)
        elif c <= m * 0.66:
            levels.append(2)
        else:
            levels.append(3)
    return levels


LANG_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a",
    "HTML": "#e34c26", "CSS": "#563d7c", "Go": "#00ADD8", "Rust": "#dea584",
    "Shell": "#89e051", "Java": "#b07219", "C++": "#f34b7d", "C": "#555555",
}


def build_from_user(user: dict, out_dir: str):
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    current, longest = compute_streaks(days)

    # languages, aggregated by byte size across public repos
    totals = {}
    stars = 0
    for repo in user["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]
    total_bytes = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:6]
    languages = [
        (name, size / total_bytes * 100, LANG_COLORS.get(name, "#8b949e"))
        for name, size in ranked
    ]

    stats = [
        ("Total Contributions (year)", cal["totalContributions"]),
        ("Commits", cc["totalCommitContributions"]),
        ("Pull Requests", cc["totalPullRequestContributions"]),
        ("Issues", cc["totalIssueContributions"]),
        ("Stars Earned", stars),
    ]

    write(out_dir, "stats.svg", stat_card("Stats", stats))
    write(out_dir, "streak.svg", streak_card(current, longest, cal["totalContributions"]))
    write(out_dir, "langs.svg", lang_bar(languages))
    write(out_dir, "year.svg", year_ramp(levels_from_counts(counts)))


def build_demo(out_dir: str):
    stats = [
        ("Total Contributions (year)", 1842),
        ("Commits", 1290),
        ("Pull Requests", 210),
        ("Issues", 96),
        ("Stars Earned", 134),
    ]
    languages = [
        ("Python", 42.0, LANG_COLORS["Python"]),
        ("TypeScript", 27.0, LANG_COLORS["TypeScript"]),
        ("JavaScript", 14.0, LANG_COLORS["JavaScript"]),
        ("Go", 9.0, LANG_COLORS["Go"]),
        ("Shell", 5.0, LANG_COLORS["Shell"]),
        ("HTML", 3.0, LANG_COLORS["HTML"]),
    ]
    import random
    random.seed(42)
    demo_counts = []
    for i in range(365):
        r = random.random()
        if r < 0.35:
            demo_counts.append(0)
        elif r < 0.7:
            demo_counts.append(random.randint(1, 3))
        elif r < 0.92:
            demo_counts.append(random.randint(4, 7))
        else:
            demo_counts.append(random.randint(8, 14))
    # force a trailing active streak so the demo streak card has a nonzero "current"
    for i in range(1, 13):
        demo_counts[-i] = random.randint(1, 5)

    write(out_dir, "stats.svg", stat_card("Stats", stats))
    write(out_dir, "streak.svg", streak_card(12, 47, 1842))
    write(out_dir, "langs.svg", lang_bar(languages))
    write(out_dir, "year.svg", year_ramp(levels_from_counts(demo_counts)))


def write(out_dir: str, name: str, content: str):
    path = os.path.join(out_dir, name)
    with open(path, "w") as f:
        f.write(content)
    print(f"wrote {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="write placeholder demo data, no network call")
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), ".."))
    args = parser.parse_args()

    if args.demo:
        build_demo(args.out)
        return

    login = os.environ.get("GITHUB_LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER")
    token = os.environ.get("GITHUB_TOKEN")
    if not login or not token:
        print("GITHUB_LOGIN and GITHUB_TOKEN must be set (or run with --demo).", file=sys.stderr)
        sys.exit(1)

    user = fetch_live(login, token)
    build_from_user(user, args.out)


if __name__ == "__main__":
    main()
